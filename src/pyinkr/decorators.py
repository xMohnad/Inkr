from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

if TYPE_CHECKING:
    from textual.notifications import SeverityLevel
    from textual.widget import Widget

F = TypeVar("F", bound=Callable[..., Any])


def catch_errors(*, severity: SeverityLevel = "error") -> Callable[[F], F]:
    """Wrap an async widget/screen method, routing any exception to `self.notify`.

    Replaces the repeated::

        try:
            ...
        except Exception as e:
            self.notify(str(e), severity="error")

    pattern that previously appeared independently in several action handlers.
    `self` must be a Textual `Widget`/`Screen` (anything with `.notify`).
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self: "Widget", *args: Any, **kwargs: Any) -> Any:
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                self.notify(str(e), severity=severity)
                return None

        return cast(F, wrapper)

    return decorator
