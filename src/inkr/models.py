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
    codec: Optional[str]
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

    @property
    def default(self):
        return self.track.default_track

    @default.setter
    def default(self, value: bool) -> None:
        self.track.default_track = value

    def toggle_default(self) -> None:
        """Toggle the default state of the track."""
        self.default = not self.default

    @property
    def name(self):
        return self.track.track_name

    @name.setter
    def name(self, name: str) -> None:
        self.track.track_name = name

    @property
    def language(self):
        return self.track.language

    @language.setter
    def language(self, language):
        self.track.language = language

    @classmethod
    def from_mkvtracks(cls, tracks: List[MKVTrack]) -> List["Track"]:
        """Create a Track instance from an MKVTrack object."""
        return [
            cls(
                track=track,
                id=i,
                type=track.track_type,
                codec=track.track_codec,
            )
            for i, track in enumerate(tracks)
        ]

    def formatted_text(self) -> Text:
        """Return formatted text for display in a Checkbox."""
        details = f"{self.language or ''} {self.codec or ''} {self.type or ''}".strip()
        default_indicator = " (Default)" if self.default else ""
        return Text(details, style="bold") + Text(
            f" {self.name or 'Unnamed'}{default_indicator}", style="italic dim bold"
        )

    def list_item(self) -> ListItem:
        """Return a ListItem representation of the track."""
        return ListItem(
            CheckboxMeta[Track](self.formatted_text(), self.enabled, metadata=self)
        )
