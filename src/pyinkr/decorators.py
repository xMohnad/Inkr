from __future__ import annotations

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import TYPE_CHECKING, Concatenate, ParamSpec, TypeVar

if TYPE_CHECKING:
    from textual.notifications import SeverityLevel
    from textual.widget import Widget

P = ParamSpec("P")
R = TypeVar("R")
W = TypeVar("W", bound="Widget")

AsyncMethod = Callable[Concatenate[W, P], Coroutine[object, object, R]]


def catch_errors(
    *, severity: SeverityLevel = "error"
) -> Callable[[AsyncMethod[W, P, R]], AsyncMethod[W, P, "R | None"]]:
    """Wrap an async widget/screen method, routing any exception to `self.notify`.

    Replaces the repeated::

        try:
            ...
        except Exception as e:
            self.notify(str(e), severity="error")

    pattern that previously appeared independently in several action handlers.
    `self` must be a Textual `Widget`/`Screen` (anything with `.notify`).
    """

    def decorator(func: AsyncMethod[W, P, R]) -> AsyncMethod[W, P, "R | None"]:
        @wraps(func)
        async def wrapper(self: W, *args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                self.notify(str(e), severity=severity)
                return None

        return wrapper

    return decorator
