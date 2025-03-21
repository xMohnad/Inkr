from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pymkv import MKVTrack
from rich.text import Text
from textual.widgets import ListItem

from .widgets import CheckboxMeta


@dataclass
class Track:
    track: MKVTrack
    id: int
    type: Optional[str]
    language: Optional[str]
    codec: Optional[str]
    name: Optional[str]
    default: bool
    enabled: bool = True

    def __repr__(self) -> str:
        """Return a string representation of the Track."""
        return (
            f"Track(type={self.type}, lang={self.language}, "
            f"codec={self.codec}, name={self.name}, default={self.default}, enabled={self.enabled})"
        )

    def toggle(self) -> None:
        """Toggle the enabled state of the track."""
        self.enabled = not self.enabled

    @classmethod
    def from_mkvtrack(cls, tracks: List[MKVTrack]) -> List["Track"]:
        """Create a Track instance from an MKVTrack object."""
        return [
            cls(
                track=track,
                id=i,
                type=track.track_type,
                language=track.language,
                codec=track.track_codec,
                name=track.track_name,
                default=bool(track.default_track),
            )
            for i, track in enumerate(tracks)
        ]

    def formatted_text(self) -> Text:
        """Return formatted text for display in a Checkbox."""
        details = f"{self.language or ''} {self.codec or ''} {self.type or ''}".strip()
        return Text(details, style="bold") + Text(
            f" {self.name or 'Unnamed'}", style="italic dim bold"
        )

    def list_item(self) -> ListItem:
        """Return a ListItem representation of the track."""
        return ListItem(
            CheckboxMeta[Track](self.formatted_text(), self.enabled, metadata=self)
        )
