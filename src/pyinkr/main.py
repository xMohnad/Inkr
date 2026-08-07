from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, override

from textual import work
from textual.app import App, SystemCommand

from pyinkr import fonts
from pyinkr.dialogs import PickFolderScreen
from pyinkr.screen import MkvManagScreen, OpenScreen
from pyinkr.services import MkvService
from pyinkr.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.screen import Screen
    from textual.types import CSSPathType


class Inkr(App[None]):
    """The application entry point: opens an MKV file, then manages it."""

    CSS_PATH: ClassVar[CSSPathType | None] = "style.tcss"

    mkv: MkvService  # pyright: ignore[reportUninitializedInstanceVariable]
    settings: Settings  # pyright: ignore[reportUninitializedInstanceVariable]
    font_faces: list[fonts.FontFile]  # pyright: ignore[reportUninitializedInstanceVariable]

    @work(exclusive=True)
    async def on_mount(self) -> None:
        """Prompt for an MKV file to open, then show the manager screen."""
        manager, path = await self.push_screen_wait(OpenScreen())
        self.mkv = MkvService(manager, path)
        self.push_screen(MkvManagScreen())

    @work(exclusive=True)
    async def action_fonts_folder(self) -> None:
        """Pick fonts folder."""
        if path := await self.push_screen_wait(
            PickFolderScreen(
                self.settings.fonts_folder,
                "Fonts Folder",
            )
        ):
            self.settings.fonts_folder = str(path)
            self.scan_font_faces(path)

    @override
    def get_system_commands(self, screen: Screen[object]) -> Iterable[SystemCommand]:
        yield SystemCommand(
            "Fonts Folder",
            "Pick fonts folder",
            self.action_fonts_folder,
        )
        yield from super().get_system_commands(screen)

    @work(exclusive=True, thread=True)
    def scan_font_faces(self, directory: Path) -> None:
        """Scan `directory` for font faces."""
        self.font_faces = fonts.scan_font_faces(directory)
        self.log.debug(f"Found {len(self.font_faces)} font faces")

    def on_load(self) -> None:
        """Load the app."""
        self.settings = Settings.load()
        self.theme = self.settings.theme
        self.font_faces = []
        if (path := self.settings.fonts_folder_path) and path.is_dir():
            self.scan_font_faces(path)

    def on_exit_app(self) -> None:
        """Exit the app."""
        if hasattr(self, "settings"):
            self.settings.theme = self.theme
            self.settings.save()


def main() -> None:
    """Run the application."""
    Inkr().run()


if __name__ == "__main__":
    main()
