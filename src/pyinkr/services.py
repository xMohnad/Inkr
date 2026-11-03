from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from pymkv import MKVAttachment, MKVFile, MKVTrack

if TYPE_CHECKING:
    from pathlib import Path

    from pymkv.models import MkvMergeOutput


class MkvService:
    """Domain layer over `pymkv.MKVFile`: owns the edit state of one opened file.

    Widgets only display this state; they never keep it themselves.
    """

    def __init__(self, manager: MKVFile, path: Path) -> None:
        """Wrap an already-loaded MKVFile; caller owns its lifecycle."""
        self.manager: MKVFile = manager
        self.path: Path = path
        self._dropped: set[int] = set()

    @property
    def tracks(self) -> list[MKVTrack]:
        """All tracks currently in the container, including dropped ones."""
        return self.manager.tracks

    @property
    def attachments(self) -> list[MKVAttachment]:
        """All attachments currently in the container, including dropped ones."""
        return self.manager.attachments

    @property
    def info_json(self) -> MkvMergeOutput | None:
        """Cached `mkvmerge -J` output for the container, if available."""
        return self.manager._info_json  # pyright: ignore[reportPrivateUsage]

    def is_kept(self, item: MKVTrack | MKVAttachment) -> bool:
        """Return whether `item` will be in the output."""
        return id(item) not in self._dropped

    def set_kept(self, item: MKVTrack | MKVAttachment, kept: bool) -> None:
        """Keep or drop `item` in the output."""
        if kept:
            self._dropped.discard(id(item))
        else:
            self._dropped.add(id(item))

    def toggle_kept(self, item: MKVTrack | MKVAttachment) -> bool:
        """Flip whether `item` is kept and return the new state."""
        self.set_kept(item, not self.is_kept(item))
        return self.is_kept(item)

    @property
    def kept_tracks(self) -> list[MKVTrack]:
        """Tracks that will be in the output."""
        return [t for t in self.tracks if self.is_kept(t)]

    def add_track(self, path: Path) -> MKVTrack:
        """Add a track from `path` and return it."""
        track = MKVTrack(
            str(path),
            track_name=path.stem,
            mkvmerge_path=self.manager.mkvmerge_path,
        )
        self.manager.add_track(track)
        return track

    def add_attachment(self, path: Path) -> MKVAttachment:
        """Add an attachment from `path` and return it."""
        attachment = MKVAttachment(str(path), name=path.name)
        self.manager.add_attachment(attachment)
        return attachment

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

    def build_output(self) -> MKVFile:
        """Return a copy of the file with dropped tracks and attachments removed."""
        output = copy.deepcopy(self.manager)
        for i in reversed(range(len(self.tracks))):
            if not self.is_kept(self.tracks[i]):
                output.remove_track(i)
        for i in reversed(range(len(self.attachments))):
            if not self.is_kept(self.attachments[i]):
                output.remove_attachment(i)
        return output
