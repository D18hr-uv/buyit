"""Startup entrypoint: seed the DB only if it is empty (non-destructive).

Run: `python -m app.db.ensure_seed`
"""
from app.db.seed import ensure_seeded

if __name__ == "__main__":
    ensure_seeded()
