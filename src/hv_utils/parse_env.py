# -----------------------------------------------------------------------------
#  Copyright (c) 2025  TwilightSparkle42
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
# -----------------------------------------------------------------------------
"""Environment variable helpers layered on :mod:`hv_utils.parse_str`.

The ``env_*`` functions:
- Fetch variables from a mapping (defaults to ``os.environ``).
- Parse them into typed values using the ``parse_*`` helpers.
- Decide whether to raise or return defaults via a ``required`` flag.

Use ``parse_*`` directly when you already have strings; use ``env_*`` when sourcing from
the environment with predictable missing/invalid handling.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from enum import Enum
from typing import TYPE_CHECKING, Any, NoReturn

from hv_utils.parse_str import (
    ItemCast,
    parse_base64_bytes,
    parse_base64_str,
    parse_bool,
    parse_datetime,
    parse_decimal,
    parse_enum,
    parse_float,
    parse_int,
    parse_json,
    parse_list,
    parse_mapping,
    parse_path,
    parse_set,
    parse_str,
    parse_timedelta,
    parse_url,
)
from hv_utils.sentinel import MISSING

if TYPE_CHECKING:
    from datetime import datetime, timedelta, tzinfo
    from decimal import Decimal
    from pathlib import Path
    from urllib.parse import ParseResult

    from hv_utils.hv_types import JSONValue


__all__ = [
    "env_base64_bytes",
    "env_base64_str",
    "env_bool",
    "env_datetime",
    "env_decimal",
    "env_enum",
    "env_float",
    "env_int",
    "env_json",
    "env_list",
    "env_mapping",
    "env_or_default",
    "env_or_none",
    "env_path",
    "env_set",
    "env_str",
    "env_timedelta",
    "env_url",
    "get_env",
    "on_error_return_value",
    "raise_error",
]

type CastFn = Callable[[str], Any]
type ErrorHandler = Callable[[str, str | None, CastFn | None], Any | None]


def raise_error(name: str, value: str | None = None, _cast: CastFn | None = None) -> NoReturn:
    """Raise a :class:`ValueError` describing the missing or invalid value.

    Args:
        name: Environment variable name.
        value: Raw value when present; ``None`` when the variable is absent.
        _cast: Casting function supplied to :func:`get_env` (unused, kept for signature parity).

    Raises:
        ValueError: Always, signaling a required variable was missing or invalid.

    """
    msg = f"Value is missing for {name!r}" if value is None else f"Invalid value for {name!r}: {value!r}"
    raise ValueError(msg)


def on_error_return_value[T](value: T | None) -> ErrorHandler:
    """Return an error handler that yields the provided value on failure.

    Useful when an environment variable is optional and a static fallback is acceptable.

    Args:
        value: Value to return when the variable is missing or fails to parse.

    Returns:
        ErrorHandler[T]: Callable compatible with :func:`get_env`'s ``on_error`` parameter.

    """

    def _on_error(_name: str, _value: str | None = None, _cast: CastFn | None = None) -> T | None:
        return value

    return _on_error


def get_env[T](
    name: str,
    *,
    cast: Callable[[str], T],
    default: T | None = MISSING,
    env: Mapping[str, str] | None = None,
    on_error: ErrorHandler = raise_error,
) -> T | None:
    """Fetch and cast an environment variable with configurable error handling.

    Behavior:
    - Missing variables: return ``default`` when provided; otherwise delegate to ``on_error``.
    - Present but invalid variables: delegate to ``on_error`` with the raw value.
    - Valid variables: return the parsed value.

    Args:
        name: Environment variable name.
        cast: Callable converting the raw string to the desired type.
        default: Value returned when the variable is missing; pass :data:`MISSING` to signal no default.
        env: Optional mapping supplying environment variables; defaults to :data:`os.environ`.
        on_error: Handler invoked for missing or invalid values; may raise or return a fallback.

    Returns:
        T | None: Parsed value, provided default, or result of ``on_error``.

    """
    if env is None:
        env = os.environ

    try:
        raw = env[name]
    except KeyError:
        if default is MISSING:
            return on_error(name, None, cast)
        return default

    try:
        return cast(raw)
    except (TypeError, ValueError):
        return on_error(name, raw, cast)


def env_or_none[T](name: str, *, cast: Callable[[str], T], env: Mapping[str, str] | None = None) -> T | None:
    """Return the cast environment variable or ``None`` when missing or invalid.

    Args:
        name: Environment variable name.
        cast: Callable converting the raw string to the desired type.
        env: Optional mapping supplying environment variables; defaults to :data:`os.environ`.

    Returns:
        T | None: Parsed value or ``None`` when absent or unparsable.

    """
    return get_env(name, cast=cast, default=None, env=env, on_error=on_error_return_value(None))


def env_or_default[T](
    name: str, *, cast: Callable[[str], T], default: T, env: Mapping[str, str] | None = None
) -> T | None:
    """Return the cast environment variable or a supplied default on failure.

    Args:
        name: Environment variable name.
        cast: Callable converting the raw string to the desired type.
        default: Value returned when the variable is missing or invalid.
        env: Optional mapping supplying environment variables; defaults to :data:`os.environ`.

    Returns:
        T | None: Parsed value or provided default when missing/invalid.

    """
    return get_env(name, cast=cast, default=default, env=env, on_error=on_error_return_value(default))


def env_str(
    name: str, *, default: str | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> str | None:
    """Return a string environment variable with optional default and requirement flag.

    Returns:
        str | None: Parsed value, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_str, default=default, required=required, env=env)


def env_bool(
    name: str, *, default: bool | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> bool | None:
    """Return a boolean environment variable parsed with :func:`parse_bool`.

    Args mirror :func:`env_str`; when ``required`` is True, a missing or invalid value raises ``ValueError``.

    Returns:
        bool | None: Parsed value, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_bool, default=default, required=required, env=env)


def env_int(
    name: str, *, default: int | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> int | None:
    """Return an integer environment variable parsed with :func:`parse_int`.

    Returns:
        int | None: Parsed value, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_int, default=default, required=required, env=env)


def env_float(
    name: str, *, default: float | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> float | None:
    """Return a floating-point environment variable parsed with :func:`parse_float`.

    Returns:
        float | None: Parsed value, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_float, default=default, required=required, env=env)


def env_decimal(
    name: str, *, default: Decimal | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> Decimal | None:
    """Return a :class:`Decimal` environment variable parsed with :func:`parse_decimal`.

    Returns:
        Decimal | None: Parsed value, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_decimal, default=default, required=required, env=env)


def env_enum[TEnum: Enum](
    name: str,
    enum_type: type[TEnum],
    *,
    default: TEnum | None = None,
    required: bool = False,
    env: Mapping[str, str] | None = None,
) -> TEnum | None:
    """Return an :class:`Enum` environment variable parsed with :func:`parse_enum`.

    Returns:
        TEnum | None: Parsed enum member, provided default, or ``None`` when optional and missing.

    """

    def parser(raw: str) -> TEnum:
        return parse_enum(raw, enum_type)

    return _env_wrapper(name, parser, default=default, required=required, env=env)


def env_path(
    name: str, *, default: Path | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> Path | None:
    """Return a :class:`Path` environment variable parsed with :func:`parse_path`.

    Returns:
        Path | None: Parsed path, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_path, default=default, required=required, env=env)


def env_url(
    name: str, *, default: ParseResult | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> ParseResult | None:
    """Return a parsed URL environment variable.

    Returns:
        ParseResult | None: Parsed URL, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_url, default=default, required=required, env=env)


def env_timedelta(
    name: str, *, default: timedelta | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> timedelta | None:
    """Return a :class:`timedelta` environment variable parsed with :func:`parse_timedelta`.

    Returns:
        timedelta | None: Parsed duration, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_timedelta, default=default, required=required, env=env)


def env_datetime(
    name: str,
    *,
    default: datetime | None = None,
    required: bool = False,
    env: Mapping[str, str] | None = None,
    tzinfo: tzinfo | None = None,
) -> datetime | None:
    """Return a :class:`datetime` environment variable parsed with :func:`parse_datetime`.

    Returns:
        datetime | None: Parsed datetime, provided default, or ``None`` when optional and missing.

    """

    def parser(raw: str) -> datetime:
        return parse_datetime(raw, tzinfo=tzinfo)

    return _env_wrapper(name, parser, default=default, required=required, env=env)


def env_list[T](  # noqa: PLR0913
    name: str,
    *,
    item_cast: ItemCast[T] | None = None,
    sep: str = ",",
    default: list[T] | None = None,
    required: bool = False,
    env: Mapping[str, str] | None = None,
) -> list[T] | None:
    """Return a list environment variable parsed with :func:`parse_list`.

    Returns:
        list[T] | None: Parsed list, provided default, or ``None`` when optional and missing.

    """

    def parser(raw: str) -> list[T]:
        return parse_list(raw, sep=sep, item_cast=item_cast)

    return _env_wrapper(name, parser, default=default, required=required, env=env)


def env_set[T](  # noqa: PLR0913
    name: str,
    *,
    item_cast: ItemCast[T] | None = None,
    sep: str = ",",
    default: set[T] | None = None,
    required: bool = False,
    env: Mapping[str, str] | None = None,
) -> set[T] | None:
    """Return a set environment variable parsed with :func:`parse_set`.

    Returns:
        set[T] | None: Parsed set, provided default, or ``None`` when optional and missing.

    """

    def parser(raw: str) -> set[T]:
        return parse_set(raw, sep=sep, item_cast=item_cast)

    return _env_wrapper(name, parser, default=default, required=required, env=env)


def env_mapping(  # noqa: PLR0913
    name: str,
    *,
    pair_sep: str = ",",
    kv_sep: str = "=",
    default: dict[str, str] | None = None,
    required: bool = False,
    env: Mapping[str, str] | None = None,
) -> dict[str, str] | None:
    """Return a mapping environment variable parsed with :func:`parse_mapping`.

    Returns:
        dict[str, str] | None: Parsed mapping, provided default, or ``None`` when optional and missing.

    """

    def parser(raw: str) -> dict[str, str]:
        return parse_mapping(raw, pair_sep=pair_sep, kv_sep=kv_sep)

    return _env_wrapper(name, parser, default=default, required=required, env=env)


def env_json(
    name: str, *, default: JSONValue | None = None, required: bool = False, env: Mapping[str, str] | None = None
) -> JSONValue | None:
    """Return a parsed JSON environment variable.

    Returns:
        JSONValue | None: Parsed JSON value, provided default, or ``None`` when optional and missing.

    """
    parser: Callable[[str], JSONValue] = parse_json
    return _env_wrapper(name, parser, default=default, required=required, env=env)


def env_base64_bytes(
    name: str,
    *,
    default: bytes | None = None,
    required: bool = False,
    env: Mapping[str, str] | None = None,
) -> bytes | None:
    """Return base64-decoded bytes from an environment variable.

    Returns:
        bytes | None: Decoded bytes, provided default, or ``None`` when optional and missing.

    """
    return _env_wrapper(name, parse_base64_bytes, default=default, required=required, env=env)


def env_base64_str(  # noqa: PLR0913
    name: str,
    *,
    default: str | None = None,
    required: bool = False,
    env: Mapping[str, str] | None = None,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> str | None:
    """Return base64-decoded text from an environment variable.

    Returns:
        str | None: Decoded string, provided default, or ``None`` when optional and missing.

    """

    def parser(raw: str) -> str:
        return parse_base64_str(raw, encoding=encoding, errors=errors)

    return _env_wrapper(name, parser, default=default, required=required, env=env)


def _env_wrapper[T](
    name: str,
    parser: Callable[[str], T],
    *,
    default: T | None,
    required: bool,
    env: Mapping[str, str] | None,
) -> T | None:
    """Shared wrapper used by ``env_*`` helpers.

    This centralises the required/default handling so each wrapper only supplies a parser and
    its own default value.

    Returns:
        T | None: Parsed value, provided default, or ``None`` when optional and missing.

    """
    handler: ErrorHandler = raise_error if required else on_error_return_value(default)
    default_value: T | None = MISSING if required else default
    return get_env(name, cast=parser, default=default_value, env=env, on_error=handler)
