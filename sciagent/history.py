"""Run history store for diffing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import RunRecord


class RunHistory:
    def __init__(self, path: Path):
        self.path = path
        self._data: Dict[str, Any] = {"runs": []}
        if path.exists():
            try:
                self._data = json.loads(path.read_text())
            except Exception:
                # If the history file is corrupted we start fresh but keep a backup.
                path.rename(path.with_suffix(".corrupted"))
                self._data = {"runs": []}

    @property
    def runs(self) -> List[Dict[str, Any]]:
        return self._data.setdefault("runs", [])

    def append(self, record: RunRecord) -> None:
        summary = {
            "run_id": record.run_id,
            "name": record.name,
            "status": record.status,
            "fingerprint": record.fingerprint,
            "metrics": record.metrics,
            "primary_metric": record.primary_metric,
            "duration_seconds": record.duration_seconds,
            "ended_at": record.ended_at.isoformat() + "Z" if record.ended_at else None,
            "config_values": record.config_values,
        }
        self.runs.append(summary)
        self._persist()

    def latest(self) -> Optional[Dict[str, Any]]:
        if not self.runs:
            return None
        return self.runs[-1]

    def best(self, metric_name: Optional[str]) -> Optional[Dict[str, Any]]:
        if not metric_name:
            return None
        candidates = [r for r in self.runs if metric_name in (r.get("metrics") or {})]
        if not candidates:
            return None
        minimize = _should_minimize(metric_name)
        return min(candidates, key=lambda r: r["metrics"][metric_name]) if minimize else max(
            candidates, key=lambda r: r["metrics"][metric_name]
        )

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))


def _should_minimize(metric_name: str) -> bool:
    lowered = metric_name.lower()
    if "loss" in lowered or "error" in lowered or lowered.startswith("wer"):
        return True
    return False
