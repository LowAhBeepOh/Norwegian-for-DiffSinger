"""Saved GUI settings, kept as JSON in the git-ignored tools folder."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .paths import TOOLS_DIR

SETTINGS_FILE = TOOLS_DIR / "settings.json"


@dataclass
class Settings:
    # None means "follow the operating system"; True/False force light/dark.
    light_mode: bool | None = None
    high_contrast: bool = False
    force_cpu: bool = False


def load() -> Settings:
    defaults = Settings()
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaults
    if not isinstance(data, dict):
        return defaults

    light = data.get("light_mode", defaults.light_mode)
    return Settings(
        light_mode=light if isinstance(light, bool) else None,
        high_contrast=bool(data.get("high_contrast", defaults.high_contrast)),
        force_cpu=bool(data.get("force_cpu", defaults.force_cpu)),
    )


def save(settings: Settings) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
