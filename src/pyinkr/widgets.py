from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar

import msgspec
from pymkv.models import MkvMergeOutput
from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Checkbox, ListItem, ListView, Tree
from textual_fspicker import FileOpen
from typing_extensions import override

from pyinkr import fonts
from pyinkr.decorators import catch_errors
from pyinkr.dialogs import DelayScreen, EditScreen, FontsScreen

if TYPE_CHECKING:
    from typing import ClassVar

    from pymkv import MKVAttachment, MKVTrack
    from rich.console import RenderableType
    from textual.binding import BindingType

    from pyinkr.main import Inkr
    from pyinkr.services import MkvService


ItemT = TypeVar("ItemT")


class ChecklistView(ListView, Generic[ItemT]):
    """Base for a `ListView` of checkbox items."""

    app: Inkr

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter,space", "toggle_button", "Toggle", show=False),
    ]

    @work(exclusive=True)
    async def on_mount(self) -> None:
        """Load items when mounted."""
        items = self.items
        async with self.batch():
            await self.extend([self.list_item(item) for item in items])
        self.index = 0 if items else None

    @property
    def mkv(self) -> "MkvService":
        """Return the application's MKV service."""
        return self.app.mkv

    @property
    def items(self) -> Sequence[ItemT]:
        """Return the domain objects backing this list, in display order."""
        raise NotImplementedError

    def formatted_text(self, item: ItemT) -> Text:
        """Return formatted text for display in a Checkbox."""
        raise NotImplementedError

    @staticmethod
    def label(item: ItemT) -> str:
        """Return a short human label used to identify `item` in dialog titles."""
        raise NotImplementedError

    def list_item(self, item: ItemT) -> ListItem:
        """Return a ListItem representation of `item`."""
        return ListItem(Checkbox(self.formatted_text(item), True))

    async def add_item(self, item: ItemT) -> None:
        """Append `item` to the list and select it."""
        await self.append(self.list_item(item))
        self.loading = False
        self.index = len(self) - 1
        self.focus()

    @property
    def checkbox(self) -> "Checkbox":
        """Return the Checkbox widget for the currently selected item."""
        if self.index is None:
            raise ValueError("No item is currently selected.")
        return self.children[self.index].query_one(Checkbox)

    @property
    def item(self) -> ItemT:
        """Return the currently selected domain object."""
        if self.index is None:
            raise ValueError("No item is currently selected.")
        return self.items[self.index]

    @catch_errors()
    async def action_toggle_button(self) -> None:
        """Toggle selection state of the current item."""
        self.checkbox.toggle()

    @work(exclusive=True)
    @catch_errors()
    async def edit_field(
        self,
        *,
        field: str,
        placeholder: str,
        attr: str,
    ) -> None:
        """Shared flow for editing a single string field on the selected item."""
        item = self.item
        title = f"Edit {field} — {self.label(item)}"
        if value := await self.app.push_screen_wait(EditScreen(getattr(item, attr), title, placeholder)):
            setattr(item, attr, value)
            self.checkbox.label = self.formatted_text(item)


class ListTrack(ChecklistView["MKVTrack"]):
    """List of MKV tracks."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add_track", "Add"),
        Binding("n", "edit_name", "Name"),
        Binding("l", "edit_lang", "Lang"),
        Binding("y", "edit_delay", "Delay"),
        Binding("d", "toggle_default", "Toggle Default"),
        Binding("f", "check_fonts", "Fonts"),
        Binding("alt+up", "move_up", "Move Up", show=False),
        Binding("alt+down", "move_down", "Move Down", show=False),
    ]

    @property
    @override
    def items(self) -> Sequence["MKVTrack"]:
        return self.mkv.tracks

    @staticmethod
    @override
    def label(item: "MKVTrack") -> str:
        """Build a short human label used to identify a track in dialog titles."""
        kind = (item.track_type or "track").capitalize()
        name = item.track_name or "Unnamed"
        return f"{kind}: {name.strip()}"

    @work(exclusive=True, thread=True)
    @catch_errors()
    async def action_add_track(self) -> None:
        """Add a new track from a file."""
        if path := self.app.call_from_thread(lambda: self.app.push_screen_wait(FileOpen())):
            self.app.call_from_thread(setattr, self, "loading", True)
            track = self.mkv.add_track(path)
            self.app.call_from_thread(self.add_item, track)

    async def action_toggle_default(self) -> None:
        """Toggle the default flag on the selected track."""
        track = self.item
        track.default_track = not track.default_track
        self.checkbox.label = self.formatted_text(track)

    def action_edit_name(self) -> None:
        """Edit the track name."""
        self.edit_field(field="Name", placeholder="Enter name...", attr="track_name")

    def action_edit_lang(self) -> None:
        """Edit the track language."""
        self.edit_field(field="Language", placeholder="Enter language...", attr="language")

    @work(exclusive=True)
    @catch_errors()
    async def action_edit_delay(self) -> None:
        """Edit the track sync delay."""
        track = self.item
        result = await self.app.push_screen_wait(
            DelayScreen(track.sync or 0, title=f"Delay — {self.label(track)}"),
        )
        if result is not None:
            track.sync = result or None
            self.checkbox.label = self.formatted_text(track)

    @work(exclusive=True, thread=True)
    @catch_errors(severity="warning")
    async def action_check_fonts(self) -> None:
        """Show the fonts required by the selected subtitle track."""
        track = self.item
        self.app.call_from_thread(setattr, self, "loading", True)
        try:
            info = fonts.analyze_subtitle_fonts(track)
            self.app.call_from_thread(
                self.app.push_screen,
                FontsScreen(info, title=f"Fonts — {self.label(track)}"),
            )
        finally:
            self.app.call_from_thread(setattr, self, "loading", False)

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

    @override
    def formatted_text(self, item: "MKVTrack") -> Text:
        """Return formatted text for display in a Checkbox."""
        name = item.track_name or "Unnamed"
        lang = item.language or "und"
        codec = item.track_codec or "?"

        text = Text(name, style="bold")
        text += Text(f"  [{lang} · {codec}]", style="dim")
        if item.default_track:
            text += Text("  DEFAULT", style="bold green")
        if item.sync:
            sign = "+" if item.sync > 0 else ""
            text += Text(f"  ⏱ {sign}{item.sync / 1000:.2f}s", style="italic yellow")
        return text


class ListAttachment(ChecklistView["MKVAttachment"]):
    """List of MKV attachments."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add_attachment", "Add"),
        Binding("n", "edit_name", "Name"),
        Binding("e", "edit_description", "Description"),
    ]

    @property
    @override
    def items(self) -> Sequence["MKVAttachment"]:
        return self.mkv.attachments

    @staticmethod
    @override
    def label(item: "MKVAttachment") -> str:
        """Build a short human label used to identify an attachment in dialog titles."""
        return item.name or Path(item.file_path).name

    @work(exclusive=True)
    @catch_errors()
    async def action_add_attachment(self) -> None:
        """Add a new attachment from a file."""
        if path := await self.app.push_screen_wait(FileOpen()):
            attachment = self.mkv.add_attachment(path)
            await self.add_item(attachment)

    def action_edit_name(self) -> None:
        """Edit the attachment name."""
        self.edit_field(field="Name", placeholder="Enter name...", attr="name")

    def action_edit_description(self) -> None:
        """Edit the attachment description."""
        self.edit_field(field="Description", placeholder="Enter description...", attr="description")

    @override
    def formatted_text(self, item: "MKVAttachment") -> Text:
        """Return formatted text for display in the list."""
        name = self.label(item)
        mime = item.mime_type or "?"

        text = Text(name, style="bold")
        text += Text(f"  [{mime}]", style="dim")
        if item.description:
            text += Text(f"  — {item.description}", style="italic")
        return text


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
    info: reactive[MkvMergeOutput | None] = reactive(None)

    async def watch_info(self, info: MkvMergeOutput | None) -> None:
        """Update the tree when info changes."""

        if info:
            self.add_json(msgspec.to_builtins(info))
        else:
            self.info = self.app.mkv.info_json

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
