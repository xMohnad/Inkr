from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, TabbedContent, TabPane
from textual_fspicker import FileOpen, FileSave
from typing_extensions import override

from pyinkr.dialogs import ProgressBarScreen
from pyinkr.services import MkvService
from pyinkr.widgets import InfoTree, ListAttachment, ListTrack, NoticeWidget

if TYPE_CHECKING:
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
                mkv = await MkvService.open(path)
            except (ValueError, OSError) as e:
                self.notify(str(e), title="Open Failed", severity="error")
                return
            finally:
                self.loading = False

            self.dismiss(mkv)

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
        self.app.mkv = await self.app.push_screen_wait(OpenScreen())

        id = self.focused and self.focused.id
        active = self.query_one(TabbedContent).active
        await self.recompose()
        if id is None:
            self.query_one(TabbedContent).active = active
            self.focus_next()
        else:
            self.query_one(f"#{id}").focus()

    @work(exclusive=True)
    async def action_save(self) -> None:
        """Pick a destination and write the edited file."""
        if not self.app.mkv.kept_tracks:
            self.notify("Keep at least one track to save.", title="No Tracks Kept", severity="error")
            return

        save_path = await self.app.push_screen_wait(FileSave(default_file=self.app.mkv.path, can_overwrite=False))
        if not save_path:
            return

        progress = ProgressBarScreen(f"Saving {save_path.name}...")
        await self.app.push_screen(progress)

        def update(value: float) -> None:
            # Called from the mux thread.
            self.app.call_from_thread(progress.progress_bar.update, progress=value)

        try:
            await self.app.mkv.save(save_path, on_progress=update)
        except ValueError as e:
            self.log.error(f"Mux failed: {e!r}")
            self.notify(str(e), title="Save Failed", severity="error")
        else:
            self.notify(f"Saved to {save_path.name}", title="Success")
        finally:
            progress.dismiss()
