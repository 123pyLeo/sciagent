"""Simple config/metric diff helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .history import RunHistory
from .models import RunRecord


@dataclass
class ConfigDiffEntry:
    key: str
    current: object
    reference: object


@dataclass
class DiffResult:
    reference_run: Optional[Dict[str, object]]
    reference_type: Optional[str]
    config_differences: List[ConfigDiffEntry]
    metric_delta: Optional[Dict[str, float]]
    reference_record: Optional[RunRecord] = None  # 完整的参考记录对象，用于详细对比


def diff_against_history(record: RunRecord, history: RunHistory) -> DiffResult:
    reference = history.best(record.primary_metric) if record.primary_metric else None
    reference_type: Optional[str] = "best" if reference else None
    if reference is None:
        reference = history.latest()
        reference_type = "previous" if reference else None

    config_diffs: List[ConfigDiffEntry] = []
    metric_delta: Optional[Dict[str, float]] = None
    reference_record_obj: Optional[RunRecord] = None

    if reference:
        config_diffs = _diff_configs(record.config_values, reference.get("config_values") or {}, reference)
        metric_delta = _diff_metric(record, reference)
        
        # 尝试从字典构建 RunRecord 对象
        try:
            reference_record_obj = RunRecord(**reference)
        except Exception:
            pass  # 如果无法构建，保持为 None

    return DiffResult(
        reference_run=reference,
        reference_type=reference_type,
        config_differences=config_diffs,
        metric_delta=metric_delta,
        reference_record=reference_record_obj,
    )


def _diff_configs(current: Dict[str, object], reference_config: Dict[str, object], 
                  full_reference: Optional[Dict[str, object]] = None) -> List[ConfigDiffEntry]:
    """
    对比配置差异
    
    特殊处理：如果 reference_config 的 _tracked_params 是 None，
    尝试从 full_reference 的 metrics 中提取参数值
    
    Args:
        current: 当前运行的 config_values
        reference_config: 参考运行的 config_values
        full_reference: 完整的参考运行记录（包含 metrics）
    """
    reference = dict(reference_config)  # 复制一份避免修改原始数据
    
    # 如果当前有 _tracked_params 但 reference 没有，尝试从 metrics 提取
    if "_tracked_params" in current and current["_tracked_params"] is not None:
        if "_tracked_params" not in reference or reference["_tracked_params"] is None:
            # 尝试从完整记录的 metrics 提取参数
            if full_reference:
                ref_metrics = full_reference.get("metrics", {})
                if isinstance(ref_metrics, dict):
                    # 提取常见的参数字段
                    param_keys = ["learning_rate", "lr", "batch_size", "epochs", 
                                 "optimizer", "model_type", "hidden_size", "dropout"]
                    extracted_params = {}
                    for key in param_keys:
                        if key in ref_metrics:
                            extracted_params[key] = ref_metrics[key]
                    
                    if extracted_params:
                        # 加入提取的参数
                        reference["_tracked_params"] = extracted_params
    
    keys = sorted(set(current) | set(reference))
    diffs: List[ConfigDiffEntry] = []
    for key in keys:
        cur_val = current.get(key)
        ref_val = reference.get(key)
        if cur_val != ref_val:
            diffs.append(ConfigDiffEntry(key=key, current=cur_val, reference=ref_val))
    return diffs


def _diff_metric(record: RunRecord, reference: Dict[str, object]) -> Optional[Dict[str, float]]:
    metric_name = record.primary_metric
    if not metric_name:
        return None
    current_value = record.metrics.get(metric_name)
    ref_metrics = reference.get("metrics") or {}
    reference_value = ref_metrics.get(metric_name) if isinstance(ref_metrics, dict) else None
    if current_value is None or reference_value is None:
        return None
    return {
        "metric": metric_name,
        "current": float(current_value),
        "reference": float(reference_value),
        "delta": float(current_value - reference_value),
    }
