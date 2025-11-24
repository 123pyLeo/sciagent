"""Helpers for loading configuration files that feed the fingerprint."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Sequence

try:  # Optional dependency that is commonly available.
    import yaml  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    yaml = None


@dataclass
class ConfigSource:
    """Structured representation of a config file the user provided."""

    path: Path
    content: Any
    raw_text: str

    @property
    def as_mapping(self) -> Mapping[str, Any] | None:
        if isinstance(self.content, Mapping):
            return self.content
        return None


def load_config_sources(paths: Sequence[str] | None) -> List[ConfigSource]:
    """Load config files, keeping both structured and raw text."""

    results: List[ConfigSource] = []
    if not paths:
        return results

    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        text = path.read_text()
        suffix = path.suffix.lower()
        content: Any
        if suffix in {".json"}:
            content = json.loads(text)
        elif suffix in {".yaml", ".yml"}:
            if yaml is None:
                raise RuntimeError(
                    "PyYAML is required to parse YAML configs but is not installed."
                )
            content = yaml.safe_load(text)
        else:
            # Fallback to raw payload for Hydra/joblib outputs or plain text files.
            content = text
        results.append(ConfigSource(path=path, content=content, raw_text=text))
    return results


def flatten_mapping(values: Mapping[str, Any] | None, prefix: str = "") -> Mapping[str, Any]:
    """Create a flattened dict using dotted keys to simplify diff rendering."""

    if values is None:
        return {}

    output: dict[str, Any] = {}
    for key, value in values.items():
        dotted = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            output.update(flatten_mapping(value, dotted))
        else:
            output[dotted] = value
    return output


def canonical_payload(sources: Iterable[ConfigSource]) -> str:
    """Combine all config sources into a canonical JSON string."""

    payload = []
    for src in sources:
        payload.append(
            {
                "path": str(src.path),
                "content": src.content,
            }
        )
    return json.dumps(payload, sort_keys=True, default=str)
