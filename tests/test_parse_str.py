# -----------------------------------------------------------------------------
#  Copyright (c) 2025  TwilightSparkle42
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
# -----------------------------------------------------------------------------
"""Tests for string-to-value parsers."""

from __future__ import annotations

import base64
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from urllib.parse import ParseResult

import pytest

from hv_utils.parse_str import (
    parse_base64_bytes,
    parse_base64_str,
    parse_bool,
    parse_bytes_size,
    parse_datetime,
    parse_decimal,
    parse_enum,
    parse_float,
    parse_int,
    parse_json,
    parse_json_typed,
    parse_list,
    parse_mapping,
    parse_path,
    parse_set,
    parse_timedelta,
    parse_url,
)


class Color(Enum):
    """Simple enum for color parsing tests."""

    RED = "red"
    BLUE = "blue"


def test_parse_bool_accepts_truthy_and_falsy_tokens() -> None:
    """parse_bool handles canonical truthy/falsy tokens and rejects invalid values."""
    assert parse_bool("TRUE") is True
    assert parse_bool("0") is False
    with pytest.raises(ValueError, match="Invalid boolean literal: 'maybe'"):
        parse_bool("maybe")


def test_parse_int_requires_integer_strings() -> None:
    """parse_int converts valid integers and rejects non-integer inputs."""
    assert parse_int("10") == 10  # noqa: PLR2004
    with pytest.raises(ValueError, match=r"Invalid integer literal: '10\.5'"):
        parse_int("10.5")


def test_parse_float_accepts_decimal_strings() -> None:
    """parse_float returns floating-point values for decimal strings."""
    assert parse_float("3.14") == pytest.approx(math.pi, abs=0.002)  # Near Pi
    assert math.isnan(parse_float("nan"))
    assert math.isinf(parse_float("inf"))
    assert math.isinf(parse_float("-inf"))
    with pytest.raises(ValueError, match="Invalid float literal: 'abc'"):
        parse_float("abc")


def test_parse_decimal_preserves_precision() -> None:
    """parse_decimal returns Decimal values and rejects invalid input."""
    assert parse_decimal("2.50") == Decimal("2.50")
    with pytest.raises(ValueError, match="Invalid decimal literal: 'abc'"):
        parse_decimal("abc")


def test_parse_enum_accepts_names_and_values() -> None:
    """parse_enum resolves enum members by name or value."""
    assert parse_enum("RED", Color) is Color.RED
    assert parse_enum("blue", Color) is Color.BLUE
    assert parse_enum("  RED  ", Color) is Color.RED
    with pytest.raises(ValueError, match="Invalid Color literal: 'green'"):
        parse_enum("green", Color)


def test_parse_url_requires_scheme() -> None:
    """parse_url parses URLs with schemes and rejects missing schemes."""
    result = parse_url("https://example.com/path")
    assert isinstance(result, ParseResult)
    with pytest.raises(ValueError, match=r"Invalid URL \(missing scheme\): 'example\.com/path'"):
        parse_url("example.com/path")


def test_parse_timedelta_supports_time_units() -> None:
    """parse_timedelta accepts second, minute, hour, and day suffixes."""
    assert parse_timedelta("10s") == timedelta(seconds=10)
    assert parse_timedelta("2h") == timedelta(hours=2)
    with pytest.raises(ValueError, match="Invalid duration literal: '5w'"):
        parse_timedelta("5w")


def test_parse_datetime_applies_default_tzinfo() -> None:
    """parse_datetime attaches tzinfo when the input is naive."""
    parsed = parse_datetime("2025-01-02T03:04:05", tzinfo=UTC)
    assert parsed == datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)
    aware = parse_datetime("2025-01-02T03:04:05+00:00", tzinfo=UTC)
    assert aware.tzinfo is UTC


def test_parse_bytes_size_accepts_decimal_and_binary_units() -> None:
    """parse_bytes_size converts decimal and binary unit suffixes."""
    ten_megabytes = 10_000_000
    assert parse_bytes_size("10MB") == ten_megabytes
    assert parse_bytes_size("1Gi") == 1024**3
    with pytest.raises(ValueError, match=r"Size must resolve to whole bytes: '1\.5B'"):
        parse_bytes_size("1.5B")
    with pytest.raises(ValueError, match=r"Unknown size unit in '10XB'"):
        parse_bytes_size("10XB")


def test_parse_list_splits_values_with_separator() -> None:
    """parse_list splits a string into a list using the provided separator."""
    assert parse_list("a,b,c") == ["a", "b", "c"]
    with pytest.raises(ValueError, match="Empty item in separated list: 'a,,b'"):
        parse_list("a,,b")


def test_parse_set_casts_items_and_respects_separator() -> None:
    """parse_set converts separated tokens to a set using the given cast."""
    assert parse_set("1|2|3", sep="|", item_cast=int) == {1, 2, 3}
    with pytest.raises(ValueError, match="Empty item in separated list: '1\\|\\|2'"):
        parse_set("1||2", sep="|", item_cast=int)


def test_parse_mapping_reads_key_value_pairs() -> None:
    """parse_mapping parses mappings separated by pair and kv delimiters."""
    assert parse_mapping("k1=v1,k2=v2") == {"k1": "v1", "k2": "v2"}
    with pytest.raises(ValueError, match="Empty key in pair '=value'"):
        parse_mapping("=value")


def test_parse_json_returns_parsed_object() -> None:
    """parse_json loads JSON payloads from strings."""
    assert parse_json('{"a":1}') == {"a": 1}
    with pytest.raises(ValueError, match="Expecting property name"):
        parse_json("{invalid}")


def test_parse_json_typed_enforces_loader_errors() -> None:
    """parse_json_typed returns typed results and raises on invalid JSON."""
    assert parse_json_typed("1") == 1
    with pytest.raises(ValueError, match="Expecting property name"):
        parse_json_typed("{")


def test_parse_base64_bytes_decodes_payload() -> None:
    """parse_base64_bytes decodes base64 strings into bytes."""
    payload = base64.b64encode(b"hello").decode()
    assert parse_base64_bytes(payload) == b"hello"
    with pytest.raises(ValueError, match="Invalid base64 literal: 'not-base64'"):
        parse_base64_bytes("not-base64")


def test_parse_base64_str_decodes_payload() -> None:
    """parse_base64_str decodes base64 strings into text."""
    payload = base64.b64encode(b"hello").decode()
    assert parse_base64_str(payload) == "hello"
    with pytest.raises(ValueError, match="Invalid base64 literal: 'bad%%'"):
        parse_base64_str("bad%%")


def test_parse_path_returns_path_object() -> None:
    """parse_path converts string paths to Path instances."""
    assert parse_path("/tmp/data") == Path("/tmp/data")  # noqa: S108 - test only
