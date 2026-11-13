"""Make the repository root importable (api/, scripts/) wherever pytest is launched from."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_state_db(tmp_path, monkeypatch):
    """Every test gets its own user-state store (scenarios, conversations, answer cache)."""
    monkeypatch.setenv("FIREWISE_STATE_DB", str(tmp_path / "state.sqlite"))


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from api import ratelimit
    ratelimit.reset()
    yield
    ratelimit.reset()
