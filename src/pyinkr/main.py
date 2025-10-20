from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import App
from textual.logging import TextualHandler

from pyinkr.screen import MkvManagScreen, OpenScreen

if TYPE_CHECKING:
    from pathlib import Path

    from textual.driver import Driver
    from textual.types import CSSPathType

    from pyinkr.wrapper.mkvmerge import MkvMerge


class Inkr(App[None]):
    CSS_PATH: ClassVar[CSSPathType | None] = "style.tcss"
    SCREENS = {"Open": OpenScreen, "MkvManager": MkvManagScreen}  # pyright: ignore[reportUnannotatedClassAttribute]

    def __init__(
        self,
        driver_class: type[Driver] | None = None,
        css_path: CSSPathType | None = None,
        watch_css: bool = False,
        ansi_color: bool = False,
    ):
        self.manager: MkvMerge
        self.path: Path

        super().__init__(driver_class, css_path, watch_css, ansi_color)

    @work(exclusive=True)
    async def on_mount(self) -> None:
        logging.basicConfig(level=logging.NOTSET, handlers=[TextualHandler()])
        self.manager, self.path = await self.push_screen_wait("Open")
        self.push_screen("MkvManager")


def main() -> None:
    Inkr().run()


if __name__ == "__main__":
    main()
