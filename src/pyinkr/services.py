from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from pymkv import MKVFile, MKVTrack

if TYPE_CHECKING:
    from pathlib import Path

    from pymkv.models import MkvMergeOutput


class MkvService:
    """Thin domain-layer wrapper around `pymkv.MKVFile`."""

    def __init__(self, manager: MKVFile, path: Path) -> None:
        self.manager: MKVFile = manager
        self.path: Path = path

    @property
    def tracks(self) -> list[MKVTrack]:
        """All tracks currently in the container."""
        return self.manager.tracks

    @property
    def title(self) -> str | None:
        return self.manager.title

    @title.setter
    def title(self, value: str) -> None:
        self.manager.title = value

    @property
    def info_json(self) -> MkvMergeOutput | None:
        return self.manager._info_json

    def add_track(self, path: Path) -> MKVTrack:
        """Add a track from `path` and return it."""
        track = MKVTrack(
            str(path),
            track_name=path.stem,
            mkvmerge_path=self.manager.mkvmerge_path,
        )
        self.manager.add_track(track)
        return track

    def remove_track(self, index: int) -> None:
        self.manager.remove_track(index)

    def move_track_up(self, index: int) -> None:
        self.manager.move_track_backward(index)

    def move_track_down(self, index: int) -> None:
        self.manager.move_track_forward(index)

    def mux(self, save_path: Path, progress_handler: Callable[[int], None]) -> None:
        self.manager.mux(save_path, progress_handler=progress_handler)
