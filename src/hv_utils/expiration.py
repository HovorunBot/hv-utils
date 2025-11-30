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
"""Utilities for representing absolute or relative expiration moments."""

__all__ = [
    "Expiration",
    "ExpiresAfter",
    "ExpiresAtDT",
    "ExpiresAtTS",
    "ExpiresIn",
]
import datetime
from abc import ABC, abstractmethod
from typing import final, override


class Expiration(ABC):
    """Interface for expressing expiration points or timeouts."""

    @abstractmethod
    def as_timestamp(self) -> float:
        """Return the expiration moment as seconds since the Unix epoch.

        Returns:
            Expiration instant encoded as a floating-point timestamp.

        """

    @abstractmethod
    def as_datetime(self, tz: datetime.tzinfo = datetime.UTC) -> datetime.datetime:
        """Return a timezone-aware datetime when expiration occurs.

        Args:
            tz: Target timezone for the resulting datetime; defaults to UTC.

        Returns:
            Datetime of expiration converted to the requested timezone.

        """

    @abstractmethod
    def as_ttl(self) -> datetime.timedelta:
        """Return time-to-live that remains until expiration.

        Returns:
            Remaining duration until expiration. Implementations that track a fixed
            moment clamp negative durations to zero; relative implementations such as
            ``ExpiresIn`` return the configured TTL because the target moment is always
            evaluated at call time.

        """


@final
class ExpiresIn(Expiration):
    """Expiration computed relative to the invocation moment.

    Args:
        ttl: Duration added to the current time whenever expiration is queried.

    """

    def __init__(self, ttl: datetime.timedelta) -> None:
        """Store TTL used for all subsequent expiration computations."""
        self._ttl = ttl

    @override
    def as_timestamp(self) -> float:
        return (datetime.datetime.now(datetime.UTC) + self._ttl).timestamp()

    @override
    def as_datetime(self, tz: datetime.tzinfo = datetime.UTC) -> datetime.datetime:
        return datetime.datetime.now(tz) + self._ttl

    @override
    def as_ttl(self) -> datetime.timedelta:
        return self._ttl


@final
class ExpiresAfter(Expiration):
    """Expiration anchored to a start instant and a TTL.

    Args:
        ttl: Allowed duration after ``since`` until expiration.
        since: Timezone-aware datetime that marks the start of the TTL window.

    Raises:
        ValueError: If ``since`` is not timezone-aware.

    """

    def __init__(self, ttl: datetime.timedelta, since: datetime.datetime) -> None:
        """Bind TTL to the provided ``since`` datetime.

        Raises:
            ValueError: If ``since`` is not timezone-aware.

        """
        timezone_error = "since parameter must be timezone-aware datetime"
        if since.tzinfo is None:
            raise ValueError(timezone_error)
        self._since = since
        self._ttl = ttl

    @override
    def as_timestamp(self) -> float:
        return (self._since + self._ttl).timestamp()

    @override
    def as_datetime(self, tz: datetime.tzinfo = datetime.UTC) -> datetime.datetime:
        return (self._since + self._ttl).astimezone(tz)

    @override
    def as_ttl(self) -> datetime.timedelta:
        now = datetime.datetime.now(datetime.UTC)
        remaining = (self._since + self._ttl) - now
        return max(datetime.timedelta(0), remaining)


@final
class ExpiresAtTS(Expiration):
    """Expiration defined by a Unix timestamp.

    Args:
        timestamp: Non-negative seconds since the Unix epoch when expiration occurs.

    Raises:
        ValueError: If ``timestamp`` is negative.

    """

    def __init__(self, timestamp: float) -> None:
        """Capture absolute expiration timestamp.

        Raises:
            ValueError: If ``timestamp`` is negative.

        """
        invalid_timestamp_error = "timestamp must be non-negative number of seconds since EPOCH"
        if timestamp < 0.0:
            raise ValueError(invalid_timestamp_error)
        self._timestamp = timestamp

    @override
    def as_timestamp(self) -> float:
        return self._timestamp

    @override
    def as_datetime(self, tz: datetime.tzinfo = datetime.UTC) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self._timestamp, tz=tz)

    @override
    def as_ttl(self) -> datetime.timedelta:
        now = datetime.datetime.now(datetime.UTC).timestamp()
        remaining_seconds = max(0.0, self._timestamp - now)
        return datetime.timedelta(seconds=remaining_seconds)


@final
class ExpiresAtDT(Expiration):
    """Expiration defined by a timezone-aware datetime.

    Args:
        expires_at: Absolute moment when expiration occurs.

    Raises:
        ValueError: If ``expires_at`` is naive.

    """

    def __init__(self, expires_at: datetime.datetime) -> None:
        """Store absolute expiration datetime.

        Raises:
            ValueError: If ``expires_at`` is naive.

        """
        timezone_error = "expires_at datetime must be timezone-aware"
        if expires_at.tzinfo is None:
            raise ValueError(timezone_error)
        self._dt = expires_at

    @override
    def as_timestamp(self) -> float:
        return self._dt.timestamp()

    @override
    def as_datetime(self, tz: datetime.tzinfo = datetime.UTC) -> datetime.datetime:
        return self._dt.astimezone(tz)

    @override
    def as_ttl(self) -> datetime.timedelta:
        now = datetime.datetime.now(datetime.UTC)
        remaining = self._dt - now
        return max(datetime.timedelta(0), remaining)
