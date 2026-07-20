import json
from typing import Literal, Protocol

from pydantic import BaseModel, Field, ValidationError

from models import QCResult
from services.gemini_client import GeminiClient, GeminiClientError


PROMPT_VERSION = "phase4b_v1"


class QCInterpretationError(Exception):
    """Base exception for QC interpretation failures."""


class QCInterpretationGenerationError(QCInterpretationError):
    """Raised when Gemini cannot generate an interpretation."""


class QCInterpretationValidationError(QCInterpretationError):
    """Raised when Gemini returns invalid interpretation JSON."""


class QCInterpretation(BaseModel):
    overall_status: Literal["pass", "review", "fail"]
    risk_level: Literal["low", "medium", "high"]
    summary: str = Field(min_length=1)
    key_findings: list[str] = Field(min_length=1)
    recommendations: list[str] = Field(min_length=1)
    suggested_actions: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


class GeminiTextClient(Protocol):
    def generate_text(
        self,
        contents: str,
        response_mime_type: str | None = None,
    ) -> str:
        """Generate text from a model provider."""


def _qc_metrics_payload(qc_result: QCResult) -> dict[str, int | float | str]:
    return {
        "total_sequences": qc_result.total_sequences,
        "sequence_length": qc_result.sequence_length,
        "gc_percent": qc_result.gc_percent,
        "per_base_quality_status": qc_result.per_base_quality_status,
        "per_sequence_quality_status": qc_result.per_sequence_quality_status,
        "adapter_content_status": qc_result.adapter_content_status,
        "overrepresented_sequences_status": qc_result.overrepresented_sequences_status,
    }


def build_qc_interpretation_prompt(qc_result: QCResult) -> str:
    """Build a deterministic prompt from parsed QC metrics only."""
    metrics_json = json.dumps(
        _qc_metrics_payload(qc_result),
        indent=2,
        sort_keys=True,
    )

    return f"""You are BioQC Agent, a bioinformatics quality-control assistant.

Interpret only the parsed FastQC metrics provided below.
Do not infer from raw sequencing reads, file contents, patient data, or any source not shown.
Do not request or reference the original FastQC ZIP file.

Return structured JSON only. Do not include Markdown, prose outside JSON, or code fences.

Required JSON schema:
{{
  "overall_status": "pass" | "review" | "fail",
  "risk_level": "low" | "medium" | "high",
  "summary": "string",
  "key_findings": ["string"],
  "recommendations": ["string"],
  "suggested_actions": ["string"],
  "limitations": ["string"]
}}

Guidance:
- Use "pass" only when all supplied module statuses are pass.
- Use "review" when any supplied module status is warn or unknown.
- Use "fail" when any supplied module status is fail.
- Keep the summary concise and practical for a genomics lab user.
- Include at least one limitation explaining that the interpretation is based only on parsed FastQC metrics.

Prompt version: {PROMPT_VERSION}

Parsed QC metrics:
{metrics_json}
"""


def validate_interpretation_json(response_text: str) -> QCInterpretation:
    """Validate Gemini JSON output into a structured interpretation object."""
    try:
        return QCInterpretation.model_validate_json(response_text)
    except ValidationError as exc:
        raise QCInterpretationValidationError(
            "Gemini returned JSON that does not match the expected interpretation schema."
        ) from exc
    except ValueError as exc:
        raise QCInterpretationValidationError(
            "Gemini returned invalid JSON for the QC interpretation."
        ) from exc


def interpret_qc_result(
    qc_result: QCResult,
    gemini_client: GeminiTextClient | None = None,
) -> QCInterpretation:
    """Generate and validate an AI interpretation for parsed QC metrics."""
    client = gemini_client or GeminiClient()
    prompt = build_qc_interpretation_prompt(qc_result)

    try:
        response_text = client.generate_text(
            prompt,
            response_mime_type="application/json",
        )
    except GeminiClientError as exc:
        raise QCInterpretationGenerationError(
            "Gemini failed to generate a QC interpretation."
        ) from exc

    return validate_interpretation_json(response_text)
