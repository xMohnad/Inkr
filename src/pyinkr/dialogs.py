from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input

if TYPE_CHECKING:
    from typing import ClassVar, override

    from textual.binding import BindingType


class EditScreen(ModalScreen[str | None]):
    """A modal screen for editing information"""

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
        """
        Initialize the EditScreen.

        Args:
            value: The initial value for the input field.
            title: The title to display at the top of the screen.
            placeholder: Optional placeholder text for the input.
            name: The name of the screen.
            id: The ID of the screen.
            classes: The CSS classes for the screen.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._value: str = value or ""
        self._title: str = title
        self._placeholder: str = placeholder

    @override
    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
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
        """Handles cancellation (button or escape key)."""
        self.dismiss(None)
