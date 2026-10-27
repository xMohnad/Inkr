from __future__ import annotations

import logging
import re
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from fontTools.ttLib import TTFont
from fontTools.ttLib.ttCollection import TTCollection

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from pymkv import MKVTrack

logging.getLogger("fontTools").setLevel(logging.CRITICAL)

SUPPORTED_SUBTITLE_CODECS: frozenset[str] = frozenset({"SubStationAlpha"})
"""mkvmerge's human-readable codec name, shared by both ASS and SSA."""

FONT_FILE_EXTENSIONS: frozenset[str] = frozenset({".ttf", ".otf", ".ttc", ".otc"})
"""File extensions treated as fonts when scanning a folder."""


def is_subtitle_track(track: MKVTrack) -> bool:
    """Return whether `track` is a subtitle track."""
    return (track.track_type or "").lower() == "subtitles"


def is_supported_subtitle(track: MKVTrack) -> bool:
    """Return whether `track` is a subtitle format this module can parse (ASS/SSA)."""
    return (track.track_codec or "") in SUPPORTED_SUBTITLE_CODECS


def _iter_subtitle_lines(track: MKVTrack) -> Iterator[str]:
    """Yield the lines of an ASS/SSA subtitle track.

    Must be fully consumed by the caller before this generator resumes
    past the `with` block below, or the temporary file will already be
    gone.
    """
    source = Path(track.file_path)
    if source.suffix.lower() in (".ass", ".ssa"):
        with source.open(encoding="utf-8-sig", errors="ignore") as f:
            yield from f
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        output = Path(track.extract(tmp_dir, silent=True))
        with output.open(encoding="utf-8-sig", errors="ignore") as f:
            yield from f


def _normalize_font_name(name: str) -> str:
    """Strip the '@' prefix ASS uses for vertical text (e.g. '@Arial' -> 'Arial')."""
    name = name.strip()
    if name.startswith("@"):
        name = name[1:].strip()
    return name


def _parse_weight(value: str) -> int:
    r"""Parse a \b tag value into an OS/2-style weight (100-900)."""
    try:
        val = round(float(value))
    except ValueError:
        return 400
    if val == 0:
        return 400
    if val == 1:
        return 700
    if val < 100:
        return 400
    return val


def _parse_bool_field(value: str) -> bool:
    """Return whether a Style Bold/Italic field ('-1'/'1' vs '0') is true."""
    return value.strip() not in ("", "0")


class FontUsage(NamedTuple):
    """A font name plus the weight/italic state it was used with."""

    name: str
    weight: int
    italic: bool

    @property
    def is_bold(self) -> bool:
        """Return whether this usage is bold."""
        return self.weight >= 700


@dataclass(frozen=True, slots=True)
class FontFile:
    """One font face found on disk, with the info needed to match it to a `FontUsage`."""

    path: Path
    family_names: frozenset[str]
    weight: int
    italic: bool


@dataclass(frozen=True, slots=True)
class _ParsedAss:
    """The subset of an ASS/SSA file relevant to font detection."""

    styles: dict[str, FontUsage]
    dialogue_lines: list[tuple[str, str]]
    """(style name, raw text) for each Dialogue event."""
    has_embedded_fonts: bool


@dataclass(frozen=True, slots=True)
class SubtitleFontInfo:
    """Fonts a subtitle track needs, and whether it already embeds fonts."""

    usages: frozenset[FontUsage]
    has_embedded_fonts: bool


def _parse_ass_minimal(lines: Iterable[str]) -> _ParsedAss:
    """Parse the fields needed for font detection out of ASS/SSA source lines."""
    styles: dict[str, FontUsage] = {}
    dialogue_lines: list[tuple[str, str]] = []
    has_fonts_section = False
    section = ""

    for line in lines:
        if not (line := line.strip()):
            continue

        if line[0] == "[" and line[-1] == "]":
            section = line.lower()
            has_fonts_section |= section == "[fonts]"
            continue

        if section in ("[fonts]", "[graphics]"):
            continue

        prefix = line[:9].lower()

        if section == "[events]" and prefix.startswith("dialogue:"):
            parts = line[9:].split(",", 9)
            if len(parts) == 10:
                dialogue_lines.append((parts[3].strip(), parts[9]))

        elif section in ("[v4+ styles]", "[v4 styles]") and prefix.startswith("style:"):
            parts = line[6:].split(",", 9)
            if len(parts) < 9 or not (name := parts[0].strip()):
                continue

            styles[name] = FontUsage(
                name=_normalize_font_name(parts[1]),
                weight=700 if _parse_bool_field(parts[7]) else 400,
                italic=_parse_bool_field(parts[8]),
            )

    return _ParsedAss(styles, dialogue_lines, has_fonts_section)


_RELEVANT_RE = re.compile(r"\\(?:fn|r|i\d|b\d)")

_TAG_RE = re.compile(
    r"\\(?:"
    r"fn(?P<fn>[^\\}]*)"
    r"|r(?P<r>[^\\}]*)"
    r"|i(?P<i>\d)"
    r"|b(?P<b>\d+)"
    r"|[a-z]+\([^)]*\)"
    r")"
)
"""Matches tracked tags (\\fn, \\r, \\i, \\b); the last branch consumes and skips tags with (...) arguments."""


def _extract_font_usages(styles: dict[str, FontUsage], dialogue_lines: list[tuple[str, str]]) -> set[FontUsage]:
    r"""Walk every dialogue line and collect every distinct font/weight/italic combo used.

    Limitation: font changes inside \t(...) animated transforms aren't tracked.
    """
    default = styles.get("Default") or next(iter(styles.values()), None)
    if default is None:
        return set()

    usages: set[FontUsage] = set()
    has_relevant_tag = _RELEVANT_RE.search
    iter_tags = _TAG_RE.finditer

    for style, text in dialogue_lines:
        line_style = styles.get(style, default)
        usages.add(line_style)

        if "\\" not in text or has_relevant_tag(text) is None:
            continue

        current = line_style
        for m in iter_tags(text):
            if (tag := m.lastgroup) is None:
                continue

            value = m.group(tag).strip()

            if tag == "r":
                current = styles.get(value, line_style) if value else line_style
            elif tag == "b" and value:
                current = FontUsage(current.name, _parse_weight(value), current.italic)
            elif tag == "i" and value:
                current = FontUsage(current.name, current.weight, value != "0")
            else:  # fn
                name = _normalize_font_name(value) if value else line_style.name
                current = FontUsage(name, current.weight, current.italic)

            usages.add(current)

    return usages


def _load_font_objects(path: Path) -> list[TTFont]:
    """Load `path` as a list of TTFont objects, or an empty list if unreadable/unsupported."""
    try:
        with path.open("rb") as f:
            magic = f.read(4)

        if magic == b"ttcf":
            return TTCollection(path, lazy=True).fonts
        if magic in (b"\x00\x01\x00\x00", b"OTTO"):
            return [TTFont(path, lazy=True)]
        return []
    except Exception:
        return []


def _read_font_faces(path: Path) -> list[FontFile]:
    """Return a `FontFile` for each usable face in the font file at `path`."""
    results: list[FontFile] = []
    for tt in _load_font_objects(path):
        names: set[str] = set()
        with suppress(Exception):
            for record in tt["name"].names:
                # IDs: Family, Full name, Typographic family
                if record.nameID in (1, 4, 16) and (n := record.toUnicode().strip()):
                    names.add(n.lower())

        weight, italic = 400, False
        if "OS/2" in tt:
            os2 = tt["OS/2"]
            weight = int(getattr(os2, "usWeightClass", 400)) or 400
            fs = getattr(os2, "fsSelection", 0)
            italic = bool(fs & 1 or fs & (1 << 9))  # bit 0 = Italic, bit 9 = Oblique

        results.append(FontFile(path=path, family_names=frozenset(names), weight=weight, italic=italic))
    return results


@lru_cache(maxsize=32)
def analyze_subtitle_fonts(track: MKVTrack) -> SubtitleFontInfo:
    """Return the fonts `track` needs, and whether it already embeds fonts.

    Raises:
        ValueError: if `track` isn't a subtitle track, or isn't in a
            supported format (ASS/SSA).
    """
    if not is_subtitle_track(track):
        raise ValueError("Selected track is not a subtitle track.")

    if not is_supported_subtitle(track):
        raise ValueError(f"Font checking isn't supported for '{track.track_codec}' subtitles (only ASS/SSA).")

    parsed = _parse_ass_minimal(_iter_subtitle_lines(track))
    usages = _extract_font_usages(parsed.styles, parsed.dialogue_lines)
    return SubtitleFontInfo(frozenset(usages), parsed.has_embedded_fonts)


def scan_font_faces(directory: Path) -> list[FontFile]:
    """Scan `directory` for font files, returning every face found."""
    faces: list[FontFile] = []
    for candidate in directory.rglob("*"):
        if candidate.is_file() and candidate.suffix.lower() in FONT_FILE_EXTENSIONS:
            faces.extend(_read_font_faces(candidate))
    return faces


def find_best_match(usage: FontUsage, faces: Iterable[FontFile]) -> FontFile | None:
    """Return the face among `faces` that best matches `usage`'s name/weight/italic, if any."""
    target = usage.name.strip().lower()
    candidates = [face for face in faces if target in face.family_names]
    if candidates:
        return min(candidates, key=lambda face: (face.italic != usage.italic, abs(face.weight - usage.weight)))
    return None
