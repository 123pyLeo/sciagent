"""Dataclasses shared across modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_loader import ConfigSource

RunStatus = str


@dataclass
class RunSpec:
    command: str
    workdir: Path
    name: Optional[str]
    state_dir: Path
    config_sources: List[ConfigSource]
    metadata: Dict[str, Any]
    metrics: Dict[str, float]
    metrics_file: Optional[Path]
    primary_metric: Optional[str]
    suggestion_count: int


@dataclass
class RunRecord:
    run_id: str
    name: Optional[str]
    command: str
    workdir: Path
    fingerprint: str
    env_snapshot: Dict[str, Any]
    metadata: Dict[str, Any]
    status: RunStatus = "pending"
    exit_code: Optional[int] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    primary_metric: Optional[str] = None
    log_path: Optional[Path] = None
    artifact_paths: Dict[str, str] = field(default_factory=dict)
    suggestion_count: int = 3
    suggestions: List[str] = field(default_factory=list)
    config_values: Dict[str, Any] = field(default_factory=dict)

    def finish(self, status: RunStatus, exit_code: Optional[int]) -> None:
        self.status = status
        self.exit_code = exit_code
        self.ended_at = datetime.utcnow()
        self.duration_seconds = (self.ended_at - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "name": self.name,
            "command": self.command,
            "workdir": str(self.workdir),
            "fingerprint": self.fingerprint,
            "env_snapshot": self.env_snapshot,
            "metadata": self.metadata,
            "status": self.status,
            "exit_code": self.exit_code,
            "started_at": self.started_at.isoformat() + "Z",
            "ended_at": self.ended_at.isoformat() + "Z" if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "metrics": self.metrics,
            "primary_metric": self.primary_metric,
            "log_path": str(self.log_path) if self.log_path else None,
            "artifact_paths": self.artifact_paths,
            "suggestions": self.suggestions,
            "config_values": self.config_values,
        }
