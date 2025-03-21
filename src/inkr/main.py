#!/usr/bin/env python

from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane
from textual_fspicker import FileOpen, FileSave

from .mkv_manager import MkvManager
from .widgets import ListTrack


class Inkr(App):
    CSS_PATH = "style.tcss"
    BINDINGS = [Binding("o", "open", "Open")]

    def compose(self) -> ComposeResult:
        yield Header()
        # TODO: Add more tabs for info, chapters and attachments
        with TabbedContent(initial="track"):
            with TabPane("Track", id="track"):
                yield ListTrack()
        yield Footer()

    async def action_open(self):
        self.query_one(ListTrack).loading = True
        self.push_screen(FileOpen(), callback=self.initialize_mkv_manager)  # pyright: ignore

    @work(exclusive=True, thread=True)
    async def initialize_mkv_manager(self, file):
        if not file:
            self.notify("Canceled")
        else:
            self.mkv_manager = MkvManager(file)
            self.query_one(ListTrack).on_mount()
            self.bind("s", "save", description="Save")

        self.query_one(ListTrack).loading = False

    @work(exclusive=True)
    async def action_save(self):
        save_path = await self.push_screen(
            FileSave(default_file=self.mkv_manager.filepath.name),
            wait_for_dismiss=True,
        )
        if not save_path:
            return self.notify("Canceled")

        self.mkv_manager.save(save_path)


def main():
    Inkr().run()


if __name__ == "__main__":
    main()
