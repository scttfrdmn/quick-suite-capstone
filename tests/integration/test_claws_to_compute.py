"""Integration tests: claws S3 export → compute_run.

Pipeline under test:
  claws.excavate result in S3
    → claws.export(s3://output-bucket/path/result.json)
      → compute_run(profile_id, source_uri=s3://…)
        → Step Functions execution started with source_uri in input

This validates the hand-off contract: the S3 URI produced by claws.export is
a valid source_uri accepted by compute_run, and the SFN execution carries
that URI into the pipeline so the extract Lambda can find the data.
"""

from __future__ import annotations

import json

import boto3
import pytest

import tools.export.handler as _export
import tools.shared as _shared

USER_ARN = "arn:aws:iam::123456789012:user/analyst"


@pytest.mark.integration
class TestClawsToCompute:
    def test_export_to_s3_produces_valid_source_uri(
        self, claws_runs_bucket
    ):
        """claws.export(s3://) writes a JSON file that is a valid S3 URI."""
        run_id = "run-int-c2c-001"
        rows = [{"student_id": "S001", "gpa": 3.5}, {"student_id": "S002", "gpa": 2.8}]
        _shared.store_result(run_id, rows)

        output_bucket = "qs-compute-results-test"
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=output_bucket)

        export_event = {
            "run_id": run_id,
            "destination": {
                "type": "s3",
                "uri": f"s3://{output_bucket}/exports/{run_id}.json",
            },
            "include_provenance": False,
        }
        resp = _export.handler(export_event, None)
        body = json.loads(resp["body"])

        assert resp["statusCode"] == 200, body
        assert body["status"] == "complete"

        # Verify the file is actually there
        s3 = boto3.client("s3", region_name="us-east-1")
        obj = s3.get_object(Bucket=output_bucket, Key=f"exports/{run_id}.json")
        payload = json.loads(obj["Body"].read())
        assert payload == rows

    def test_compute_run_accepts_s3_source_uri(
        self,
        claws_runs_bucket,
        spend_table,
        state_machine_arn,
        compute_run_mod,
        profiles_json,
        monkeypatch,
    ):
        """compute_run starts a Step Functions execution when given a valid
        s3:// source_uri from a claws export."""
        run_id = "run-int-c2c-002"
        rows = [{"student_id": f"S{i:03d}", "gpa": 3.0} for i in range(60)]
        _shared.store_result(run_id, rows)

        # Export to S3
        output_bucket = "qs-compute-results-test-2"
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=output_bucket)
        export_event = {
            "run_id": run_id,
            "destination": {
                "type": "s3",
                "uri": f"s3://{output_bucket}/exports/{run_id}.json",
            },
            "include_provenance": False,
        }
        _export.handler(export_event, None)

        # Submit to compute_run using the exported S3 URI
        monkeypatch.setenv("PROFILES_CONFIG", profiles_json)
        monkeypatch.setenv("SPEND_TABLE", "qs-compute-spend-test")
        monkeypatch.setenv("STATE_MACHINE_ARN", state_machine_arn)
        monkeypatch.setenv("MONTHLY_BUDGET_USD", "50")
        monkeypatch.setenv("ENABLE_EMR", "false")
        compute_run_mod._PROFILES = None

        run_event = {
            "profile_id": "explore-correlations",
            "source_uri": f"s3://{output_bucket}/exports/{run_id}.json",
            "user_arn": USER_ARN,
            "parameters": {},
        }
        result = compute_run_mod.handler(run_event, None)

        assert result.get("status") == "started", result
        assert "execution_arn" in result
        assert "job_id" in result
        assert result["profile_id"] == "explore-correlations"

    def test_sfn_execution_input_carries_source_uri(
        self,
        claws_runs_bucket,
        spend_table,
        state_machine_arn,
        compute_run_mod,
        profiles_json,
        monkeypatch,
    ):
        """The SFN execution input includes source_uri so the extract Lambda
        can locate the claws result without a QuickSight dataset."""
        output_bucket = "qs-compute-results-test-3"
        source_uri = f"s3://{output_bucket}/exports/run-int-c2c-003.json"
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=output_bucket)

        monkeypatch.setenv("PROFILES_CONFIG", profiles_json)
        monkeypatch.setenv("SPEND_TABLE", "qs-compute-spend-test")
        monkeypatch.setenv("STATE_MACHINE_ARN", state_machine_arn)
        monkeypatch.setenv("MONTHLY_BUDGET_USD", "50")
        monkeypatch.setenv("ENABLE_EMR", "false")
        compute_run_mod._PROFILES = None

        run_event = {
            "profile_id": "explore-correlations",
            "source_uri": source_uri,
            "user_arn": USER_ARN,
            "parameters": {},
        }
        result = compute_run_mod.handler(run_event, None)
        assert result.get("status") == "started", result

        # Inspect the SFN execution input to verify source_uri was passed through
        sfn = boto3.client("stepfunctions", region_name="us-east-1")
        exec_detail = sfn.describe_execution(executionArn=result["execution_arn"])
        exec_input = json.loads(exec_detail["input"])

        assert exec_input["source_uri"] == source_uri
        assert exec_input["user_arn"] == USER_ARN
        assert exec_input["profile"]["profile_id"] == "explore-correlations"
