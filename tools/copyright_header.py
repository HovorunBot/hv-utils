# -----------------------------------------------------------------------------
#  Copyright (c) 2025  TwilightSparkle42
#
#  This file is part of hv-utils.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
#
#  Contributions:
#     - TwilightSparkle42 — automation for license headers
# -----------------------------------------------------------------------------
"""Utility to apply a standardized BSD-3-Clause copyright banner to files."""

from __future__ import annotations

import argparse
import logging
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DEFAULT_EXCLUDE_DIRS = {".git", ".idea", ".venv", ".mypy_cache", ".ruff_cache", "__pycache__"}
HEADER_TEMPLATE = """# -----------------------------------------------------------------------------
#  Copyright (c) {year}  {author}
#
#  This file is part of {project}.
#  It is licensed under the BSD 3-Clause License.
#  See the LICENSE file in the project root for full license text.
#
#  Contributions:
{contributions}
# -----------------------------------------------------------------------------"""
CONTRIBUTION_INDENT = "     "
MIN_COPYRIGHT_PARTS = 4
ENCODING = "utf-8"
LOGGER = logging.getLogger("tools.copyright_header")


@dataclass(frozen=True)
class HeaderConfig:
    """Configuration for generating copyright headers."""

    author: str
    year: int
    project: str
    contributions: list[str]


def build_header(config: HeaderConfig) -> str:
    """Construct the header text using the provided configuration.

    Returns:
        str: Fully formatted header block ending with a newline.

    """
    return (
        HEADER_TEMPLATE.format(
            year=config.year,
            author=config.author,
            project=config.project,
            contributions="\n".join(f"#{CONTRIBUTION_INDENT}- {item}" for item in config.contributions),
        )
        + "\n"
    )


def _pyproject_defaults(pyproject_path: Path) -> tuple[str, str]:
    data = tomllib.loads(pyproject_path.read_text(encoding=ENCODING))
    project = data.get("project", {})
    name = project.get("name", "hv-utils")
    authors = project.get("authors") or []
    author = authors[0].get("name", "hv-utils") if authors else "hv-utils"
    return name, author


def _iter_python_files(paths: Iterable[Path], exclude_dirs: set[str]) -> Iterable[Path]:
    for base in paths:
        if not base.exists():
            continue
        if base.is_file() and base.suffix == ".py":
            yield base
            continue
        for candidate in base.rglob("*.py"):
            if any(part in exclude_dirs for part in candidate.parts):
                continue
            yield candidate


def _has_header(text: str) -> bool:
    return text.lstrip().startswith("# ---")


def _extract_header_block(body_lines: list[str]) -> tuple[str, int] | None:
    """Return the existing header block and end index if present.

    Returns:
        tuple[str, int] | None: Captured header text and the index of its closing line.

    """
    if not body_lines or not body_lines[0].startswith("# ---"):
        return None
    try:
        end_idx = next(idx for idx, line in enumerate(body_lines[1:], start=1) if line.startswith("# ---"))
    except StopIteration:
        return None
    header_block = "\n".join(body_lines[: end_idx + 1]) + "\n"
    return header_block, end_idx


def _parse_copyright_line(line: str) -> tuple[int, str] | None:
    stripped = line.lstrip("#").strip()
    if not stripped.startswith("Copyright (c)"):
        return None
    parts = stripped.split()
    if len(parts) < MIN_COPYRIGHT_PARTS:
        return None
    try:
        year = int(parts[2])
    except ValueError:
        return None
    author = " ".join(parts[3:])
    return year, author


def _split_leading_metadata(lines: list[str]) -> tuple[list[str], list[str]]:
    metadata: list[str] = []
    idx = 0
    if lines and lines[0].startswith("#!"):
        metadata.append(lines[0])
        idx += 1
    if idx < len(lines) and lines[idx].startswith("# -*- coding:"):
        metadata.append(lines[idx])
        idx += 1
    return metadata, lines[idx:]


def apply_header(files: Iterable[Path], header: str) -> list[Path]:
    """Apply the header to each file, returning the list of modified paths.

    Returns:
        list[Path]: Files that were updated.

    """
    updated: list[Path] = []
    target_lines = header.splitlines()
    for path in files:
        text = path.read_text(encoding=ENCODING)
        lines = text.splitlines()
        metadata, body = _split_leading_metadata(lines)
        new_body = _prepare_body(body, target_lines, header)
        if new_body is None:
            continue
        joined = "\n".join(metadata + new_body)
        if text.endswith("\n"):
            joined += "\n"
        path.write_text(joined, encoding=ENCODING)
        updated.append(path)
    return updated


def _prepare_body(body: list[str], target_lines: list[str], header: str) -> list[str] | None:
    existing = _extract_header_block(body)
    if existing is None:
        return [*target_lines, "", *body]

    current_header, end_idx = existing
    current_lines = body[: end_idx + 1]
    target_meta = _parse_copyright_line(target_lines[1]) if len(target_lines) > 1 else None
    current_meta = _parse_copyright_line(current_lines[1]) if len(current_lines) > 1 else None
    if current_header == header or current_meta is None or target_meta is None:
        return None

    current_year, current_author = current_meta
    target_year, target_author = target_meta
    if current_author != target_author or current_year == target_year:
        return None

    return [*target_lines, *body[end_idx + 1 :]]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the copyright header tool.

    Returns:
        argparse.Namespace: Parsed arguments.

    """
    parser = argparse.ArgumentParser(description="Apply hv-utils BSD-3-Clause copyright header.")
    parser.add_argument("--author", help="Author name for the header.")
    parser.add_argument("--year", type=int, help="Year for the header (default: current).")
    parser.add_argument("--project", help="Project name (default: from pyproject).")
    parser.add_argument(
        "--contribution",
        action="append",
        help="Contribution entry (can be repeated). Defaults to '<author> — general maintenance'.",
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        default=["src", "tests"],
        help="Directories or files to process.",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=sorted(DEFAULT_EXCLUDE_DIRS),
        help="Directory names to skip during recursion.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only report files missing the header; do not modify files.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for applying headers; returns non-zero when --check finds missing headers.

    Returns:
        int: Exit status code.

    """
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pyproject_path = Path("pyproject.toml")
    project_name, default_author = (
        _pyproject_defaults(pyproject_path) if pyproject_path.exists() else ("hv-utils", "hv-utils")
    )
    author = args.author or default_author
    year = args.year or datetime.now(tz=UTC).year
    project = args.project or project_name
    contributions = args.contribution or [f"{author} — general maintenance"]
    header = build_header(HeaderConfig(author=author, year=year, project=project, contributions=contributions))
    paths = [Path(p) for p in args.paths]
    files = list(_iter_python_files(paths, set(args.exclude)))
    if not files:
        return 0
    missing = [path for path in files if not _has_header(path.read_text(encoding=ENCODING))]
    if args.check:
        for path in missing:
            LOGGER.info("%s", path)
        return 1 if missing else 0
    updated = apply_header(files, header)
    for path in updated:
        LOGGER.info("Added header: %s", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
