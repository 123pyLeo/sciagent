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
    
    会自动展开嵌套字典（如 _code_config、_tracked_params），
    只显示实际变化的参数。
    
    Args:
        current: 当前运行的 config_values
        reference_config: 参考运行的 config_values
        full_reference: 完整的参考运行记录（包含 metrics）
    """
    # 展开嵌套字典
    current_flat = _flatten_config(current)
    reference_flat = _flatten_config(reference_config)
    
    keys = sorted(set(current_flat) | set(reference_flat))
    diffs: List[ConfigDiffEntry] = []
    
    for key in keys:
        cur_val = current_flat.get(key)
        ref_val = reference_flat.get(key)
        if cur_val != ref_val:
            diffs.append(ConfigDiffEntry(key=key, current=cur_val, reference=ref_val))
    
    return diffs


def _flatten_config(config: Dict[str, object], prefix: str = "") -> Dict[str, object]:
    """
    展开嵌套的配置字典
    
    例如：
        {"_code_config": {"lr": 0.001, "batch_size": 32}}
    变成：
        {"lr": 0.001, "batch_size": 32}
    """
    result: Dict[str, object] = {}
    
    # 需要展开的特殊 key
    nested_keys = {"_code_config", "_tracked_params", "_cmd_params"}
    
    for key, value in config.items():
        if key in nested_keys and isinstance(value, dict):
            # 展开嵌套字典，不加前缀
            for inner_key, inner_value in value.items():
                result[inner_key] = inner_value
        elif isinstance(value, dict) and not key.startswith("_"):
            # 其他字典用点号展开
            for inner_key, inner_value in value.items():
                result[f"{key}.{inner_key}"] = inner_value
        else:
            result[key] = value
    
    return result


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
