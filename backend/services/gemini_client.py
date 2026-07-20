from google import genai
from google.genai import types

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
        response_text = self.generate_text("Reply with exactly: ok")

        return {
            "model": self.model,
            "response": response_text.strip(),
        }

    def generate_text(
        self,
        contents: str,
        response_mime_type: str | None = None,
    ) -> str:
        """Generate text from Gemini with optional response MIME constraints."""
        config = None
        if response_mime_type is not None:
            config = types.GenerateContentConfig(
                response_mime_type=response_mime_type,
            )

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            raise GeminiClientError(
                f"Gemini content generation failed: {exc}"
            ) from exc

        return response.text or ""
