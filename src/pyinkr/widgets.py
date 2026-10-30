from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar

import msgspec
from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Checkbox, ListItem, ListView, Tree
from textual_fspicker import FileOpen
from typing_extensions import override

from pyinkr import fonts
from pyinkr.dialogs import DelayScreen, EditScreen, FontsScreen

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import ClassVar

    from pymkv import MKVAttachment, MKVTrack
    from pymkv.models import MkvMergeOutput
    from rich.console import RenderableType
    from textual.app import ComposeResult
    from textual.binding import BindingType
    from textual.widget import AwaitMount

    from pyinkr.main import Inkr
    from pyinkr.services import MkvService


ItemT = TypeVar("ItemT")


class ChecklistView(ListView, Generic[ItemT]):
    """Base for a `ListView` of checkbox items."""

    app: Inkr

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add", "Add"),
        Binding("enter,space", "toggle_button", "Toggle", show=False),
    ]

    @override
    def compose(self) -> ComposeResult:
        for item in self.items:
            yield self.list_item(item)

    @override
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Check if an action may run."""
        return action == "add" or not self.is_empty

    @property
    def mkv(self) -> MkvService:
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

    def add_item(self, item: ItemT) -> AwaitMount:
        """Append `item` to the list and select it."""
        return self.append(self.list_item(item))

    @property
    def checkbox(self) -> Checkbox:
        """Return the Checkbox widget for the currently selected item."""
        assert self.index is not None
        return self.children[self.index].query_one(Checkbox)

    @property
    def item(self) -> ItemT:
        """Return the currently selected domain object."""
        assert self.index is not None
        return self.items[self.index]

    def action_toggle_button(self) -> None:
        """Toggle selection state of the current item."""
        self.checkbox.toggle()

    @work(exclusive=True)
    async def action_edit(
        self,
        field: str,
        attr: str | None = None,
        placeholder: str | None = None,
    ) -> None:
        """Shared flow for editing a single string field on the selected item."""
        if placeholder is None:
            placeholder = f"Enter {field}..."
        if attr is None:
            attr = field
        item = self.item
        title = f"Edit {field.capitalize()} — {self.label(item)}"
        value = await self.app.push_screen_wait(EditScreen(getattr(item, attr), title, placeholder))
        if value is not None:
            try:
                setattr(item, attr, value)
                self.checkbox.label = self.formatted_text(item)
            except ValueError as e:
                self.notify(str(e), severity="error")


class ListTrack(ChecklistView["MKVTrack"]):
    """List of MKV tracks."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("n", "edit('name', 'track_name')", "Name"),
        Binding("l", "edit('language')", "Lang"),
        Binding("y", "edit_delay", "Delay"),
        Binding("d", "toggle_default", "Toggle Default"),
        Binding("f", "check_fonts", "Fonts"),
        Binding("alt+up", "move_track(-1)", "Move Up", show=False),
        Binding("alt+down", "move_track(1)", "Move Down", show=False),
    ]

    @property
    @override
    def items(self) -> Sequence[MKVTrack]:
        return self.mkv.tracks

    @staticmethod
    @override
    def label(item: MKVTrack) -> str:
        """Build a short human label used to identify a track in dialog titles."""
        kind = (item.track_type or "track").capitalize()
        name = item.track_name or "Unnamed"
        return f"{kind}: {name.strip()}"

    @work(exclusive=True, thread=True)
    async def action_add(self) -> None:
        """Add a new track from a file."""
        if path := self.app.call_from_thread(self.app.push_screen_wait, FileOpen()):
            self.app.call_from_thread(self.set_loading, True)
            try:
                assert isinstance(path, Path)
                track = self.mkv.add_track(path)
                self.app.call_from_thread(self.add_item, track)
            except ValueError as e:
                self.notify(str(e), severity="error")
            finally:
                self.app.call_from_thread(self.set_loading, False)

    def action_toggle_default(self) -> None:
        """Toggle the default flag on the selected track."""
        track = self.item
        track.default_track = not track.default_track
        self.checkbox.label = self.formatted_text(track)

    @work(exclusive=True)
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
    async def action_check_fonts(self) -> None:
        """Show the fonts required by the selected subtitle track."""
        track = self.item
        self.app.call_from_thread(self.set_loading, True)
        try:
            info = fonts.analyze_subtitle_fonts(track)
            self.app.call_from_thread(
                self.app.push_screen,
                FontsScreen(info, title=f"Fonts — {self.label(track)}"),
            )
        except ValueError as e:
            self.notify(str(e), severity="warning")
        finally:
            self.app.call_from_thread(self.set_loading, False)

    def action_move_track(self, delta: int) -> None:
        """Move the selected track by `delta` positions."""
        index = self.index
        if index is None:
            return

        new_index = index + delta
        if 0 <= new_index < len(self):
            if delta < 0:
                self.mkv.move_track_up(index)
                self.move_child(index, before=new_index)
            else:
                self.mkv.move_track_down(index)
                self.move_child(index, after=new_index)

            self.index = new_index

    @override
    def formatted_text(self, item: MKVTrack) -> Text:
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
        Binding("n", "edit('name')", "Name"),
        Binding("e", "edit('description')", "Description"),
    ]

    @property
    @override
    def items(self) -> Sequence[MKVAttachment]:
        return self.mkv.attachments

    @staticmethod
    @override
    def label(item: MKVAttachment) -> str:
        """Build a short human label used to identify an attachment in dialog titles."""
        return item.name or Path(item.file_path).name

    @work(exclusive=True)
    async def action_add(self) -> None:
        """Add a new attachment from a file."""
        if path := await self.app.push_screen_wait(FileOpen()):
            attachment = self.mkv.add_attachment(path)
            self.add_item(attachment)

    @override
    def formatted_text(self, item: MKVAttachment) -> Text:
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

    def watch_info(self, info: MkvMergeOutput | None) -> None:
        """Update the tree when info changes."""
        if info:
            self.add_json(msgspec.to_builtins(info))
        else:
            self.info = self.app.mkv.info_json

    @work(exclusive=True)
    async def action_edit_title(self) -> None:
        """Edit the MKV container title."""
        mkv = self.app.mkv.manager
        title = await self.app.push_screen_wait(
            EditScreen(mkv.title, "Edit MKV Title", "Enter title..."),
        )
        if title is not None:
            mkv.title = title


class NoticeWidget(Widget):
    """A widget that displays notices."""

    can_focus: bool = True
    """Widget may receive focus."""
    can_focus_children: bool = False
    """Widget's children may receive focus."""

    @override
    def render(self) -> RenderableType:
        return "Press [bold green]o[/] to open a file"
