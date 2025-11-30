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
"""Unit tests for cron expression parsing utilities."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from itertools import islice

import pytest

from hv_utils.cron import CronSchedule, cron_matches, parse_cron


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        pytest.param(
            "0 0 1 1 0",
            CronSchedule((0,), (0,), (1,), (1,), (0,)),
            id="literals",
        ),
        pytest.param(
            "* * * * *",
            CronSchedule(
                tuple(range(60)),
                tuple(range(24)),
                tuple(range(1, 32)),
                tuple(range(1, 13)),
                tuple(range(7)),
            ),
            id="wildcards",
        ),
        pytest.param(
            "*/15 0-12/6 1,15 1-3 1-5/2",
            CronSchedule(
                tuple(range(0, 60, 15)),
                (0, 6, 12),
                (1, 15),
                (1, 2, 3),
                (1, 3, 5),
            ),
            id="steps-and-ranges",
        ),
        pytest.param(
            "5,10-20/5 8,20 10-12 4,6-8 0,2-4",
            CronSchedule(
                (5, 10, 15, 20),
                (8, 20),
                (10, 11, 12),
                (4, 6, 7, 8),
                (0, 2, 3, 4),
            ),
            id="mixed-list-and-ranges",
        ),
        pytest.param(
            "30 14 * * 1-5",
            CronSchedule(
                (30,),
                (14,),
                tuple(range(1, 32)),
                tuple(range(1, 13)),
                (1, 2, 3, 4, 5),
            ),
            id="weekday-range",
        ),
        pytest.param(
            "0 */8 */2 */3 *",
            CronSchedule(
                (0,),
                (0, 8, 16),
                tuple(range(1, 32, 2)),
                (1, 4, 7, 10),
                tuple(range(7)),
            ),
            id="stepped-month-and-day",
        ),
        pytest.param(
            "15,45 6-18/6 5,10-20/5 2,4,6 0,6",
            CronSchedule(
                (15, 45),
                (6, 12, 18),
                (5, 10, 15, 20),
                (2, 4, 6),
                (0, 6),
            ),
            id="edge-dow-values",
        ),
        pytest.param(
            "0 6 10 JAN,FEB,MAR 1",
            CronSchedule(
                (0,),
                (6,),
                (10,),
                (1, 2, 3),
                (1,),
            ),
            id="month-name-list",
        ),
        pytest.param(
            "0 9 15 APR-JUN/2 0",
            CronSchedule(
                (0,),
                (9,),
                (15,),
                (4, 6),
                (0,),
            ),
            id="month-name-range-step",
        ),
        pytest.param(
            "45 18 1 JAN-DEC/3 0-6/2",
            CronSchedule(
                (45,),
                (18,),
                (1,),
                (1, 4, 7, 10),
                (0, 2, 4, 6),
            ),
            id="month-name-yearly-step",
        ),
        pytest.param(
            "0 0 * * 0,7",
            CronSchedule(
                (0,),
                (0,),
                tuple(range(1, 32)),
                tuple(range(1, 13)),
                (0,),
            ),
            id="dow-seven-as-sunday",
        ),
        pytest.param(
            "0 0 1 jan mon",
            CronSchedule((0,), (0,), (1,), (1,), (1,)),
            id="case-insensitive-names",
        ),
        pytest.param(
            "*/65 * * * *",
            CronSchedule(
                (0,),
                tuple(range(24)),
                tuple(range(1, 32)),
                tuple(range(1, 13)),
                tuple(range(7)),
            ),
            id="large-step-value",
        ),
    ],
)
def test_cron_parser_valid(
    expression: str,
    expected: CronSchedule,
) -> None:
    """Validate cron parsing across multiple expression complexities."""
    parsed = parse_cron(expression)

    assert parsed == expected


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("0 0", id="too-few-fields"),
        pytest.param("0 0 1 1 0 extra", id="too-many-fields"),
        pytest.param("0 24 * * *", id="hour-out-of-range"),
        pytest.param("0 -1 * * *", id="negative-hour"),
        pytest.param("0 0 32 * *", id="day-out-of-range"),
        pytest.param("0 0 1 13 *", id="month-out-of-range"),
        pytest.param("0 0 1 JANUARY *", id="invalid-month-name"),
        pytest.param("0 0 1 * MONDAY", id="invalid-dow-name"),
        pytest.param("*/0 * * * *", id="zero-step"),
        pytest.param("*/-5 * * * *", id="negative-step"),
        pytest.param("0 0 10-5 * *", id="descending-range"),
    ],
)
def test_cron_parser_invalid(expression: str) -> None:
    """Ensure malformed cron expressions are rejected."""
    with pytest.raises(ValueError, match=re.escape(f"{expression!r} is not valid cron expression.")):
        parse_cron(expression)


@pytest.mark.parametrize(
    ("expression", "when", "expected"),
    [
        pytest.param(
            "0 12 15 * 1",
            datetime(2025, 1, 15, 12, 0, tzinfo=UTC),
            True,
            id="dom-match-when-dow-also-restricted",
        ),
        pytest.param(
            "0 12 15 * 1",
            datetime(2025, 1, 13, 12, 0, tzinfo=UTC),
            True,
            id="dow-match-when-dom-restricted",
        ),
        pytest.param(
            "0 12 15 * 1",
            datetime(2025, 1, 14, 12, 0, tzinfo=UTC),
            False,
            id="neither-dom-nor-dow-match",
        ),
        pytest.param(
            "0 9 * * 1",
            datetime(2025, 1, 14, 9, 0, tzinfo=UTC),
            False,
            id="dow-only-no-match",
        ),
        pytest.param(
            "0 9 * * 1",
            datetime(2025, 1, 13, 9, 0, tzinfo=UTC),
            True,
            id="dow-only-match",
        ),
        pytest.param(
            "0 9 1 * *",
            datetime(2025, 1, 1, 9, 0, tzinfo=UTC),
            True,
            id="dom-only-match",
        ),
        pytest.param(
            "0 9 1 * *",
            datetime(2025, 1, 2, 9, 0, tzinfo=UTC),
            False,
            id="dom-only-no-match",
        ),
    ],
)
def test_cron_matches_day_fields_or_logic(expression: str, when: datetime, *, expected: bool) -> None:
    """Day-of-month and day-of-week apply an OR rule per cron specification."""
    assert cron_matches(expression, when) is expected


def test_cron_schedule_from_exp_factory() -> None:
    """CronSchedule.from_exp should mirror parse_cron output."""
    expression = "*/5 1,2 1 JAN MON"

    parsed = parse_cron(expression)
    constructed = CronSchedule.from_exp(expression)

    assert constructed == parsed


@pytest.mark.parametrize(
    ("expression", "start", "inclusive", "expected"),
    [
        ("*/5 * * * *", datetime(2025, 1, 1, 0, 2, tzinfo=UTC), False, datetime(2025, 1, 1, 0, 5, tzinfo=UTC)),
        ("*/5 * * * *", datetime(2025, 1, 1, 0, 10, tzinfo=UTC), True, datetime(2025, 1, 1, 0, 10, tzinfo=UTC)),
        ("0 12 15 * 1", datetime(2025, 1, 13, 11, 0, tzinfo=UTC), False, datetime(2025, 1, 13, 12, 0, tzinfo=UTC)),
        ("0 12 15 * 1", datetime(2025, 1, 14, 11, 0, tzinfo=UTC), False, datetime(2025, 1, 15, 12, 0, tzinfo=UTC)),
    ],
)
def test_cron_schedule_next(expression: str, start: datetime, *, inclusive: bool, expected: datetime) -> None:
    """Next occurrence is computed correctly with dom/dow OR semantics."""
    schedule = CronSchedule.from_exp(expression)

    assert schedule.next(start, inclusive=inclusive) == expected


def test_cron_schedule_iterates_future_beats() -> None:
    """Iterating over a schedule yields successive matches."""
    schedule = CronSchedule.from_exp("0 0 1 * *")
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    beats = list(islice(schedule.iter(start, inclusive=True), 3))

    assert beats == [
        datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
        datetime(2025, 2, 1, 0, 0, tzinfo=UTC),
        datetime(2025, 3, 1, 0, 0, tzinfo=UTC),
    ]


def test_cron_schedule_next_respects_max_lookahead() -> None:
    """Schedules that cannot match within the horizon raise an error."""
    schedule = CronSchedule.from_exp("0 0 29 2 *")  # Feb 29
    start = datetime(2023, 3, 1, 0, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="No matching time within 364 days"):
        schedule.next(start, max_lookahead_days=364)


def test_cron_matches_treats_wildcard_dow_as_unrestricted() -> None:
    """Wildcard DOW should not block matches."""
    schedule = CronSchedule.from_exp("* * * * *")
    when = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

    assert cron_matches(schedule, when)
