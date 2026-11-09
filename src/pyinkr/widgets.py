from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import msgspec
from textual import on, work
from textual.binding import Binding
from textual.content import Content
from textual.message import Message
from textual.widgets import ListItem, ListView, Static, Tree
from textual_fspicker import FileOpen
from typing_extensions import override

from pyinkr.dialogs import DelayScreen, EditScreen, FontsScreen

if TYPE_CHECKING:
    from typing import ClassVar

    from pymkv import MKVAttachment, MKVTrack
    from textual.app import ComposeResult
    from textual.binding import BindingType
    from textual.style import Style
    from textual.visual import VisualType
    from textual.widget import AwaitMount

    from pyinkr.main import Inkr
    from pyinkr.services import MkvService


ItemT = TypeVar("ItemT", "MKVTrack", "MKVAttachment")


class ReloadRequested(Message, bubble=False):
    """Posted to reload a widget on opening a file."""


class ChecklistRow(ListItem):
    """One row of a `ChecklistView`; remembers the item it shows."""

    def __init__(self, target: Any, content: VisualType) -> None:
        """Initialize the row for `target` with its content."""
        super().__init__(Static(content))
        self.target = target

    def set_content(self, content: VisualType) -> None:
        """Replace the row text."""
        self.query_one(Static).update(content)


class ChecklistView(ListView, Generic[ItemT]):
    """A list of MKV items that can each be kept or dropped from the output.

    The keep/drop state lives in `MkvService`; rows only render it.
    """

    app: Inkr

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "checklist--kept",
        "checklist--removed",
        "checklist--name",
        "checklist--name-removed",
        "checklist--unnamed",
        "checklist--meta",
    }

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add", "Add"),
        Binding("space", "toggle_keep", "Keep/Drop"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]

    MARK_KEPT: ClassVar[str] = "✔"
    MARK_REMOVED: ClassVar[str] = "✘"
    UNNAMED_LABEL: ClassVar[str] = "Unnamed"

    @property
    def mkv(self) -> MkvService:
        """Return the application's MKV service."""
        return self.app.mkv

    @property
    def items(self) -> list[ItemT]:
        """Return the domain objects backing this list, in display order."""
        raise NotImplementedError

    def format_item(self, item: ItemT, kept: bool) -> VisualType:
        """Return the row visual for `item`."""
        raise NotImplementedError

    def mark_part(self, kept: bool) -> tuple[str, Style]:
        """Return the kept/removed mark with its style."""
        vs = self.get_visual_style
        if kept:
            return f"{self.MARK_KEPT} ", vs("checklist--kept", partial=True)
        return f"{self.MARK_REMOVED} ", vs("checklist--removed", partial=True)

    def name_part(self, name: str | None, kept: bool) -> tuple[str, Style]:
        """Return the item name with its style, or a placeholder if missing."""
        vs = self.get_visual_style
        if not name:
            return self.UNNAMED_LABEL, vs("checklist--unnamed", partial=True)
        return name, vs("checklist--name" if kept else "checklist--name-removed", partial=True)

    @override
    def compose(self) -> ComposeResult:
        yield from self.make_rows()

    def make_row(self, item: ItemT) -> ChecklistRow:
        """Build the row for `item`."""
        return ChecklistRow(item, self.format_item(item, self.mkv.is_kept(item)))

    def make_rows(self) -> list[ChecklistRow]:
        """Build a row for each item."""
        return [self.make_row(item) for item in self.items]

    def add_row(self, item: ItemT) -> AwaitMount:
        """Append a row for `item` to the end of the list."""
        return self.append(self.make_row(item))

    def refresh_row(self, item: ItemT) -> None:
        """Re-render the row showing `item`."""
        for row in self.query(ChecklistRow):
            if row.target is item:
                row.set_content(self.format_item(item, self.mkv.is_kept(item)))
                return

    @property
    def current(self) -> ItemT | None:
        """Return the highlighted item, if any."""
        row = self.highlighted_child
        return row.target if isinstance(row, ChecklistRow) else None

    @override
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Hide item actions while the list is empty."""
        return action == "add" or len(self) > 0

    def toggle_keep(self, item: ItemT) -> None:
        """Flip whether `item` stays in the output."""
        self.mkv.toggle_kept(item)
        self.refresh_row(item)

    def action_toggle_keep(self) -> None:
        """Toggle the highlighted item."""
        if (item := self.current) is not None:
            self.toggle_keep(item)

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        """Toggle on Enter or click."""
        event.stop()
        if isinstance(event.item, ChecklistRow):
            self.toggle_keep(event.item.target)

    @on(ReloadRequested)
    async def _reload(self) -> None:
        """Reload the rows."""
        index = self.index
        async with self.batch():
            await self.clear()
            await self.extend(self.make_rows())
        self.index = index

    @work(exclusive=True)
    async def action_edit(self, title: str, attr: str, placeholder: str = "") -> None:
        """Edit a text attribute of the highlighted item."""
        if (item := self.current) is None:
            return

        value = await self.app.push_screen_wait(EditScreen(getattr(item, attr), title, placeholder))
        if value is None:
            return

        try:
            setattr(item, attr, value)
        except ValueError as e:
            self.notify(str(e), title="Invalid Value", severity="error")
        else:
            self.refresh_row(item)


class ListTrack(ChecklistView["MKVTrack"]):
    """List of MKV tracks."""

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "track--default",
        "track--forced",
        "track--sync",
        "track--video",
        "track--audio",
        "track--subtitles",
        "track--other",
    }

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("n", "edit('Track Name', 'track_name', 'Track name')", "Name"),
        Binding("l", "edit('Language', 'language', 'e.g. eng, jpn, ara')", "Language"),
        Binding("y", "edit_delay", "Delay"),
        Binding("d", "toggle_default", "Default"),
        Binding("f", "check_fonts", "Fonts"),
        Binding("alt+up", "move_track(-1)", "Move Up", show=False),
        Binding("alt+down", "move_track(1)", "Move Down", show=False),
    ]

    KNOWN_KINDS: ClassVar[frozenset[str]] = frozenset({"video", "audio", "subtitles"})
    DEFAULT_LANGUAGE: ClassVar[str] = "und"

    @property
    @override
    def items(self) -> list[MKVTrack]:
        return self.mkv.tracks

    @work(exclusive=True)
    async def action_add(self) -> None:
        """Add a new track from a file."""
        if path := await self.app.push_screen_wait(FileOpen()):
            self.loading = True
            try:
                track = await self.mkv.add_track(path)
            except (ValueError, OSError) as e:
                self.notify(str(e), title="Add Failed", severity="error")
                return
            finally:
                self.loading = False

            self.add_row(track)

    def action_toggle_default(self) -> None:
        """Toggle the default flag of the highlighted track."""
        if (track := self.current) is not None:
            track.default_track = not track.default_track
            self.refresh_row(track)

    @work(exclusive=True)
    async def action_edit_delay(self) -> None:
        """Edit the track sync delay."""
        if (track := self.current) is None:
            return

        delay = await self.app.push_screen_wait(DelayScreen(track.sync or 0, "Track Delay"))
        if delay is None:
            return

        track.sync = delay or None
        self.refresh_row(track)

    @work(exclusive=True)
    async def action_check_fonts(self) -> None:
        """Show the fonts required by the selected subtitle track."""
        if (track := self.current) is None:
            return

        self.loading = True
        try:
            info = await self.mkv.analyze_fonts(track)
        except ValueError as e:
            self.notify(str(e), title="Fonts", severity="warning")
            return
        finally:
            self.loading = False

        attachments = self.screen.query_one(ListAttachment)
        self.app.push_screen(
            FontsScreen(
                info=info,
                attach=attachments.add_path,
                title=f"Fonts — {track.track_name or self.UNNAMED_LABEL}",
            )
        )

    def action_move_track(self, delta: int) -> None:
        """Move the highlighted track by one position."""
        index = self.index
        if index is None or not self.mkv.move_track(index, delta):
            return

        new_index = index + delta
        if delta < 0:
            self.move_child(index, before=new_index)
        else:
            self.move_child(index, after=new_index)
        self.index = new_index

    @override
    def format_item(self, item: MKVTrack, kept: bool) -> VisualType:
        """Return formatted content for a track."""
        vs = self.get_visual_style

        kind = (item.track_type or "").lower()
        kind_cls = f"track--{kind}" if kind in self.KNOWN_KINDS else "track--other"
        lang = item.language or self.DEFAULT_LANGUAGE

        parts: list[str | tuple[str, Style]] = [
            self.mark_part(kept),
            (kind[:1].upper() or "O", vs(kind_cls, partial=True)),
            "  ",
            self.name_part(item.track_name, kept),
            ("  ·  " + " · ".join(filter(None, (lang, item.track_codec))), vs("checklist--meta", partial=True)),
        ]

        if item.default_track:
            parts.append(("  DEFAULT", vs("track--default", partial=True)))
        if item.forced_track:
            parts.append(("  FORCED", vs("track--forced", partial=True)))
        if item.sync:
            parts.append((f"  ⏱ {item.sync / 1000:+.2f}s", vs("track--sync", partial=True)))

        return Content.assemble(*parts)


class ListAttachment(ChecklistView["MKVAttachment"]):
    """List of MKV attachments."""

    COMPONENT_CLASSES: ClassVar[set[str]] = {"attachment--description"}

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("n", "edit('Attachment Name', 'name', 'File name')", "Name"),
        Binding("e", "edit('Description', 'description', 'Description')", "Description"),
    ]

    @property
    @override
    def items(self) -> list[MKVAttachment]:
        return self.mkv.attachments

    def add_path(self, path: Path, description: str | None = None) -> AwaitMount:
        """Attach the file at `path` and show it in the list."""
        attachment = self.mkv.add_attachment(path)
        if description:
            attachment.description = description
        return self.add_row(attachment)

    @work(exclusive=True)
    async def action_add(self) -> None:
        """Add a new attachment from a file."""
        if path := await self.app.push_screen_wait(FileOpen()):
            self.add_path(path)

    @override
    def format_item(self, item: MKVAttachment, kept: bool) -> VisualType:
        """Return formatted content for an attachment."""
        name = item.name or Path(item.file_path).name
        vs = self.get_visual_style

        parts: list[str | tuple[str, Style]] = [
            self.mark_part(kept),
            self.name_part(name, kept),
        ]
        if item.mime_type:
            parts.append((f"  ·  {item.mime_type}", vs("checklist--meta", partial=True)))
        if item.description:
            parts.append((f"  — {item.description}", vs("attachment--description", partial=True)))

        return Content.assemble(*parts)


class InfoTree(Tree[None]):
    """A widget that displays MKV Info."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("t", "edit_title", "Title"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("h", "scroll_left", show=False),
        Binding("l", "scroll_right", show=False),
    ]

    app: Inkr

    @override
    def on_mount(self) -> None:
        """Populate the tree when the DOM is ready."""
        self.show_root = False
        self._reload()

    @on(ReloadRequested)
    def _reload(self) -> None:
        """Reload the tree."""
        info = self.app.mkv.info_json or {}
        self.clear().add_json(msgspec.to_builtins(info))

    @work(exclusive=True)
    async def action_edit_title(self) -> None:
        """Edit the MKV container title."""
        mkv = self.app.mkv.manager
        title = await self.app.push_screen_wait(
            EditScreen(mkv.title, "Edit MKV Title", "Enter title..."),
        )
        if title is not None:
            mkv.title = title
