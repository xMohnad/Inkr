#!/usr/bin/env python

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, TabbedContent, TabPane
from textual_fspicker import FileOpen, FileSave

from pyinkr.mkv_manager import MkvManager
from pyinkr.widgets import InfoTree, ListTrack

if TYPE_CHECKING:
    from pyinkr.main import Inkr


class OpenScreen(Screen[MkvManager]):
    BINDINGS = [
        Binding("o", "open", "Open"),
        Binding("escape", "back", "Back", tooltip="Back To Opened MKV"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def action_open(self):
        def open(path):
            if path:
                self.loading = True
                self.__init_manager(path)

        self.app.push_screen(FileOpen(), open)

    @work(exclusive=True, thread=True, group="init_manager")
    async def __init_manager(self, path):
        try:
            manager = MkvManager(path)
            self.dismiss(manager)
        except Exception as e:
            self.notify(str(e), severity="error")

        self.loading = False

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
        self.app.manager = await self.app.push_screen_wait("Open")
        await self.recompose()

    @work(exclusive=True)
    async def action_save(self):
        save_path = await self.app.push_screen_wait(
            FileSave(default_file=self.app.manager.filepath.name)
        )
        if save_path:
            self.app.manager.save(save_path)


class Inkr(App):
    manager: "MkvManager"

    CSS_PATH = "style.tcss"
    SCREENS = {"Open": OpenScreen, "MkvManager": MkvManagScreen}

    @work(exclusive=True)
    async def on_mount(self):
        self.manager = await self.push_screen_wait("Open")
        self.push_screen("MkvManager")


def main():
    Inkr().run()


if __name__ == "__main__":
    main()
