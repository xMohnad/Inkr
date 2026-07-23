from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, override

from pymkv import MKVFile
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Checkbox, Footer, Header, TabbedContent, TabPane
from textual_fspicker import FileOpen, FileSave

from pyinkr.dialogs import ProgressBarScreen
from pyinkr.services import MkvService
from pyinkr.widgets import InfoTree, ListTrack, NoticeWidget

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.binding import BindingType
    from textual.reactive import Reactive

    from pyinkr.main import Inkr


class OpenScreen(Screen[tuple[type[MKVFile], type[Path]]]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("o", "open", "Open"),
        Binding("escape", "back", "Back", tooltip="Back To Opened MKV"),
    ]

    path: reactive[Path] = reactive(Path(), init=False)
    app: Inkr
    loading: Reactive[bool]

    @override
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
            self.app.call_from_thread(
                self.notify,
                f"Couldn't open '{path.name}': {e}",
                title="Open failed",
                severity="error",
            )
        finally:
            self.app.call_from_thread(setattr, self, "loading", False)

    @work(exclusive=True)
    async def action_open(self) -> None:
        if path := await self.app.push_screen_wait(FileOpen()):
            self.loading = True
            self.path = path

    async def action_back(self) -> None:
        if hasattr(self.app, "mkv"):
            await self.run_action("app.back")
        else:
            self.notify("Open MKV First", severity="warning")


class MkvManagScreen(Screen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("s", "save", "Save"),
        Binding("escape", "back_to_open", "Back To Open Screen", False),
    ]
    app: Inkr

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        # TODO: Add more tabs for chapters and attachments
        with TabbedContent(initial="info-tab", id="tabs"):
            with TabPane("Info", id="info-tab"):
                yield InfoTree("INFO", id="info")
            with TabPane("Tracks", id="track-tab"):
                yield ListTrack(id="track")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_title()

    def _refresh_title(self) -> None:
        self.sub_title = self.app.mkv.path.name

    @work(exclusive=True)
    async def action_back_to_open(self) -> None:
        focused_id = "#info"  # Default to info tab
        if (focused := self.focused) and self.focused.id:
            focused_id = f"#{focused.id}"
        manager, path = await self.app.push_screen_wait("Open")
        self.app.mkv = MkvService(manager, path)
        self.refresh(layout=True, recompose=True)
        self._refresh_title()
        self.query_one(focused_id).focus()

    @staticmethod
    def _indices_to_remove(checkboxes: Iterable[Checkbox]) -> list[int]:
        return [i for i, cb in enumerate(checkboxes) if not cb.value][::-1]

    @work(exclusive=True)
    async def action_save(self) -> None:
        """Save editing video"""
        if save_path := await self.app.push_screen_wait(FileSave(default_file=self.app.mkv.path, can_overwrite=False)):
            for i in self._indices_to_remove(self.query_one(ListTrack).query(Checkbox)):
                self.app.mkv.remove_track(i)

            try:
                self.app.push_screen(ProgressBarScreen(f"Saving {save_path.name}..."))
                self._mux(save_path)
            except Exception as e:
                self.notify(f"Save failed: {e}", severity="error")
                screens = self.app.screen_stack
                if screens and isinstance(screens[-1], ProgressBarScreen):
                    self.app.pop_screen()

    @work(exclusive=True, thread=True)
    async def _mux(self, save_path: Path) -> None:
        def update(progress: int) -> None:
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
