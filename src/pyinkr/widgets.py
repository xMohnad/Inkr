from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from msgspec.structs import Struct, asdict
from pymkv.models import MkvMergeOutput
from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Checkbox, ListItem, ListView, Tree
from textual_fspicker import FileOpen
from typing_extensions import override

from pyinkr.decorators import catch_errors
from pyinkr.dialogs import DelayScreen, EditScreen

if TYPE_CHECKING:
    from typing import Callable

    from pymkv import MKVAttachment, MKVTrack
    from rich.console import RenderableType
    from textual.binding import BindingType

    from pyinkr.main import Inkr
    from pyinkr.services import MkvService


class ListTrack(ListView):
    """List of MKV tracks."""

    app: Inkr

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add_track", "Add"),
        Binding("n", "edit_name", "Name"),
        Binding("l", "edit_lang", "Lang"),
        Binding("y", "edit_delay", "Delay"),
        Binding("d", "toggle_default", "Toggle Default"),
        Binding("enter,space", "select", "Select", show=False),
        Binding("alt+up", "move_up", "Move Up", show=False),
        Binding("alt+down", "move_down", "Move Down", show=False),
    ]

    @work(exclusive=True)
    @override
    async def on_mount(self) -> None:
        """Load tracks when mounted."""
        async with self.batch():
            await self.extend([self.list_item(track) for track in self.mkv.tracks])
        self.index: int = 0

    @work(exclusive=True, thread=True)
    @catch_errors()
    async def action_add_track(self) -> None:
        """Add a new track from a file."""
        if path := self.app.call_from_thread(self.app.push_screen_wait, FileOpen()):
            self.app.call_from_thread(setattr, self, "loading", True)
            track = self.mkv.add_track(path)
            self.app.call_from_thread(self.append, self.list_item(track))
            self.app.call_from_thread(setattr, self, "loading", False)
            self.app.call_from_thread(self.focus)

    async def action_toggle_default(self) -> None:
        """Toggle the default flag on the selected track."""
        track = self.get_track
        track.default_track = not track.default_track
        self.get_checkbox.label = self.formatted_text(track)

    @work(exclusive=True)
    async def action_edit_name(self) -> None:
        """Edit the track name."""
        await self._edit_track_field(
            title=f"Edit Name — {self._track_label(self.get_track)}",
            placeholder="Enter name...",
            get=lambda t: t.track_name,
            set=self._set_track_name,
        )

    @work(exclusive=True)
    async def action_edit_lang(self) -> None:
        """Edit the track language."""
        await self._edit_track_field(
            title=f"Edit Language — {self._track_label(self.get_track)}",
            placeholder="Enter language...",
            get=lambda t: t.language,
            set=self._set_track_lang,
        )

    @work(exclusive=True)
    @catch_errors()
    async def action_edit_delay(self) -> None:
        """Edit the track sync delay."""
        track = self.get_track
        result = await self.app.push_screen_wait(
            DelayScreen(track.sync or 0, title=f"Delay — {self._track_label(track)}")
        )
        if result is not None:
            track.sync = result or None
            self.get_checkbox.label = self.formatted_text(track)

    @staticmethod
    def _track_label(track: "MKVTrack") -> str:
        """Build a short human label used to identify a track in dialog titles."""
        kind = (track.track_type or "track").capitalize()
        name = track.track_name or "Unnamed"
        return f"{kind}: {name.strip()}"

    @catch_errors()
    async def _edit_track_field(
        self,
        *,
        title: str,
        placeholder: str,
        get: "Callable[[MKVTrack], str | None]",
        set: "Callable[[MKVTrack, str], None]",
    ) -> None:
        """Shared flow for editing a single string field on the selected track."""
        track = self.get_track
        if value := await self.app.push_screen_wait(EditScreen(get(track), title, placeholder)):
            set(track, value)
            self.get_checkbox.label = self.formatted_text(track)

    @staticmethod
    def _set_track_name(track: "MKVTrack", value: str) -> None:
        track.track_name = value

    @staticmethod
    def _set_track_lang(track: "MKVTrack", value: str) -> None:
        track.language = value

    @catch_errors()
    async def action_select(self) -> None:
        """Toggle selection state of the current track."""
        self.get_checkbox.toggle()

    async def action_move_up(self) -> None:
        """Move the selected track up."""
        if self.index is not None and self.index > 0:
            self.mkv.move_track_up(self.index)
            self.move_child(self.index, before=self.index - 1)
            self.index -= 1

    async def action_move_down(self) -> None:
        """Move the selected track down."""
        if self.index is not None and self.index < len(self.mkv.tracks) - 1:
            self.mkv.move_track_down(self.index)
            self.move_child(self.index, after=self.index + 1)
            self.index += 1

    def formatted_text(self, track: "MKVTrack") -> Text:
        """Return formatted text for display in a Checkbox."""
        name = track.track_name or "Unnamed"
        lang = track.language or "und"
        codec = track.track_codec or "?"

        text = Text(name, style="bold")
        text += Text(f"  [{lang} · {codec}]", style="dim")
        if track.default_track:
            text += Text("  DEFAULT", style="bold green")
        if track.sync:
            sign = "+" if track.sync > 0 else ""
            text += Text(f"  ⏱ {sign}{track.sync / 1000:.2f}s", style="italic yellow")
        return text

    def list_item(self, track: "MKVTrack", value: bool = True) -> ListItem:
        """Return a ListItem representation of the track."""
        return ListItem(Checkbox(self.formatted_text(track), value))

    @property
    def get_checkbox(self) -> "Checkbox":
        """Return the Checkbox widget for the currently selected track."""
        if self.index is None:
            raise ValueError("No track is currently selected.")
        return self.children[self.index].query_one(Checkbox)

    @property
    def get_track(self) -> "MKVTrack":
        """Return the currently selected track."""
        if self.index is None:
            raise ValueError("No track is currently selected.")
        return self.mkv.tracks[self.index]

    @property
    def mkv(self) -> "MkvService":
        """Return the application's MKV service."""
        return self.app.mkv


class ListAttachment(ListView):
    """List of MKV attachments."""

    app: Inkr

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add_attachment", "Add"),
        Binding("n", "edit_name", "Name"),
        Binding("e", "edit_description", "Description"),
        Binding("enter,space", "select", "Select", show=False),
    ]

    @work(exclusive=True)
    @override
    async def on_mount(self) -> None:
        """Load attachments when mounted."""
        async with self.batch():
            await self.extend([self.list_item(attachment) for attachment in self.mkv.attachments])
        self.index: int | None = 0

    @work(exclusive=True, thread=True)
    @catch_errors()
    async def action_add_attachment(self) -> None:
        """Add a new attachment from a file."""
        if path := self.app.call_from_thread(self.app.push_screen_wait, FileOpen()):
            attachment = self.mkv.add_attachment(path)
            self.app.call_from_thread(self.append, self.list_item(attachment))
            self.app.call_from_thread(self.focus)

    @catch_errors()
    async def action_select(self) -> None:
        """Toggle the selected attachment."""
        self.get_checkbox.toggle()

    @work(exclusive=True)
    async def action_edit_name(self) -> None:
        """Edit the attachment name."""
        await self._edit_attachment_field(
            title=f"Edit Name — {self._attachment_label(self.get_attachment)}",
            placeholder="Enter name...",
            get=lambda a: a.name,
            set=self._set_attachment_name,
        )

    @work(exclusive=True)
    async def action_edit_description(self) -> None:
        """Edit the attachment description."""
        await self._edit_attachment_field(
            title=f"Edit Description — {self._attachment_label(self.get_attachment)}",
            placeholder="Enter description...",
            get=lambda a: a.description,
            set=self._set_attachment_description,
        )

    @staticmethod
    def _attachment_label(attachment: "MKVAttachment") -> str:
        """Build a short human label used to identify an attachment in dialog titles."""
        return attachment.name or Path(attachment.file_path).name

    @catch_errors()
    async def _edit_attachment_field(
        self,
        *,
        title: str,
        placeholder: str,
        get: "Callable[[MKVAttachment], str | None]",
        set: "Callable[[MKVAttachment, str], None]",
    ) -> None:
        """Shared flow for editing a single string field on the selected attachment."""
        attachment = self.get_attachment
        if value := await self.app.push_screen_wait(EditScreen(get(attachment), title, placeholder)):
            set(attachment, value)
            self.get_checkbox.label = self.formatted_text(attachment)

    @staticmethod
    def _set_attachment_name(attachment: "MKVAttachment", value: str) -> None:
        attachment.name = value

    @staticmethod
    def _set_attachment_description(attachment: "MKVAttachment", value: str) -> None:
        attachment.description = value

    def formatted_text(self, attachment: "MKVAttachment") -> Text:
        """Return formatted text for display in the list."""
        name = self._attachment_label(attachment)
        mime = attachment.mime_type or "?"

        text = Text(name, style="bold")
        text += Text(f"  [{mime}]", style="dim")
        if attachment.description:
            text += Text(f"  — {attachment.description}", style="italic")
        return text

    def list_item(self, attachment: "MKVAttachment", value: bool = True) -> ListItem:
        """Return a ListItem representation of the attachment."""
        return ListItem(Checkbox(self.formatted_text(attachment), value))

    @property
    def get_checkbox(self) -> "Checkbox":
        """Return the Checkbox widget for the currently selected attachment."""
        if self.index is None:
            raise ValueError("No attachment is currently selected.")
        return self.children[self.index].query_one(Checkbox)

    @property
    def get_attachment(self) -> "MKVAttachment":
        """Return the currently selected attachment."""
        if self.index is None:
            raise ValueError("No attachment is currently selected.")
        return self.mkv.attachments[self.index]

    @property
    def mkv(self) -> "MkvService":
        """Return the application's MKV service."""
        return self.app.mkv


class InfoTree(Tree[None]):
    """A widget that displays MKV Info."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("t", "edit_title", "Edit Title"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("h", "scroll_left", show=False),
        Binding("l", "scroll_right", show=False),
    ]

    app: Inkr
    info: reactive[MkvMergeOutput | None] = reactive(None, init=False)

    @override
    def on_mount(self) -> None:
        """Initialize the tree when mounted."""
        if info := self.app.mkv.info_json:
            self.info = info

    async def watch_info(self, info: MkvMergeOutput | None) -> None:
        """Update the tree when info changes."""

        def struct_to_dict(obj: object) -> dict[str, object] | list[object] | object:
            """Convert msgspec Struct objects to nested dictionaries."""
            if isinstance(obj, Struct):
                return {k: struct_to_dict(v) for k, v in asdict(obj).items()}
            elif isinstance(obj, list):
                return [struct_to_dict(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: struct_to_dict(v) for k, v in obj.items()}
            else:
                return obj

        if info:
            self.add_json(struct_to_dict(info))

    @work(exclusive=True)
    @catch_errors()
    async def action_edit_title(self) -> None:
        """Edit the MKV container title."""
        if title := await self.app.push_screen_wait(
            EditScreen(self.app.mkv.title, "Edit MKV Title", "Enter new title...")
        ):
            self.app.mkv.title = title
            self.notify(f"Title updated: {title}", title="Title Updated", severity="information")


class NoticeWidget(Widget):
    """A widget that displays notices."""

    can_focus: bool = True
    """Widget may receive focus."""
    can_focus_children: bool = False
    """Widget's children may receive focus."""

    @override
    def render(self) -> RenderableType:  # noqa: D102 (pure yield/return, no non-obvious behavior)
        return "Press [bold green]o[/] to open a file"
