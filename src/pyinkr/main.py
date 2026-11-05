from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from textual import work
from textual.app import App, SystemCommand
from textual.worker import get_current_worker

from pyinkr import fonts
from pyinkr.dialogs import PickFolderScreen
from pyinkr.screen import MkvManagScreen, OpenScreen
from pyinkr.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from textual.screen import Screen
    from textual.types import CSSPathType

    from pyinkr.services import MkvService


class Inkr(App[None]):
    """The application entry point: opens an MKV file, then manages it."""

    CSS_PATH: ClassVar[CSSPathType | None] = "style.tcss"

    mkv: MkvService  # pyright: ignore[reportUninitializedInstanceVariable]
    settings: Settings  # pyright: ignore[reportUninitializedInstanceVariable]
    font_faces: list[fonts.FontFile]  # pyright: ignore[reportUninitializedInstanceVariable]

    @work(exclusive=True)
    async def on_mount(self) -> None:
        """Prompt for an MKV file to open, then show the manager screen."""
        self.mkv = await self.push_screen_wait(OpenScreen())
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
        yield SystemCommand("Fonts Folder", "Pick fonts folder", self.action_fonts_folder)
        yield from super().get_system_commands(screen)

    @work(exclusive=True, thread=True, group="faces")
    def scan_font_faces(self, directory: Path | None = None) -> None:
        """Scan a folder for font faces and store them in `font_faces`.

        Args:
            directory: Folder to scan. Defaults to the saved fonts folder.
        """
        directory = directory or self.settings.fonts_folder_path
        if directory and directory.is_dir():
            faces = fonts.scan_font_faces(directory)
            if get_current_worker().is_cancelled:
                return
            self.font_faces = faces
            self.log.debug(f"Found {len(self.font_faces)} font faces")

    def on_load(self) -> None:
        """Initialize app state before it starts."""
        self.settings = Settings.load()
        self.theme = self.settings.theme
        self.font_faces = []

    def on_ready(self) -> None:
        """Run startup tasks once the app is ready."""
        self.scan_font_faces()

    def on_exit_app(self) -> None:
        """Persist app state before exiting."""
        if hasattr(self, "settings"):
            self.settings.theme = self.theme
            self.settings.save()


def main() -> None:
    """Run the application."""
    Inkr().run()


if __name__ == "__main__":
    main()
