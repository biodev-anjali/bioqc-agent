def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "bioqc-agent",
    }


def test_upload_parse_results_workflow(client, sample_fastqc_zip_path):
    with sample_fastqc_zip_path.open("rb") as sample_file:
        upload_response = client.post(
            "/api/jobs/upload",
            files={
                "file": (
                    "sample_fastqc.zip",
                    sample_file,
                    "application/zip",
                )
            },
        )

    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    job = upload_payload["job"]
    assert upload_payload["message"] == "File uploaded successfully."
    assert job["original_filename"] == "sample_fastqc.zip"
    assert job["stored_filename"] == "sample_fastqc.zip"
    assert job["file_type"] == "fastqc_zip"
    assert job["status"] == "uploaded"
    assert job["error_message"] is None

    job_id = job["id"]
    parse_response = client.post(f"/api/jobs/{job_id}/parse")

    assert parse_response.status_code == 200
    parse_payload = parse_response.json()
    assert parse_payload["message"] == "FastQC report parsed successfully."
    assert parse_payload["job"]["id"] == job_id
    assert parse_payload["job"]["status"] == "parsed"

    parsed_result = parse_payload["result"]
    assert parsed_result["job_id"] == job_id
    assert parsed_result["total_sequences"] == 1_250_000
    assert parsed_result["sequence_length"] == "150"
    assert parsed_result["gc_percent"] == 48.0
    assert parsed_result["per_base_quality_status"] == "pass"
    assert parsed_result["per_sequence_quality_status"] == "pass"
    assert parsed_result["adapter_content_status"] == "warn"
    assert parsed_result["overrepresented_sequences_status"] == "pass"

    results_response = client.get(f"/api/jobs/{job_id}/results")

    assert results_response.status_code == 200
    assert results_response.json() == parsed_result
