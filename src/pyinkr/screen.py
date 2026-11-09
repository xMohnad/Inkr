from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.binding import Binding
from textual.content import Content
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList, TabbedContent, TabPane
from textual.widgets.option_list import Option, OptionDoesNotExist
from textual_fspicker import FileSave
from typing_extensions import override

from pyinkr.dialogs import ProgressBarScreen
from pyinkr.widgets import InfoTree, ListAttachment, ListTrack, ReloadRequested

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType

    from pyinkr.main import Inkr


class HomeScreen(Screen[None]):
    """The app's home screen."""

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "resume--label",
        "resume--name",
        "open--label",
        "recent--name",
        "recent--path",
    }

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("o", "app.open", "Open"),
        Binding("r", "resume", "Resume"),
    ]

    app: Inkr

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList()
        yield Footer()

    def on_screen_resume(self) -> None:
        """Rebuild the list every time the screen is shown."""
        self.populate()

    @staticmethod
    def short_dir(path: Path) -> str:
        """Return `path` with the home folder abbreviated to `~`."""
        try:
            relative = path.relative_to(Path.home())
        except (ValueError, RuntimeError):
            return str(path)
        return f"~/{relative}" if relative.parts else "~"

    def populate(self) -> None:
        """Fill the list with the options."""
        options: list[Option | None] = []

        if self.app.has_mkv:
            options.append(self._resume_option())

        options.append(self._open_option())

        if recent := self.app.settings.recent_paths:
            options.append(None)
            options.extend(map(self._recent_option, recent))

        option_list = self.query_one(OptionList)
        selected = option_list.highlighted_option
        selected = selected and selected.id or ""
        option_list.set_options(options)
        try:
            option_list.highlighted = option_list.get_option_index(selected)
        except OptionDoesNotExist:
            option_list.highlighted = 0

    def _resume_option(self) -> Option:
        """Build the option that returns to the open file."""
        return Option(
            Content.assemble(
                ("▶ Resume  ", self.get_visual_style("resume--label", partial=True)),
                (self.app.mkv.path.name, self.get_visual_style("resume--name", partial=True)),
            ),
            id="resume",
        )

    def _open_option(self) -> Option:
        """Build the option that opens a file."""
        label = self.get_visual_style("open--label", partial=True)
        return Option(Content.assemble(("Open file…", label)), id="open")

    def _recent_option(self, path: Path) -> Option:
        """Build the option for a recent file."""
        return Option(
            Content.assemble(
                (path.name, self.get_visual_style("recent--name", partial=True)),
                "\n",
                (self.short_dir(path.parent), self.get_visual_style("recent--path", partial=True)),
            ),
            id=str(path),
        )

    @on(OptionList.OptionSelected)
    def _selected(self, event: OptionList.OptionSelected) -> None:
        """Run the action of the selected home list option."""
        event.stop()
        match event.option_id:
            case None:
                return
            case "resume":
                self.action_resume()
            case "open":
                self.app.open_mkv()
            case path:
                self.app.open_mkv(Path(path))

    def action_resume(self) -> None:
        """Return to the open file."""
        if self.app.has_mkv:
            self.app.push_screen("manager")
        else:
            self.notify("Open File First", title="No File Open", severity="warning")


class MkvManagScreen(Screen[None]):
    """Screen for editing tracks, attachments, and info of an open MKV file."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("s", "save", "Save"),
        Binding("escape", "app.pop_screen", "Home", False),
    ]
    app: Inkr

    @override
    def compose(self) -> ComposeResult:
        self._update_title()
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

    def _update_title(self) -> None:
        """Update the subtitle from the file path."""
        self.sub_title = self.app.mkv.path.name

    @on(ReloadRequested)
    def _reload(self) -> None:
        """Reload the screen's widgets."""
        self._update_title()
        for pane in self.query(TabPane):
            pane.children[0].post_message(ReloadRequested())

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
