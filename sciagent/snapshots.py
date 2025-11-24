"""Placeholder snapshot manager."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class SnapshotManager:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.snapshot_dir = run_dir / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save_last(self, reason: str, extra: Optional[Dict[str, object]] = None) -> Path:
        payload = {
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "reason": reason,
        }
        if extra:
            payload.update(extra)
        path = self.snapshot_dir / "last.ckpt.json"
        path.write_text(json.dumps(payload, indent=2))
        return path

    def save_best(self, metric_name: str, metric_value: float) -> Path:
        payload = {
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "metric": metric_name,
            "value": metric_value,
        }
        path = self.snapshot_dir / f"best_{metric_name}.ckpt.json"
        path.write_text(json.dumps(payload, indent=2))
        return path
