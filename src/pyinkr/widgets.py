from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Checkbox, ListItem, ListView, Tree
from textual_fspicker import FileOpen

from pyinkr.dialogs import EditScreen

if TYPE_CHECKING:
    from pymkv import MKVTrack
    from rich.console import RenderableType

    from pyinkr.main import Inkr


class ListTrack(ListView):
    """List of MKV tracks."""

    app: Inkr

    BINDINGS = [
        Binding("a", "add_track", "Add"),
        Binding("n", "edit_name", "Name"),
        Binding("l", "edit_lang", "Lang"),
        Binding("d", "toggle_default", "Toggle Default"),
        Binding("enter,space", "select", "Select", show=False),
        Binding("alt+up", "move_up", "Move Up", show=False),
        Binding("alt+down", "move_down", "Move Down", show=False),
    ]

    @work(exclusive=True)
    async def on_mount(self) -> None:
        """Mount the tracks when the widget is mounted."""
        self.tracks = self.app.manager.tracks
        async with self.batch():
            await self.extend([self.list_item(track) for track in self.tracks])
        self.index = 0

    @work(exclusive=True)
    async def action_add_track(self) -> None:
        """Add a new track to the MKV file."""
        if path := await self.app.push_screen_wait(FileOpen()):
            try:
                self.app.manager.add_track(str(path))
                track = self.list_item(self.tracks[-1])
                self.append(track)
            except Exception as e:
                self.notify(f"Error adding track: {str(e)}", severity="error")

    async def action_toggle_default(self) -> None:
        """Set the selected track as default."""
        track = self.get_track
        track.default_track = not track.default_track
        self.get_checkbox.label = self.formatted_text(track)

    @work(exclusive=True)
    async def action_edit_name(self) -> None:
        """Edit the name of the selected track."""
        track = self.get_track
        if name := await self.app.push_screen_wait(EditScreen(track.track_name, "Edit Name", "Enter name...")):
            try:
                track.track_name = name
                self.get_checkbox.label = self.formatted_text(track)
            except Exception as e:
                self.notify(f"Error: {str(e)}", severity="error")

    @work(exclusive=True)
    async def action_edit_lang(self) -> None:
        """Edit the language of the selected MKV track."""
        track = self.get_track
        if lang := await self.app.push_screen_wait(EditScreen(track.language, "Edit Language", "Enter Language...")):
            try:
                track.language = lang
                self.get_checkbox.label = self.formatted_text(track)
            except Exception as e:
                self.notify(f"Error: {str(e)}", severity="error")

    def action_select(self) -> None:
        """Toggle selection state of the current track."""
        if self.index is not None:
            self.get_checkbox.toggle()

    async def action_move_up(self) -> None:
        """Move the selected track up."""
        if self.index is not None and self.index > 0:
            self.app.manager.move_track_backward(self.index)
            self.move_child(self.index, before=self.index - 1)
            self.index -= 1

    async def action_move_down(self) -> None:
        """Move the selected track down."""
        if self.index is not None and self.index < len(self.tracks) - 1:
            self.app.manager.move_track_forward(self.index)
            self.move_child(self.index, after=self.index + 1)
            self.index += 1

    def formatted_text(self, track: "MKVTrack") -> Text:
        """Return formatted text for display in a Checkbox."""
        details = f"{track.language or ''} {track.track_codec or ''} {track.track_type or ''}".strip()
        default_indicator = " (Default)" if track.default_track else ""
        return Text(details, style="bold") + Text(
            f" {track.track_name or 'Unnamed'}{default_indicator}",
            style="italic dim bold",
        )

    def list_item(self, track: "MKVTrack", value: bool = True) -> ListItem:
        """Return a ListItem representatiOn of the track."""
        return ListItem(Checkbox(self.formatted_text(track), value))

    @property
    def get_checkbox(self) -> "Checkbox":
        assert self.index is not None
        return self.children[self.index].query_one(Checkbox)

    @property
    def get_track(self) -> "MKVTrack":
        assert self.index is not None
        return self.tracks[self.index]


class InfoTree(Tree[None]):
    """A widget that displays MKV Info."""

    BINDINGS = [
        Binding("t", "edit_title", "Edit Title"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("h", "scroll_left", show=False),
        Binding("l", "scroll_right", show=False),
    ]

    app: Inkr
    data: reactive[dict[Any, Any] | None] = reactive(None, init=False)

    def on_mount(self) -> None:
        """Called when the component is mounted to the DOM."""
        self.data = self.app.manager._info_json

    async def watch_data(self, data: Optional[dict[Any, Any]]) -> None:
        """
        Reactive watcher for the `data` attribute.

        Args:
            data: The new data value that was set. Can be any decoded JSON structure.
        """
        if data:
            self.add_json(data)

    @work(exclusive=True)
    async def action_edit_title(self) -> None:
        """Edit the title of MKV container."""
        if title := await self.app.push_screen_wait(
            EditScreen(self.app.manager.title, "Edit MKV Title", "Enter New title...")
        ):
            try:
                self.app.manager.title = title
                self.notify(f"Title updated: {title}", severity="information")
            except ValueError as e:
                self.notify(str(e), severity="error")


class NoticeWidget(Widget):
    can_focus: bool = True
    """Widget may receive focus."""
    can_focus_children: bool = False
    """Widget's children may receive focus."""

    def render(self) -> RenderableType:
        return "Press [bold green]o[/] to open a file  ⍩⃝"
