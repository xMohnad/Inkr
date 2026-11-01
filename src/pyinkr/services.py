from __future__ import annotations

from typing import TYPE_CHECKING

from pymkv import MKVAttachment, MKVFile, MKVTrack

if TYPE_CHECKING:
    from pathlib import Path

    from pymkv.models import MkvMergeOutput


class MkvService:
    """Thin domain-layer wrapper around `pymkv.MKVFile`."""

    def __init__(self, manager: MKVFile, path: Path) -> None:
        """Wrap an already-loaded MKVFile; caller owns its lifecycle."""
        self.manager: MKVFile = manager
        self.path: Path = path

    @property
    def tracks(self) -> list[MKVTrack]:
        """All tracks currently in the container."""
        return self.manager.tracks

    @property
    def info_json(self) -> MkvMergeOutput | None:
        """Cached `mkvmerge -J` output for the container, if available."""
        return self.manager._info_json  # pyright: ignore[reportPrivateUsage]

    def add_track(self, path: Path) -> MKVTrack:
        """Add a track from `path` and return it."""
        track = MKVTrack(
            str(path),
            track_name=path.stem,
            mkvmerge_path=self.manager.mkvmerge_path,
        )
        self.manager.add_track(track)
        return track

    def move_track(self, index: int, delta: int) -> bool:
        """Move the track at `index` by one position (`delta` is -1 or 1).

        Returns:
            Whether the track moved; `False` at the list boundaries.
        """
        if delta not in (-1, 1) or not 0 <= index + delta < len(self.tracks):
            return False

        if delta < 0:
            self.manager.move_track_backward(index)
        else:
            self.manager.move_track_forward(index)

        return True

    @property
    def attachments(self) -> list[MKVAttachment]:
        """All attachments currently in the container."""
        return self.manager.attachments

    def add_attachment(self, path: Path) -> MKVAttachment:
        """Add an attachment from `path` and return it."""
        attachment = MKVAttachment(str(path), name=path.name)
        self.manager.add_attachment(attachment)
        return attachment
