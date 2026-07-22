from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import App
from textual.reactive import Reactive

from pyinkr.screen import MkvManagScreen, OpenScreen
from pyinkr.services import MkvService

if TYPE_CHECKING:
    from textual.types import CSSPathType


class Inkr(App[None]):
    CSS_PATH: ClassVar[CSSPathType | None] = "style.tcss"
    SCREENS = {"Open": OpenScreen, "MkvManager": MkvManagScreen}  # pyright: ignore[reportUnannotatedClassAttribute]
    theme: Reactive[str] = Reactive("tokyo-night")

    mkv: MkvService

    @work(exclusive=True)
    async def on_mount(self) -> None:
        manager, path = await self.push_screen_wait("Open")
        self.mkv = MkvService(manager, path)
        self.push_screen("MkvManager")


def main() -> None:
    Inkr().run()


if __name__ == "__main__":
    main()
