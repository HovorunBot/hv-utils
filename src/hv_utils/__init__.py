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

"""Core utilities exposed by the hv-utils package."""

__all__ = ["hello"]


def hello() -> str:
    """Return a friendly greeting from hv-utils.

    Returns:
        str: Friendly greeting message.

    """
    return "Hello from hv-utils!"
