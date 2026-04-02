"""Integration tests: roda_load/s3_load lookup entry → compute_run(claws://).

Pipeline under test:
  roda_load or s3_load writes:
    ClawsLookupTable: roda-{slug} → Quick Sight dataset_id

  claws-resolver reads:
    ClawsLookupTable: roda-{slug} → dataset_id  ✓

  compute_run accepts:
    source_uri=claws://roda-{slug}  →  SFN execution started

This validates the existing claws:// bridge that connects Open Data to
Compute: the dataset registered by roda_load is resolvable by claws-resolver,
and compute_run passes the claws:// URI through to the SFN so the extract
Lambda can resolve it at execution time.
"""

from __future__ import annotations

import json

import boto3
import pytest

USER_ARN = "arn:aws:iam::123456789012:user/analyst"


@pytest.mark.integration
class TestDataToCompute:
    def test_claws_resolver_reads_roda_lookup_entry(
        self, lookup_table, claws_resolver_mod
    ):
        """claws-resolver resolves a roda-{slug} source_id written by roda_load."""
        # Simulate what roda_load writes
        lookup_table.put_item(Item={
            "source_id": "roda-noaa-ghcn",
            "dataset_id": "qs-noaa-ghcn-dataset-abc123",
        })

        result = claws_resolver_mod.handler({"source_id": "roda-noaa-ghcn"}, None)

        assert "error" not in result, result
        assert result["source_id"] == "roda-noaa-ghcn"
        assert result["dataset_id"] == "qs-noaa-ghcn-dataset-abc123"

    def test_claws_resolver_reads_s3_lookup_entry(
        self, lookup_table, claws_resolver_mod
    ):
        """claws-resolver resolves an s3-{label} source_id written by s3_load."""
        lookup_table.put_item(Item={
            "source_id": "s3-ir-data",
            "dataset_id": "qs-institutional-research-xyz",
        })

        result = claws_resolver_mod.handler({"source_id": "s3-ir-data"}, None)

        assert result["dataset_id"] == "qs-institutional-research-xyz"

    def test_claws_resolver_returns_error_for_missing_source(
        self, lookup_table, claws_resolver_mod
    ):
        """claws-resolver returns an error dict (no exception) for unknown source_id."""
        result = claws_resolver_mod.handler({"source_id": "roda-does-not-exist"}, None)

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_compute_run_accepts_claws_uri(
        self,
        lookup_table,
        spend_table,
        state_machine_arn,
        compute_run_mod,
        profiles_json,
        monkeypatch,
    ):
        """compute_run validates claws:// source_uri and starts a SFN execution.

        The extract Lambda (inside SFN) does the actual claws:// → dataset_id
        resolution at execution time. Here we verify compute_run accepts the
        URI and starts the execution with it in the SFN input.
        """
        # Seed the lookup table as roda_load would
        lookup_table.put_item(Item={
            "source_id": "roda-noaa-ghcn",
            "dataset_id": "qs-noaa-ghcn-test",
        })

        monkeypatch.setenv("PROFILES_CONFIG", profiles_json)
        monkeypatch.setenv("SPEND_TABLE", "qs-compute-spend-test")
        monkeypatch.setenv("STATE_MACHINE_ARN", state_machine_arn)
        monkeypatch.setenv("MONTHLY_BUDGET_USD", "50")
        monkeypatch.setenv("ENABLE_EMR", "false")
        compute_run_mod._PROFILES = None

        run_event = {
            "profile_id": "explore-correlations",
            "source_uri": "claws://roda-noaa-ghcn",
            "user_arn": USER_ARN,
            "parameters": {},
        }
        result = compute_run_mod.handler(run_event, None)

        assert result.get("status") == "started", result
        assert "execution_arn" in result

    def test_sfn_execution_input_carries_claws_uri(
        self,
        lookup_table,
        spend_table,
        state_machine_arn,
        compute_run_mod,
        profiles_json,
        monkeypatch,
    ):
        """The SFN input preserves the claws:// URI verbatim so the extract
        Lambda receives it and can invoke claws-resolver to resolve it."""
        lookup_table.put_item(Item={
            "source_id": "roda-cms-data",
            "dataset_id": "qs-cms-dataset-001",
        })

        monkeypatch.setenv("PROFILES_CONFIG", profiles_json)
        monkeypatch.setenv("SPEND_TABLE", "qs-compute-spend-test")
        monkeypatch.setenv("STATE_MACHINE_ARN", state_machine_arn)
        monkeypatch.setenv("MONTHLY_BUDGET_USD", "50")
        monkeypatch.setenv("ENABLE_EMR", "false")
        compute_run_mod._PROFILES = None

        run_event = {
            "profile_id": "explore-correlations",
            "source_uri": "claws://roda-cms-data",
            "user_arn": USER_ARN,
            "parameters": {},
        }
        result = compute_run_mod.handler(run_event, None)
        assert result.get("status") == "started", result

        sfn = boto3.client("stepfunctions", region_name="us-east-1")
        exec_input = json.loads(
            sfn.describe_execution(executionArn=result["execution_arn"])["input"]
        )

        assert exec_input["source_uri"] == "claws://roda-cms-data"
        assert exec_input["dataset_id"] == ""  # dataset_id is empty; source_uri is used
