"""
Phase 3 database migration.

Creates the qc_results table and ensures all SQLAlchemy models are registered.
Safe to run multiple times.
"""

from sqlalchemy import inspect

import models  # noqa: F401
from database import Base, engine
from models import QCResult


def migrate() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "qc_results" in existing_tables:
        print("qc_results table already exists.")
    else:
        QCResult.__table__.create(bind=engine)
        print("Created qc_results table.")

    Base.metadata.create_all(bind=engine)
    print("Phase 3 migration complete.")


if __name__ == "__main__":
    migrate()
