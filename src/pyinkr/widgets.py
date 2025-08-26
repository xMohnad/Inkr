from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from textual import on, work
from textual.binding import Binding
from textual.reactive import Reactive
from textual.widgets import Checkbox, ListView, Tree
from textual.widgets._toggle_button import ToggleButton
from textual_fspicker import FileOpen

from pyinkr.screen import EditScreen

if TYPE_CHECKING:
    from rich.console import RenderableType
    from rich.text import TextType

    from pyinkr.main import Inkr


MetadataType = TypeVar("MetadataType")


class CheckboxMeta(Checkbox, Generic[MetadataType]):
    def __init__(
        self,
        label: TextType = "",
        value: bool = False,
        button_first: bool = True,
        metadata: MetadataType = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        tooltip: RenderableType | None = None,
    ) -> None:
        super().__init__(
            label,
            value,
            button_first,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            tooltip=tooltip,
        )
        self.metadata = metadata

    class Changed(ToggleButton.Changed):
        """Posted when the value of the checkbox changes.

        This message can be handled using an `on_checkbox_changed` method.
        """

        @property
        def checkbox(self) -> CheckboxMeta:
            """The checkbox that was changed."""
            assert isinstance(self._toggle_button, CheckboxMeta)
            return self._toggle_button

        @property
        def control(self) -> CheckboxMeta:
            """An alias for [Changed.checkbox][textual.widgets.Checkbox.Changed.checkbox]."""
            return self.checkbox


class ListTrack(ListView):
    """List of MKV tracks."""

    app: Inkr

    BINDINGS = [
        Binding("a", "add_track", "Add"),
        Binding("n", "edit_name", "Name"),
        Binding("l", "edit_lang", "Lang"),
        Binding("d", "toggle_default", "Toggle Default"),
        Binding("space", "select", "Select", show=False),
        Binding("alt+up", "move_up", "Move Up", show=False),
        Binding("alt+down", "move_down", "Move Down", show=False),
    ]

    @work(exclusive=True)
    async def on_mount(self):
        """Mount the tracks when the widget is mounted."""
        self.tracks = self.app.manager.tracks
        async with self.batch():
            await self.clear()
            await self.extend([track.list_item() for track in self.tracks])
        self.index = 0

    @work(exclusive=True)
    async def action_add_track(self):
        """Add a new track to the MKV file."""

        path = await self.app.push_screen_wait(FileOpen())

        async def background_work() -> None:
            """Background task for track processing."""
            try:
                # Process file in background
                track = self.app.manager.add_track(str(path)).list_item()

                # Update UI from main thread
                self.app.call_from_thread(self.append, track)
            except Exception as e:
                self.notify(f"Error adding track: {str(e)}", severity="error")

        # Start background processing
        self.run_worker(
            background_work,
            thread=True,
            exclusive=True,
            name="Add Track Worker",
        )

    async def action_toggle_default(self):
        """Set the selected track as default."""
        if self.index is not None:
            checkbox = self.get_checkbox
            track = checkbox.metadata
            track.toggle_default()
            checkbox.label = track.formatted_text()

    async def action_edit_name(self):
        """Edit the name of the selected track."""
        self.edit_track_attribute("name", "Edit Name", "Enter name...", "name_editor")

    async def action_edit_lang(self):
        """Edit the language of the selected MKV track."""
        self.edit_track_attribute(
            "language", "Edit Language", "Enter Language...", "language_editor"
        )

    @on(CheckboxMeta.Changed)
    def on_changed(self, event: CheckboxMeta.Changed) -> None:
        """Handle checkbox state changes."""
        event.checkbox.metadata.toggle()

    def action_select(self):
        """Toggle selection state of the current track."""
        if self.index is not None:
            self.get_checkbox.toggle()

    async def action_move_up(self):
        """Move the selected track up."""
        if self.index is not None and self.index > 0:
            track = self.get_checkbox.metadata
            self.app.manager.move_track_backward(self.index)
            self.pop(self.index)
            await self.insert(self.index - 1, [track.list_item()])
            self.index -= 1

    async def action_move_down(self):
        """Move the selected track down."""
        if self.index is not None and self.index < len(self.tracks) - 1:
            track = self.get_checkbox.metadata
            self.app.manager.move_track_forward(self.index)
            self.pop(self.index)
            await self.insert(self.index + 2, [track.list_item()])
            self.index += 1

    @work(exclusive=True)
    async def edit_track_attribute(
        self, attribute: str, title: str, placeholder: str, screen_name: str
    ) -> None:
        """Helper function to edit a track attribute."""

        if self.index is None:
            self.notify("No track selected", severity="warning")
            return

        checkbox = self.get_checkbox
        track = checkbox.metadata

        new_value = await self.app.push_screen_wait(
            EditScreen(
                getattr(track, attribute),
                title,
                placeholder,
                name=screen_name,
            )
        )

        if new_value is None or not (new_value := new_value.strip()):
            return

        try:
            setattr(track, attribute, new_value)
            checkbox.label = track.formatted_text()
        except ValueError as e:
            self.notify(str(e), severity="error")

    @property
    def get_checkbox(self):
        return cast(CheckboxMeta, self.children[self.index].children[0])


class InfoTree(Tree[None]):
    """A widget that displays MKV Info."""

    app: Inkr

    data = Reactive(dict[str, Any])
    BINDINGS = [
        Binding("t", "edit_title", "Edit Title"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("h", "scroll_left", show=False),
        Binding("l", "scroll_right", show=False),
    ]

    def on_mount(self):
        self.data = self.app.manager.info_json

    async def watch_data(self, data: dict) -> None:
        """
        Reactive watcher for the `data` attribute.

        Args:
            data (dict): A dictionary representing the new data to display.
                Typically this will be MKV metadata or any JSON-like structure.
        """
        self.clear()
        self.add_json(data, self.root)

    @work(exclusive=True)
    async def action_edit_title(self) -> None:
        """Edit the title of MKV container."""
        title = await self.app.push_screen_wait(
            EditScreen(
                value=self.app.manager.mkv.title,
                title="Edit MKV Title",
                placeholder="Enter new title...",
            )
        )
        if not title:
            return

        try:
            self.app.manager.mkv.title = (new_title := title.strip())
            self.notify(f"Title updated: {new_title.strip()}", severity="information")
        except ValueError as e:
            self.notify(str(e), severity="error")
