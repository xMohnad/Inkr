from __future__ import annotations

from pathlib import Path
from typing import List

from pymkv import MKVFile, MKVTrack

from .models import Track


class MkvManager:
    """Handles operations on the MKV file."""

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)

        if not self.filepath.exists():
            raise FileNotFoundError(f"The file {filepath} does not exist.")

        self.mkv: MKVFile = MKVFile(filepath)
        self.tracks: List[Track] = Track.from_mkvtrack(self.mkv.tracks)

    def save(self, save_path: Path) -> None:
        """
        Save the MKV file.

        :param save_path: The destination file path.
        """
        for track in self.tracks[:]:
            if not track.enabled:
                self.remove_track(track)

        if self.filepath.resolve() == save_path.resolve():
            save_path = save_path.with_stem(save_path.stem + "_copy")

        self.mkv.mux(save_path)

    def add_track(self, track_path: str) -> Track:
        """Add a new track to the MKV file."""
        track = MKVTrack(file_path=track_path)
        self.mkv.add_track(track)
        track = Track.from_mkvtrack([track])[0]
        self.tracks.append(track)
        self.rearrange_tracks()
        return track

    def remove_track(self, track: Track):
        """Remove a track from the MKV file."""
        self.mkv.remove_track(track.id)
        del self.tracks[track.id]

    def extract_track(self, track: Track, save_path: str):
        track.track.extract(save_path)

    def move_track_forward(self, index: int) -> None:
        tracks = self.tracks
        if index < 0 or index >= len(tracks) - 1:
            raise IndexError("Cannot move forward: Index out of range")
        self.mkv.move_track_forward(index)
        tracks[index], tracks[index + 1] = tracks[index + 1], tracks[index]
        self.rearrange_tracks()

    def move_track_backward(self, index: int) -> None:
        tracks = self.tracks
        if index <= 0 or index >= len(tracks):
            raise IndexError("Cannot move backward: Index out of range")
        self.mkv.move_track_backward(index)
        tracks[index], tracks[index - 1] = tracks[index - 1], tracks[index]
        self.rearrange_tracks()

    def rearrange_tracks(self) -> None:
        for index, track in enumerate(self.tracks):
            track.id = index
