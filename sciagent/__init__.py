"""SciAgent package initializer."""

from __future__ import annotations

from .track import (
    ParamTracker,
    log_params,
    log_param,
    log_metrics,
    log_metric,
    log_metadata,
    save,
    auto_track,
    track,
)

__all__ = [
    "__version__",
    # 参数追踪
    "ParamTracker",
    "log_params",
    "log_param",
    "log_metrics",
    "log_metric",
    "log_metadata",
    "save",
    "auto_track",
    "track",
]
