"""RunGuardian orchestration layer."""

from __future__ import annotations

import json
import os
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .config_loader import ConfigSource, flatten_mapping
from .diff_engine import diff_against_history
from .environment import collect_environment_snapshot
from .fingerprint import build_fingerprint
from .history import RunHistory
from .models import RunRecord, RunSpec
from .reporting import ReportGenerator
from .snapshots import SnapshotManager
from .param_parser import parse_command_params, detect_config_files, extract_python_args


class RunGuardian:
    def __init__(self, spec: RunSpec):
        self.spec = spec
        self.state_dir = spec.state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = self._build_run_id()
        self.run_dir = self.state_dir / "runs" / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.run_dir / "command.log"
        self.record_path = self.run_dir / "run_record.json"
        self.history = RunHistory(self.state_dir / "history.json")
        self.snapshot_manager = SnapshotManager(self.run_dir)
        self.reporter = ReportGenerator(self.run_dir)
        self.env_snapshot = collect_environment_snapshot(self.spec.workdir)
        self.config_values = self._flatten_configs(spec.config_sources)
        
        # 自动解析命令行参数
        cmd_params = self._extract_command_params()
        if cmd_params:
            self.config_values.update({"_cmd_params": cmd_params})
        
        # 自动检测配置文件
        detected_configs = detect_config_files(spec.command, spec.workdir)
        if detected_configs:
            for config_file in detected_configs:
                if config_file not in [s.path for s in spec.config_sources]:
                    try:
                        from .config_loader import load_config_sources
                        additional_sources = load_config_sources([str(config_file)])
                        additional_configs = self._flatten_configs(additional_sources)
                        self.config_values.update(additional_configs)
                    except Exception:
                        pass  # 静默失败，不影响主流程
        
        # 注意：params.json 在脚本运行时生成，所以在 __init__ 阶段不读取
        # 改为在脚本运行结束后再读取（见 _aggregate_metrics 方法）
        
        self.record = RunRecord(
            run_id=self.run_id,
            name=self.spec.name,
            command=self.spec.command,
            workdir=self.spec.workdir,
            fingerprint=self._build_fingerprint(),
            env_snapshot=self.env_snapshot,
            metadata=self.spec.metadata,
            primary_metric=self.spec.primary_metric,
            suggestion_count=self.spec.suggestion_count,
            config_values=self.config_values,
        )
        self.record.log_path = self.log_path
        self._persist_record()

    def execute(self) -> int:
        exit_code: Optional[int] = None
        interrupted = False
        caught_exception: Optional[BaseException] = None
        try:
            exit_code = self._run_command()
            status = "succeeded" if exit_code == 0 else "failed"
            self.record.finish(status=status, exit_code=exit_code)
        except KeyboardInterrupt as exc:  # pragma: no cover - runtime path
            interrupted = True
            caught_exception = exc
            self.snapshot_manager.save_last("keyboard_interrupt")
            self.record.finish(status="interrupted", exit_code=None)
        except Exception as exc:  # pragma: no cover - runtime path
            caught_exception = exc
            self.snapshot_manager.save_last("exception", {"error": str(exc)})
            self.record.finish(status="failed", exit_code=None)
        finally:
            metrics = self._aggregate_metrics()
            if metrics:
                self.record.metrics.update(metrics)
                # 如果没有指定主要指标，自动检测
                if not self.record.primary_metric and metrics:
                    self.record.primary_metric = self._auto_detect_primary_metric(metrics)
            diff = diff_against_history(self.record, self.history)
            self.reporter.generate(self.record, diff)
            self._persist_record()
            self.history.append(self.record)
        if interrupted:
            raise KeyboardInterrupt from caught_exception
        if caught_exception and not interrupted:
            raise caught_exception
        return exit_code or 0

    def _run_command(self) -> int:
        process = subprocess.Popen(
            self.spec.command,
            cwd=self.spec.workdir,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            executable=os.environ.get("SHELL", "/bin/sh"),
        )
        assert process.stdout is not None
        try:
            with self.log_path.open("w") as log_file:
                for line in process.stdout:
                    print(line, end="")
                    log_file.write(line)
                    log_file.flush()
        except KeyboardInterrupt:
            _terminate_process(process)
            raise
        return process.wait()

    def _build_run_id(self) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        suffix = self.spec.name or "anon"
        safe_suffix = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in suffix)
        return f"{timestamp}_{safe_suffix}"

    def _build_fingerprint(self) -> str:
        return build_fingerprint(
            command=self.spec.command,
            metadata=self.spec.metadata,
            config_sources=self.spec.config_sources,
            env_snapshot=self.env_snapshot,
        )

    def _flatten_configs(self, sources: list[ConfigSource]) -> Dict[str, object]:
        flat: Dict[str, object] = {}
        for index, source in enumerate(sources):
            mapping = flatten_mapping(source.as_mapping, prefix=source.path.stem if source.as_mapping else "")
            if mapping:
                flat.update(mapping)
            else:
                flat[f"raw[{index}]({source.path.name})"] = source.raw_text
        return flat

    def _aggregate_metrics(self) -> Dict[str, float]:
        combined: Dict[str, float] = {}
        combined.update(self._safe_float_map(self.spec.metrics))
        
        # 确定 metrics 文件路径
        metrics_file_path = None
        
        if self.spec.metrics_file:
            # 用户指定的路径
            metrics_file_path = self.spec.metrics_file
            if not metrics_file_path.is_absolute():
                metrics_file_path = (self.spec.workdir / metrics_file_path).resolve()
        else:
            # 自动检测常见位置的 metrics 文件
            metrics_file_path = self._auto_detect_metrics_file()
        
        # 读取 metrics 文件
        if metrics_file_path and metrics_file_path.exists():
            try:
                data = json.loads(metrics_file_path.read_text())
                combined.update(self._safe_float_map(data))
            except Exception:
                pass  # 静默失败，不影响主流程
        
        # ✅ 在脚本运行结束后读取 params.json
        # 将参数加入 config_values（用于 Config Diff）
        params_file = self.spec.workdir / "params.json"
        if params_file.exists():
            try:
                with open(params_file, 'r') as f:
                    params_data = json.load(f)
                if params_data:
                    # 更新到 config_values（而不是 metrics）
                    self.config_values.update({"_tracked_params": params_data})
            except Exception:
                pass  # 静默失败
        
        return combined
    
    def _auto_detect_metrics_file(self) -> Optional[Path]:
        """
        自动检测 metrics 文件
        
        优先级：
        1. workdir/metrics.json
        2. workdir/outputs/metrics.json
        3. workdir/results/metrics.json
        4. workdir/logs/metrics.json
        5. 训练脚本所在目录/metrics.json
        
        Returns:
            找到的 metrics 文件路径，如果没找到返回 None
        """
        # 常见的 metrics 文件位置
        common_locations = [
            self.spec.workdir / "metrics.json",
            self.spec.workdir / "outputs" / "metrics.json",
            self.spec.workdir / "results" / "metrics.json",
            self.spec.workdir / "logs" / "metrics.json",
            self.spec.workdir / "output" / "metrics.json",
        ]
        
        # 尝试从命令中提取脚本路径
        try:
            # 提取 python xxx.py 中的脚本路径
            import re
            match = re.search(r'python\s+([^\s]+\.py)', self.spec.command)
            if match:
                script_path = Path(match.group(1))
                if not script_path.is_absolute():
                    script_path = self.spec.workdir / script_path
                # 脚本所在目录
                script_dir = script_path.parent
                common_locations.append(script_dir / "metrics.json")
        except Exception:
            pass
        
        # 按优先级查找
        for location in common_locations:
            if location.exists() and location.is_file():
                return location
        
        return None

    def _extract_command_params(self) -> Dict[str, object]:
        """从命令中提取参数"""
        try:
            # 提取 Python 命令的参数
            params = extract_python_args(self.spec.command)
            
            # 如果没有提取到，尝试通用解析
            if not params:
                params = parse_command_params(self.spec.command)
            
            return params
        except Exception:
            return {}
    
    @staticmethod
    def _safe_float_map(values: Optional[Dict[str, object]]) -> Dict[str, float]:
        output: Dict[str, float] = {}
        if not values:
            return output
        for key, value in values.items():
            try:
                output[key] = float(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
        return output
    
    @staticmethod
    def _auto_detect_primary_metric(metrics: Dict[str, float]) -> Optional[str]:
        """
        智能检测主要指标
        优先级：
        1. 常见的性能指标（accuracy, f1, precision, recall, auc等）
        2. 损失类指标（loss, error等）
        3. 其他指标（按字典序第一个）
        """
        if not metrics:
            return None
        
        metric_names = list(metrics.keys())
        
        # 优先级1：常见性能指标（越高越好）
        priority_metrics = ['accuracy', 'acc', 'f1_score', 'f1', 'precision', 'recall', 'auc', 'map', 'ap']
        for metric in priority_metrics:
            for name in metric_names:
                if metric in name.lower():
                    return name
        
        # 优先级2：损失类指标（越低越好）
        loss_metrics = ['loss', 'error', 'mse', 'mae', 'rmse']
        for metric in loss_metrics:
            for name in metric_names:
                if metric in name.lower():
                    return name
        
        # 优先级3：返回第一个
        return metric_names[0]

    def _persist_record(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.record_path.write_text(json.dumps(self.record.to_dict(), indent=2, sort_keys=True))


def _terminate_process(process: subprocess.Popen[str]) -> None:
    try:
        process.send_signal(signal.SIGINT)
    except Exception:
        pass
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()
