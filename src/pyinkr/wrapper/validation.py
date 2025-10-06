"""
Provides a flexible options system with hook-based validation and transformation logic.

Overview:
    Each field in an options class represents a configurable key, with type hints
    determining what values are accepted. Hooks can be attached to validate or
    modify values dynamically upon assignment.

Type semantics:
    bool  -> Flag options (on/off switches).
    None  -> Presence-only flags (e.g., ``--webm`` has no value, only presence).
    str   -> Textual options (e.g., title, language, name).
    int   -> Numeric options (e.g., synchronization delay in ms or frames).

Hook declaration:
    Hooks are methods that run automatically when a field is set. They can be defined in two ways:
      1. Using the decorator: @hook_for("field1", "field2", ...)
      2. By naming convention: define a method named _on_<field_name>_set

Hook return behavior:
    - Return False: cancel the assignment (value is rejected).
    - Return True or None: accept the original value as-is.
    - Return any other value: use that as the new stored value.

Example:
    ```python
    @dataclass
    class MyOpts(Options):
        title: str | None = None

        @hook_for("title")
        def _validate_and_normalize(self, value):
            if not isinstance(value, str):
                return False
            # Normalize the string before storing
            return value.strip().lower()

    opts = MyOpts()
    opts.title = "  Awesome Title  "
    print(opts.title)  # -> "awesome title"
    ```
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, fields
from functools import cached_property
from typing import Callable, Final, Literal, TypeAlias, TypeVar, get_type_hints, override

from dacite.types import is_optional
from textual import log

_ValueType: TypeAlias = bool | None | str | int
_HookType: TypeAlias = Callable[..., _ValueType]
_F = TypeVar("_F", bound=_HookType)

FLAG_METADATA_KEY: Final = "presence-only"
PRESENCE_ONLY_FIELD: Final[bool] = field(default=False, metadata={FLAG_METADATA_KEY: True})


def hook_for(*fields: str) -> Callable[[_F], _F]:
    """
    Decorator to register one hook for multiple fields.

    Example:
        ```python
        @hook_for("track_name", "language")
        def _validate_string(self, value) -> bool:
            return isinstance(value, str)
        ```
    """

    def decorator(func: _F) -> _F:
        setattr(func, "_hook_fields", fields)
        return func

    return decorator


@dataclass
class Options:
    def __post_init__(self) -> None:
        for attr_name in dir(self):
            method: _HookType | None = getattr(self, attr_name, None)
            hook_keys: list[str] = getattr(method, "_hook_fields", [])

            if callable(method) and hook_keys:
                for key in hook_keys:
                    setattr(self, f"_on_{key}_set", method)

    @cached_property
    def _types(self) -> dict[str, type]:
        return get_type_hints(self.__class__)

    @override
    def __setattr__(self, name: str, value: object, /) -> None:
        """Set an attribute, optionally using a hook to validate or transform the value."""
        hook_name = f"_on_{name}_set"
        hook: _HookType | None = getattr(self, hook_name, None)
        field_type = self._types.get(name)

        used_value = value
        if field_type is None:
            log.debug("[Attr] %r is not a field (likely a method or hook). Skipping type check.", name)
        elif is_optional(field_type) and value is None:
            log.debug("[Hook] %r=%r allows None (Optional). Skipping check.", name, value)
        elif callable(hook):
            result = hook(value)

            # Block assignment
            if result is False:
                log.debug("[Hook] Assignment for %r blocked by hook.", name)
                return

            # If hook returns True or None => accept original
            if result not in (True, None):
                used_value = result
                log.debug("[Hook] %r transformed: %r -> %r", name, value, used_value)
            else:
                log.debug("[Hook] %r set to %r", name, used_value)

        super().__setattr__(name, used_value)

    def items(self) -> Iterable[tuple[str, _ValueType | None]]:
        """
        Yield all active option key–value pairs.

        Behavior:
            - Converts field names to command-line–style keys by replacing underscores with dashes.
            - Skips internal fields (those starting with an underscore) and unset fields (value is None).
            - For presence-only flags (fields with metadata ``FLAG_METADATA_KEY``), yields the key with
              a value of None when the flag is True, indicating that only its presence matters.

        Returns:
            Iterable[tuple[str, _ValueType | None]]:
                An iterator of (option_name, value) pairs suitable for serialization or command-line output.
        """
        for f in fields(self):
            option: str = f.name.replace("_", "-")
            value: _ValueType | None = getattr(self, f.name, None)
            if value is None or f.name.startswith("_"):
                continue
            if FLAG_METADATA_KEY in f.metadata and value is True:
                yield option, None
            else:
                yield option, value

    # Global-level validation hooks

    @hook_for("track_name", "title")
    def _validate_string(self, value: object) -> bool:
        """Validate that given value is a non-empty string."""
        return isinstance(value, str) and len(value) > 0

    @hook_for("default_track", "forced_track", "no_track_tags", "webm")
    def _validate_flag(self, value: object) -> bool:
        """Validate that given value is a boolean flag."""
        return isinstance(value, bool)

    @hook_for("sync")
    def _validate_integer(self, value: object) -> bool:
        """Validate that given value is an integer."""
        return isinstance(value, int)


@dataclass
class TrackOptions(Options):
    """Options for track-level settings."""

    track_name: str | None = None
    language: str | None = None
    default_track: bool | None = None
    forced_track: bool | None = None
    no_track_tags: bool = PRESENCE_ONLY_FIELD
    compression: Literal["zlib", "none", "mpeg4_p2", "mpeg4p2"] | None = None
    sync: int | None = None

    def _on_compression_set(self, value: str) -> bool:
        """Validate that the value is one of the allowed compression types."""
        return value in {"zlib", "none", "mpeg4_p2", "mpeg4p2"}


@dataclass
class GlobalOptions(Options):
    """Options for global-level settings."""

    title: str | None = None
    default_language: str | None = None
    webm: bool = PRESENCE_ONLY_FIELD
