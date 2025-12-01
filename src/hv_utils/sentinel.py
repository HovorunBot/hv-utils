# -----------------------------------------------------------------------------
#  Copyright (c) 2025  TwilightSparkle42
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
#
#  Contributions:
#     - TwilightSparkle42 — general maintenance
# -----------------------------------------------------------------------------
"""Sentinel helpers for representing missing values."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final, NoReturn, Self, cast

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["MISSING", "MissingType"]


class MissingType:
    """Sentinel representing an unspecified value.

    This instance is intentionally typed as ``Any`` to satisfy strict type
    checkers while still allowing identity checks at runtime to distinguish
    between omitted and explicitly provided values such as ``None``.
    """

    __slots__ = ()
    _instance: Self | None = None
    _ALLOWED_ATTRIBUTES: Final[frozenset[str]] = frozenset({
        "__bool__",
        "__class__",
        "__copy__",
        "__deepcopy__",
        "__repr__",
        "__reduce__",
        "__reduce_ex__",
        "__str__",
    })

    def __new__(cls) -> Self:
        """Ensure the sentinel remains a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __getattribute__(self, name: str) -> Any:  # noqa: ANN401
        """Restrict attribute access to a minimal allowlist.

        Returns:
            Any: The requested magic method or attribute when permitted.

        Raises:
            AttributeError: When accessing any attribute not explicitly allowed.

        """
        if name in MissingType._ALLOWED_ATTRIBUTES:
            return super().__getattribute__(name)
        message = f"Missing sentinel has no attribute '{name}'"
        raise AttributeError(message)

    def __setattr__(self, name: str, value: object) -> NoReturn:
        """Raise when setting attributes on the sentinel.

        Raises:
            AttributeError: Always, because the sentinel is immutable.

        """
        message = "Missing sentinel is immutable"
        raise AttributeError(message)

    def __delattr__(self, name: str) -> NoReturn:
        """Raise when deleting attributes on the sentinel.

        Raises:
            AttributeError: Always, because the sentinel is immutable.

        """
        message = "Missing sentinel is immutable"
        raise AttributeError(message)

    def __bool__(self) -> bool:
        """Evaluate the sentinel as falsy.

        Returns:
            bool: Always ``False``.

        """
        return False

    def __repr__(self) -> str:
        """Return a stable representation for debugging.

        Returns:
            str: The literal "Missing".

        """
        return "Missing"

    def __str__(self) -> str:
        """Return a user-facing string representation.

        Returns:
            str: The literal "Missing".

        """
        return "Missing"

    def __copy__(self) -> MissingType:
        """Return the singleton instance during shallow copy.

        Returns:
            MissingType: Always the singleton sentinel.

        """
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> MissingType:
        """Return the singleton instance during deep copy.

        Args:
            memo: Copy memoization dictionary.

        Returns:
            MissingType: Always the singleton sentinel.

        """
        memo[id(self)] = self
        return self

    def __reduce__(self) -> tuple[Callable[[], MissingType], tuple[()]]:
        """Reduce to the module-level singleton when pickled.

        Returns:
            tuple[Callable[[], MissingType], tuple[()]]: Factory and arguments used for pickling.

        """
        return _get_missing, ()


def _get_missing() -> MissingType:
    return cast("MissingType", MISSING)


MISSING: Final[Any] = MissingType()
