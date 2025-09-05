#!/usr/bin/env python

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import App

from pyinkr.screen import MkvManagScreen, OpenScreen

if TYPE_CHECKING:
    from pathlib import Path

    from pymkv import MKVFile


class Inkr(App[None]):
    manager: "MKVFile"
    path: Path

    CSS_PATH = "style.tcss"
    SCREENS = {"Open": OpenScreen, "MkvManager": MkvManagScreen}

    @work(exclusive=True)
    async def on_mount(self) -> None:
        self.manager, self.path = await self.push_screen_wait("Open")
        self.push_screen("MkvManager")


def main() -> None:
    Inkr().run()


if __name__ == "__main__":
    main()
