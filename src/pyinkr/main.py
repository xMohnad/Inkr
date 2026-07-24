from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import App
from textual.reactive import Reactive

from pyinkr.screen import MkvManagScreen, OpenScreen
from pyinkr.services import MkvService

if TYPE_CHECKING:
    from textual.types import CSSPathType


class Inkr(App[None]):
    """The application entry point: opens an MKV file, then manages it."""

    CSS_PATH: ClassVar[CSSPathType | None] = "style.tcss"
    theme: Reactive[str] = Reactive("tokyo-night")

    mkv: MkvService  # pyright: ignore[reportUninitializedInstanceVariable]

    @work(exclusive=True)
    async def on_mount(self) -> None:
        """Prompt for an MKV file to open, then show the manager screen."""
        manager, path = await self.push_screen_wait(OpenScreen())
        self.mkv = MkvService(manager, path)
        self.push_screen(MkvManagScreen())


def main() -> None:
    """Run the application."""
    Inkr().run()


if __name__ == "__main__":
    main()
