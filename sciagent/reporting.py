"""Generate run reports and placeholder visuals."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import List

from .diff_engine import DiffResult
from .models import RunRecord

_PLACEHOLDER_IMG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+ju0R4QAAAABJRU5ErkJggg=="
)


class ReportGenerator:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir

    def _render_current_config(self, record: RunRecord) -> str:
        """渲染当前配置信息"""
        lines = []
        
        # 命令行参数
        if record.config_values and "_cmd_params" in record.config_values:
            cmd_params = record.config_values["_cmd_params"]
            if isinstance(cmd_params, dict) and cmd_params:
                lines.append("### Command Parameters")
                lines.append("| Parameter | Value |")
                lines.append("| --- | --- |")
                for key, value in cmd_params.items():
                    lines.append(f"| `{key}` | {value} |")
                lines.append("")
        
        # Metadata
        if record.metadata:
            lines.append("### Metadata")
            lines.append("| Key | Value |")
            lines.append("| --- | --- |")
            for key, value in record.metadata.items():
                lines.append(f"| `{key}` | {value} |")
            lines.append("")
        
        # 配置文件内容（排除 _cmd_params）
        config_items = {k: v for k, v in record.config_values.items() if k != "_cmd_params"} if record.config_values else {}
        if config_items:
            lines.append("### Config Files")
            lines.append("| Key | Value |")
            lines.append("| --- | --- |")
            for key, value in list(config_items.items())[:20]:  # 限制显示前20个
                lines.append(f"| `{key}` | {value} |")
            if len(config_items) > 20:
                lines.append(f"| ... | *{len(config_items) - 20} more items* |")
            lines.append("")
        
        return "\n".join(lines) if lines else "*No configuration data*"

    def generate(self, record: RunRecord, diff: DiffResult) -> None:
        suggestions = _suggestions(record, diff)
        record.suggestions = suggestions
        report_path = self.run_dir / "report.md"
        report_path.write_text(self._render_markdown(record, diff, suggestions))
        curve_path = self.run_dir / "curves.png"
        curve_path.write_bytes(_PLACEHOLDER_IMG)
        record.artifact_paths["report"] = str(report_path)
        record.artifact_paths["curves"] = str(curve_path)

    def _render_markdown(self, record: RunRecord, diff: DiffResult, suggestions: List[str]) -> str:
        # 获取参考运行记录（用于对比）
        ref_record = diff.reference_record if hasattr(diff, 'reference_record') else None
        
        blocks = [
            f"# SciAgent Report — {record.name or record.run_id}",
            f"*Status*: **{record.status}**  |  *Fingerprint*: `{record.fingerprint}`",
            "## Command",
            f"```\n{record.command}\n```",
            "## Metrics",
            _render_metrics(record, reference_record=ref_record),
        ]
        
        # 添加当前配置信息（如果有）
        if record.config_values or record.metadata:
            blocks.append("## Configuration")
            blocks.append(self._render_current_config(record))
        
        blocks.extend([
            "## Config Diff",
            _render_config_diff(diff),
            "## Suggestions",
            "\n".join(f"- {item}" for item in suggestions) or "- No suggestions",
        ])
        if diff.metric_delta:
            metric = diff.metric_delta
            blocks.insert(
                4,
                "\n".join(
                    [
                        "## Primary Metric",
                        f"Reference ({diff.reference_type or 'n/a'}): {metric['reference']}",
                        f"Current: {metric['current']} (Δ {metric['delta']:+.4f})",
                    ]
                ),
            )
        return "\n\n".join(blocks)


def _render_metrics(record: RunRecord, reference_record: Optional[RunRecord] = None) -> str:
    """渲染 Metrics 部分，如果有参考运行则显示对比"""
    if not record.metrics:
        # 尝试显示命令行参数作为替代
        if record.config_values and "_cmd_params" in record.config_values:
            lines = ["*No metrics yet. Command parameters captured:*\n"]
            lines.append("| Parameter | Value |")
            lines.append("| --- | --- |")
            cmd_params = record.config_values["_cmd_params"]
            if isinstance(cmd_params, dict):
                for key, value in cmd_params.items():
                    lines.append(f"| {key} | {value} |")
                lines.append("\n💡 *Metrics will appear after your script writes `metrics.json`*")
                return "\n".join(lines)
        return "No metrics yet. Your script can write metrics to `metrics.json` for automatic tracking."
    
    # 如果有参考运行，显示对比
    if reference_record and reference_record.metrics:
        lines = ["| Metric | Current | Reference | Change |", "| --- | --- | --- | --- |"]
        ref_metrics = reference_record.metrics
        
        for key, value in record.metrics.items():
            current_val = value
            ref_val = ref_metrics.get(key)
            
            # 格式化当前值
            if isinstance(current_val, (int, float)):
                current_str = f"{current_val:.6g}"
            else:
                current_str = str(current_val)
            
            # 如果有参考值，计算差异
            if ref_val is not None and isinstance(current_val, (int, float)) and isinstance(ref_val, (int, float)):
                ref_str = f"{ref_val:.6g}"
                delta = current_val - ref_val
                
                # 格式化变化
                if abs(delta) < 0.000001:
                    change_str = "—"
                else:
                    sign = "+" if delta > 0 else ""
                    change_str = f"{sign}{delta:.6g}"
                    
                    # 添加百分比（如果有意义）
                    if abs(ref_val) > 0.000001:
                        percent = (delta / abs(ref_val)) * 100
                        change_str += f" ({sign}{percent:.1f}%)"
                
                lines.append(f"| {key} | {current_str} | {ref_str} | {change_str} |")
            else:
                # 没有参考值或类型不匹配
                ref_str = str(ref_val) if ref_val is not None else "—"
                lines.append(f"| {key} | {current_str} | {ref_str} | — |")
        
        return "\n".join(lines)
    else:
        # 没有参考运行，只显示当前值
        lines = ["| Metric | Value |", "| --- | --- |"]
        for key, value in record.metrics.items():
            lines.append(f"| {key} | {value} |")
        return "\n".join(lines)


def _render_config_diff(diff: DiffResult) -> str:
    if not diff.config_differences:
        return "*No changes from previous run. Current configuration shown in metadata below.*"
    
    lines = []
    for entry in diff.config_differences[:15]:
        key = entry.key
        current = entry.current
        reference = entry.reference
        
        # 特殊处理 _tracked_params（展开显示）
        if key == "_tracked_params" and isinstance(current, dict) and isinstance(reference, dict):
            lines.append("**参数变化**：\n")
            # 获取所有参数的键
            all_keys = sorted(set(current.keys()) | set(reference.keys()))
            for param_key in all_keys:
                cur_val = current.get(param_key, "—")
                ref_val = reference.get(param_key, "—")
                if cur_val != ref_val:
                    lines.append(f"- **{param_key}**: `{ref_val}` → `{cur_val}`")
        else:
            # 其他配置项
            lines.append(f"- **{key}**: `{reference}` → `{current}`")
    
    if len(diff.config_differences) > 15:
        lines.append(f"\n*… 还有 {len(diff.config_differences) - 15} 项差异*")
    
    return "\n".join(lines) if lines else "*No changes*"


def _suggestions(record: RunRecord, diff: DiffResult) -> List[str]:
    items: List[str] = []
    if record.status != "succeeded":
        items.append(
            "Run finished abnormally. Check command.log for stack traces and consider lowering batch size if it was an OOM."
        )
    if diff.metric_delta:
        delta = diff.metric_delta["delta"]
        direction = "decreased" if delta < 0 else "increased"
        metric_name = diff.metric_delta["metric"]
        items.append(
            f"Primary metric {metric_name} {direction} by {abs(delta):.4f} vs {diff.reference_type or 'reference'} run. Revisit key config changes below."
        )
    if diff.config_differences:
        key_names = ", ".join(entry.key for entry in diff.config_differences[:3])
        items.append(
            f"Most divergent hyperparameters: {key_names}. Validate whether these were intentional before launching the next run."
        )
    if not items:
        items.append(
            "Fingerprint unchanged and metrics steady. Consider exploring new configs or enabling advanced snapshot hooks for richer insights."
        )
    return items[: record.suggestion_count]
