"""
Scenario YAML runner for Quick Suite cross-stack E2E scenarios.

Each scenario.yaml describes a multi-step workflow across deployed stacks.
The runner:
  - Discovers CloudFormation outputs to locate Lambda ARNs
  - Resolves {step_id.field.path} references between steps
  - Invokes each step's Lambda and applies assertions
  - Polls status-check steps until completion or timeout

Invoke pattern per stack:
  data, compute, router  → plain JSON response (return value is the result)
  claws                  → API Gateway envelope ({statusCode, body: json_str})
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import boto3
import pytest
import yaml

# ---------------------------------------------------------------------------
# Stack → CloudFormation stack name
# ---------------------------------------------------------------------------

STACK_NAMES: dict[str, str] = {
    "data": "QuickSuiteOpenData",
    "compute": "QuickSuiteCompute",
    "router": "QuickSuiteRouter",
    "claws": "ClawsToolsStack",
}

# Stacks that return plain JSON (not API Gateway envelope)
_PLAIN_JSON_STACKS = {"data", "compute", "router"}


# ---------------------------------------------------------------------------
# Scenario data model
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    name: str
    display_name: str
    description: str
    category: str
    requires: dict
    steps: list[dict]
    path: Path  # path to the scenario.yaml file


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_scenarios(root: Path | None = None) -> list[Scenario]:
    """Walk examples/ under the capstone root and load all scenario.yaml files."""
    if root is None:
        root = Path(__file__).parent.parent.parent / "examples"
    scenarios = []
    for yaml_path in sorted(root.rglob("scenario.yaml")):
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        scenarios.append(Scenario(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            description=data.get("description", ""),
            category=data.get("category", ""),
            requires=data.get("requires", {}),
            steps=data.get("steps", []),
            path=yaml_path,
        ))
    return scenarios


# ---------------------------------------------------------------------------
# CloudFormation output cache
# ---------------------------------------------------------------------------

_cfn_cache: dict[str, dict[str, str]] = {}


def _cfn_outputs(stack_name: str, region: str, profile: str | None) -> dict[str, str]:
    key = f"{profile}:{region}:{stack_name}"
    if key not in _cfn_cache:
        session = boto3.Session(profile_name=profile, region_name=region)
        cfn = session.client("cloudformation")
        try:
            resp = cfn.describe_stacks(StackName=stack_name)
            raw = resp["Stacks"][0].get("Outputs", [])
            _cfn_cache[key] = {o["OutputKey"]: o["OutputValue"] for o in raw}
        except Exception:
            _cfn_cache[key] = {}
    return _cfn_cache[key]


def stack_deployed(stack_key: str, region: str, profile: str | None) -> bool:
    stack_name = STACK_NAMES.get(stack_key)
    if not stack_name:
        return False
    outputs = _cfn_outputs(stack_name, region, profile)
    return bool(outputs)


# ---------------------------------------------------------------------------
# Lambda ARN resolution
# ---------------------------------------------------------------------------

def _resolve_arn(
    tool: str, stack_key: str, region: str, profile: str | None
) -> str | None:
    """Return the Lambda ARN for a tool in a given stack.

    Strategies (tried in order):
    1. ToolArns JSON blob in CFN outputs (data + compute stacks)
    2. Individual {ToolName}FunctionArn CFN output (claws stack)
    3. Naming convention: {prefix}-{tool} Lambda function name
    """
    stack_name = STACK_NAMES.get(stack_key)
    if not stack_name:
        return None

    outputs = _cfn_outputs(stack_name, region, profile)

    # Strategy 1: ToolArns JSON blob
    if "ToolArns" in outputs:
        try:
            arns = json.loads(outputs["ToolArns"])
            if tool in arns:
                return arns[tool]
        except (json.JSONDecodeError, KeyError):
            pass

    # Strategy 2: {ToolName}FunctionArn individual output
    # claws tools are named like "claws-discover", but stored as "discoverFunctionArn"
    tool_key = tool.replace("claws-", "")
    output_key = f"{tool_key}FunctionArn"
    if output_key in outputs:
        return outputs[output_key]

    # Strategy 3: naming convention
    prefixes = {
        "data": "qs-data-",
        "compute": "qs-compute-",
        "router": "qs-router-",
        "claws": "",
    }
    prefix = prefixes.get(stack_key, "")
    fn_name = f"{prefix}{tool.replace('_', '-')}"

    session = boto3.Session(profile_name=profile, region_name=region)
    lam = session.client("lambda", region_name=region)
    try:
        resp = lam.get_function(FunctionName=fn_name)
        return resp["Configuration"]["FunctionArn"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Reference resolver  {step_id.field.subfield}  or  {step_id.field[0].sub}
# ---------------------------------------------------------------------------

_REF_RE = re.compile(r"\{([^}]+)\}")


def _get_nested(data: Any, path_str: str) -> Any:
    """Traverse a nested dict/list using dot-and-bracket notation.

    "results[0].dataset_id"  →  data["results"][0]["dataset_id"]
    "results.0.dataset_id"   →  same
    """
    # Normalise bracket indices to dot notation: results[0] → results.0
    path_str = re.sub(r"\[(\d+)\]", r".\1", path_str)
    parts = path_str.split(".")
    node = data
    for part in parts:
        if part == "":
            continue
        if isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(node, dict):
            node = node.get(part)
        else:
            return None
    return node


def resolve_refs(value: Any, step_results: dict[str, Any]) -> Any:
    """Recursively resolve {step_id.path} references in a value."""
    if isinstance(value, str):
        def _replace(m: re.Match) -> str:
            ref = m.group(1)
            dot = ref.index(".") if "." in ref else len(ref)
            step_id = ref[:dot]
            path = ref[dot + 1:] if dot < len(ref) else ""
            result = step_results.get(step_id)
            if result is None:
                return m.group(0)  # leave unresolved
            resolved = _get_nested(result, path) if path else result
            return str(resolved) if resolved is not None else m.group(0)

        return _REF_RE.sub(_replace, value)

    if isinstance(value, dict):
        return {k: resolve_refs(v, step_results) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_refs(v, step_results) for v in value]
    return value


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

def _assert_step(result: dict, assertions: list[dict], step_id: str) -> None:
    for spec in assertions:
        path = spec.get("path", "")
        op = spec.get("op", "exists")
        expected = spec.get("value")

        actual = _get_nested(result, path) if path else result

        if op == "exists":
            assert actual is not None and actual != "" and actual != [], \
                f"Step '{step_id}': expected '{path}' to exist, got {actual!r}"

        elif op == "eq":
            assert actual == expected, \
                f"Step '{step_id}': expected '{path}' == {expected!r}, got {actual!r}"

        elif op == "gte":
            assert actual is not None and actual >= expected, \
                f"Step '{step_id}': expected '{path}' >= {expected}, got {actual!r}"

        elif op == "in":
            assert actual in expected, \
                f"Step '{step_id}': expected '{path}' in {expected!r}, got {actual!r}"

        else:
            raise ValueError(f"Unknown assertion op '{op}' in step '{step_id}'")


# ---------------------------------------------------------------------------
# Lambda invocation
# ---------------------------------------------------------------------------

def _invoke_lambda(
    fn_arn: str,
    payload: dict,
    stack_key: str,
    region: str,
    profile: str | None,
) -> dict:
    session = boto3.Session(profile_name=profile, region_name=region)
    lam = session.client("lambda", region_name=region)
    resp = lam.invoke(
        FunctionName=fn_arn,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(),
    )
    raw = json.loads(resp["Payload"].read())

    if resp.get("FunctionError"):
        raise RuntimeError(f"Lambda FunctionError: {raw}")

    # claws stack wraps response in API Gateway envelope
    if stack_key not in _PLAIN_JSON_STACKS:
        body = raw.get("body", "{}")
        return json.loads(body) if isinstance(body, str) else raw

    return raw


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

class ScenarioRunner:
    def __init__(self, region: str = "us-east-1", profile: str | None = None):
        self.region = region
        self.profile = profile

    def check_requirements(self, scenario: Scenario) -> None:
        """Skip the test if any required stack is not deployed."""
        required = scenario.requires.get("stacks", [])
        missing = [s for s in required if not stack_deployed(s, self.region, self.profile)]
        if missing:
            pytest.skip(
                f"Scenario '{scenario.name}' requires stacks {missing} "
                f"which are not deployed (check AWS_PROFILE and region)."
            )

    def run(self, scenario: Scenario) -> None:
        self.check_requirements(scenario)

        step_results: dict[str, Any] = {}

        for step in scenario.steps:
            step_id = step["id"]
            tool = step["tool"]
            stack_key = step["stack"]
            raw_input = step.get("input", {})
            assertions = step.get("assert", [])
            poll_cfg = step.get("poll")

            # Resolve references in input
            resolved_input = resolve_refs(raw_input, step_results)

            # Find Lambda ARN
            fn_arn = _resolve_arn(tool, stack_key, self.region, self.profile)
            if not fn_arn:
                pytest.skip(
                    f"Step '{step_id}': cannot resolve ARN for tool '{tool}' "
                    f"in stack '{stack_key}'. Check CFN outputs or naming convention."
                )

            # Execute (with optional polling)
            if poll_cfg:
                result = self._poll(
                    fn_arn, resolved_input, stack_key,
                    assertions, step_id, poll_cfg,
                )
            else:
                result = _invoke_lambda(fn_arn, resolved_input, stack_key, self.region, self.profile)
                if assertions:
                    _assert_step(result, assertions, step_id)

            step_results[step_id] = result

    def _poll(
        self,
        fn_arn: str,
        payload: dict,
        stack_key: str,
        assertions: list[dict],
        step_id: str,
        poll_cfg: dict,
    ) -> dict:
        interval = poll_cfg.get("interval_seconds", 15)
        max_attempts = poll_cfg.get("max_attempts", 20)

        result: dict = {}
        for attempt in range(max_attempts):
            result = _invoke_lambda(fn_arn, payload, stack_key, self.region, self.profile)
            # Check if assertions are satisfied (polling stops on success or terminal state)
            try:
                if assertions:
                    _assert_step(result, assertions, step_id)
                return result  # assertions passed — done
            except AssertionError:
                if attempt < max_attempts - 1:
                    time.sleep(interval)
                # On last attempt, let the assertion failure propagate
        if assertions:
            _assert_step(result, assertions, step_id)
        return result
