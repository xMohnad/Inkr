"""
Provides a customizable options dictionary with hook-based validation
for setting keys.

Key Type Mapping:
    bool: Used for flag options (on/off switches).
    None: Used for flags without values (presence only, e.g., ``--webm``).
    str:  Used for textual options (e.g., name, language, title, tags, compression).
    int:  Used for numeric options (e.g., sync delay in ms or frames).

Hook definition methods:
    1) Use @hook_for("key1", "key2", ...)
    2) Or define a method named: _on_<key_with_-_replaced_by_>_set
     e.g. for key "track-name" the hook name is "_on_track_name_set"

Hook return semantics:
    - If hook returns False -> the assignment is blocked.
    - If hook returns True or None -> assignment proceeds and the original value is used.
    - If hook returns any other value -> that value is used as the *replacement* value to store.

Example:
    ```python
    class MyOpts(OptionsDict[str, object]):
        @hook_for("title")
        def _validate_and_normalize(self, value):
            if not isinstance(value, str):
                return False
            # normalize
            return value.strip().lower()

    opts = MyOpts()
    opts["title"] = "  Awesome Title  " # hook returns "awesome title" -> stored value is "awesome title"
    ```
"""

from __future__ import annotations

from typing import Callable, Generic, Literal, TypeVar, override

from textual import log

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


_F = TypeVar("_F", bound=Callable[..., object])


def hook_for(*keys: str) -> Callable[[_F], _F]:
    """
    Decorator to register one hook for multiple keys.

    Example:
        ```python
        @hook_for("track-name", "language")
        def validate_string(self, value) -> bool:
            return isinstance(value, str)
        ```
    """

    def decorator(func: _F) -> _F:
        setattr(func, "_hook_keys", keys)
        return func

    return decorator


class OptionsDict(dict[_KT, _VT], Generic[_KT, _VT]):
    """A dictionary subclass that supports validation/transformation hooks when setting keys."""

    def __init__(self, initial: dict[_KT, _VT] | None = None) -> None:
        """
        Initialize the dictionary optionally

        Args:
            initial (dict[_KT, _VT] | None): Optional initial dictionary
                to pre-populate the OptionsDict. If None, starts empty.
        """
        super().__init__()

        if initial:
            self.update(initial)

        # register hooks for multiple keys
        for attr_name in dir(self):
            method: Callable[[_VT], _VT | bool | None] | None = getattr(self, attr_name, None)
            hook_keys: list[str] = getattr(method, "_hook_keys", [])

            if callable(method) and hook_keys:
                for key in hook_keys:
                    setattr(self, f"_on_{self._convert_attr(key)}_set", method)

    @override
    def __setitem__(self, key: _KT, value: _VT, /) -> None:
        """Set self[key] to value, possibly using a hook to validate/transform it."""
        assert isinstance(key, str), f"Key must be a string, got {type(key).__name__}"

        hook_name = f"_on_{self._convert_attr(key)}_set"
        hook: Callable[[_VT], _VT | bool | None] | None = getattr(self, hook_name, None)

        used_value = value
        if callable(hook):
            result = hook(value)

            # Block assignment
            if result is False:
                log.debug(f"[Hook] Assignment for '{key}' was blocked.")
                return

            # If hook returns True or None => accept original
            if result is True or result is None:
                used_value = value
                log.debug(f"[Hook] set {key} to {used_value!r}")
            else:
                # Any other return value is used as replacement
                used_value = result
                log.debug(f"[Hook] transformed {key}: {value!r} -> {used_value!r}")

        super().__setitem__(key, used_value)

    def set_option(self, option: _KT, value: _VT) -> None:
        """Set an option."""
        self[option] = value

    def _convert_attr(self, attr_name: str) -> str:
        """Normalize attribute names for hook lookup."""
        return attr_name.replace("-", "_")

    # Types

    def _string(self, value: object) -> bool:
        """Validate that value is a non-empty string."""
        return isinstance(value, str) and len(value) > 0


Trackeys = Literal[
    "track-name",
    "language",
    "sync",
    "tags",
    "default-track",
    "forced-track",
    "hearing-impaired-flag",
    "visual-impaired-flag",
    "original-flag",
    "commentary-flag",
    "compression",
    "no-track-tags",
]
"""Defines some available keys for track options."""


class TrackOptions(OptionsDict[Trackeys, object]):
    """
    Options dictionary for track-level settings.

    Hooks:
        - `track-name`, `tags`:
            Must be non-empty strings.
        - `default-track`, `forced-track`, `hearing-impaired-flag`,
          `visual-impaired-flag`, `original-flag`, `commentary-flag`,
          `no-track-tags`:
            Must be boolean flags.
        - `sync`:
            Must be an integer (e.g., sync delay in ms or frames).
        - `compression`:
            Must be one of the allowed values: "zlib", "none", "mpeg4_p2", "mpeg4p2".
    """

    @hook_for("track-name", "tags")
    def _validate_string(self, value: object) -> bool:
        """Validate that the value is a non-empty string."""
        return self._string(value)

    @hook_for(
        "default-track",
        "forced-track",
        "hearing-impaired-flag",
        "visual-impaired-flag",
        "original-flag",
        "commentary-flag",
        "no-track-tags",
    )
    def _validate_flag(self, value: object) -> bool:
        """Validate that the value is a boolean flag."""
        return isinstance(value, bool)

    @hook_for("sync")
    def _validate_sync(self, value: object) -> bool:
        """Validate that the value is an integer."""
        return isinstance(value, int)

    @hook_for("compression")
    def _validate_compression(self, value: object) -> bool:
        """Validate that the value is one of the allowed compression types."""
        return value in {"zlib", "none", "mpeg4_p2", "mpeg4p2"}


GlobalKeys = Literal[
    "title",
    "disable-track-statistics-tags",
    "default-language",
    "webm",
    "split",
]
"""Defines some available keys for global options."""


class GlobalOptions(OptionsDict[GlobalKeys, object]):
    """
    Options dictionary for global-level settings.

    Hooks:
        - `disable-track-statistics-tags`:
            Must be a boolean flag.
        - `title`:
            Must be a non-empty string.
    """

    @hook_for("disable-track-statistics-tags")
    def _validate_flag(self, value: object) -> bool:
        """Validate that the flag is boolean."""
        return isinstance(value, bool)

    def _on_title_set(self, value: object) -> bool:
        """Validate that title is a non-empty string."""
        return self._string(value)
