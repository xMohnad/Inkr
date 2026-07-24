from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from pymkv import MKVFile
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Checkbox, Footer, Header, TabbedContent, TabPane
from textual_fspicker import FileOpen, FileSave
from typing_extensions import override

from pyinkr.dialogs import ProgressBarScreen
from pyinkr.services import MkvService
from pyinkr.widgets import InfoTree, ListAttachment, ListTrack, NoticeWidget

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.binding import BindingType
    from textual.reactive import Reactive

    from pyinkr.main import Inkr


class OpenScreen(Screen[tuple[MKVFile, Path]]):
    """Screen for selecting and opening an MKV file."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("o", "open", "Open"),
        Binding("escape", "back", "Back", tooltip="Back To Opened MKV"),
    ]

    path: reactive[Path] = reactive(Path(), init=False)
    app: Inkr
    loading: Reactive[bool]

    @override
    def compose(self) -> ComposeResult:  # noqa: D102 (pure yield chain, no non-obvious behavior)
        yield Header()
        yield NoticeWidget()
        yield Footer()

    @work(exclusive=True, thread=True)
    async def watch_path(self, path: Path) -> None:
        """Open the MKV file at the given path."""
        try:
            manager = MKVFile(path)
            self.app.call_from_thread(self.dismiss, (manager, path))
        except Exception as e:
            self.app.call_from_thread(
                self.notify,
                f"Couldn't open '{path.name}': {e}",
                title="Open Failed",
                severity="error",
            )
        finally:
            self.app.call_from_thread(setattr, self, "loading", False)

    @work(exclusive=True)
    async def action_open(self) -> None:
        """Prompt the user to choose an MKV file to open."""
        if path := await self.app.push_screen_wait(FileOpen()):
            self.loading = True
            self.path = path

    async def action_back(self) -> None:
        """Return to the manager screen if an MKV file is already open."""
        if hasattr(self.app, "mkv"):
            await self.run_action("app.back")
        else:
            self.notify("Open MKV First", title="No File Open", severity="warning")


class MkvManagScreen(Screen[None]):
    """Screen for editing tracks, attachments, and info of an open MKV file."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("s", "save", "Save"),
        Binding("escape", "back_to_open", "Back To Open Screen", False),
    ]
    app: Inkr

    @override
    def compose(self) -> ComposeResult:  # noqa: D102 (pure yield chain, no non-obvious behavior)
        yield Header()
        # TODO: Add a tab for chapters
        with TabbedContent(initial="info-tab", id="tabs"):
            with TabPane("Info", id="info-tab"):
                yield InfoTree("INFO", id="info")
            with TabPane("Tracks", id="track-tab"):
                yield ListTrack(id="track")
            with TabPane("Attachments", id="attachment-tab"):
                yield ListAttachment(id="attachment")
        yield Footer()

    def on_mount(self) -> None:
        """Set the screen's subtitle when mounted."""
        self._refresh_title()

    def _refresh_title(self) -> None:
        """Update the subtitle to the current MKV file name."""
        self.sub_title = self.app.mkv.path.name

    @work(exclusive=True)
    async def action_back_to_open(self) -> None:
        """Return to the open screen and load a new MKV file."""
        focused_id = "#info"  # Default to info tab
        if (focused := self.focused) and self.focused.id:
            focused_id = f"#{focused.id}"

        manager, path = await self.app.push_screen_wait(OpenScreen())
        self.app.mkv = MkvService(manager, path)
        self.refresh(layout=True, recompose=True)
        self._refresh_title()
        self.query_one(focused_id).focus()

    @staticmethod
    def _indices_to_remove(checkboxes: Iterable[Checkbox]) -> list[int]:
        """Return unchecked checkbox indices in descending order."""
        return [i for i, cb in enumerate(checkboxes) if not cb.value][::-1]

    @work(exclusive=True)
    async def action_save(self) -> None:
        """Save the MKV file, applying track and attachment selections."""
        if save_path := await self.app.push_screen_wait(FileSave(default_file=self.app.mkv.path, can_overwrite=False)):
            for i in self._indices_to_remove(self.query_one(ListTrack).query(Checkbox)):
                self.app.mkv.remove_track(i)

            for i in self._indices_to_remove(self.query_one(ListAttachment).query(Checkbox)):
                self.app.mkv.remove_attachment(i)

            try:
                self.app.push_screen(ProgressBarScreen(f"Saving {save_path.name}..."))
                self._mux(save_path)
            except Exception as e:
                self.notify(f"Save failed: {e}", title="Save Failed", severity="error")
                screens = self.app.screen_stack
                if screens and isinstance(screens[-1], ProgressBarScreen):
                    self.app.pop_screen()

    @work(exclusive=True, thread=True)
    async def _mux(self, save_path: Path) -> None:
        """Mux and write the MKV file."""

        def update(progress: int) -> None:
            """Forward mux progress to the active ProgressBarScreen."""
            screen = self.app.screen_stack[-1]
            if isinstance(screen, ProgressBarScreen):
                self.app.call_from_thread(screen.update, progress)

        self.app.mkv.mux(save_path, progress_handler=update)
        self.app.call_from_thread(
            self.notify,
            f"Saved to {save_path.name}",
            title="Success",
            severity="information",
        )
