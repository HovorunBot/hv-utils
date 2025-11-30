# hv-utils

Typed utility library for consolidating reusable Python helpers. The project is in early alpha; the current public
surface is the `hello()` greeting exported from `hv_utils.__init__`.

## What you need

- Python 3.12+. Keep 3.13 and 3.14 available if you want to run the full matrix locally.
- [uv](https://docs.astral.sh/uv/) for dependency management.
- Runtime stays standard-library only; dev tools live in the `dev` dependency group.

## Quick start

- Install dev tools: `uv sync --group dev`
- Ensure you work from the repo root so `src/` is discoverable.
- Try it out: `uv run python -c "from hv_utils import hello; print(hello())"`

## How we work

- Functional-first utilities; keep state to a minimum.
- Standard library only at runtime. If an optional dependency is unavoidable, add an extra in `pyproject.toml`, guard
  the import with `try/except ImportError`, and raise a friendly install hint.
- Absolute imports only. Expose public helpers from `src/hv_utils/__init__.py`.
- Always type everything and keep `mypy --strict` green.
- TDD over heroics: write or update tests before implementing behavior, cover edge cases, and keep functions small and
  composable.
- Follow `ruff`/PEP 8 style (line length 120).

## Common commands

- Format: `uv run ruff format .`
- Lint (autofix): `uv run ruff check --fix .`
- Type-check: `uv run mypy src tests`
- Tests (current Python): `uv run pytest`
- Tests on a specific interpreter: `uv run --python 3.13 pytest`
- Full matrix (requires those interpreters installed):
    - `uv run --python 3.12 pytest`
    - `uv run --python 3.13 pytest`
    - `uv run --python 3.14 pytest`

## Pre-commit

- Install hooks: `pre-commit install` (uses your machine-level pre-commit)
- Run all hooks manually: `pre-commit run --all-files`
- Hooks auto-add the BSD-3 header (via `python -m tools.copyright_header`), then run the same uv-powered format, lint, type-check, and test commands listed above.

## Contributing

- Keep PRs small and focused on one utility or fix.
- Add tests, docstrings, and `__init__` exports alongside new utilities.
- Run format, lint, mypy, and pytest before opening a PR; for compatibility-sensitive changes, run the full matrix.
