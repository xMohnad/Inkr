"""
This module provides a high-level wrapper around the `mkvmerge` tool
to manage Matroska (MKV) files programmatically.

Usage Example:
    ```python
    from pyinkr.wrapper import MkvMerge

    mkv = MkvMerge("input.mkv")
    mkv.add_track("extra_audio.mkv")
    print(mkv.generate_command(as_string=True))  # Show mkvmerge command
    mkv.mux()  # Execute muxing
    ```
"""

from __future__ import annotations

import json
import logging
import platform
import shlex
import shutil
import subprocess as sp
from contextlib import ExitStack
from itertools import count
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, Final, TextIO

from dacite import from_dict
from textual import log

from pyinkr.wrapper.schema import MkvInfo, Track
from pyinkr.wrapper.validation import GlobalOptions, TrackOptions


def _get_mkvmerge_path() -> str | None:
    if platform.system() == "Windows":
        return shutil.which("mkvmerge.exe")
    return shutil.which("mkvmerge")


MKVMERGE_PATH: str | None = _get_mkvmerge_path()


class MkvTrack:
    """Represents a single track within an MKV file or a standalone media file."""

    _track_ignore: Final[dict[str, list[str]]] = {
        "subtitle": ["no-audio", "no-video"],
        "video": ["no-audio", "no-subtitles"],
        "audio": ["no-video", "no-subtitles"],
        "default": ["no-audio", "no-video", "no-subtitles"],
    }
    """Internal mapping of track types to options that should be ignored for that type."""

    def __init__(
        self,
        file_path: Path | str,
        options: TrackOptions,
        track_info: Track,
        file_id: int = 0,
        track: int = 0,
    ) -> None:
        """
        Initialize an MkvTrack instance.

        Args:
            file_path (str | Path): Path to the track file or the MKV containing the track.
            options (TrackOptions): Options to apply to the track (e.g., language, default, forced).
            track_info (Track): Metadata about the track as parsed from mkvmerge JSON output (`-J`).
            file_id (int): Identifier of the file this track belongs to, useful when multiple files
                are being merged. Defaults to 0.
            track (int): Index of the track within the file. Defaults to 0.
        """
        self.file_path: Path = Path(file_path)
        self.options: TrackOptions = options
        self.track_info: Track = track_info
        self.file_id: int = file_id
        self.track: int = track

    @property
    def codec(self) -> str:
        """
        Returns the codec of the track.

        Examples:
            'H.264' for video, 'AAC' for audio.
        """
        return self.track_info.codec

    @property
    def type(self) -> str:
        """
        Returns the type of the track.

        Possible values include 'video', 'audio', 'subtitle', or 'buttons'.
        """
        return self.track_info.type

    def generate_options(self) -> list[str]:
        """
        Generate mkvmerge command-line options for this track.

        Combines user-specified options with default ignored options
        based on track type.

        Returns:
            list[str]: Command-line arguments suitable for mkvmerge.
        """
        options: list[str] = []

        # Normalize track type for subtitles/buttons
        ttype = self.type
        if ttype in ["subtitles", "buttons"]:
            ttype = ttype[:-1]

        for k, v in self.options.items():
            if v is not None:
                if isinstance(v, bool):
                    options.extend([f"--{k}", f"{self.track}:{int(v)}"])
                else:
                    options.extend([f"--{k}", f"{self.track}:{v}"])
            else:
                options.extend([f"--{k}"])

        # Add ignored options based on track type
        for o in self._track_ignore.get(ttype, self._track_ignore["default"]):
            options.append(f"--{o}")

        options.extend([f"--{ttype}-tracks", str(self.track), "(", f"{self.file_path.absolute()}", ")"])
        return options


class MkvMerge:
    """
    A class that contains all the sources, attachments, and options required to create an
    actual useful set of configuration options.  It will also mux everything together.

    Attributes:
        tracks (list[MkvTrack]): List of all associated MkvTrack objects.
        mkvmerge_path (Path): Path to the mkvmerge binary.
        info (MkvInfo): Metadata about the current MKV file.
        raw_info (dict): Raw JSON output from mkvmerge for the current file.
        options (GlobalOptions): Global mkvmerge options such as title.
        output (Path): Path to the output file for muxing.
    """

    def __init__(
        self,
        file_path: Path,
        mkvmerge_path: str | Path | None = MKVMERGE_PATH,
    ) -> None:
        """Initialize MkvMerge object for a target MKV file.

        Args:
            file_path (Path): Path to the target Matroska (MKV) file.
            mkvmerge_path (str | Path, optional): Path to the mkvmerge binary.
                Defaults to the preconfigured MKVMERGE_PATH.

        Raises:
            FileNotFoundError: If mkvmerge binary cannot be found.
        """
        if not mkvmerge_path:
            raise FileNotFoundError("mkvmerge is not at the specified path, add it there or set `mkvmerge_path`")

        self._file_path: Path = file_path
        self._number_file: count[int] = count(1)
        self.tracks: list[MkvTrack] = []
        """List of all the associated MkvTracks"""

        self.mkvmerge_path: Path = Path(mkvmerge_path)
        logging.debug(f"Found 'mkvmerge' binary ({platform.system()}): {self.mkvmerge_path}")

        self.info: MkvInfo
        self.raw_info: dict[str, object] = {}

        self.file_path = file_path
        self.options: GlobalOptions = GlobalOptions(title=self.info.container.properties.title)
        """options to set for `mkvmerge`."""

        self.output: Path = Path("output.mkv")
        """The output file to mux to."""

    @property
    def file_path(self) -> Path:
        """Return the current Matroska file path."""
        return self._file_path

    @file_path.setter
    def file_path(self, value: Path) -> None:
        """
        Set the path to the Matroska file and load its tracks.

        Args:
            value (Path): Path to the MKV file.

        Raises:
            ValueError: If the file is not a supported Matroska container.
            FileNotFoundError: If the file cannot be accessed.
        """
        self._file_path = value
        self.info = self.get_info()
        self.add_tracks_from_info(self.info.tracks, self.file_path)

    def get_info(self, file_path: None | Path = None) -> MkvInfo:
        """
        Retrieve metadata for an MKV file using mkvmerge JSON output.

        Args:
            file_path (Path, optional): MKV file to inspect. Defaults to instance's `file_path`.

        Raises:
            FileNotFoundError: If mkvmerge binary or file not found.
            ValueError: If file is not supported or JSON cannot be parsed.

        Returns:
            MkvInfo: Parsed metadata from mkvmerge JSON output.
        """
        file_path = file_path or self.file_path
        command = [self.mkvmerge_path, "-i", str(file_path), "-F", "json"]
        try:
            output = sp.run(command, capture_output=True)
        except (sp.CalledProcessError, FileNotFoundError):
            raise FileNotFoundError("mkvmerge is not at the specified path, add it there")

        data: dict[str, object] = json.loads(output.stdout)  # pyright: ignore[reportAny]

        if not data["container"]["supported"]:  # pyright: ignore[reportIndexIssue]
            raise ValueError(f"'{file_path.name}' is not a supported Matroska file.")
        if file_path == self.file_path:
            self.raw_info = data

        return from_dict(MkvInfo, data)

    def add_tracks_from_info(self, tracks_info: list[Track], source_file: Path, file_id: int = 0) -> list[MkvTrack]:
        """
        Load all tracks from a Matroska file.

        Args:
            tracks_info (list[Track]): Tracks as parsed from mkvmerge JSON output.
            source_file (Path): Source file containing the tracks.
            file_id (int): File identifier for this source. Default is 0.
        """
        new_tracks: list[MkvTrack] = []
        for track in tracks_info:
            new_track = MkvTrack(
                source_file,
                TrackOptions(
                    track.properties.track_name,
                    track.properties.language,
                    track.properties.default_track,
                    track.properties.forced_track,
                ),
                track,
                track.id,
                file_id,
            )
            self.tracks.append(new_track)
            new_tracks.append(new_track)
        return new_tracks

    def add_track(self, track: Path) -> list[MkvTrack]:
        """
        Add a new track from a file.

        Args:
            track (Path): Path to the track file to add.

        Raises:
            ValueError: If the file is not a supported Matroska file.
        """
        track_info = self.get_info(track)
        return self.add_tracks_from_info(track_info.tracks, track, next(self._number_file))

    @property
    def track_order(self) -> list[str]:
        """
        Return the order of tracks for muxing.

        Automatically generated unless overridden.

        Returns:
            list[str]: Track order suitable for mkvmerge CLI.
        """
        unique_file_dict: dict[str, int] = {}
        for track in self.tracks:
            file_path = str(track.file_path)
            if file_path not in unique_file_dict:
                unique_file_dict[file_path] = len(unique_file_dict)

        return [f"{unique_file_dict[str(track.file_path)]}:{track.track}" for track in self.tracks]

    def remove_track(self, track_index: int) -> None:
        """
        Remove a track from the mux.

        Args:
            track_index (int): Index of the track to remove.

        Raises:
            IndexError: If the index is out of range.
        """
        if not 0 <= track_index < len(self.tracks):
            raise IndexError("track index out of range")
        del self.tracks[track_index]

    def move_track_forward(self, track_index: int) -> None:
        """
        Move a track forward in the order.

        Args:
            track_index (int): Index of the track to move.

        Raises:
            IndexError: If index is out of range or already last.
        """
        if not 0 <= track_index < len(self.tracks) - 1:
            raise IndexError("Track index out of range")
        self.tracks[track_index], self.tracks[track_index + 1] = (
            self.tracks[track_index + 1],
            self.tracks[track_index],
        )

    def move_track_backward(self, track_index: int) -> None:
        """
        Move a track backward in the order.

        Args:
            track_index (int): Index of the track to move.

        Raises:
            IndexError: If index is out of range or already first.
        """
        if not 0 < track_index < len(self.tracks):
            raise IndexError("Track index out of range")
        self.tracks[track_index], self.tracks[track_index - 1] = (
            self.tracks[track_index - 1],
            self.tracks[track_index],
        )

    def generate_command(self, as_string: bool = False) -> list[str] | str:
        """
        Generate mkvmerge command-line arguments.

        Args:
            as_string (bool): If True, return command as a single string for shell execution.
                              Defaults to False (returns list of arguments).

        Returns:
            list[str] | str: Command-line arguments or single string for execution.
        """
        command = [str(self.mkvmerge_path)]

        # Add global options
        for k, v in self.options.items():
            if v is None:
                command.append(f"--{k}")
            elif isinstance(v, bool):
                command.extend([f"--{k}", str(int(v))])
            else:
                command.extend([f"--{k}", str(v)])

        command.extend(["--output", f"{self.output.absolute()}"])

        # Add track-specific options
        for track in self.tracks:
            command.extend(track.generate_options())
        command.extend(["--track-order", ",".join(self.track_order)])

        return shlex.join(command) if as_string else command

    def save_command(self, filename: Path | None = None) -> str:
        """
        Save the generated command as a JSON file.

        If `filename` is provided, the command is saved to that path with a `.json` extension.
        If no `filename` is provided, a temporary file is created and used.

        Args:
            filename (Path | None): The path where the JSON file should be saved.
                If None, a temporary file will be created. Defaults to None.

        Returns:
            str: The path to the file where the JSON data was saved.
        """

        with ExitStack() as stack:
            f: IO[str] | TextIO
            if filename is None:
                tmp_file = NamedTemporaryFile(mode="w", delete=False, suffix=".json")
                f = stack.enter_context(tmp_file)
                file_path = tmp_file.name
            else:
                path = filename.with_suffix(".json")
                f = stack.enter_context(path.open("w"))
                file_path = str(path)

            json.dump(self.generate_command()[1:], f)

        return file_path

    def mux(self) -> int:
        """
        Execute muxing with mkvmerge using all tracks and global options.

        Returns:
            int: Return code from mkvmerge process.

        Notes:
            - Command is written to a temporary JSON file.
            - Temporary file is deleted after execution.
        """
        output_file = self.save_command()
        command = f'"{self.mkvmerge_path}" "@{output_file}"'

        log.debug(f"Creating temp file: {output_file}")
        log.debug("Command: ", command)

        results = sp.run(
            shlex.split(command),
            stdout=sp.PIPE,
            stderr=sp.PIPE,
        )
        log.debug(f"Process completed with {results.returncode}")

        if output_file:
            Path(output_file).unlink()

        return results.returncode
