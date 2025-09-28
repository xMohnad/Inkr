from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AttachmentProperties:
    """Properties of an attachment within the MKV file.

    Attributes:
        uid (int | None): Unique identifier for the attachment, if available.
    """

    uid: int | None


@dataclass
class Attachment:
    """Represents an attachment embedded in the MKV file (e.g., fonts, images).

    Attributes:
        content_type (str): MIME type of the attachment (e.g., 'application/x-truetype-font').
        description (str): Optional description provided in the MKV metadata.
        file_name (str): Name of the attached file.
        id (int): Identifier for the attachment.
        properties (AttachmentProperties): Properties containing UID and related metadata.
        size (int): Size of the attachment in bytes.
    """

    content_type: str
    description: str
    file_name: str
    id: int
    properties: AttachmentProperties
    size: int


@dataclass
class EntryCount:
    """Represents counts of various MKV entries (chapters, tags, etc.).

    Attributes:
        num_entries (int): Number of entries of this type.
        track_id (int | None): Associated track ID, if applicable.
    """

    num_entries: int
    track_id: int | None


@dataclass
class ContainerProperties:
    """Detailed properties of the MKV container.

    Attributes:
        container_type (int): Numeric identifier for the container type.
        date_local (str | None): Local creation date of the MKV file.
        date_utc (str | None): UTC creation date of the MKV file.
        duration (int | None): Duration of the file in nanoseconds.
        is_providing_timestamps (bool): Whether the container provides timestamps.
        muxing_application (str | None): Application used to mux the file.
        segment_uid (str | None): Unique identifier for the segment.
        timestamp_scale (int | None): Scale factor for timestamps (nanoseconds).
        title (str | None): Title of the MKV file.
        writing_application (str | None): Application used to write the file.
    """

    container_type: int
    date_local: str | None
    date_utc: str | None
    duration: int | None
    is_providing_timestamps: bool
    muxing_application: str | None
    segment_uid: str | None
    timestamp_scale: int | None
    title: str | None
    writing_application: str | None


@dataclass
class Container:
    """General information about the MKV container.

    Attributes:
        properties (ContainerProperties): Detailed metadata of the container.
        recognized (bool): Whether the container format is recognized.
        supported (bool): Whether the container is supported.
        type (str): Type of the container (e.g., 'Matroska').
    """

    properties: ContainerProperties
    recognized: bool
    supported: bool
    type: str


@dataclass
class TrackProperties:
    """Properties specific to a track within the MKV file.

    Attributes:
        codec_id (str | None): Identifier of the codec used for this track.
        default_track (bool | None): Whether this track is the default.
        enabled_track (bool | None): Whether this track is enabled.
        forced_track (bool | None): Whether this track is forced.
        language (str | None): Language code (ISO 639-2).
        language_ietf (str | None): IETF BCP 47 language code.
        track_name (str | None): Name assigned to the track.
        flag_commentary (bool | None): True if the track is commentary.
        flag_hearing_impaired (bool | None): True if track aids hearing-impaired.
        flag_original (bool | None): True if track is in the original language.
        flag_visual_impaired (bool | None): True if track aids visually-impaired.
    """

    codec_id: str | None
    default_track: bool | None
    enabled_track: bool | None
    forced_track: bool | None
    language: str | None
    language_ietf: str | None
    track_name: str | None
    flag_commentary: bool | None
    flag_hearing_impaired: bool | None
    flag_original: bool | None
    flag_visual_impaired: bool | None


@dataclass
class Track:
    """Represents a single track in the MKV file (video, audio, subtitle).

    Attributes:
        codec (str): Codec name of the track.
        id (int): Unique identifier for the track.
        properties (TrackProperties): Detailed metadata for the track.
        type (str): Type of the track (e.g., 'video', 'audio', 'subtitles').
    """

    codec: str
    id: int
    properties: TrackProperties
    type: str


@dataclass
class MkvInfo:
    """Top-level representation of MKV file metadata.

    Attributes:
        attachments (list[Attachment]): List of attachments embedded in the file.
        container (Container): Container information and properties.
        tracks (list[Track]): List of all tracks (video, audio, subtitles).
        chapters (list[EntryCount]): List of chapter entries.
        file_name (str): Name of the MKV file.
        global_tags (list[EntryCount]): Global metadata tags.
        identification_format_version (int): Version of the identification format.
        track_tags (list[EntryCount]): Track-specific metadata tags.
        errors (list[str]): Errors encountered while parsing.
        warnings (list[str]): Warnings generated during parsing.
    """

    attachments: list[Attachment]
    container: Container
    tracks: list[Track]
    chapters: list[EntryCount]
    file_name: str
    global_tags: list[EntryCount]
    identification_format_version: int
    track_tags: list[EntryCount]
    errors: list[str]
    warnings: list[str]
