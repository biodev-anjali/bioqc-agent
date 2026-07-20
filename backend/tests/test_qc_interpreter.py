import pytest

from services.gemini_client import GeminiClientError
from services.qc_interpreter import (
    PROMPT_VERSION,
    QCInterpretationGenerationError,
    QCInterpretationValidationError,
    build_qc_interpretation_prompt,
    interpret_qc_result,
    validate_interpretation_json,
)


class ParsedQCResult:
    total_sequences = 1_250_000
    sequence_length = "150"
    gc_percent = 48.0
    per_base_quality_status = "pass"
    per_sequence_quality_status = "pass"
    adapter_content_status = "warn"
    overrepresented_sequences_status = "pass"


VALID_INTERPRETATION_JSON = """
{
  "overall_status": "review",
  "risk_level": "medium",
  "summary": "Overall read quality is acceptable, but adapter content should be reviewed.",
  "key_findings": [
    "Per-base sequence quality passed.",
    "Adapter content produced a warning."
  ],
  "recommendations": [
    "Review adapter content before downstream analysis."
  ],
  "suggested_actions": [
    "Trim adapters and rerun FastQC."
  ],
  "limitations": [
    "This interpretation is based only on parsed FastQC metrics."
  ]
}
"""


class SuccessfulGeminiClient:
    def __init__(self) -> None:
        self.contents = None
        self.response_mime_type = None

    def generate_text(
        self,
        contents: str,
        response_mime_type: str | None = None,
    ) -> str:
        self.contents = contents
        self.response_mime_type = response_mime_type
        return VALID_INTERPRETATION_JSON


class FailingGeminiClient:
    def generate_text(
        self,
        contents: str,
        response_mime_type: str | None = None,
    ) -> str:
        raise GeminiClientError("Gemini unavailable.")


def test_prompt_generation_uses_only_parsed_qc_metrics():
    prompt = build_qc_interpretation_prompt(ParsedQCResult())

    assert PROMPT_VERSION in prompt
    assert '"total_sequences": 1250000' in prompt
    assert '"sequence_length": "150"' in prompt
    assert '"adapter_content_status": "warn"' in prompt
    assert "Return structured JSON only" in prompt
    assert "Do not request or reference the original FastQC ZIP file" in prompt
    assert "fastqc_data.txt" not in prompt
    assert ".zip" not in prompt.lower()


def test_validate_interpretation_json_success():
    interpretation = validate_interpretation_json(VALID_INTERPRETATION_JSON)

    assert interpretation.overall_status == "review"
    assert interpretation.risk_level == "medium"
    assert interpretation.summary.startswith("Overall read quality")
    assert interpretation.key_findings[0] == "Per-base sequence quality passed."
    assert interpretation.recommendations == [
        "Review adapter content before downstream analysis."
    ]
    assert interpretation.suggested_actions == [
        "Trim adapters and rerun FastQC."
    ]
    assert interpretation.limitations == [
        "This interpretation is based only on parsed FastQC metrics."
    ]


def test_validate_interpretation_json_rejects_invalid_json():
    with pytest.raises(QCInterpretationValidationError):
        validate_interpretation_json("not json")


def test_validate_interpretation_json_rejects_invalid_schema():
    invalid_schema_json = """
    {
      "overall_status": "maybe",
      "risk_level": "medium",
      "summary": "Missing required list fields."
    }
    """

    with pytest.raises(QCInterpretationValidationError):
        validate_interpretation_json(invalid_schema_json)


def test_interpret_qc_result_mocks_gemini_response():
    gemini_client = SuccessfulGeminiClient()

    interpretation = interpret_qc_result(
        ParsedQCResult(),
        gemini_client=gemini_client,
    )

    assert interpretation.overall_status == "review"
    assert gemini_client.response_mime_type == "application/json"
    assert gemini_client.contents is not None
    assert '"gc_percent": 48.0' in gemini_client.contents


def test_interpret_qc_result_handles_gemini_failure():
    with pytest.raises(QCInterpretationGenerationError):
        interpret_qc_result(
            ParsedQCResult(),
            gemini_client=FailingGeminiClient(),
        )
