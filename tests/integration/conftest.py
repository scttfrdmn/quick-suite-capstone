"""Shared fixtures for Quick Suite Capstone cross-project integration tests.

All tests in this directory require Substrate (the AWS emulator). The
`substrate` fixture from pytest-substrate starts the server, resets state,
and sets AWS_ENDPOINT_URL so every boto3 client in this process routes to
Substrate automatically.

Project code lives in three sibling directories. We add each project root to
sys.path so their modules can be imported:
  - quick-suite-claws/  → `tools.*` package imports
  - quick-suite-compute/ → loaded dynamically via importlib
  - quick-suite-data/   → loaded dynamically via importlib
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import boto3
import pytest

# ---------------------------------------------------------------------------
# sys.path setup — must happen at conftest import time, before test collection
# ---------------------------------------------------------------------------

CAPSTONE_ROOT = Path(__file__).parent.parent.parent
CLAWS_ROOT = CAPSTONE_ROOT / "quick-suite-claws"
COMPUTE_ROOT = CAPSTONE_ROOT / "quick-suite-compute"
DATA_ROOT = CAPSTONE_ROOT / "quick-suite-data"
PROFILES_DIR = COMPUTE_ROOT / "config" / "profiles"

# claws uses package-style imports (tools.shared, tools.export.handler, …)
if str(CLAWS_ROOT) not in sys.path:
    sys.path.insert(0, str(CLAWS_ROOT))

# Seed env vars before any module-level boto3 clients are created at import time
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("CLAWS_RUNS_BUCKET", "claws-runs-test")
os.environ.setdefault("CLAWS_LOOKUP_TABLE", "qs-claws-lookup-test")
os.environ.setdefault("QUICKSIGHT_ACCOUNT_ID", "123456789012")

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _load_handler(repo_root: Path, lambda_dir: str) -> object:
    """Load a Lambda handler module fresh (no sys.modules cache).

    Loading after the `substrate` fixture sets AWS_ENDPOINT_URL ensures that
    any module-level boto3 clients point to Substrate, not real AWS.
    """
    path = repo_root / "lambdas" / lambda_dir / "handler.py"
    alias = f"_int_{lambda_dir.replace('-', '_')}_{id(path)}"
    spec = importlib.util.spec_from_file_location(alias, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_profiles_json() -> str:
    profiles = []
    for p in sorted(PROFILES_DIR.glob("*.json")):
        with open(p) as f:
            profiles.append(json.load(f))
    return json.dumps(profiles)


_PROFILES_JSON = _load_profiles_json()

# ---------------------------------------------------------------------------
# autouse fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def aws_env(substrate, monkeypatch):
    """Standard env vars used by all claws and compute handlers."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("CLAWS_RUNS_BUCKET", "claws-runs-test")
    monkeypatch.setenv("CLAWS_LOOKUP_TABLE", "qs-claws-lookup-test")
    monkeypatch.setenv("QUICKSIGHT_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("CLAWS_GUARDRAIL_ID", "")
    monkeypatch.setenv("CLAWS_METRICS_NAMESPACE", "")


@pytest.fixture(autouse=True)
def reset_claws_singletons():
    """Reset claws shared.py boto3 singletons before and after each test.

    tools/shared.py creates boto3 clients lazily as module-level singletons.
    Resetting them to None before each test ensures they are re-created with
    the current AWS_ENDPOINT_URL (pointing to Substrate).
    """
    import tools.shared as _shared  # noqa: PLC0415

    _shared._s3 = None
    _shared._dynamodb = None
    _shared._bedrock = None
    _shared._cloudwatch = None
    # Patch module-level constants that were fixed at import time
    _shared.RUNS_BUCKET = "claws-runs-test"
    _shared.PLANS_TABLE = "claws-plans-test"
    _shared.SCHEMAS_TABLE = "claws-schemas-test"
    _shared.GUARDRAIL_ID = ""
    _shared.METRICS_NAMESPACE = ""
    yield
    _shared._s3 = None
    _shared._dynamodb = None
    _shared._bedrock = None
    _shared._cloudwatch = None


@pytest.fixture(autouse=True)
def reset_export_singletons():
    """Reset export handler boto3 singletons."""
    import tools.export.handler as _export  # noqa: PLC0415

    _export._qs_client = None
    _export.EVENTS_CLIENT = None
    # Patch constants imported by value from tools.shared
    _export.RUNS_BUCKET = "claws-runs-test"
    _export.CLAWS_LOOKUP_TABLE = "qs-claws-lookup-test"
    _export.QUICKSIGHT_ACCOUNT_ID = "123456789012"
    yield
    _export._qs_client = None
    _export.EVENTS_CLIENT = None


# ---------------------------------------------------------------------------
# Shared AWS resource fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def claws_runs_bucket(substrate):
    """S3 bucket for claws excavation results."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="claws-runs-test")
    return s3


@pytest.fixture()
def lookup_table(substrate):
    """DynamoDB ClawsLookupTable (source_id → dataset_id bridge)."""
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="qs-claws-lookup-test",
        KeySchema=[{"AttributeName": "source_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "source_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    return ddb.Table("qs-claws-lookup-test")


@pytest.fixture()
def spend_table(substrate):
    """DynamoDB spend table for compute budget pre-check."""
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="qs-compute-spend-test",
        KeySchema=[
            {"AttributeName": "user_arn", "KeyType": "HASH"},
            {"AttributeName": "month", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_arn", "AttributeType": "S"},
            {"AttributeName": "month", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return ddb.Table("qs-compute-spend-test")


@pytest.fixture()
def state_machine_arn(substrate):
    """A minimal Step Functions state machine in Substrate."""
    sfn = boto3.client("stepfunctions", region_name="us-east-1")
    resp = sfn.create_state_machine(
        name="qs-compute-job-test",
        definition=json.dumps({
            "Comment": "Integration test stub",
            "StartAt": "Done",
            "States": {"Done": {"Type": "Succeed"}},
        }),
        roleArn="arn:aws:iam::123456789012:role/qs-compute-sfn",
        type="STANDARD",
    )
    return resp["stateMachineArn"]


@pytest.fixture()
def profiles_json():
    return _PROFILES_JSON


# ---------------------------------------------------------------------------
# Handler module fixtures (loaded fresh per test, after Substrate is up)
# ---------------------------------------------------------------------------

@pytest.fixture()
def compute_run_mod(substrate, monkeypatch):
    """compute-run handler loaded fresh after Substrate sets AWS_ENDPOINT_URL."""
    mod = _load_handler(COMPUTE_ROOT, "compute-run")
    mod._PROFILES = None  # force profile reload from env
    return mod


@pytest.fixture()
def claws_resolver_mod(substrate, monkeypatch):
    """claws-resolver handler loaded fresh after Substrate sets AWS_ENDPOINT_URL."""
    monkeypatch.setenv("CLAWS_LOOKUP_TABLE", "qs-claws-lookup-test")
    mod = _load_handler(DATA_ROOT, "claws-resolver")
    return mod
