"""Unit tests for chain executor service."""
import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.models.chain_execution import StepStatus
from app.models.cron_task import HttpMethod
from app.models.task_chain import ChainStatus
from app.services.chain_executor import (
    ChainExecutionContext,
    VariableSubstitutionError,
    determine_chain_status,
    evaluate_condition,
    extract_variable_from_jsonpath,
    extract_variables_from_response,
    log_chain_execution_complete,
    log_chain_execution_start,
    log_step_execution,
    prepare_step_request,
    substitute_variables,
    substitute_variables_in_dict,
)


class TestSubstituteVariables:
    """Tests for substitute_variables function."""

    def test_simple_substitution(self):
        """Test simple variable substitution."""
        template = "Hello, {{name}}!"
        variables = {"name": "World"}
        result = substitute_variables(template, variables)
        assert result == "Hello, World!"

    def test_multiple_substitutions(self):
        """Test multiple variable substitutions."""
        template = "{{greeting}}, {{name}}! Today is {{day}}."
        variables = {"greeting": "Hello", "name": "Alice", "day": "Monday"}
        result = substitute_variables(template, variables)
        assert result == "Hello, Alice! Today is Monday."

    def test_empty_template(self):
        """Test with empty template."""
        result = substitute_variables("", {"name": "test"})
        assert result == ""

    def test_none_template(self):
        """Test with None template."""
        result = substitute_variables(None, {"name": "test"})
        assert result is None

    def test_no_variables_in_template(self):
        """Test template without variables."""
        template = "No variables here"
        result = substitute_variables(template, {"unused": "value"})
        assert result == "No variables here"

    def test_missing_variable_raises_error(self):
        """Test that missing variable raises error."""
        template = "Hello, {{name}}!"
        variables = {}
        with pytest.raises(VariableSubstitutionError) as exc_info:
            substitute_variables(template, variables)
        assert "Variable 'name' not found" in str(exc_info.value)

    def test_none_value_becomes_empty_string(self):
        """Test that None value becomes empty string."""
        template = "Value: {{value}}"
        variables = {"value": None}
        result = substitute_variables(template, variables)
        assert result == "Value: "

    def test_numeric_value(self):
        """Test numeric value substitution."""
        template = "Count: {{count}}"
        variables = {"count": 42}
        result = substitute_variables(template, variables)
        assert result == "Count: 42"

    def test_url_substitution(self):
        """Test URL with variable substitution."""
        template = "https://api.example.com/users/{{user_id}}/posts"
        variables = {"user_id": "12345"}
        result = substitute_variables(template, variables)
        assert result == "https://api.example.com/users/12345/posts"


class TestSubstituteVariablesInDict:
    """Tests for substitute_variables_in_dict function."""

    def test_simple_dict_substitution(self):
        """Test simple dict value substitution."""
        data = {"Authorization": "Bearer {{token}}"}
        variables = {"token": "abc123"}
        result = substitute_variables_in_dict(data, variables)
        assert result == {"Authorization": "Bearer abc123"}

    def test_multiple_values(self):
        """Test multiple values in dict."""
        data = {
            "Authorization": "Bearer {{token}}",
            "X-User-Id": "{{user_id}}",
        }
        variables = {"token": "abc123", "user_id": "42"}
        result = substitute_variables_in_dict(data, variables)
        assert result == {
            "Authorization": "Bearer abc123",
            "X-User-Id": "42",
        }

    def test_empty_dict(self):
        """Test empty dict."""
        result = substitute_variables_in_dict({}, {"key": "value"})
        assert result == {}


class TestExtractVariableFromJsonpath:
    """Tests for extract_variable_from_jsonpath function."""

    def test_simple_extraction(self):
        """Test simple JSONPath extraction."""
        data = {"user": {"id": 123, "name": "Alice"}}
        result = extract_variable_from_jsonpath(data, "$.user.id")
        assert result == 123

    def test_nested_extraction(self):
        """Test nested JSONPath extraction."""
        data = {"data": {"response": {"items": [{"id": 1}, {"id": 2}]}}}
        result = extract_variable_from_jsonpath(data, "$.data.response.items[0].id")
        assert result == 1

    def test_array_extraction(self):
        """Test array extraction."""
        data = {"items": [1, 2, 3]}
        result = extract_variable_from_jsonpath(data, "$.items[1]")
        assert result == 2

    def test_not_found_returns_none(self):
        """Test non-existent path returns None."""
        data = {"user": {"id": 123}}
        result = extract_variable_from_jsonpath(data, "$.user.email")
        assert result is None

    def test_invalid_jsonpath_returns_none(self):
        """Test invalid JSONPath returns None."""
        data = {"user": {"id": 123}}
        result = extract_variable_from_jsonpath(data, "invalid[[[")
        assert result is None

    def test_root_extraction(self):
        """Test root element extraction."""
        data = {"value": "test"}
        result = extract_variable_from_jsonpath(data, "$.value")
        assert result == "test"


class TestExtractVariablesFromResponse:
    """Tests for extract_variables_from_response function."""

    def test_extract_multiple_variables(self):
        """Test extracting multiple variables."""
        response_body = json.dumps({
            "data": {"id": 123, "token": "abc"},
            "status": "success",
        })
        extract_config = {
            "user_id": "$.data.id",
            "auth_token": "$.data.token",
        }
        result = extract_variables_from_response(response_body, extract_config)
        assert result == {"user_id": 123, "auth_token": "abc"}

    def test_empty_response_body(self):
        """Test empty response body."""
        result = extract_variables_from_response("", {"var": "$.value"})
        assert result == {}

    def test_none_response_body(self):
        """Test None response body."""
        result = extract_variables_from_response(None, {"var": "$.value"})
        assert result == {}

    def test_empty_extract_config(self):
        """Test empty extract config."""
        result = extract_variables_from_response('{"data": 123}', {})
        assert result == {}

    def test_invalid_json_response(self):
        """Test invalid JSON response."""
        result = extract_variables_from_response("not json", {"var": "$.value"})
        assert result == {}

    def test_partial_extraction(self):
        """Test partial variable extraction (some not found)."""
        response_body = json.dumps({"data": {"id": 123}})
        extract_config = {
            "found": "$.data.id",
            "not_found": "$.data.email",
        }
        result = extract_variables_from_response(response_body, extract_config)
        assert result == {"found": 123}


class TestEvaluateCondition:
    """Tests for evaluate_condition function."""

    def test_no_condition(self):
        """Test with no condition (always true)."""
        result, details = evaluate_condition({}, 200, None)
        assert result is True
        assert "No condition" in details

    def test_none_condition(self):
        """Test with None condition."""
        result, details = evaluate_condition(None, 200, None)
        assert result is True

    def test_status_code_equals(self):
        """Test status code equals."""
        condition = {"operator": "status_code_equals", "value": 200}
        result, details = evaluate_condition(condition, 200, None)
        assert result is True
        assert "200" in details and "==" in details

    def test_status_code_equals_failure(self):
        """Test status code equals failure."""
        condition = {"operator": "status_code_equals", "value": 200}
        result, details = evaluate_condition(condition, 404, None)
        assert result is False

    def test_status_code_in(self):
        """Test status code in list."""
        condition = {"operator": "status_code_in", "value": [200, 201, 204]}
        result, details = evaluate_condition(condition, 201, None)
        assert result is True

    def test_status_code_in_single_value(self):
        """Test status code in with single value."""
        condition = {"operator": "status_code_in", "value": 200}
        result, details = evaluate_condition(condition, 200, None)
        assert result is True

    def test_status_code_not_in(self):
        """Test status code not in list."""
        condition = {"operator": "status_code_not_in", "value": [400, 401, 403, 500]}
        result, details = evaluate_condition(condition, 200, None)
        assert result is True

    def test_status_code_not_in_failure(self):
        """Test status code not in failure."""
        condition = {"operator": "status_code_not_in", "value": [400, 401, 403]}
        result, details = evaluate_condition(condition, 401, None)
        assert result is False

    def test_equals_value(self):
        """Test equals condition."""
        condition = {"operator": "equals", "field": "$.status", "value": "success"}
        response = json.dumps({"status": "success"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is True

    def test_equals_value_failure(self):
        """Test equals condition failure."""
        condition = {"operator": "equals", "field": "$.status", "value": "success"}
        response = json.dumps({"status": "error"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is False

    def test_not_equals_value(self):
        """Test not equals condition."""
        condition = {"operator": "not_equals", "field": "$.status", "value": "error"}
        response = json.dumps({"status": "success"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is True

    def test_contains_value(self):
        """Test contains condition."""
        condition = {"operator": "contains", "field": "$.message", "value": "success"}
        response = json.dumps({"message": "Operation was a success!"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is True

    def test_not_contains_value(self):
        """Test not contains condition."""
        condition = {"operator": "not_contains", "field": "$.message", "value": "error"}
        response = json.dumps({"message": "All good"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is True

    def test_regex_match(self):
        """Test regex condition."""
        condition = {"operator": "regex", "field": "$.code", "value": r"^OK-\d+$"}
        response = json.dumps({"code": "OK-123"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is True

    def test_regex_no_match(self):
        """Test regex condition no match."""
        condition = {"operator": "regex", "field": "$.code", "value": r"^OK-\d+$"}
        response = json.dumps({"code": "ERROR-123"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is False

    def test_regex_invalid_pattern(self):
        """Test regex with invalid pattern."""
        condition = {"operator": "regex", "field": "$.code", "value": "[[["}
        response = json.dumps({"code": "test"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is False
        assert "Invalid regex" in details

    def test_exists_true(self):
        """Test exists condition."""
        condition = {"operator": "exists", "field": "$.data.id"}
        response = json.dumps({"data": {"id": 123}})
        result, details = evaluate_condition(condition, 200, response)
        assert result is True
        assert "exists" in details

    def test_exists_false(self):
        """Test exists condition failure."""
        condition = {"operator": "exists", "field": "$.data.email"}
        response = json.dumps({"data": {"id": 123}})
        result, details = evaluate_condition(condition, 200, response)
        assert result is False

    def test_not_exists_true(self):
        """Test not exists condition."""
        condition = {"operator": "not_exists", "field": "$.data.email"}
        response = json.dumps({"data": {"id": 123}})
        result, details = evaluate_condition(condition, 200, response)
        assert result is True

    def test_not_exists_no_response(self):
        """Test not exists with no response body."""
        condition = {"operator": "not_exists", "field": "$.data.id"}
        result, details = evaluate_condition(condition, 200, None)
        assert result is True
        assert "No response body" in details

    def test_exists_no_response(self):
        """Test exists with no response body."""
        condition = {"operator": "exists", "field": "$.data.id"}
        result, details = evaluate_condition(condition, 200, None)
        assert result is False

    def test_operator_requires_field(self):
        """Test operator requiring field without field."""
        condition = {"operator": "equals", "value": "test"}
        result, details = evaluate_condition(condition, 200, '{"data": "test"}')
        assert result is False
        assert "requires 'field'" in details

    def test_value_operator_no_response(self):
        """Test value operator without response body."""
        condition = {"operator": "equals", "field": "$.data", "value": "test"}
        result, details = evaluate_condition(condition, 200, None)
        assert result is False
        assert "No response body" in details

    def test_value_operator_invalid_json(self):
        """Test value operator with invalid JSON response."""
        condition = {"operator": "equals", "field": "$.data", "value": "test"}
        result, details = evaluate_condition(condition, 200, "not json")
        assert result is False
        assert "not valid JSON" in details

    def test_unknown_operator(self):
        """Test unknown operator."""
        condition = {"operator": "unknown_operator"}
        result, details = evaluate_condition(condition, 200, None)
        assert result is False
        assert "Unknown condition operator" in details

    def test_exists_invalid_json(self):
        """Test exists with invalid JSON."""
        condition = {"operator": "exists", "field": "$.data"}
        result, details = evaluate_condition(condition, 200, "not json")
        assert result is False
        assert "not valid JSON" in details

    def test_not_exists_invalid_json(self):
        """Test not_exists with invalid JSON."""
        condition = {"operator": "not_exists", "field": "$.data"}
        result, details = evaluate_condition(condition, 200, "not json")
        assert result is True
        assert "not valid JSON" in details

    def test_contains_none_value(self):
        """Test contains with None actual value."""
        condition = {"operator": "contains", "field": "$.missing", "value": "test"}
        response = json.dumps({"data": "test"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is False

    def test_not_contains_none_value(self):
        """Test not_contains with None actual value."""
        condition = {"operator": "not_contains", "field": "$.missing", "value": "test"}
        response = json.dumps({"data": "test"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is True

    def test_regex_none_value(self):
        """Test regex with None actual value."""
        condition = {"operator": "regex", "field": "$.missing", "value": r"\d+"}
        response = json.dumps({"data": "test"})
        result, details = evaluate_condition(condition, 200, response)
        assert result is False


class TestDetermineChainStatus:
    """Tests for determine_chain_status function."""

    def test_all_success(self):
        """Test all steps successful."""
        result = determine_chain_status(
            completed=5, failed=0, skipped=0, total=5, stop_on_failure=True
        )
        assert result == ChainStatus.SUCCESS

    def test_all_failed(self):
        """Test all steps failed."""
        result = determine_chain_status(
            completed=0, failed=5, skipped=0, total=5, stop_on_failure=True
        )
        assert result == ChainStatus.FAILED

    def test_partial_success(self):
        """Test partial success (some completed, some failed)."""
        result = determine_chain_status(
            completed=3, failed=2, skipped=0, total=5, stop_on_failure=False
        )
        assert result == ChainStatus.PARTIAL

    def test_all_skipped(self):
        """Test all steps skipped."""
        result = determine_chain_status(
            completed=0, failed=0, skipped=5, total=5, stop_on_failure=True
        )
        assert result == ChainStatus.FAILED

    def test_partial_with_skipped(self):
        """Test partial with some skipped."""
        result = determine_chain_status(
            completed=2, failed=0, skipped=3, total=5, stop_on_failure=True
        )
        assert result == ChainStatus.PARTIAL


class TestPrepareStepRequest:
    """Tests for prepare_step_request function."""

    def test_url_substitution(self):
        """Test URL variable substitution."""
        step = MagicMock()
        step.url = "https://api.example.com/users/{{user_id}}"
        step.headers = {"Authorization": "Bearer {{token}}"}
        step.body = '{"action": "{{action}}"}'

        variables = {"user_id": "123", "token": "abc", "action": "update"}
        url, headers, body = prepare_step_request(step, variables)

        assert url == "https://api.example.com/users/123"
        assert headers == {"Authorization": "Bearer abc"}
        assert body == '{"action": "update"}'

    def test_no_body(self):
        """Test step without body."""
        step = MagicMock()
        step.url = "https://api.example.com/test"
        step.headers = {}
        step.body = None

        url, headers, body = prepare_step_request(step, {})

        assert url == "https://api.example.com/test"
        assert headers == {}
        assert body is None

    def test_empty_headers(self):
        """Test step with empty headers (None)."""
        step = MagicMock()
        step.url = "https://api.example.com/test"
        step.headers = None
        step.body = None

        url, headers, body = prepare_step_request(step, {})

        assert headers == {}

    def test_missing_variable_raises(self):
        """Test that missing variable raises error."""
        step = MagicMock()
        step.url = "https://api.example.com/users/{{user_id}}"
        step.headers = {}
        step.body = None

        with pytest.raises(VariableSubstitutionError):
            prepare_step_request(step, {})


class TestChainExecutionContext:
    """Tests for ChainExecutionContext class."""

    def create_mock_chain(self, stop_on_failure: bool = True):
        """Create a mock chain."""
        chain = MagicMock()
        chain.id = "test-chain-id"
        chain.name = "Test Chain"
        chain.stop_on_failure = stop_on_failure
        chain.steps = []
        return chain

    def test_initialization(self):
        """Test context initialization."""
        chain = self.create_mock_chain()
        context = ChainExecutionContext(chain)

        assert context.chain == chain
        assert context.variables == {}
        assert context.completed_steps == 0
        assert context.failed_steps == 0
        assert context.skipped_steps == 0
        assert context.previous_status_code is None
        assert context.previous_response_body is None

    def test_initialization_with_variables(self):
        """Test context initialization with variables."""
        chain = self.create_mock_chain()
        initial_vars = {"key1": "value1", "key2": "value2"}
        context = ChainExecutionContext(chain, initial_vars)

        assert context.variables == {"key1": "value1", "key2": "value2"}
        # Ensure original dict is not modified
        initial_vars["key3"] = "value3"
        assert "key3" not in context.variables

    def test_update_from_step_result_success(self):
        """Test updating context after successful step."""
        chain = self.create_mock_chain()
        context = ChainExecutionContext(chain)

        context.update_from_step_result(
            status=StepStatus.SUCCESS,
            status_code=200,
            response_body='{"data": "test"}',
            extracted_variables={"new_var": "value"},
        )

        assert context.completed_steps == 1
        assert context.failed_steps == 0
        assert context.skipped_steps == 0
        assert context.previous_status_code == 200
        assert context.previous_response_body == '{"data": "test"}'
        assert context.variables == {"new_var": "value"}

    def test_update_from_step_result_failed(self):
        """Test updating context after failed step."""
        chain = self.create_mock_chain()
        context = ChainExecutionContext(chain)

        context.update_from_step_result(
            status=StepStatus.FAILED,
            status_code=500,
            response_body='{"error": "internal"}',
        )

        assert context.completed_steps == 0
        assert context.failed_steps == 1
        assert context.skipped_steps == 0

    def test_update_from_step_result_skipped(self):
        """Test updating context after skipped step."""
        chain = self.create_mock_chain()
        context = ChainExecutionContext(chain)

        context.update_from_step_result(status=StepStatus.SKIPPED)

        assert context.completed_steps == 0
        assert context.failed_steps == 0
        assert context.skipped_steps == 1

    def test_should_continue_after_success(self):
        """Test should_continue after successful step."""
        chain = self.create_mock_chain(stop_on_failure=True)
        context = ChainExecutionContext(chain)
        step = MagicMock()
        step.continue_on_failure = False

        assert context.should_continue(step, StepStatus.SUCCESS) is True

    def test_should_continue_after_failure_stop_on_failure(self):
        """Test should_continue after failure with stop_on_failure."""
        chain = self.create_mock_chain(stop_on_failure=True)
        context = ChainExecutionContext(chain)
        step = MagicMock()
        step.continue_on_failure = False

        assert context.should_continue(step, StepStatus.FAILED) is False

    def test_should_continue_after_failure_continue_on_failure(self):
        """Test should_continue after failure with continue_on_failure."""
        chain = self.create_mock_chain(stop_on_failure=True)
        context = ChainExecutionContext(chain)
        step = MagicMock()
        step.continue_on_failure = True

        assert context.should_continue(step, StepStatus.FAILED) is True

    def test_should_continue_after_failure_chain_no_stop(self):
        """Test should_continue after failure with chain not stopping."""
        chain = self.create_mock_chain(stop_on_failure=False)
        context = ChainExecutionContext(chain)
        step = MagicMock()
        step.continue_on_failure = False

        assert context.should_continue(step, StepStatus.FAILED) is True

    def test_get_final_status(self):
        """Test get_final_status."""
        chain = self.create_mock_chain()
        context = ChainExecutionContext(chain)
        context.completed_steps = 3
        context.failed_steps = 0
        context.skipped_steps = 0

        status = context.get_final_status(total_steps=3)
        assert status == ChainStatus.SUCCESS


class TestLoggingFunctions:
    """Tests for logging functions."""

    def test_log_chain_execution_start(self):
        """Test chain execution start logging."""
        chain = MagicMock()
        chain.id = "test-id"
        chain.name = "Test Chain"
        chain.steps = [MagicMock(), MagicMock()]

        # Should not raise
        log_chain_execution_start(chain, {"var1": "value1"})

    def test_log_step_execution(self):
        """Test step execution logging."""
        chain = MagicMock()
        chain.id = "test-id"

        step = MagicMock()
        step.id = "step-id"
        step.name = "Test Step"
        step.method = HttpMethod.GET

        # Should not raise
        log_step_execution(
            chain=chain,
            step=step,
            step_index=0,
            url="https://example.com",
            status=StepStatus.SUCCESS,
            duration_ms=100,
            error=None,
        )

    def test_log_step_execution_with_error(self):
        """Test step execution logging with error."""
        chain = MagicMock()
        chain.id = "test-id"

        step = MagicMock()
        step.id = "step-id"
        step.name = "Test Step"
        step.method = HttpMethod.POST

        # Should not raise
        log_step_execution(
            chain=chain,
            step=step,
            step_index=0,
            url="https://example.com",
            status=StepStatus.FAILED,
            duration_ms=50,
            error="Connection timeout",
        )

    def test_log_chain_execution_complete(self):
        """Test chain execution complete logging."""
        chain = MagicMock()
        chain.id = "test-id"
        chain.name = "Test Chain"

        # Should not raise
        log_chain_execution_complete(
            chain=chain,
            status=ChainStatus.SUCCESS,
            completed=5,
            failed=0,
            skipped=0,
            duration_ms=1000,
        )
