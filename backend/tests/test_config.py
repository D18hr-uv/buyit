"""Unit tests for deploy-facing config helpers and the non-destructive seed."""
from app.config import Settings
from app.db.seed import ensure_seeded
from app.db.session import session_scope
from app.db.models import Product


def test_cors_origin_list_parsing():
    assert Settings(cors_origins="*").cors_origin_list == ["*"]
    assert Settings(cors_origins="").cors_origin_list == ["*"]
    assert Settings(
        cors_origins="https://a.com, https://b.com"
    ).cors_origin_list == ["https://a.com", "https://b.com"]


def test_ensure_seeded_is_noop_when_populated():
    # conftest already seeded the DB; ensure_seeded must not wipe it.
    with session_scope() as s:
        before = s.query(Product).count()
    ensure_seeded()
    with session_scope() as s:
        assert s.query(Product).count() == before
