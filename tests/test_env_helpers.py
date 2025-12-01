# -----------------------------------------------------------------------------
#  Copyright (c) 2025  TwilightSparkle42
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
# -----------------------------------------------------------------------------
"""Tests for environment variable helpers."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path

import pytest

from hv_utils.parse_env import (
    env_base64_bytes,
    env_base64_str,
    env_bool,
    env_datetime,
    env_decimal,
    env_enum,
    env_float,
    env_int,
    env_json,
    env_list,
    env_mapping,
    env_or_default,
    env_or_none,
    env_path,
    env_set,
    env_str,
    env_timedelta,
    env_url,
    get_env,
)
from hv_utils.parse_str import parse_bool, parse_int


class Color(Enum):
    """Sample enum for env parsing tests."""

    RED = "red"
    BLUE = "blue"


def test_get_env_returns_cast_value() -> None:
    """get_env returns the cast value when present."""
    env = {"PORT": "8080"}
    assert get_env("PORT", cast=int, env=env) == 8080  # noqa: PLR2004


def test_get_env_missing_returns_default_without_on_error() -> None:
    """get_env returns the default when missing without invoking error handler."""
    env: dict[str, str] = {}
    calls: list[tuple[str, str | None]] = []

    def handler(name: str, value: str | None, _cast: object) -> str:
        calls.append((name, value))
        return "unused"

    result = get_env("TOKEN", cast=str, default="fallback", env=env, on_error=handler)

    assert result == "fallback"
    assert calls == []


def test_get_env_missing_invokes_error_handler() -> None:
    """get_env calls the error handler when the variable is missing."""

    def handler(name: str, value: str | None, _cast: object) -> str:
        assert name == "SECRET"
        assert value is None
        return "placeholder"

    assert get_env("SECRET", cast=str, env={}, on_error=handler) == "placeholder"


def test_get_env_invalid_value_invokes_error_handler() -> None:
    """get_env defers invalid values to the error handler."""

    def handler(name: str, value: str | None, _cast: object) -> bool:
        assert name == "DEBUG"
        assert value == "maybe"
        return False

    assert get_env("DEBUG", cast=parse_bool, env={"DEBUG": "maybe"}, on_error=handler) is False


def test_get_env_handles_type_error_from_cast() -> None:
    """get_env handles TypeError from the cast function via the error handler."""

    def cast_int(_value: str) -> int:
        msg = "boom"
        raise TypeError(msg)

    def handler(name: str, value: str | None, _cast: object) -> int:
        assert name == "SIZE"
        assert value == "ten"
        return 10

    assert get_env("SIZE", cast=cast_int, env={"SIZE": "ten"}, on_error=handler) == 10  # noqa: PLR2004


def test_get_env_raises_for_missing_and_invalid_values() -> None:
    """get_env raises descriptive errors for missing or invalid values."""
    with pytest.raises(ValueError, match="Value is missing for 'MISSING'"):
        get_env("MISSING", cast=int, env={})

    with pytest.raises(ValueError, match="Invalid value for 'INVALID': 'oops'"):
        get_env("INVALID", cast=int, env={"INVALID": "oops"})


def test_env_str_returns_default_when_missing() -> None:
    """env_str returns default when the variable is absent."""
    assert env_str("NAME", default="guest", env={}) == "guest"


def test_env_bool_honors_required_flag() -> None:
    """env_bool raises when required value is missing."""
    env = {"ENABLED": "true"}
    assert env_bool("ENABLED", required=True, env=env) is True
    with pytest.raises(ValueError, match="Value is missing for 'MISSING'"):
        env_bool("MISSING", required=True, env={})


def test_env_int_parses_integers_or_raises() -> None:
    """env_int parses integer strings and raises on invalid input."""
    env = {"COUNT": "5"}
    assert env_int("COUNT", required=True, env=env) == 5  # noqa: PLR2004
    with pytest.raises(ValueError, match="Invalid value for 'COUNT': 'five'"):
        env_int("COUNT", required=True, env={"COUNT": "five"})


def test_env_enum_resolves_member_values() -> None:
    """env_enum resolves Enum members by value."""
    env = {"COLOR": "red"}
    assert env_enum("COLOR", Color, required=True, env=env) is Color.RED
    with pytest.raises(ValueError, match="Invalid value for 'COLOR': 'green'"):
        env_enum("COLOR", Color, required=True, env={"COLOR": "green"})


def test_env_float_returns_default_when_missing() -> None:
    """env_float returns provided default when variable is missing."""
    assert env_float("RATIO", default=1.5, env={}) == 1.5  # noqa: PLR2004


def test_env_decimal_returns_default_when_missing() -> None:
    """env_decimal falls back to default when the variable is absent."""
    assert env_decimal("PRICE", default=Decimal("9.99"), env={}) == Decimal("9.99")


def test_env_path_returns_default_path() -> None:
    """env_path returns default Path when value is missing."""
    assert env_path("HOME", default=Path("/tmp"), env={}) == Path("/tmp")  # noqa: S108 - test only


def test_env_url_respects_default_none() -> None:
    """env_url returns None when default is explicitly None."""
    assert env_url("SERVICE_URL", default=None, env={}) is None


def test_env_datetime_applies_tzinfo() -> None:
    """env_datetime parses timestamps and attaches tzinfo when naive."""
    env = {"START": "2025-01-01T00:00:00"}
    start = env_datetime("START", env=env, tzinfo=UTC)
    assert start == datetime(2025, 1, 1, tzinfo=UTC)


def test_env_timedelta_parses_duration_strings() -> None:
    """env_timedelta converts duration strings to timedeltas."""
    env = {"INTERVAL": "15m"}
    assert env_timedelta("INTERVAL", env=env) == timedelta(minutes=15)


def test_env_list_parses_collection_values() -> None:
    """env_list splits comma-separated values into a list."""
    env = {"LIST": "a,b,c"}
    assert env_list("LIST", env=env) == ["a", "b", "c"]


def test_env_set_parses_typed_collection_values() -> None:
    """env_set parses separated tokens into a typed set."""
    env = {"SET": "1;2;3"}
    assert env_set("SET", env=env, sep=";", item_cast=int) == {1, 2, 3}


def test_env_mapping_parses_key_value_pairs() -> None:
    """env_mapping parses delimited key-value pairs."""
    env = {"MAP": "k1=v1,k2=v2"}
    assert env_mapping("MAP", env=env) == {"k1": "v1", "k2": "v2"}


def test_env_json_parses_json_payloads() -> None:
    """env_json returns parsed JSON structures."""
    env = {"CONFIG": '{"debug": true}'}
    assert env_json("CONFIG", env=env) == {"debug": True}


def test_env_base64_bytes_decodes_bytes_payload() -> None:
    """env_base64_bytes decodes base64 content into bytes."""
    env = {"SECRET": base64.b64encode(b"secret").decode()}
    assert env_base64_bytes("SECRET", env=env) == b"secret"


def test_env_base64_str_decodes_text_payload() -> None:
    """env_base64_str decodes base64 content into text."""
    env = {"SECRET": base64.b64encode(b"secret").decode()}
    assert env_base64_str("SECRET", env=env) == "secret"


def test_env_or_none_returns_none_on_missing_or_invalid() -> None:
    """env_or_none returns None for missing or invalid values."""
    assert env_or_none("OPTIONAL", cast=str, env={}) is None
    assert env_or_none("OPTIONAL", cast=parse_int, env={"OPTIONAL": "oops"}) is None


def test_env_or_default_returns_default_on_missing_or_invalid() -> None:
    """env_or_default returns the default for missing or invalid values."""
    assert env_or_default("TIMEOUT", cast=parse_int, default=30, env={}) == 30  # noqa: PLR2004
    assert env_or_default("TIMEOUT", cast=parse_int, default=30, env={"TIMEOUT": "oops"}) == 30  # noqa: PLR2004
