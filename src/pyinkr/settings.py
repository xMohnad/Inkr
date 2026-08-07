from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from platformdirs import user_config_dir


@dataclass(slots=True)
class Settings:
    """User-configurable application settings"""

    theme: str = "tokyo-night"
    fonts_folder: str | None = None

    @staticmethod
    def settings_dir() -> Path:
        """Return settings directory."""
        path = Path(user_config_dir("pyinkr", appauthor=False))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def settings_path(cls) -> Path:
        """Return settings file path."""
        return cls.settings_dir() / "settings.json"

    @classmethod
    def load(cls) -> Settings:
        """Load settings from disk."""
        path = cls.settings_path()
        if not path.exists():
            return cls()

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {f.name for f in fields(cls)}
            return cls(**{k: v for k, v in data.items() if k in known})
        except (OSError, ValueError):
            return cls()

    def save(self) -> None:
        """Save settings to disk atomically."""
        path = self.settings_path()
        payload = json.dumps(asdict(self), indent=2, ensure_ascii=False)

        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp_name, path)
        except OSError:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    @property
    def fonts_folder_path(self) -> Path | None:
        """Return `fonts_folder` as Path."""
        return Path(self.fonts_folder) if self.fonts_folder else None
