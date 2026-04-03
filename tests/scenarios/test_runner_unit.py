"""
Unit tests for tests/scenarios/runner.py internal logic.

These tests do NOT make any AWS calls. All Lambda invocations and
CloudFormation lookups are patched with unittest.mock.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.scenarios.runner import (
    Scenario,
    ScenarioRunner,
    _assert_step,
    _get_nested,
    discover_scenarios,
    resolve_refs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scenario(
    steps: list[dict] | None = None,
    requires: dict | None = None,
    name: str = "test-scenario",
) -> Scenario:
    return Scenario(
        name=name,
        display_name=name,
        description="",
        category="test",
        requires=requires or {},
        steps=steps or [],
        path=Path("/fake/scenario.yaml"),
    )


# ---------------------------------------------------------------------------
# 1. _get_nested
# ---------------------------------------------------------------------------

class TestGetNested:
    def test_simple_field(self):
        assert _get_nested({"a": 1}, "a") == 1

    def test_nested_two_levels(self):
        assert _get_nested({"a": {"b": 2}}, "a.b") == 2

    def test_nested_three_levels(self):
        assert _get_nested({"a": {"b": {"c": 42}}}, "a.b.c") == 42

    def test_list_by_dot_index(self):
        assert _get_nested({"items": ["x", "y"]}, "items.0") == "x"

    def test_list_by_dot_index_second_element(self):
        assert _get_nested({"items": ["x", "y"]}, "items.1") == "y"

    def test_list_by_bracket_index(self):
        assert _get_nested({"items": ["x", "y"]}, "items[0]") == "x"

    def test_list_by_bracket_index_second_element(self):
        assert _get_nested({"items": ["x", "y"]}, "items[1]") == "y"

    def test_list_nested_dict(self):
        data = {"results": [{"dataset_id": "noaa-ghcn"}, {"dataset_id": "other"}]}
        assert _get_nested(data, "results[0].dataset_id") == "noaa-ghcn"
        assert _get_nested(data, "results.1.dataset_id") == "other"

    def test_missing_key_returns_none(self):
        assert _get_nested({"a": 1}, "b") is None

    def test_missing_nested_key_returns_none(self):
        assert _get_nested({"a": {"b": 1}}, "a.c") is None

    def test_out_of_range_list_bracket(self):
        assert _get_nested({"items": ["x"]}, "items[5]") is None

    def test_out_of_range_list_dot(self):
        assert _get_nested({"items": ["x"]}, "items.5") is None

    def test_path_into_non_dict_non_list_returns_none(self):
        assert _get_nested({"a": 42}, "a.b") is None

    def test_empty_path_returns_data_unchanged(self):
        data = {"a": 1}
        # An empty string path should traverse nothing and return the root
        # The implementation splits on "." giving [""], skips empty parts
        result = _get_nested(data, "")
        assert result == data

    def test_bracket_notation_deep(self):
        data = {"datasets": [{"tags": ["climate", "noaa"]}]}
        assert _get_nested(data, "datasets[0].tags[1]") == "noaa"


# ---------------------------------------------------------------------------
# 2. resolve_refs
# ---------------------------------------------------------------------------

class TestResolveRefs:
    def test_plain_string_unchanged(self):
        assert resolve_refs("hello", {}) == "hello"

    def test_integer_unchanged(self):
        assert resolve_refs(42, {}) == 42

    def test_none_unchanged(self):
        assert resolve_refs(None, {}) is None

    def test_simple_ref(self):
        result = resolve_refs("{search.count}", {"search": {"count": 5}})
        assert result == "5"

    def test_nested_ref(self):
        step_results = {"search": {"datasets": [{"slug": "noaa-ghcn"}]}}
        result = resolve_refs("{search.datasets.0.slug}", step_results)
        assert result == "noaa-ghcn"

    def test_nested_ref_bracket_notation(self):
        step_results = {"search": {"results": [{"dataset_id": "roda-123"}]}}
        result = resolve_refs("{search.results[0].dataset_id}", step_results)
        assert result == "roda-123"

    def test_ref_in_dict_value(self):
        step_results = {"search": {"datasets": [{"slug": "noaa-ghcn"}]}}
        resolved = resolve_refs({"slug": "{search.datasets.0.slug}"}, step_results)
        assert resolved == {"slug": "noaa-ghcn"}

    def test_ref_in_dict_key_is_not_resolved(self):
        # Keys are passed through unchanged; only values are resolved
        step_results = {"search": {"count": 5}}
        resolved = resolve_refs({"{search.count}": "value"}, step_results)
        assert "{search.count}" in resolved

    def test_ref_in_list(self):
        step_results = {"search": {"count": 7}}
        resolved = resolve_refs(["{search.count}"], step_results)
        assert resolved == ["7"]

    def test_unresolvable_ref_left_unchanged(self):
        result = resolve_refs("{missing.field}", {})
        assert result == "{missing.field}"

    def test_unresolvable_step_leaves_token(self):
        result = resolve_refs("{nonexistent.count}", {"search": {"count": 3}})
        assert result == "{nonexistent.count}"

    def test_mixed_string_prefix(self):
        step_results = {"load": {"source_id": "roda-noaa-ghcn"}}
        result = resolve_refs("claws://{load.source_id}", step_results)
        assert result == "claws://roda-noaa-ghcn"

    def test_mixed_string_multiple_refs(self):
        step_results = {"a": {"x": "foo"}, "b": {"y": "bar"}}
        result = resolve_refs("{a.x}-and-{b.y}", step_results)
        assert result == "foo-and-bar"

    def test_recursive_dict(self):
        step_results = {"run": {"job_id": "abc-123"}}
        resolved = resolve_refs({"input": {"job_id": "{run.job_id}"}}, step_results)
        assert resolved == {"input": {"job_id": "abc-123"}}

    def test_recursive_list_of_dicts(self):
        step_results = {"run": {"job_id": "j1"}}
        resolved = resolve_refs([{"id": "{run.job_id}"}], step_results)
        assert resolved == [{"id": "j1"}]

    def test_ref_with_no_subpath_resolves_whole_step(self):
        # A ref like "{step_id}" with no dot — step_id has no ".", so path=""
        # resolve_refs returns str(whole result) when path is ""
        step_results = {"search": {"count": 3}}
        # The ref "{search}" has no dot, so dot == len("search"), path=""
        # resolved = result (the whole dict), str of that
        result = resolve_refs("{search}", step_results)
        assert "count" in result  # stringified dict contains the key

    def test_none_resolved_to_original_token(self):
        # Field exists in step but _get_nested returns None (missing sub-key)
        step_results = {"search": {"count": 5}}
        result = resolve_refs("{search.missing_field}", step_results)
        assert result == "{search.missing_field}"


# ---------------------------------------------------------------------------
# 3. _assert_step
# ---------------------------------------------------------------------------

class TestAssertStep:

    # --- exists ---

    def test_exists_passes_with_string(self):
        _assert_step({"field": "value"}, [{"path": "field", "op": "exists"}], "step1")

    def test_exists_passes_with_integer(self):
        _assert_step({"count": 3}, [{"path": "count", "op": "exists"}], "step1")

    def test_exists_passes_with_list(self):
        _assert_step({"items": ["a"]}, [{"path": "items", "op": "exists"}], "step1")

    def test_exists_fails_when_none(self):
        with pytest.raises(AssertionError, match="step1"):
            _assert_step({"field": None}, [{"path": "field", "op": "exists"}], "step1")

    def test_exists_fails_when_empty_string(self):
        with pytest.raises(AssertionError, match="step1"):
            _assert_step({"field": ""}, [{"path": "field", "op": "exists"}], "step1")

    def test_exists_fails_when_empty_list(self):
        with pytest.raises(AssertionError, match="step1"):
            _assert_step({"field": []}, [{"path": "field", "op": "exists"}], "step1")

    def test_exists_fails_when_key_missing(self):
        with pytest.raises(AssertionError, match="step1"):
            _assert_step({}, [{"path": "field", "op": "exists"}], "step1")

    def test_exists_error_includes_path(self):
        with pytest.raises(AssertionError, match="my_field"):
            _assert_step({}, [{"path": "my_field", "op": "exists"}], "sid")

    # --- eq ---

    def test_eq_passes(self):
        _assert_step({"status": "created"}, [{"path": "status", "op": "eq", "value": "created"}], "s")

    def test_eq_fails_wrong_value(self):
        with pytest.raises(AssertionError, match="step2"):
            _assert_step(
                {"status": "failed"},
                [{"path": "status", "op": "eq", "value": "created"}],
                "step2",
            )

    def test_eq_integer_match(self):
        _assert_step({"code": 200}, [{"path": "code", "op": "eq", "value": 200}], "s")

    def test_eq_error_includes_step_id(self):
        with pytest.raises(AssertionError, match="my_step"):
            _assert_step({"x": 1}, [{"path": "x", "op": "eq", "value": 2}], "my_step")

    # --- gte ---

    def test_gte_passes_equal(self):
        _assert_step({"total": 5}, [{"path": "total", "op": "gte", "value": 5}], "s")

    def test_gte_passes_greater(self):
        _assert_step({"total": 10}, [{"path": "total", "op": "gte", "value": 5}], "s")

    def test_gte_fails_less_than(self):
        with pytest.raises(AssertionError, match="step3"):
            _assert_step(
                {"total": 3},
                [{"path": "total", "op": "gte", "value": 5}],
                "step3",
            )

    def test_gte_fails_when_none(self):
        with pytest.raises(AssertionError):
            _assert_step({"total": None}, [{"path": "total", "op": "gte", "value": 1}], "s")

    # --- in ---

    def test_in_passes(self):
        _assert_step(
            {"status": "SUCCEEDED"},
            [{"path": "status", "op": "in", "value": ["SUCCEEDED", "FAILED"]}],
            "s",
        )

    def test_in_passes_second_element(self):
        _assert_step(
            {"status": "FAILED"},
            [{"path": "status", "op": "in", "value": ["SUCCEEDED", "FAILED"]}],
            "s",
        )

    def test_in_fails(self):
        with pytest.raises(AssertionError, match="step4"):
            _assert_step(
                {"status": "RUNNING"},
                [{"path": "status", "op": "in", "value": ["SUCCEEDED", "FAILED"]}],
                "step4",
            )

    def test_in_error_includes_step_id(self):
        with pytest.raises(AssertionError, match="poll_step"):
            _assert_step(
                {"status": "RUNNING"},
                [{"path": "status", "op": "in", "value": ["SUCCEEDED"]}],
                "poll_step",
            )

    # --- unknown op ---

    def test_unknown_op_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown assertion op"):
            _assert_step({"x": 1}, [{"path": "x", "op": "magic"}], "s")

    def test_unknown_op_error_includes_step_id(self):
        with pytest.raises(ValueError, match="my_step"):
            _assert_step({"x": 1}, [{"path": "x", "op": "bogus"}], "my_step")

    # --- multiple assertions ---

    def test_multiple_assertions_all_pass(self):
        result = {"status": "created", "id": "abc", "count": 5}
        _assert_step(
            result,
            [
                {"path": "status", "op": "eq", "value": "created"},
                {"path": "id", "op": "exists"},
                {"path": "count", "op": "gte", "value": 1},
            ],
            "multi",
        )

    def test_multiple_assertions_second_fails(self):
        with pytest.raises(AssertionError):
            _assert_step(
                {"status": "created", "id": ""},
                [
                    {"path": "status", "op": "eq", "value": "created"},
                    {"path": "id", "op": "exists"},
                ],
                "multi",
            )

    # --- no path — asserts on the root result ---

    def test_exists_no_path_passes(self):
        _assert_step({"any": "data"}, [{"op": "exists"}], "s")


# ---------------------------------------------------------------------------
# 4. ScenarioRunner.run() — mocked AWS
# ---------------------------------------------------------------------------

class TestScenarioRunnerRun:
    """Tests for the full run() pipeline with Lambda calls mocked out."""

    def _runner(self) -> ScenarioRunner:
        return ScenarioRunner(region="us-east-1", profile=None)

    # --- happy path: 2-step scenario ---

    @patch("tests.scenarios.runner.stack_deployed", return_value=True)
    @patch("tests.scenarios.runner._resolve_arn", return_value="arn:aws:lambda:us-east-1:123:function:qs-data-roda-search")
    @patch("tests.scenarios.runner._invoke_lambda")
    def test_two_step_scenario_runs_successfully(
        self, mock_invoke, mock_arn, mock_deployed
    ):
        mock_invoke.return_value = {"results": [{"dataset_id": "noaa-ghcn"}], "total": 1}
        scenario = _make_scenario(
            requires={"stacks": ["data"]},
            steps=[
                {
                    "id": "search",
                    "tool": "roda_search",
                    "stack": "data",
                    "input": {"query": "NOAA"},
                    "assert": [{"path": "results", "op": "exists"}],
                }
            ],
        )
        runner = self._runner()
        runner.run(scenario)
        mock_invoke.assert_called_once()

    # --- reference resolution between steps ---

    @patch("tests.scenarios.runner.stack_deployed", return_value=True)
    @patch("tests.scenarios.runner._resolve_arn", return_value="arn:aws:lambda:us-east-1:123:function:fake")
    @patch("tests.scenarios.runner._invoke_lambda")
    def test_reference_resolved_between_steps(
        self, mock_invoke, mock_arn, mock_deployed
    ):
        search_result = {"results": [{"dataset_id": "noaa-ghcn"}], "total": 1}
        load_result = {"status": "created", "source_uri": "s3://bucket/noaa-ghcn/"}

        mock_invoke.side_effect = [search_result, load_result]

        scenario = _make_scenario(
            requires={"stacks": ["data"]},
            steps=[
                {
                    "id": "search",
                    "tool": "roda_search",
                    "stack": "data",
                    "input": {"query": "NOAA"},
                    "assert": [],
                },
                {
                    "id": "load",
                    "tool": "roda_load",
                    "stack": "data",
                    "input": {"dataset_id": "{search.results[0].dataset_id}"},
                    "assert": [{"path": "status", "op": "eq", "value": "created"}],
                },
            ],
        )
        runner = self._runner()
        runner.run(scenario)

        assert mock_invoke.call_count == 2
        # Second call's payload must have the resolved dataset_id
        _, kwargs_or_second_arg = mock_invoke.call_args_list[1][0], mock_invoke.call_args_list[1]
        second_call_payload = mock_invoke.call_args_list[1][0][1]  # positional arg index 1 = payload
        assert second_call_payload["dataset_id"] == "noaa-ghcn"

    # --- skip when stack not deployed ---

    @patch("tests.scenarios.runner.stack_deployed", return_value=False)
    def test_skip_when_required_stack_not_deployed(self, mock_deployed):
        scenario = _make_scenario(
            requires={"stacks": ["data", "compute"]},
            steps=[],
        )
        runner = self._runner()
        with pytest.raises(pytest.skip.Exception):
            runner.run(scenario)

    # --- failing assertion raises AssertionError ---

    @patch("tests.scenarios.runner.stack_deployed", return_value=True)
    @patch("tests.scenarios.runner._resolve_arn", return_value="arn:aws:lambda:us-east-1:123:function:fake")
    @patch("tests.scenarios.runner._invoke_lambda")
    def test_failing_assertion_raises(self, mock_invoke, mock_arn, mock_deployed):
        mock_invoke.return_value = {"status": "error", "results": []}
        scenario = _make_scenario(
            requires={"stacks": ["data"]},
            steps=[
                {
                    "id": "search",
                    "tool": "roda_search",
                    "stack": "data",
                    "input": {},
                    "assert": [{"path": "results", "op": "exists"}],
                }
            ],
        )
        runner = self._runner()
        with pytest.raises(AssertionError):
            runner.run(scenario)

    # --- error key in Lambda response caught by assertion ---

    @patch("tests.scenarios.runner.stack_deployed", return_value=True)
    @patch("tests.scenarios.runner._resolve_arn", return_value="arn:aws:lambda:us-east-1:123:function:fake")
    @patch("tests.scenarios.runner._invoke_lambda")
    def test_error_key_in_response_caught_by_eq_assertion(
        self, mock_invoke, mock_arn, mock_deployed
    ):
        mock_invoke.return_value = {"error": "ThrottlingException", "message": "Rate exceeded"}

        scenario = _make_scenario(
            requires={"stacks": ["data"]},
            steps=[
                {
                    "id": "search",
                    "tool": "roda_search",
                    "stack": "data",
                    "input": {},
                    "assert": [
                        # This assertion expects "created" but gets "ThrottlingException"
                        {"path": "error", "op": "eq", "value": "ThrottlingException"}
                    ],
                }
            ],
        )
        runner = self._runner()
        # The assertion matches the error field value — should NOT raise
        runner.run(scenario)

    @patch("tests.scenarios.runner.stack_deployed", return_value=True)
    @patch("tests.scenarios.runner._resolve_arn", return_value="arn:aws:lambda:us-east-1:123:function:fake")
    @patch("tests.scenarios.runner._invoke_lambda")
    def test_error_key_in_response_fails_exists_assertion_when_no_results(
        self, mock_invoke, mock_arn, mock_deployed
    ):
        mock_invoke.return_value = {"error": "ServiceUnavailable", "results": []}

        scenario = _make_scenario(
            requires={"stacks": ["data"]},
            steps=[
                {
                    "id": "search",
                    "tool": "roda_search",
                    "stack": "data",
                    "input": {},
                    "assert": [{"path": "results", "op": "exists"}],
                }
            ],
        )
        runner = self._runner()
        with pytest.raises(AssertionError):
            runner.run(scenario)

    # --- scenario with no required stacks always runs ---

    @patch("tests.scenarios.runner.stack_deployed")
    @patch("tests.scenarios.runner._resolve_arn", return_value="arn:fake")
    @patch("tests.scenarios.runner._invoke_lambda", return_value={"ok": True})
    def test_no_required_stacks_skips_stack_check(
        self, mock_invoke, mock_arn, mock_deployed
    ):
        scenario = _make_scenario(
            requires={},  # no stacks key
            steps=[
                {
                    "id": "s1",
                    "tool": "some_tool",
                    "stack": "data",
                    "input": {},
                    "assert": [],
                }
            ],
        )
        runner = self._runner()
        runner.run(scenario)
        mock_deployed.assert_not_called()

    # --- ARN resolution failure skips step ---

    @patch("tests.scenarios.runner.stack_deployed", return_value=True)
    @patch("tests.scenarios.runner._resolve_arn", return_value=None)
    def test_skip_when_arn_cannot_be_resolved(self, mock_arn, mock_deployed):
        scenario = _make_scenario(
            requires={"stacks": ["data"]},
            steps=[
                {
                    "id": "search",
                    "tool": "roda_search",
                    "stack": "data",
                    "input": {},
                    "assert": [],
                }
            ],
        )
        runner = self._runner()
        with pytest.raises(pytest.skip.Exception):
            runner.run(scenario)

    # --- step results are accumulated across steps ---

    @patch("tests.scenarios.runner.stack_deployed", return_value=True)
    @patch("tests.scenarios.runner._resolve_arn", return_value="arn:fake")
    @patch("tests.scenarios.runner._invoke_lambda")
    def test_step_results_accumulated_across_three_steps(
        self, mock_invoke, mock_arn, mock_deployed
    ):
        mock_invoke.side_effect = [
            {"results": [{"dataset_id": "ds-1"}], "total": 1},
            {"status": "created", "source_uri": "s3://b/ds-1/"},
            {"job_id": "j-999", "estimated_cost_usd": 0.05},
        ]

        scenario = _make_scenario(
            requires={"stacks": ["data", "compute"]},
            steps=[
                {"id": "search", "tool": "roda_search", "stack": "data", "input": {}, "assert": []},
                {
                    "id": "load",
                    "tool": "roda_load",
                    "stack": "data",
                    "input": {"dataset_id": "{search.results[0].dataset_id}"},
                    "assert": [],
                },
                {
                    "id": "run",
                    "tool": "compute_run",
                    "stack": "compute",
                    "input": {"dataset_uri": "{load.source_uri}"},
                    "assert": [{"path": "job_id", "op": "exists"}],
                },
            ],
        )
        runner = self._runner()
        runner.run(scenario)

        assert mock_invoke.call_count == 3
        run_payload = mock_invoke.call_args_list[2][0][1]
        assert run_payload["dataset_uri"] == "s3://b/ds-1/"


# ---------------------------------------------------------------------------
# 5. discover_scenarios — validates real examples/ directory
# ---------------------------------------------------------------------------

class TestDiscoverScenarios:
    def test_discovers_at_least_11_scenarios(self):
        examples_root = (
            Path(__file__).parent.parent.parent / "examples"
        )
        scenarios = discover_scenarios(root=examples_root)

        assert len(scenarios) >= 11, (
            f"Expected at least 11 scenarios, found {len(scenarios)}"
        )

        for s in scenarios:
            assert s.name, f"Scenario at {s.path} has empty name"
            assert s.category, f"Scenario '{s.name}' has empty category"
            assert isinstance(s.steps, list) and len(s.steps) > 0, (
                f"Scenario '{s.name}' has no steps"
            )
            assert isinstance(s.requires, dict), (
                f"Scenario '{s.name}' requires is not a dict"
            )

    def test_each_scenario_has_valid_path(self):
        examples_root = Path(__file__).parent.parent.parent / "examples"
        scenarios = discover_scenarios(root=examples_root)
        for s in scenarios:
            assert s.path.exists(), f"Scenario path does not exist: {s.path}"
            assert s.path.name == "scenario.yaml"

    def test_scenarios_span_both_categories(self):
        examples_root = Path(__file__).parent.parent.parent / "examples"
        scenarios = discover_scenarios(root=examples_root)
        categories = {s.category for s in scenarios}
        assert "academic-research" in categories
        assert "institutional-analytics" in categories
