"""
STAR
Situation: Cloud batch and streaming jobs require repeatable configuration without hard coding paths.
Task: Provide a simple loader that works locally and in managed runtimes.
Action: Load YAML files, merge runtime overrides, and validate required keys.
Result: The same job can run in local, dev, stage, and prod with minimal code changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a required configuration value is missing."""


def load_yaml_config(path: str | Path, required_keys: list[str] | None = None) -> dict[str, Any]:
    """Load YAML configuration and verify required top level keys.

    Parameters
    ----------
    path:
        YAML file location.
    required_keys:
        Top level keys that must exist before a pipeline starts.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    missing = [key for key in required_keys or [] if key not in config]
    if missing:
        raise ConfigError(f"Missing required config keys: {', '.join(missing)}")

    return config
