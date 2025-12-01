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
"""Unit tests for sentinel utilities."""

from __future__ import annotations

import pickle  # noqa: S403 - we are testing pickling here
from copy import copy
from dataclasses import asdict, dataclass, replace

import pytest

from hv_utils.sentinel import MISSING


def test_missing_attribute_access_is_forbidden() -> None:
    """Missing raises when accessed or mutated like a normal object."""
    assert bool(MISSING) is False
    for attr in ("anything", "__dict__", "value"):
        with pytest.raises(AttributeError):
            getattr(MISSING, attr)
    with pytest.raises(AttributeError):
        MISSING.new_attr = "blocked"
    with pytest.raises(AttributeError):
        delattr(MISSING, "value")


def test_missing_behaves_like_any_for_type_checkers() -> None:
    """MISSING is annotated as Any to satisfy strict type checks."""

    def expects_str(value: str) -> str:
        return value

    assert expects_str(MISSING) is MISSING


@dataclass
class Record:
    """Dataclass fixture leveraging the missing sentinel."""

    label: str
    payload: object = MISSING


def _summarize(record: Record) -> str:
    if record.payload is MISSING:
        return f"{record.label}:missing"
    if record.payload is None:
        return f"{record.label}:none"
    return f"{record.label}:{record.payload}"


def test_missing_dataclass_defaults_are_distinguishable() -> None:
    """Dataclasses preserve identity of MISSING defaults versus explicit None."""
    defaulted = Record(label="first")
    explicit_none = Record(label="second", payload=None)
    filled = replace(defaulted, payload="value")

    assert _summarize(defaulted) == "first:missing"
    assert _summarize(explicit_none) == "second:none"
    assert _summarize(filled) == "first:value"
    assert asdict(defaulted)["payload"] is MISSING
    assert MISSING.__class__.__name__ == "MissingType"


def test_missing_supports_pickle_and_copy() -> None:
    """Pickling and copying preserve the singleton identity."""
    assert pickle.loads(pickle.dumps(MISSING)) is MISSING  # noqa: S301 - required for testing, nothing danger here
    assert copy(MISSING) is MISSING
    assert copy(MISSING) is MISSING


def test_missing_magic_methods_are_invokable() -> None:
    """Magic methods are accessible for standard protocols."""
    assert repr(MISSING) == "Missing"
    assert str(MISSING) == "Missing"
    assert bool(MISSING) is False
    assert MISSING.__repr__() == "Missing"  # noqa: PLC2801
    assert MISSING.__str__() == "Missing"  # noqa: PLC2801
    assert MISSING.__bool__() is False  # noqa: PLC2801
    assert MISSING.__copy__() is MISSING  # noqa: PLC2801
    assert MISSING.__deepcopy__({}) is MISSING  # noqa: PLC2801
