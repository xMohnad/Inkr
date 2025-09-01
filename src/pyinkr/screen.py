#!/usr/bin/env python

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, TabbedContent, TabPane
from textual_fspicker import FileOpen, FileSave

from pyinkr.mkv_manager import MkvManager
from pyinkr.widgets import InfoTree, ListTrack, NoticeWidget

if TYPE_CHECKING:
    from pyinkr.main import Inkr


class OpenScreen(Screen[MkvManager]):
    BINDINGS = [
        Binding("o", "open", "Open"),
        Binding("escape", "back", "Back", tooltip="Back To Opened MKV"),
    ]
    path = reactive(Path, init=False)

    def compose(self) -> ComposeResult:
        yield Header()
        yield NoticeWidget()
        yield Footer()

    @work(exclusive=True, thread=True)
    async def watch_path(self, path: Path):
        self.app.call_from_thread(setattr, self, "loading", True)

        try:
            manager = MkvManager(str(path))
            self.app.call_from_thread(self.dismiss, manager)
        except Exception as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")

        self.app.call_from_thread(setattr, self, "loading", False)

    @work(exclusive=True)
    async def action_open(self):
        if path := await self.app.push_screen_wait(FileOpen()):
            self.path = path

    async def action_back(self):
        if hasattr(self.app, "manager"):
            await self.run_action("app.back")
        else:
            self.notify("Open MKV First", severity="warning")


class MkvManagScreen(Screen):
    BINDINGS = [
        Binding("s", "save", "Save"),
        Binding("escape", "back_to_open", "Back To Open Screen", False),
    ]
    app: Inkr

    def compose(self) -> ComposeResult:
        yield Header()
        # TODO: Add more tabs for info, chapters and attachments
        with TabbedContent(initial="info-tab", id="tabs"):
            with TabPane("Info", id="info-tab"):
                yield InfoTree("INFO", id="info")
            with TabPane("Track", id="track-tab"):
                yield ListTrack(id="track")
        yield Footer()

    @work(exclusive=True)
    async def action_back_to_open(self):
        focused_id = "#info"  # Default to info tab
        if focused := self.focused:
            focused_id = f"#{focused.id}"
        self.app.manager = await self.app.push_screen_wait("Open")
        await self.recompose()
        self.query_one(focused_id).focus()

    @work(exclusive=True)
    async def action_save(self):
        if save_path := await self.app.push_screen_wait(
            FileSave(default_file=self.app.manager.filepath.name)
        ):
            self.app.manager.save(save_path)
