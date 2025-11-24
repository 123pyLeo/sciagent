"""Fingerprint utilities."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable

from .config_loader import ConfigSource, canonical_payload


def build_fingerprint(
    command: str,
    metadata: Dict[str, Any],
    config_sources: Iterable[ConfigSource],
    env_snapshot: Dict[str, Any],
) -> str:
    canonical = {
        "command": command,
        "metadata": metadata,
        "configs": json.loads(canonical_payload(config_sources)) if config_sources else [],
        "env": env_snapshot,
    }
    serialized = json.dumps(canonical, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
