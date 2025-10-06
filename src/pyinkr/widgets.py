from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Checkbox, ListItem, ListView, Tree
from textual_fspicker import FileOpen

from pyinkr.dialogs import EditScreen
from pyinkr.wrapper.mkvmerge import MkvTrack

if TYPE_CHECKING:
    from rich.console import RenderableType
    from textual.binding import BindingType

    from pyinkr.main import Inkr


class ListTrack(ListView):
    """List of MKV tracks."""

    app: Inkr
    index: reactive[int | None]

    BINDINGS: ClassVar[list[BindingType]] = [
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
        async with self.batch():
            await self.extend([self.list_item(track) for track in self.app.manager.tracks])
        self.index = 0

    @work(exclusive=True)
    async def action_add_track(self) -> None:
        """Add a new track to the MKV file."""
        if path := await self.app.push_screen_wait(FileOpen()):
            try:
                async with self.batch():
                    for track in self.app.manager.add_track(path):
                        self.append(self.list_item(track))
            except Exception as e:
                self.notify(f"Error adding track: {str(e)}", severity="error")

    async def action_toggle_default(self) -> None:
        """Set the selected track as default."""
        track = self.get_track
        track.options.default_track = not track.options.default_track
        self.get_checkbox.label = self.formatted_text(track)

    @work(exclusive=True)
    async def action_edit_name(self) -> None:
        """Edit the name of the selected track."""
        track = self.get_track
        if name := await self.app.push_screen_wait(EditScreen(track.options.track_name, "Edit Name", "Enter name...")):
            track.options.track_name = name
            self.get_checkbox.label = self.formatted_text(track)

    @work(exclusive=True)
    async def action_edit_lang(self) -> None:
        """Edit the language of the selected MKV track."""
        track = self.get_track
        current_lang = track.options.language
        if lang := await self.app.push_screen_wait(EditScreen(current_lang, "Edit Language", "Enter Language...")):
            try:
                track.options.language = lang
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
        if self.index is not None and self.index < len(self.app.manager.tracks) - 1:
            self.app.manager.move_track_forward(self.index)
            self.move_child(self.index, after=self.index + 1)
            self.index += 1

    def formatted_text(self, track: MkvTrack) -> Text:
        """Return formatted text for display in a Checkbox."""
        details = f"{track.options.language or ''} {track.codec or ''} {track.type or ''}".strip()
        default_indicator = " (Default)" if track.options.default_track else ""
        return Text(details, style="bold") + Text(
            f" {track.options.track_name or 'Unnamed'}{default_indicator}",
            style="italic dim bold",
        )

    def list_item(self, track: MkvTrack, value: bool = True) -> ListItem:
        """Return a ListItem representatiOn of the track."""
        return ListItem(Checkbox(self.formatted_text(track), value))

    @property
    def get_checkbox(self) -> Checkbox:
        assert self.index is not None
        return self.children[self.index].query_one(Checkbox)

    @property
    def get_track(self) -> MkvTrack:
        assert self.index is not None
        return self.app.manager.tracks[self.index]


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
    info: reactive[dict[str, object] | None] = reactive(None, init=False)

    @override
    def on_mount(self) -> None:
        """Called when the component is mounted to the DOM."""
        self.info = self.app.manager.raw_info

    async def watch_info(self, info: dict[str, object]) -> None:
        """
        Reactive watcher for the `data` attribute.

        Args:
            data: The new data value that was set. Can be any decoded JSON structure.
        """
        if info:
            self.add_json(info)  # pyright: ignore[reportUnknownMemberType]

    @work(exclusive=True)
    async def action_edit_title(self) -> None:
        """Prompt the user to edit the MKV container title."""
        current_title = self.app.manager.options.title
        if title := await self.app.push_screen_wait(EditScreen(current_title, "Edit MKV Title", "Enter New title...")):
            if not current_title == title:
                self.app.manager.options.title = title
                self.notify(f"Title updated: {title}", severity="information")


class NoticeWidget(Widget):
    can_focus: bool = True
    """Widget may receive focus."""
    can_focus_children: bool = False
    """Widget's children may receive focus."""

    @override
    def render(self) -> RenderableType:
        return "Press [bold green]o[/] to open a file  ⍩⃝"
