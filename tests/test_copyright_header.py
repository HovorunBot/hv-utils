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
"""Tests for enforcing the BSD 3-Clause header insertion utility."""

from pathlib import Path

from tools.copyright_header import HeaderConfig, apply_header, build_header


def test_apply_header_inserts_template(tmp_path: Path) -> None:
    """Header is inserted when missing."""
    file_path = tmp_path / "module.py"
    file_path.write_text("def demo() -> None:\n    pass\n", encoding="utf-8")

    header = build_header(
        HeaderConfig(
            author="Contributor",
            year=2025,
            project="hv-utils",
            contributions=["Contributor — added demo"],
        ),
    )
    updated = apply_header([file_path], header)

    content = file_path.read_text(encoding="utf-8")
    assert updated == [file_path]
    assert content.startswith(header)
    assert "def demo()" in content


def test_apply_header_skips_files_with_existing_header(tmp_path: Path) -> None:
    """Existing header prevents duplicate insertion."""
    existing_header = (
        "# -----------------------------------------------------------------------------\n"
        "#  Copyright (c) 2025  Someone\n"
        "#\n"
        "#  This file is part of hv-utils.\n"
        "#  It is licensed under the BSD 3-Clause License.\n"
        "#  See the LICENSE file in the project root for full license text.\n"
        "#\n"
        "#  Contributions:\n"
        "#     - Someone — example contribution\n"
        "# -----------------------------------------------------------------------------\n"
    )
    file_path = tmp_path / "module.py"
    file_path.write_text(f"{existing_header}\nVALUE = 1\n", encoding="utf-8")
    header = build_header(
        HeaderConfig(
            author="Another",
            year=2025,
            project="hv-utils",
            contributions=["Another — demo"],
        ),
    )

    updated = apply_header([file_path], header)

    content = file_path.read_text(encoding="utf-8")
    assert updated == []
    assert content.startswith(existing_header)


def test_apply_header_updates_existing_header_year(tmp_path: Path) -> None:
    """Existing header is replaced when the requested header differs."""
    existing_header = (
        "# -----------------------------------------------------------------------------\n"
        "#  Copyright (c) 2024  Someone\n"
        "#\n"
        "#  This file is part of hv-utils.\n"
        "#  It is licensed under the BSD 3-Clause License.\n"
        "#  See the LICENSE file in the project root for full license text.\n"
        "#\n"
        "#  Contributions:\n"
        "#     - Someone — example contribution\n"
        "# -----------------------------------------------------------------------------\n"
    )
    file_path = tmp_path / "module.py"
    file_path.write_text(f"{existing_header}\nVALUE = 2\n", encoding="utf-8")
    header = build_header(
        HeaderConfig(
            author="Someone",
            year=2025,
            project="hv-utils",
            contributions=["Someone — example contribution"],
        ),
    )

    updated = apply_header([file_path], header)

    content = file_path.read_text(encoding="utf-8")
    assert updated == [file_path]
    assert content.startswith(header)
