from fastapi import APIRouter, HTTPException, status

from services.gemini_client import (
    GeminiClient,
    GeminiClientError,
    GeminiConfigurationError,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/health")
def ai_health_check() -> dict[str, str]:
    try:
        result = GeminiClient().health_check()
    except GeminiConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GeminiClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",
        "provider": "gemini",
        **result,
    }
