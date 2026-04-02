"""Integration tests: claws excavation result → Quick Sight dataset.

Pipeline under test:
  claws.excavate (result stored in S3)
    → claws.export(quicksight://)
      → Quick Sight data source + dataset created
      → ClawsLookupTable: claws-{run_id} → dataset_id

  Then: claws-resolver reads the lookup entry, proving that the exported
  dataset can be picked up by downstream compute jobs via claws:// URIs.
"""

from __future__ import annotations

import json

import boto3
import pytest

import tools.export.handler as _export
import tools.shared as _shared


@pytest.mark.integration
class TestClawsToQuickSight:
    def test_excavation_result_exported_to_quicksight(
        self, claws_runs_bucket, lookup_table
    ):
        """export(quicksight://) creates a QuickSight dataset and registers it
        in ClawsLookupTable with key claws-{run_id}."""
        run_id = "run-int-qs-001"
        rows = [
            {"station_id": "USW00094728", "date": "2024-01-01", "temp_c": 22.5},
            {"station_id": "USW00094729", "date": "2024-01-01", "temp_c": 18.1},
        ]
        _shared.store_result(run_id, rows)

        event = {
            "run_id": run_id,
            "destination": {"type": "quicksight", "uri": "quicksight://weather-analysis"},
            "include_provenance": False,
        }
        resp = _export.handler(event, None)
        body = json.loads(resp["body"])

        assert resp["statusCode"] == 200, body
        assert body["status"] == "complete"
        assert "dataset_id" in body
        assert body["dataset_id"].startswith("claws-dset-")

        # Verify the ClawsLookupTable entry was written
        source_id = f"claws-{run_id}"
        item = lookup_table.get_item(Key={"source_id": source_id}).get("Item")
        assert item is not None, f"ClawsLookupTable missing entry for {source_id}"
        assert item["dataset_id"] == body["dataset_id"]
        assert item["dataset_name"] == "weather-analysis"

    def test_dataset_name_derived_from_uri(self, claws_runs_bucket, lookup_table):
        """The dataset_name in ClawsLookupTable matches the URI path."""
        run_id = "run-int-qs-002"
        rows = [{"gene": "BRCA1", "count": 42}, {"gene": "TP53", "count": 17}]
        _shared.store_result(run_id, rows)

        event = {
            "run_id": run_id,
            "destination": {"type": "quicksight", "uri": "quicksight://genomics-jan-2024"},
            "include_provenance": False,
        }
        resp = _export.handler(event, None)
        body = json.loads(resp["body"])

        assert body["status"] == "complete"
        item = lookup_table.get_item(Key={"source_id": f"claws-{run_id}"})["Item"]
        assert item["dataset_name"] == "genomics-jan-2024"

    def test_export_writes_csv_to_runs_bucket(self, claws_runs_bucket, lookup_table):
        """The CSV and manifest files are written to the runs S3 bucket."""
        run_id = "run-int-qs-003"
        rows = [{"x": "1", "y": "2"}, {"x": "3", "y": "4"}]
        _shared.store_result(run_id, rows)

        s3 = boto3.client("s3", region_name="us-east-1")
        event = {
            "run_id": run_id,
            "destination": {"type": "quicksight", "uri": "quicksight://test-csv"},
            "include_provenance": False,
        }
        _export.handler(event, None)

        # List objects in the runs bucket for this run
        objects = s3.list_objects_v2(Bucket="claws-runs-test", Prefix=run_id)
        keys = [obj["Key"] for obj in objects.get("Contents", [])]
        csv_keys = [k for k in keys if k.endswith(".csv")]
        manifest_keys = [k for k in keys if k.endswith("-manifest.json")]
        assert csv_keys, "Expected CSV file in runs bucket"
        assert manifest_keys, "Expected manifest file in runs bucket"

    def test_claws_resolver_reads_exported_dataset(
        self, claws_runs_bucket, lookup_table, claws_resolver_mod
    ):
        """After export(quicksight://), the claws-resolver can resolve the
        exported dataset_id from the run_id's source_id."""
        run_id = "run-int-qs-004"
        rows = [{"record": "alpha"}, {"record": "beta"}]
        _shared.store_result(run_id, rows)

        export_event = {
            "run_id": run_id,
            "destination": {"type": "quicksight", "uri": "quicksight://resolver-test"},
            "include_provenance": False,
        }
        export_body = json.loads(_export.handler(export_event, None)["body"])
        exported_dataset_id = export_body["dataset_id"]

        # Resolve via claws-resolver
        resolver_resp = claws_resolver_mod.handler(
            {"source_id": f"claws-{run_id}"}, None
        )
        assert "error" not in resolver_resp, resolver_resp
        assert resolver_resp["dataset_id"] == exported_dataset_id
