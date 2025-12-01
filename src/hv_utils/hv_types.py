# -----------------------------------------------------------------------------
#  Copyright (c) 2025  TwilightSparkle42
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
# -----------------------------------------------------------------------------
"""Shared JSON-oriented type aliases used across hv-utils."""

from __future__ import annotations

__all__ = ["JSONArray", "JSONDict", "JSONScalar", "JSONValue"]

type JSONScalar = str | int | float | bool | None
type JSONArray = list[JSONValue]
type JSONDict = dict[str, JSONValue]
type JSONValue = JSONScalar | JSONDict | JSONArray
