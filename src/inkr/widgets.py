from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, cast

from textual import on, work
from textual.binding import Binding
from textual.widgets import Checkbox, ListView
from textual.widgets._toggle_button import ToggleButton
from textual_fspicker import FileOpen

if TYPE_CHECKING:
    from rich.console import RenderableType
    from rich.text import TextType

    from inkr.main import Inkr


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
        Binding("space", "select", "Select", show=False),
        Binding("o", "open_video", "Open Video", show=False),
        Binding("alt+up", "move_up", "Move Up", show=False),
        Binding("alt+down", "move_down", "Move Down", show=False),
    ]

    @work(exclusive=True)
    async def on_mount(self):
        """Mount the tracks when the widget is mounted."""
        if hasattr(self.app, "mkv_manager"):
            self.tracks = self.app.mkv_manager.tracks
            async with self.batch():
                await self.clear()
                await self.extend([track.list_item() for track in self.tracks])
            self.index = 0
            self.focus()

    @work(exclusive=True)
    async def action_add_track(self):
        if not hasattr(self.app, "mkv_manager"):
            return self.notify("Open MKV First")

        path = await self.app.push_screen(FileOpen(), wait_for_dismiss=True)
        if not path:
            return self.notify("Canceled")

        self.append(self.app.mkv_manager.add_track(str(path)).list_item())

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
            self.app.mkv_manager.move_track_backward(self.index)
            self.pop(self.index)
            await self.insert(self.index - 1, [track.list_item()])
            self.index -= 1

    async def action_move_down(self):
        """Move the selected track down."""
        if self.index is not None and self.index < len(self.tracks) - 1:
            track = self.get_checkbox.metadata
            self.app.mkv_manager.move_track_forward(self.index)
            self.pop(self.index)
            await self.insert(self.index + 2, [track.list_item()])
            self.index += 1

    @property
    def get_checkbox(self):
        return cast(CheckboxMeta, self.children[self.index].children[0])
