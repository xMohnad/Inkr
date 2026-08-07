from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, Horizontal, Middle
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, ProgressBar, Static
from textual_fspicker import SelectDirectory
from typing_extensions import override

from pyinkr import fonts
from pyinkr.decorators import catch_errors

if TYPE_CHECKING:
    from typing import ClassVar

    from textual.binding import BindingType

    from pyinkr.main import Inkr


class EditScreen(ModalScreen[str | None]):
    """A modal screen for editing information."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel")]

    def __init__(
        self,
        value: str | None = None,
        title: str = "Edit",
        placeholder: str = "",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the EditScreen with the given value, title, and placeholder."""
        super().__init__(name=name, id=id, classes=classes)
        self._value: str = value or ""
        self._title: str = title
        self._placeholder: str = placeholder

    @override
    def compose(self) -> ComposeResult:  # noqa: D102 (pure yield chain, no non-obvious behavior)
        yield Header()
        with Container() as container:
            container.border_title = self._title
            yield Input(value=self._value, id="edit-input", placeholder=self._placeholder)
            with Horizontal():
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", id="cancel-btn")
        yield Footer()

    @on(Button.Pressed, "#save-btn")
    @on(Input.Submitted, "#edit-input")
    def save_name(self) -> None:
        """Handle save button press - dismiss with the new value."""
        self.dismiss(self.query_one("#edit-input", Input).value.strip())

    @on(Button.Pressed, "#cancel-btn")
    def action_cancel(self) -> None:
        """Handle cancellation (button or escape key)."""
        self.dismiss(None)


class DelayScreen(ModalScreen[int | None]):
    """A modal screen for adjusting a track's synchronization delay.

    Delay is edited in seconds (matching how players display subtitle/audio
    delay) but stored and returned in milliseconds, since that's the unit
    `MKVTrack.sync` (and mkvmerge's `--sync`) expects.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("plus,equals_sign,up", "increment", "+0.1s"),
        Binding("minus,down", "decrement", "-0.1s"),
        Binding("r", "reset", "Reset"),
    ]

    STEP_MS: ClassVar[int] = 100
    """Amount (in ms) each +/- press adjusts the delay by."""

    def __init__(
        self,
        delay_ms: int = 0,
        title: str = "Track Delay",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the DelayScreen with the given delay (in milliseconds) and title."""
        super().__init__(name=name, id=id, classes=classes)
        self._delay_ms: int = delay_ms
        self._title: str = title

    @override
    def compose(self) -> ComposeResult:  # noqa: D102 (pure yield chain, no non-obvious behavior)
        yield Header()
        with Container() as container:
            container.border_title = self._title
            with Horizontal(id="delay-row"):
                yield Button("-", id="dec-btn", tooltip="Decrease (-, ↓)")
                yield Input(value=self._format(self._delay_ms), id="delay-input")
                yield Button("+", id="inc-btn", tooltip="Increase (+, ↑)")
            with Horizontal(id="action-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", id="cancel-btn")
        yield Footer()

    @staticmethod
    def _format(delay_ms: int) -> str:
        """Format a millisecond delay as seconds, e.g. `250` -> `\"0.25\"`."""
        return f"{delay_ms / 1000:.2f}"

    def _current_ms(self) -> int:
        """Parse the input field, falling back to the last known value."""
        raw = self.query_one("#delay-input", Input).value.strip()
        try:
            return round(float(raw) * 1000)
        except ValueError:
            return self._delay_ms

    def _set_ms(self, delay_ms: int) -> None:
        """Set the delay and refresh the input field."""
        self._delay_ms = delay_ms
        self.query_one("#delay-input", Input).value = self._format(delay_ms)

    @on(Button.Pressed, "#dec-btn")
    def action_decrement(self) -> None:
        """Step the delay down by `STEP_MS`."""
        self._set_ms(self._current_ms() - self.STEP_MS)

    @on(Button.Pressed, "#inc-btn")
    def action_increment(self) -> None:
        """Step the delay up by `STEP_MS`."""
        self._set_ms(self._current_ms() + self.STEP_MS)

    def action_reset(self) -> None:
        """Reset the delay to 0s."""
        self._set_ms(0)

    @on(Button.Pressed, "#save-btn")
    @on(Input.Submitted, "#delay-input")
    def save_delay(self) -> None:
        """Handle save - dismiss with the delay in milliseconds."""
        self.dismiss(self._current_ms())

    @on(Button.Pressed, "#cancel-btn")
    def action_cancel(self) -> None:
        """Handle cancellation (button or escape key)."""
        self.dismiss(None)


class ProgressBarScreen(ModalScreen[None]):
    """A modal screen showing progress for a long-running operation."""

    def __init__(
        self,
        title: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the ProgressBarScreen with the given title."""
        super().__init__(name=name, id=id, classes=classes)
        self._title: str = title
        self._total: float = 100.0

    @override
    def compose(self) -> ComposeResult:  # noqa: D102 (pure yield chain, no non-obvious behavior)
        yield Header()
        with Container() as container:
            container.border_title = self._title
            with Center():
                with Middle():
                    yield ProgressBar(total=self._total)
        yield Footer()

    @property
    def progress_bar(self) -> ProgressBar:
        """Return the ProgressBar widget from the current screen."""
        return self.query_one(ProgressBar)

    def update(self, progress: int) -> None:
        """Update the progress bar, dismissing the screen once `progress` reaches the total."""
        self.progress_bar.update(progress=progress)
        if progress >= self._total:
            self.dismiss(None)


class FontsScreen(ModalScreen[None]):
    """A modal screen listing the fonts a subtitle track needs."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,enter,space", "close", "Close"),
        Binding("i", "import_fonts", "Import"),
    ]

    app: Inkr

    def __init__(
        self,
        info: fonts.SubtitleFontInfo,
        title: str = "Fonts Used",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the FontsScreen with the fonts to display."""
        super().__init__(name=name, id=id, classes=classes)
        self._info: fonts.SubtitleFontInfo = info
        self._title: str = title
        self._usages: list[fonts.FontUsage] = sorted(info.usages, key=lambda u: (u.name.lower(), u.weight, u.italic))

    @override
    def compose(self) -> ComposeResult:  # noqa: D102 (pure yield chain, no non-obvious behavior)
        yield Header()
        with Container(id="fonts-container") as container:
            container.border_title = self._title
            container.border_subtitle = f"{len(self._info.usages)} variant(s)"
            if self._info.has_embedded_fonts:
                yield Static("This subtitle already embeds its own fonts.", id="fonts-note")
            if self._usages:
                yield DataTable(id="fonts-table", cursor_type="row", zebra_stripes=True)
            else:
                with Center():
                    with Middle():
                        yield Static("No fonts found in this subtitle.")
        yield Footer()

    def on_mount(self) -> None:
        """Populate the table once mounted."""
        if usages := self._usages:
            table = self.query_one("#fonts-table", DataTable)
            table.add_columns("Font", "Style", ("Status", "status"))
            for i, usage in enumerate(usages):
                table.add_row(usage.name, self._style_label(usage), "-", key=str(i))

    @staticmethod
    def _style_label(usage: fonts.FontUsage) -> Text:
        """Return a colored 'Bold', 'Italic', 'Bold, Italic', or 'Regular' label."""
        parts = [name for flag, name in ((usage.is_bold, "Bold"), (usage.italic, "Italic")) if flag]
        if not parts:
            return Text("Regular", style="dim")
        return Text(", ".join(parts), style="bold yellow")

    @work(exclusive=True)
    @catch_errors(severity="warning")
    async def action_import_fonts(self) -> None:
        """Import every font this subtitle needs."""
        if not (self.app.font_faces and self._usages):
            return

        from pyinkr.widgets import ListAttachment

        list_view = self.app.screen_stack[-2].query_one(ListAttachment)
        table = self.query_one("#fonts-table", DataTable)

        seen: set[str] = {Path(n.file_path).name for n in self.app.mkv.attachments}
        for i, usage in enumerate(self._usages):
            match = fonts.find_best_match(usage, self.app.font_faces)
            if not match:
                status = Text("Not Found", style="bold red")
            elif match.path.name in seen:
                status = Text("Already Attached", style="bold cyan")
            else:
                seen.add(match.path.name)
                status = Text("Imported", style="bold green")

                a = self.app.mkv.add_attachment(match.path)
                a.description = str(status)
                list_view.add_item(a)

            table.update_cell(str(i), "status", status, update_width=True)

    def action_close(self) -> None:
        """Close the screen."""
        self.dismiss(None)


class PickFolderScreen(ModalScreen[Path | None]):
    """A modal screen for picking a folder."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("s", "save", "Save"),
        Binding("p", "browse", "Browse"),
    ]

    def __init__(
        self,
        value: str | None = None,
        title: str | None = None,
        placeholder: str = "Path to a folder...",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the folder picker."""
        super().__init__(name=name, id=id, classes=classes)
        self._value: str | None = value
        self._title: str | None = title
        self._placeholder: str = placeholder

    @override
    def compose(self) -> ComposeResult:  # noqa: D102 (pure yield chain, no non-obvious behavior)
        yield Header()
        with Container() as container:
            container.border_title = self._title
            with Horizontal(id="folder-row"):
                yield Input(
                    value=self._value,
                    placeholder=self._placeholder,
                    id="folder-input",
                )
                yield Button("Browse", id="browse-btn")
            with Horizontal(id="action-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", id="cancel-btn")
        yield Footer()

    @on(Button.Pressed, "#browse-btn")
    @work(exclusive=True)
    async def action_browse(self) -> None:
        """Open folder picker."""
        folder_input = self.query_one("#folder-input", Input)
        value = folder_input.value.strip()
        location = Path(value if value else ".")

        if location.is_file():
            location = location.parent

        while not location.exists() and location != location.parent:
            location = location.parent

        if not location.exists():
            location = Path(".")

        if path := await self.app.push_screen_wait(SelectDirectory(location=location)):
            folder_input.value = str(path)

    @on(Button.Pressed, "#save-btn")
    def action_save(self) -> None:
        """Dismiss with the selected folder."""
        folder_input = self.query_one("#folder-input", Input)
        value = folder_input.value.strip()
        path = Path(value) if value else None

        if not path or not path.is_dir():
            folder_input.add_class("-invalid")
            self.notify("Please enter a valid folder path.", severity="error")
            return

        self.dismiss(path)

    @on(Button.Pressed, "#cancel-btn")
    def action_cancel(self) -> None:
        """Handle cancellation (button or escape key)."""
        self.dismiss(None)
