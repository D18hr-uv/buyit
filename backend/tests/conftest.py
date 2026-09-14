"""Test setup: use an isolated temp SQLite DB and seed it once per session."""
import os
import tempfile

# Must be set before any app module imports (config caches settings on first read).
_tmpdir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test_buyit.db"
os.environ["LLM_PROVIDER"] = "stub"
os.environ["OPENAI_API_KEY"] = ""

import pytest

from app.db.seed import seed


@pytest.fixture(autouse=True)
def seeded_db():
    """Re-seed a fresh DB before every test for isolation (agent tests mutate state)."""
    seed()
    yield
