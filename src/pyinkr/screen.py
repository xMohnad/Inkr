from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pymkv import MKVFile
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Checkbox, Footer, Header, TabbedContent, TabPane
from textual_fspicker import FileOpen, FileSave

from pyinkr.widgets import InfoTree, ListTrack, NoticeWidget

if TYPE_CHECKING:
    from pyinkr.main import Inkr


class OpenScreen(Screen[tuple[type[MKVFile], type[Path]]]):
    BINDINGS = [
        Binding("o", "open", "Open"),
        Binding("escape", "back", "Back", tooltip="Back To Opened MKV"),
    ]

    path = reactive(Path(), init=False)

    def compose(self) -> ComposeResult:
        yield Header()
        yield NoticeWidget()
        yield Footer()

    @work(exclusive=True, thread=True)
    async def watch_path(self, path: Path) -> None:
        try:
            manager = MKVFile(path)
            self.app.call_from_thread(self.dismiss, (manager, path))
        except Exception as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        finally:
            self.app.call_from_thread(setattr, self, "loading", False)

    @work(exclusive=True)
    async def action_open(self) -> None:
        if path := await self.app.push_screen_wait(FileOpen()):
            self.loading = True
            self.path = path

    async def action_back(self) -> None:
        if hasattr(self.app, "manager"):
            await self.run_action("app.back")
        else:
            self.notify("Open MKV First", severity="warning")


class MkvManagScreen(Screen[None]):
    BINDINGS = [
        Binding("s", "save", "Save"),
        Binding("w", "toggle_overwrite", "Overwrite video", False),
        Binding("escape", "back_to_open", "Back To Open Screen", False),
    ]
    app: Inkr

    can_overwrite: bool = False
    """Flag to say if an existing file can be overwritten."""

    def compose(self) -> ComposeResult:
        yield Header()
        # TODO: Add more tabs for chapters and attachments
        with TabbedContent(initial="info-tab", id="tabs"):
            with TabPane("Info", id="info-tab"):
                yield InfoTree("INFO", id="info")
            with TabPane("Track", id="track-tab"):
                yield ListTrack(id="track")
        yield Footer()

    @work(exclusive=True)
    async def action_back_to_open(self) -> None:
        focused_id = "#info"  # Default to info tab
        if (focused := self.focused) and self.focused.id:
            focused_id = f"#{focused.id}"
        self.app.manager, self.app.path = await self.app.push_screen_wait("Open")
        await self.recompose()
        self.query_one(focused_id).focus()

    @work(exclusive=True)
    async def action_save(self) -> None:
        """Save edttin video"""
        if save_path := await self.app.push_screen_wait(
            FileSave(default_file=self.app.path, can_overwrite=self.can_overwrite)
        ):
            for i, checkbox in enumerate(self.query_one(ListTrack).query(Checkbox)):
                if not checkbox.value:
                    self.app.manager.remove_track(i)

            self.app.manager.mux(save_path)

    def action_toggle_overwrite(self) -> None:
        self.can_overwrite ^= True
        self.notify(f"Overwrite: {self.can_overwrite}")
