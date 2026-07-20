from google import genai

from config import get_settings


class GeminiClientError(Exception):
    """Raised when Gemini API connectivity or generation fails."""


class GeminiConfigurationError(GeminiClientError):
    """Raised when Gemini API configuration is missing or invalid."""


class GeminiClient:
    """Small wrapper around the Gemini API client."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY is not configured.")

        self.model = settings.gemini_model
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def health_check(self) -> dict[str, str]:
        """Verify Gemini connectivity with a tiny text generation request."""
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents="Reply with exactly: ok",
            )
        except Exception as exc:
            raise GeminiClientError(
                f"Gemini connectivity check failed: {exc}"
            ) from exc

        return {
            "model": self.model,
            "response": (response.text or "").strip(),
        }
