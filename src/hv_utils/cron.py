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
"""Cron expression parser utilities.

This module provides functionality to parse standard five-field cron expressions
into explicit integer schedules.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Final, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

__all__ = ["CronSchedule", "cron_matches", "parse_cron"]
CRON_WEEKDAY_COUNT: Final[int] = 7

EXPECTED_FIELD_COUNT: Final[int] = 5
SUNDAY_ALIAS_VALUE: Final[int] = 7
_ONE_MINUTE = timedelta(minutes=1)

FIELD_RANGES = {
    "minutes": tuple(range(60)),
    "hours": tuple(range(24)),
    "day_of_month": tuple(range(1, 32)),
    "month": tuple(range(1, 13)),
    "day_of_week": tuple(range(SUNDAY_ALIAS_VALUE + 1)),
}

DAY_NAME_TO_INDEX = {"SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6}
MONTH_NAME_TO_INDEX = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


class CronSchedule(NamedTuple):
    """Structured representation of the five cron fields.

    Each attribute contains a tuple of integer values that represent the
    concrete schedule derived from the raw cron expression.
    """

    minute: tuple[int, ...]
    hour: tuple[int, ...]
    day_of_month: tuple[int, ...]
    month: tuple[int, ...]
    day_of_week: tuple[int, ...]

    @property
    def dom(self) -> tuple[int, ...]:
        """Alias for ``day_of_month`` property."""
        return self.day_of_month

    @property
    def dow(self) -> tuple[int, ...]:
        """Alias for ``day_of_week`` property."""
        return self.day_of_week

    @classmethod
    def from_exp(cls, expression: str) -> CronSchedule:
        """Create a :class:`CronSchedule` from a cron expression.

        Returns:
            CronSchedule: Parsed schedule.

        """
        return parse_cron(expression)

    def matches(self, when: datetime) -> bool:
        """Return whether the provided datetime matches this schedule.

        Returns:
            bool: True when ``when`` satisfies this schedule.

        """
        return cron_matches(self, when)

    def next(self, start: datetime, *, inclusive: bool = False, max_lookahead_days: int = 366) -> datetime:
        """Return the next datetime on or after ``start`` matching this schedule.

        Args:
            start: Datetime to start searching from.
            inclusive: When True, return ``start`` if it already matches.
            max_lookahead_days: Maximum days to search before giving up.

        Returns:
            datetime: The next matching datetime.

        Raises:
            ValueError: If no match is found within ``max_lookahead_days``.

        """
        if inclusive and self.matches(start):
            return start
        horizon_minutes = max_lookahead_days * 24 * 60
        current = start
        for _ in range(horizon_minutes):
            current += _ONE_MINUTE
            if self.matches(current):
                return current
        message = f"No matching time within {max_lookahead_days} days from {start!r}."
        raise ValueError(message)

    def iter(self, start: datetime, *, inclusive: bool = False, max_lookahead_days: int = 366) -> Iterable[datetime]:
        """Yield successive datetimes that satisfy this schedule.

        Args:
            start: Datetime to start searching from.
            inclusive: When True, yield ``start`` if it already matches.
            max_lookahead_days: Maximum days to search between yielded values.

        Yields:
            datetime: Matching datetimes in ascending order.

        """
        current = start
        first = True
        while True:
            next_match = self.next(
                current,
                inclusive=inclusive if first else False,
                max_lookahead_days=max_lookahead_days,
            )
            yield next_match
            current = next_match + _ONE_MINUTE
            first = False


def parse_cron(expression: str) -> CronSchedule:
    """Parse a cron expression into explicit field values.

    The parser expects the traditional five-field format: minute, hour,
    day of month, month, and day of week. Each field supports single
    values, ranges, steps (``*/n``), and comma-separated lists.

    Args:
        expression: Raw cron expression using space-separated fields.

    Returns:
        CronSchedule: Sorted integer values per field of the expression.

    Raises:
        ValueError: If the expression has invalid syntax or values.

    """
    expression_parts = expression.split()
    if len(expression_parts) != EXPECTED_FIELD_COUNT:
        raise ValueError(_invalid_cron_message(expression))

    minutes, hours, day_of_month, month, day_of_week = expression_parts
    try:
        return CronSchedule(
            minute=_parse_expression(minutes, FIELD_RANGES["minutes"]),
            hour=_parse_expression(hours, FIELD_RANGES["hours"]),
            day_of_month=_parse_expression(day_of_month, FIELD_RANGES["day_of_month"]),
            month=_parse_expression(month, FIELD_RANGES["month"], transform_map=MONTH_NAME_TO_INDEX),
            day_of_week=_parse_expression(
                day_of_week,
                FIELD_RANGES["day_of_week"],
                transform_map=DAY_NAME_TO_INDEX,
                normalizer=_normalize_day_of_week,
            ),
        )
    except ValueError as exc:
        raise ValueError(_invalid_cron_message(expression)) from exc


def cron_matches(expression: str | CronSchedule, when: datetime) -> bool:
    """Return whether a datetime matches a cron expression.

    The day-of-month and day-of-week fields follow traditional cron OR
    semantics: if both are restricted, the expression matches when either
    field matches the datetime. If one of the fields is a wildcard, only
    the other is considered.

    Args:
        expression: Cron expression string or parsed :class:`CronSchedule`.
        when: Datetime to evaluate (naive or timezone-aware).

    Returns:
        bool: True when ``when`` satisfies the expression.

    Raises:
        TypeError: If ``when`` is not a :class:`datetime` instance.

    """
    if not isinstance(when, datetime):
        message = "when must be a datetime instance."
        raise TypeError(message)
    schedule = parse_cron(expression) if isinstance(expression, str) else expression
    minute_ok = when.minute in schedule.minute
    hour_ok = when.hour in schedule.hour
    month_ok = when.month in schedule.month
    if not (minute_ok and hour_ok and month_ok):
        return False

    dom_wildcard = set(schedule.day_of_month) == set(FIELD_RANGES["day_of_month"])
    dow_wildcard = set(schedule.day_of_week) == {_normalize_day_of_week(value) for value in FIELD_RANGES["day_of_week"]}

    dom_match = when.day in schedule.day_of_month
    dow_match = _cron_weekday(when) in schedule.day_of_week

    if dom_wildcard and dow_wildcard:
        return True
    if dom_wildcard:
        return dow_match
    if dow_wildcard:
        return dom_match
    return dom_match or dow_match


def _parse_expression(
    expr: str,
    allowed: tuple[int, ...],
    transform_map: dict[str, int] | None = None,
    normalizer: Callable[[int], int] | None = None,
) -> tuple[int, ...]:
    """Expand a comma-delimited cron field into explicit integers.

    Args:
        expr: Field value that may include comma-separated tokens.
        allowed: Sequence of acceptable integer values for the field.
        transform_map: Optional mapping of symbolic tokens to integers.
        normalizer: Optional callable used to normalise parsed values.

    Returns:
        tuple[int, ...]: Sorted set of integers represented by ``expr``.

    Raises:
        ValueError: If any part of the expression is malformed or out of range.

    """
    parts = expr.split(",")
    result: set[int] = set()
    try:
        for part in parts:
            values = _parse_part(part, allowed, transform_map)
            if normalizer:
                values = tuple(normalizer(value) for value in values)
            result.update(values)
    except ValueError as exc:
        raise ValueError(_invalid_cron_message(expr)) from exc

    return tuple(sorted(result))


def _parse_part(part: str, allowed: tuple[int, ...], transform_map: dict[str, int] | None = None) -> tuple[int, ...]:
    """Interpret a single cron token.

    Args:
        part: Individual token from a cron field.
        allowed: Sequence of permissible integer values.
        transform_map: Mapping of symbolic values (names or aliases) to integers.

    Returns:
        tuple[int, ...]: Concrete values represented by ``part``.

    Raises:
        ValueError: If ``part`` contains invalid syntax or values.

    """
    transform_map = _normalize_transform_map(transform_map)
    value_expr, step_expr = _expr_to_parts(part)

    if value_expr.upper() in transform_map:
        value_expr = str(transform_map[value_expr.upper()])

    if value_expr.isdigit():
        if step_expr != 1:
            raise ValueError(_invalid_cron_message(part))
        if int(value_expr) not in allowed:
            raise ValueError(_invalid_cron_message(part))
        return (int(value_expr),)

    if value_expr == "*":
        return tuple(range(allowed[0], allowed[-1] + 1, step_expr))

    if "-" in value_expr and (result := _parse_range(value_expr, allowed, step_expr, transform_map)):
        return result

    raise ValueError(_invalid_cron_message(part))


def _parse_range(
    value_expr: str, allowed: tuple[int, ...], step_expr: int, transform_map: dict[str, int]
) -> tuple[int, ...]:
    """Interpret a ranged cron token such as ``1-5`` or ``MON-FRI``.

    Args:
        value_expr: Range expression containing a single dash.
        allowed: Sequence of permissible integer values.
        step_expr: Step increment applied to the expanded range.
        transform_map: Mapping of symbolic values to integers.

    Returns:
        tuple[int, ...]: Values covered by the inclusive range.

    Raises:
        ValueError: If the range bounds are invalid or out of order.

    """
    start, end = value_expr.split("-")
    if start.upper() in transform_map:
        start = str(transform_map[start.upper()])
    if end.upper() in transform_map:
        end = str(transform_map[end.upper()])
    start_int, end_int = int(start), int(end)
    if start_int not in allowed or end_int not in allowed:
        raise ValueError(_invalid_cron_message(value_expr))
    if start_int > end_int:
        raise ValueError(_invalid_cron_message(value_expr))
    result = tuple(range(start_int, end_int + 1, step_expr))
    if not result:
        raise ValueError(_invalid_cron_message(value_expr))
    return result


def _invalid_cron_message(expr: str) -> str:
    """Build a standardised error message for invalid cron input.

    Args:
        expr: Offending cron expression.

    Returns:
        str: Message describing the invalid cron expression.

    """
    return f"{expr!r} is not valid cron expression."


def _expr_to_parts(expr: str) -> tuple[str, int]:
    """Split a cron token into its base expression and step.

    Args:
        expr: Raw token that may contain a step separated by ``/``.

    Returns:
        tuple[str, int]: Base token value and validated step size.

    Raises:
        ValueError: If the step value is missing, non-numeric, or non-positive.

    """
    if "/" in expr:
        value_expr, step_expr = expr.split("/")
        if not step_expr.isdigit():
            raise ValueError(_invalid_cron_message(expr))
        step_expr_int = int(step_expr)
        if step_expr_int <= 0:
            raise ValueError(_invalid_cron_message(expr))
    else:
        value_expr, step_expr_int = expr, 1

    return value_expr, step_expr_int


def _normalize_transform_map(transform_map: dict[str, int] | None) -> dict[str, int]:
    if not transform_map:
        return {}
    return {key.upper(): value for key, value in transform_map.items()}


def _normalize_day_of_week(value: int) -> int:
    return 0 if value == SUNDAY_ALIAS_VALUE else value


def _cron_weekday(when: datetime) -> int:
    """Convert a :class:`datetime` weekday to cron numbering where Sunday is 0.

    Returns:
        int: Cron-style weekday with Sunday represented by 0.

    """
    return (when.weekday() + 1) % CRON_WEEKDAY_COUNT
