# -----------------------------------------------------------------------------
#  Copyright (c) 2025  TwilightSparkle42
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
# -----------------------------------------------------------------------------
"""String-to-value parsers used by environment helpers and general utilities.

The functions in this module:
- Accept ``str`` input only.
- Return a well-typed value on success.
- Raise ``ValueError`` on malformed input (never return ``None``).

They intentionally avoid side effects and stay small so they compose cleanly with
env wrappers and other callers that need predictable error semantics.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable
from datetime import datetime, timedelta, tzinfo
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast
from urllib.parse import ParseResult, urlparse

__all__ = [
    "ItemCast",
    "JsonLoader",
    "MappingValue",
    "parse_base64_bytes",
    "parse_base64_str",
    "parse_bool",
    "parse_bytes_size",
    "parse_datetime",
    "parse_decimal",
    "parse_enum",
    "parse_float",
    "parse_int",
    "parse_json",
    "parse_json_typed",
    "parse_list",
    "parse_mapping",
    "parse_path",
    "parse_set",
    "parse_str",
    "parse_timedelta",
    "parse_url",
]


if TYPE_CHECKING:
    from hv_utils.hv_types import JSONValue

type ItemCast[T] = Callable[[str], T]
type JsonLoader[T] = Callable[[str], T]
type MappingValue[T] = Callable[[str], T]

E = TypeVar("E", bound=Enum)

_TRUE_VALUES = {"1", "true", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "no", "n", "off"}
_BYTES_DECIMAL_MULTIPLIERS: dict[str, Decimal] = {
    "": Decimal(1),
    "B": Decimal(1),
    "K": Decimal(1_000),
    "KB": Decimal(1_000),
    "M": Decimal(1_000_000),
    "MB": Decimal(1_000_000),
    "G": Decimal(1_000_000_000),
    "GB": Decimal(1_000_000_000),
    "T": Decimal(1_000_000_000_000),
    "TB": Decimal(1_000_000_000_000),
}
_BYTES_BINARY_MULTIPLIERS: dict[str, Decimal] = {
    "KI": Decimal(1024),
    "KIB": Decimal(1024),
    "MI": Decimal(1024**2),
    "MIB": Decimal(1024**2),
    "GI": Decimal(1024**3),
    "GIB": Decimal(1024**3),
    "TI": Decimal(1024**4),
    "TIB": Decimal(1024**4),
}

_SIZE_PATTERN = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]{0,3})\s*$")
_DURATION_PATTERN = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([smhdSMHD])\s*$")


def parse_str(value: str) -> str:
    """Return the input unchanged.

    Returns:
        str: The original input value.

    """
    return value


def parse_bool(value: str) -> bool:
    """Parse a boolean-like string such as ``true``/``false`` or ``1``/``0``.

    Returns:
        bool: Parsed boolean value.

    Raises:
        ValueError: If the value cannot be interpreted as a boolean.

    """
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    message = f"Invalid boolean literal: {value!r}"
    raise ValueError(message)


def parse_int(value: str) -> int:
    """Parse an integer string using base-10 semantics.

    Returns:
        int: Parsed integer.

    Raises:
        ValueError: If the value is not a valid integer literal.

    """
    try:
        return int(value.strip())
    except ValueError as exc:
        msg = f"Invalid integer literal: {value!r}"
        raise ValueError(msg) from exc


def parse_float(value: str) -> float:
    """Parse a floating-point string.

    Returns:
        float: Parsed float.

    Raises:
        ValueError: If the value is not a valid float literal.

    """
    try:
        return float(value.strip())
    except ValueError as exc:
        msg = f"Invalid float literal: {value!r}"
        raise ValueError(msg) from exc


def parse_decimal(value: str) -> Decimal:
    """Parse a decimal string into :class:`Decimal`.

    Returns:
        Decimal: Parsed decimal value.

    Raises:
        ValueError: If the value is not a valid decimal literal.

    """
    try:
        return Decimal(value.strip())
    except InvalidOperation as exc:
        msg = f"Invalid decimal literal: {value!r}"
        raise ValueError(msg) from exc


def parse_enum[E: Enum](value: str, enum_type: type[E]) -> E:
    """Parse a string into an :class:`Enum` member by name or value.

    Returns:
        E: Matching enum member.

    Raises:
        ValueError: If the value does not correspond to any member.

    """
    normalized = value.strip()
    try:
        return enum_type[normalized]
    except KeyError:
        pass
    try:
        return enum_type(normalized)
    except (ValueError, TypeError) as exc:
        message = f"Invalid {enum_type.__name__} literal: {value!r}"
        raise ValueError(message) from exc


def parse_path(value: str) -> Path:
    """Parse a filesystem path string into :class:`Path`.

    Returns:
        Path: Parsed path object.

    """
    return Path(value)


def parse_url(value: str) -> ParseResult:
    """Parse a URL string ensuring a scheme is present.

    Returns:
        ParseResult: Parsed URL object.

    Raises:
        ValueError: If the URL is missing a scheme.

    """
    result = urlparse(value)
    if not result.scheme:
        msg = f"Invalid URL (missing scheme): {value!r}"
        raise ValueError(msg)
    return result


def parse_timedelta(value: str) -> timedelta:
    """Parse duration strings such as ``10s``, ``5m``, ``2h``, ``1d``.

    Returns:
        timedelta: Parsed duration.

    Raises:
        ValueError: If the literal is not recognised.

    """
    match = _DURATION_PATTERN.fullmatch(value)
    if not match:
        msg = f"Invalid duration literal: {value!r}"
        raise ValueError(msg)
    amount_str, unit = match.groups()
    amount = float(amount_str)
    seconds_per_unit = {
        "S": 1,
        "M": 60,
        "H": 3600,
        "D": 86400,
    }
    multiplier = seconds_per_unit[unit.upper()]
    return timedelta(seconds=amount * multiplier)


def parse_datetime(value: str, *, tzinfo: tzinfo | None = None) -> datetime:
    """Parse an ISO-8601 datetime string, optionally coercing timezone.

    Returns:
        datetime: Parsed datetime with timezone adjusted if requested.

    """
    dt = datetime.fromisoformat(value)
    if tzinfo is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tzinfo)
    return dt.astimezone(tzinfo)


def parse_bytes_size(value: str) -> int:
    """Parse human-friendly byte sizes like ``10MB``, ``5k``, ``1Gi`` into bytes.

    Returns:
        int: Size in whole bytes.

    Raises:
        ValueError: If the unit is unknown or resolves to fractional bytes.

    """
    match = _SIZE_PATTERN.fullmatch(value)
    if not match:
        msg = f"Invalid byte size literal: {value!r}"
        raise ValueError(msg)
    number, unit = match.groups()
    unit_normalized = unit.upper()
    multiplier = _BYTES_DECIMAL_MULTIPLIERS.get(unit_normalized)
    if multiplier is None:
        multiplier = _BYTES_BINARY_MULTIPLIERS.get(unit_normalized)
    if multiplier is None:
        msg = f"Unknown size unit in {value!r}"
        raise ValueError(msg)
    quantity = Decimal(number) * multiplier
    if quantity != quantity.to_integral_value():
        msg = f"Size must resolve to whole bytes: {value!r}"
        raise ValueError(msg)
    return int(quantity)


def parse_list[T](value: str, *, sep: str = ",", item_cast: ItemCast[T] | None = None) -> list[T]:
    """Parse a separated list of values into a :class:`list`.

    Returns:
        list[T]: Parsed items after casting.

    Raises:
        ValueError: If any item is empty.

    """  # noqa: DOC502 - item case may raise ValueError
    caster = item_cast or parse_str
    return [caster(part) for part in _split_items(value, sep)]  # type: ignore[misc]


def parse_set[T](value: str, *, sep: str = ",", item_cast: ItemCast[T] | None = None) -> set[T]:
    """Parse a separated list of values into a :class:`set`.

    Returns:
        set[T]: Parsed items after casting.

    Raises:
        ValueError: If any item is empty.

    """  # noqa: DOC502 - ValueError may be raised by ItemCase
    caster = item_cast or parse_str
    return {caster(part) for part in _split_items(value, sep)}  # type: ignore[misc]


def parse_mapping(
    value: str,
    *,
    pair_sep: str = ",",
    kv_sep: str = "=",
    value_cast: MappingValue[str] = str,
) -> dict[str, str]:
    """Parse a separated list of key/value pairs into a :class:`dict`.

    Returns:
        dict[str, str]: Parsed mapping of keys to cast values.

    Raises:
        ValueError: If separators are missing, keys are empty, or items are empty.

    """
    pairs = _split_items(value, pair_sep)
    mapping: dict[str, str] = {}
    for pair in pairs:
        if kv_sep not in pair:
            msg = f"Missing key/value separator {kv_sep!r} in {pair!r}"
            raise ValueError(msg)
        key, raw_val = pair.split(kv_sep, 1)
        key_stripped, val_stripped = key.strip(), raw_val.strip()
        if not key_stripped:
            msg = f"Empty key in pair {pair!r}"
            raise ValueError(msg)
        mapping[key_stripped] = value_cast(val_stripped)
    return mapping


def parse_json(value: str) -> JSONValue:
    """Parse a JSON string using :func:`json.loads`.

    Returns:
        Any: Parsed JSON value.

    """
    return cast("JSONValue", json.loads(value))


def parse_json_typed[T](value: str, *, loader: JsonLoader[T] = json.loads) -> T:
    """Parse JSON into a typed object using a configurable loader.

    Returns:
        T: Parsed JSON value.

    """
    return loader(value)


def parse_base64_bytes(value: str) -> bytes:
    """Decode a base64-encoded string into bytes.

    Returns:
        bytes: Decoded payload.

    Raises:
        ValueError: If the input is not valid base64.

    """
    try:
        return base64.b64decode(value, validate=True)
    except (base64.binascii.Error, ValueError) as exc:  # type: ignore[attr-defined]
        msg = f"Invalid base64 literal: {value!r}"
        raise ValueError(msg) from exc


def parse_base64_str(value: str, *, encoding: str = "utf-8", errors: str = "strict") -> str:
    """Decode a base64-encoded string into text.

    Returns:
        str: Decoded text.

    """
    raw = parse_base64_bytes(value)
    return raw.decode(encoding, errors)


def _split_items(value: str, sep: str) -> list[str]:
    parts = [part.strip() for part in value.split(sep)]
    if any(part in {None, ""} for part in parts):
        msg = f"Empty item in separated list: {value!r}"
        raise ValueError(msg)
    return parts
