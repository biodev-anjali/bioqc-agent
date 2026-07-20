import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioqc-tests-"))
os.environ["DATABASE_URL"] = "sqlite:///" + str(TEST_ROOT / "bioqc_test.db").replace("\\", "/")
os.environ["UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["REPORTS_DIR"] = str(TEST_ROOT / "reports")

from database import Base, engine  # noqa: E402
from main import app  # noqa: E402
import models  # noqa: E402,F401


def _cleanup_test_root() -> None:
    engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


atexit.register(_cleanup_test_root)


@pytest.fixture()
def sample_fastqc_zip_path() -> Path:
    return Path(__file__).resolve().parents[2] / "sample_fastqc.zip"


@pytest.fixture()
def client() -> TestClient:
    upload_dir = TEST_ROOT / "uploads"
    reports_dir = TEST_ROOT / "reports"

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    shutil.rmtree(upload_dir, ignore_errors=True)
    shutil.rmtree(reports_dir, ignore_errors=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    with TestClient(app) as test_client:
        yield test_client

    engine.dispose()
