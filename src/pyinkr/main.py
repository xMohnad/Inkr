from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import App, SystemCommand
from textual.worker import get_current_worker
from textual_fspicker import FileOpen
from typing_extensions import override

from pyinkr import fonts
from pyinkr.dialogs import PickFolderScreen
from pyinkr.screen import HomeScreen, MkvManagScreen
from pyinkr.services import MkvService
from pyinkr.settings import Settings
from pyinkr.widgets import ReloadRequested

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from textual.screen import Screen
    from textual.types import CSSPathType


class Inkr(App[None]):
    """Terminal app for editing MKV files."""

    CSS_PATH: ClassVar[CSSPathType | None] = "style.tcss"

    mkv: MkvService  # pyright: ignore[reportUninitializedInstanceVariable]
    settings: Settings  # pyright: ignore[reportUninitializedInstanceVariable]
    font_faces: list[fonts.FontFile]  # pyright: ignore[reportUninitializedInstanceVariable]

    def on_mount(self) -> None:
        """Install the manager screen."""
        self.install_screen(MkvManagScreen(), "manager")

    @override
    def get_default_screen(self) -> Screen[None]:
        return HomeScreen(id="_default")

    @work(exclusive=True, group="open")
    async def open_mkv(self, path: Path | None = None) -> None:
        """Open an MKV file and show it in the manager screen.

        Args:
            path: File to open. Prompts for one when omitted.
        """
        path = path or await self.push_screen_wait(FileOpen())
        if not path:
            return

        # Loading hides all widgets on the active screen, so Textual moves focus away
        # from the focused widget and doesn't restore it. To avoid that, pop the manager
        # first and show loading on the screen below; the manager is pushed again
        # after the file opens and starts with fresh focus.
        if isinstance(self.screen, MkvManagScreen):
            self.pop_screen()

        has_mkv = self.has_mkv
        screen = self.screen
        screen.loading = True
        try:
            self.mkv = await MkvService.open(path)
        except (ValueError, OSError) as e:
            self.notify(str(e), title="Open Failed", severity="error")
            if has_mkv:
                self.push_screen("manager")
            return
        finally:
            screen.loading = False

        self.settings.add_recent(path)
        self.push_screen("manager")
        if has_mkv:
            self.screen.post_message(ReloadRequested())

    def action_open(self) -> None:
        """Open a file."""
        self.open_mkv()

    @property
    def has_mkv(self) -> bool:
        """Whether an MKV file is currently open."""
        return hasattr(self, "mkv")

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
        yield SystemCommand("Open File", "Open an MKV file", self.action_open)
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
