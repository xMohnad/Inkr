from __future__ import annotations

import copy
from typing import TYPE_CHECKING, ClassVar

from pymkv import MKVFile
from textual import work
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Checkbox, Footer, Header, TabbedContent, TabPane
from textual.worker import WorkerFailed
from textual_fspicker import FileOpen, FileSave
from typing_extensions import override

from pyinkr.dialogs import ProgressBarScreen
from pyinkr.services import MkvService
from pyinkr.widgets import InfoTree, ListAttachment, ListTrack, NoticeWidget

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.app import ComposeResult
    from textual.binding import BindingType

    from pyinkr.main import Inkr


class OpenScreen(Screen[MkvService]):
    """Screen for selecting and opening an MKV file."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("o", "open", "Open"),
        Binding("escape", "back", "Back", tooltip="Back To Opened MKV"),
    ]

    app: Inkr

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield NoticeWidget()
        yield Footer()

    @work(exclusive=True)
    async def action_open(self) -> None:
        """Prompt the user to choose an MKV file to open."""
        if path := await self.app.push_screen_wait(FileOpen()):
            self.loading = True
            try:
                manager = await self.run_worker(lambda: MKVFile(path), thread=True, exit_on_error=False).wait()
                self.dismiss(MkvService(manager, path))
            except WorkerFailed as e:
                self.notify(str(e.error), title="Open Failed", severity="error")
            finally:
                self.loading = False

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
    def compose(self) -> ComposeResult:
        self.sub_title = self.app.mkv.path.name
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

    @work(exclusive=True)
    async def action_back_to_open(self) -> None:
        """Return to the open screen and load a new MKV file."""
        # TODO: remember focused widget
        self.app.mkv = await self.app.push_screen_wait(OpenScreen())
        self.refresh(layout=True, recompose=True)

    @staticmethod
    def _indices_to_remove(checkboxes: Iterable[Checkbox]) -> list[int]:
        """Return unchecked checkbox indices in descending order."""
        return [i for i, cb in enumerate(checkboxes) if not cb.value][::-1]

    @work(exclusive=True)
    async def action_save(self) -> None:
        """Save the MKV file, applying track and attachment selections."""
        if not (
            save_path := await self.app.push_screen_wait(FileSave(default_file=self.app.mkv.path, can_overwrite=False))
        ):
            return

        mkv = copy.deepcopy(self.app.mkv.manager)
        for i in self._indices_to_remove(self.query_one(ListTrack).query(Checkbox)):
            mkv.remove_track(i)

        if not mkv.tracks:
            self.notify("The video must contain at least one track.", title="Missing Tracks", severity="error")
            return

        for i in self._indices_to_remove(self.query_one(ListAttachment).query(Checkbox)):
            mkv.remove_attachment(i)

        screen = ProgressBarScreen(f"Saving {save_path.name}...")
        self.app.push_screen(screen)

        try:
            updater = lambda v: self.app.call_from_thread(screen.progress_bar.update, progress=v)
            await self.app.run_worker(
                lambda: mkv.mux(save_path, progress_handler=updater), thread=True, exit_on_error=False
            ).wait()
            self.notify(f"Saved to {save_path.name}", title="Success")
        except WorkerFailed as e:
            self.notify(str(e.error), title="Save Failed", severity="error")
        finally:
            self.app.pop_screen()
