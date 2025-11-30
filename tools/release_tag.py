# -----------------------------------------------------------------------------
#  Copyright (c) 2025  TwilightSparkle42
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
# -----------------------------------------------------------------------------
"""Utilities for validating release tags against project metadata."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path


def _normalize_tag(tag: str) -> str:
    if tag.startswith("v"):
        return tag[1:]
    return tag


def validate_tag_matches_version(tag: str, project_root: Path | None = None) -> None:
    """Ensure the provided tag matches the project version in pyproject.toml.

    Raises:
        SystemExit: If the tag is empty or does not match the project version.

    """
    if not tag:
        msg = "Tag is required"
        raise SystemExit(msg)

    root = project_root or Path()
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    normalized_tag = _normalize_tag(tag)

    if normalized_tag != version:
        msg = f"Tag {normalized_tag} does not match project version {version}"
        raise SystemExit(msg)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for validating a release tag.

    Returns:
        int: Exit code (0 on success).

    """
    parser = argparse.ArgumentParser(description="Validate that a git tag matches pyproject version.")
    parser.add_argument("--tag", required=True, help="Git tag to validate (e.g., v0.0.1)")
    args = parser.parse_args(argv)

    validate_tag_matches_version(args.tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
