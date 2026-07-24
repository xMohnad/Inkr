from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, Horizontal, Middle
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, ProgressBar
from typing_extensions import override

if TYPE_CHECKING:
    from typing import ClassVar

    from textual.binding import BindingType


class EditScreen(ModalScreen[str | None]):
    """A modal screen for editing information."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "back", "Back")]

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
    def action_back(self) -> None:
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
