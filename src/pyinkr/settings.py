from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import ClassVar

from platformdirs import user_config_dir


@dataclass(slots=True)
class Settings:
    """User-configurable application settings."""

    theme: str = "tokyo-night"
    fonts_folder: str | None = None
    recent_files: list[str] = field(default_factory=list)

    MAX_RECENT: ClassVar[int] = 10
    """Maximum number of recent files kept."""

    def __post_init__(self) -> None:
        """Keep only string entries in recent files."""
        files = self.recent_files if isinstance(self.recent_files, list) else []
        self.recent_files = [f for f in files if isinstance(f, str)]

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
        try:
            data = json.loads(cls.settings_path().read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return cls()

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

    @property
    def recent_paths(self) -> list[Path]:
        """Return recent files that still exist."""
        seen = dict.fromkeys(self.recent_files)
        return [p for p in map(Path, seen) if p.is_file()]

    def add_recent(self, path: Path) -> None:
        """Move `path` to the front of the recent files."""
        entry = str(path.resolve())
        files = [f for f in self.recent_files if f != entry]
        self.recent_files = [entry, *files][: self.MAX_RECENT]
