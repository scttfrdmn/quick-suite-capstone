"""
Scenario tests — one test per scenario.yaml in examples/.

Each test drives the full workflow described in its scenario.yaml:
resolves cross-step references, invokes deployed Lambda functions,
applies assertions, and polls status steps to completion.

A test skips (not fails) when:
  - A required stack is not deployed
  - A Lambda ARN cannot be resolved (tool not registered in CFN outputs)

A test fails when:
  - A Lambda returns an error response
  - An assertion condition is not met after all polling attempts

This is intentional: skips surface missing infrastructure, failures
surface broken pipelines. Both are actionable signals.

Run:
  AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario
  AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario -k academic-research
  AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario -k noaa-climate
"""

import pytest

from tests.scenarios.runner import Scenario, ScenarioRunner

pytestmark = pytest.mark.scenario


def test_scenario(scenario: Scenario, scenario_runner: ScenarioRunner) -> None:
    """Execute a scenario end-to-end against deployed stacks.

    ``scenario`` is parametrized by conftest.pytest_generate_tests from
    every scenario.yaml under examples/.
    """
    scenario_runner.run(scenario)
