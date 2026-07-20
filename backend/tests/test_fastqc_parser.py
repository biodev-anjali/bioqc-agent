from services.fastqc_parser import parse_fastqc_zip


def test_parse_sample_fastqc_zip(sample_fastqc_zip_path):
    metrics = parse_fastqc_zip(sample_fastqc_zip_path)

    assert metrics.total_sequences == 1_250_000
    assert metrics.sequence_length == "150"
    assert metrics.gc_percent == 48.0
    assert metrics.per_base_quality_status == "pass"
    assert metrics.per_sequence_quality_status == "pass"
    assert metrics.adapter_content_status == "warn"
    assert metrics.overrepresented_sequences_status == "pass"
