# -----------------------------------------------------------------------------
#  Copyright (c) 2025  Zibertscrem
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
#
#  Contributions:
#     - Zibertscrem — general maintenance
# -----------------------------------------------------------------------------
"""Unit tests for expiration helpers."""

from __future__ import annotations

import datetime
from typing import Final

import pytest
from freezegun import freeze_time

from hv_utils.expiration import ExpiresAfter, ExpiresAtDT, ExpiresAtTS, ExpiresIn


def test_expires_in_uses_current_time() -> None:
    """ExpiresIn computes expiration relative to the call time."""
    fixed_now = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.UTC)
    ttl = datetime.timedelta(seconds=30)
    with freeze_time(fixed_now):
        expires_in = ExpiresIn(ttl)

        timestamp = expires_in.as_timestamp()
        as_datetime = expires_in.as_datetime()

    expected_expiration = fixed_now + ttl
    assert timestamp == expected_expiration.timestamp()
    assert as_datetime == expected_expiration
    assert as_datetime.tzinfo is datetime.UTC
    assert expires_in.as_ttl() == ttl


def test_expires_after_enforces_timezone_awareness() -> None:
    """ExpiresAfter rejects naive ``since`` datetimes."""
    naive_since = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.UTC).replace(tzinfo=None)

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        ExpiresAfter(datetime.timedelta(seconds=10), naive_since)


def test_expires_after_remaining_ttl_clamps_to_zero() -> None:
    """ExpiresAfter clamps negative remaining TTL to zero and converts timezones."""
    fixed_now = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.UTC)
    ttl = datetime.timedelta(seconds=5)
    since = fixed_now - datetime.timedelta(seconds=10)
    expires_after = ExpiresAfter(ttl, since)

    target_tz = datetime.timezone(datetime.timedelta(hours=2))
    expected_expiration = (since + ttl).astimezone(target_tz)

    with freeze_time(fixed_now):
        assert expires_after.as_timestamp() == pytest.approx((since + ttl).timestamp())
        assert expires_after.as_datetime(target_tz) == expected_expiration
        assert expires_after.as_ttl() == datetime.timedelta(0)


def test_expires_at_ts_enforces_non_negative_timestamp() -> None:
    """ExpiresAtTS rejects negative timestamps."""
    with pytest.raises(ValueError, match="non-negative number of seconds since EPOCH"):
        ExpiresAtTS(-1.0)


def test_expires_at_ts_returns_remaining() -> None:
    """ExpiresAtTS reports remaining TTL relative to the frozen current time."""
    fixed_now = datetime.datetime(2025, 1, 1, 8, 0, tzinfo=datetime.UTC)
    remaining_seconds: Final[float] = 42.5
    expires_at = ExpiresAtTS(fixed_now.timestamp() + remaining_seconds)

    with freeze_time(fixed_now):
        assert expires_at.as_datetime(datetime.UTC) == datetime.datetime.fromtimestamp(
            expires_at.as_timestamp(),
            tz=datetime.UTC,
        )
        assert expires_at.as_ttl() == datetime.timedelta(seconds=remaining_seconds)


def test_expires_at_dt_requires_timezone() -> None:
    """ExpiresAtDT requires timezone-aware datetimes."""
    naive_expiration = datetime.datetime(2025, 6, 1, 10, 0, tzinfo=datetime.UTC).replace(tzinfo=None)

    with pytest.raises(ValueError, match="timezone-aware"):
        ExpiresAtDT(naive_expiration)


def test_expires_at_dt_reports_remaining() -> None:
    """ExpiresAtDT exposes timestamp, datetime conversion, and remaining TTL."""
    expiration_dt = datetime.datetime(2025, 6, 1, 10, 0, tzinfo=datetime.UTC)
    fixed_now = expiration_dt - datetime.timedelta(seconds=1)
    expires_at = ExpiresAtDT(expiration_dt)

    target_tz = datetime.timezone(datetime.timedelta(hours=-5))

    with freeze_time(fixed_now):
        assert expires_at.as_timestamp() == expiration_dt.timestamp()
        assert expires_at.as_datetime(target_tz) == expiration_dt.astimezone(target_tz)
        assert expires_at.as_ttl() == datetime.timedelta(seconds=1)
