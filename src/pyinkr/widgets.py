from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from msgspec.structs import Struct, asdict
from pymkv.models import MkvMergeOutput
from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Checkbox, ListItem, ListView, Tree
from textual_fspicker import FileOpen

from pyinkr.decorators import catch_errors
from pyinkr.dialogs import DelayScreen, EditScreen

if TYPE_CHECKING:
    from typing import Callable

    from pymkv import MKVTrack
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
    async def on_mount(self) -> None:
        """Mount the tracks when the widget is mounted."""
        async with self.batch():
            await self.extend([self.list_item(track) for track in self.mkv.tracks])
        self.index = 0

    @work(exclusive=True, thread=True)
    @catch_errors()
    async def action_add_track(self) -> None:
        """Add a new track to the MKV file."""
        if path := self.app.call_from_thread(self.app.push_screen_wait, FileOpen()):
            self.app.call_from_thread(setattr, self, "loading", True)
            track = self.mkv.add_track(path)
            self.app.call_from_thread(self.append, self.list_item(track))
            self.app.call_from_thread(setattr, self, "loading", False)
            self.app.call_from_thread(self.focus)

    async def action_toggle_default(self) -> None:
        """Set the selected track as default."""
        track = self.get_track
        track.default_track = not track.default_track
        self.get_checkbox.label = self.formatted_text(track)

    @work(exclusive=True)
    async def action_edit_name(self) -> None:
        """Edit the name of the selected track."""
        await self._edit_track_field(
            title=f"Edit Name — {self._track_label(self.get_track)}",
            placeholder="Enter name...",
            get=lambda t: t.track_name,
            set=self._set_track_name,
        )

    @work(exclusive=True)
    async def action_edit_lang(self) -> None:
        """Edit the language of the selected MKV track."""
        await self._edit_track_field(
            title=f"Edit Language — {self._track_label(self.get_track)}",
            placeholder="Enter Language...",
            get=lambda t: t.language,
            set=self._set_track_lang,
        )

    @work(exclusive=True)
    @catch_errors()
    async def action_edit_delay(self) -> None:
        """Edit the synchronization delay of the selected track."""
        track = self.get_track
        result = await self.app.push_screen_wait(
            DelayScreen(track.sync or 0, title=f"Delay — {self._track_label(track)}")
        )
        if result is not None:
            track.sync = result or None
            self.get_checkbox.label = self.formatted_text(track)

    @staticmethod
    def _track_label(track: "MKVTrack") -> str:
        """A short human label used to identify a track in dialog titles."""
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

    def action_select(self) -> None:
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
        """Return a ListItem representatiOn of the track."""
        return ListItem(Checkbox(self.formatted_text(track), value))

    @property
    def get_checkbox(self) -> "Checkbox":
        """Return the Checkbox widget for the current row."""
        if self.index is None:
            raise ValueError("No track is currently selected.")
        return self.children[self.index].query_one(Checkbox)

    @property
    def get_track(self) -> "MKVTrack":
        """Return the MKVTrack for the current row."""
        if self.index is None:
            raise ValueError("No track is currently selected.")
        return self.mkv.tracks[self.index]

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
        """Called when the component is mounted to the DOM."""

        if info := self.app.mkv.info_json:
            self.info = info

    async def watch_info(self, info: MkvMergeOutput) -> None:
        """
        Reactive watcher for the `data` attribute.

        Args:
            data: The new data value that was set. Can be any decoded JSON structure.
        """

        def struct_to_dict(obj: object) -> dict[str, object] | list[object] | object:
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
        """Edit the title of MKV container."""
        if title := await self.app.push_screen_wait(
            EditScreen(self.app.mkv.title, "Edit MKV Title", "Enter New title...")
        ):
            self.app.mkv.title = title
            self.notify(f"Title updated: {title}", severity="information")


class NoticeWidget(Widget):
    can_focus: bool = True
    """Widget may receive focus."""
    can_focus_children: bool = False
    """Widget's children may receive focus."""

    @override
    def render(self) -> RenderableType:
        return "Press [bold green]o[/] to open a file"
