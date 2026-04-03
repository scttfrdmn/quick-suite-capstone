"""
Conftest for Quick Suite capstone scenario tests.

Scenario tests run against deployed AWS stacks. They skip automatically
when stacks are not deployed or credentials are absent.

Required environment:
  AWS_PROFILE=aws  (or other standard AWS credential env vars)

Optional environment:
  QS_SCENARIO_REGION   AWS region (default: us-east-1)
  QS_SCENARIO_PROFILE  AWS profile (default: $AWS_PROFILE or None)

Run all scenarios:
  AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario

Run one category:
  AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario -k academic

Run one scenario by name:
  AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario -k noaa-climate
"""

import os

import pytest

from tests.scenarios.runner import ScenarioRunner, discover_scenarios

REGION = os.environ.get("QS_SCENARIO_REGION", "us-east-1")
PROFILE = os.environ.get("QS_SCENARIO_PROFILE") or os.environ.get("AWS_PROFILE")


@pytest.fixture(scope="session")
def scenario_runner() -> ScenarioRunner:
    return ScenarioRunner(region=REGION, profile=PROFILE)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize test_scenario with every discovered scenario."""
    if "scenario" in metafunc.fixturenames:
        scenarios = discover_scenarios()
        metafunc.parametrize(
            "scenario",
            scenarios,
            ids=[s.name for s in scenarios],
        )
