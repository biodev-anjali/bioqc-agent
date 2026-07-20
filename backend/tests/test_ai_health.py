import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///" + str(
    Path(tempfile.gettempdir()) / "bioqc_ai_health_test.db"
).replace("\\", "/")
os.environ["UPLOAD_DIR"] = str(Path(tempfile.gettempdir()) / "bioqc_ai_health_uploads")
os.environ["REPORTS_DIR"] = str(Path(tempfile.gettempdir()) / "bioqc_ai_health_reports")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
import routers.ai as ai_router  # noqa: E402


class FakeGeminiClient:
    def health_check(self) -> dict[str, str]:
        return {
            "model": "test-gemini-model",
            "response": "ok",
        }


def test_ai_health_endpoint(monkeypatch):
    monkeypatch.setattr(ai_router, "GeminiClient", FakeGeminiClient)

    with TestClient(app) as client:
        response = client.get("/api/ai/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "provider": "gemini",
        "model": "test-gemini-model",
        "response": "ok",
    }
