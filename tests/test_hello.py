from hv_utils import hello


def test_hello_returns_greeting() -> None:
    """Hello returns a deterministic greeting."""
    assert hello() == "Hello from hv-utils!"  # noqa: S101
