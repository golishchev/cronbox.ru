"""Chain executor service for executing task chains."""

import json
import re
from datetime import datetime
from typing import Any

import structlog
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

from app.core.url_validator import sanitize_url_for_logging
from app.models.chain_execution import StepStatus
from app.models.task_chain import ChainStatus, ChainStep, TaskChain

logger = structlog.get_logger()

# Variable placeholder pattern: {{variable_name}}
VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class VariableSubstitutionError(Exception):
    """Error during variable substitution."""

    pass


class ConditionEvaluationError(Exception):
    """Error during condition evaluation."""

    pass


def substitute_variables(template: str, variables: dict[str, Any]) -> str:
    """Substitute {{variable}} placeholders in a string.

    Args:
        template: String containing {{variable}} placeholders
        variables: Dict of variable_name -> value

    Returns:
        String with variables substituted

    Raises:
        VariableSubstitutionError: If a required variable is missing
    """
    if not template:
        return template

    def replace_match(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name not in variables:
            raise VariableSubstitutionError(f"Variable '{var_name}' not found")
        value = variables[var_name]
        # Convert to string if not already
        return str(value) if value is not None else ""

    return VARIABLE_PATTERN.sub(replace_match, template)


def substitute_variables_in_dict(data: dict[str, str], variables: dict[str, Any]) -> dict[str, str]:
    """Substitute variables in all values of a dict."""
    return {key: substitute_variables(value, variables) for key, value in data.items()}


def extract_variable_from_jsonpath(data: dict | list, jsonpath_expr: str) -> Any | None:
    """Extract a value from JSON data using JSONPath.

    Args:
        data: JSON data (dict or list)
        jsonpath_expr: JSONPath expression (e.g., "$.data.id")

    Returns:
        Extracted value or None if not found
    """
    try:
        expr = jsonpath_parse(jsonpath_expr)
        matches = expr.find(data)
        if matches:
            return matches[0].value
        return None
    except JsonPathParserError as e:
        logger.warning(
            "Invalid JSONPath expression",
            jsonpath=jsonpath_expr,
            error=str(e),
        )
        return None
    except Exception as e:
        logger.warning(
            "JSONPath extraction failed",
            jsonpath=jsonpath_expr,
            error=str(e),
        )
        return None


def extract_variables_from_response(
    response_body: str | None,
    extract_config: dict[str, str],
) -> dict[str, Any]:
    """Extract variables from response body using JSONPath expressions.

    Args:
        response_body: JSON response body string
        extract_config: Dict of variable_name -> JSONPath expression

    Returns:
        Dict of extracted variables
    """
    if not response_body or not extract_config:
        return {}

    try:
        data = json.loads(response_body)
    except json.JSONDecodeError:
        logger.warning("Response body is not valid JSON for variable extraction")
        return {}

    extracted = {}
    for var_name, jsonpath_expr in extract_config.items():
        value = extract_variable_from_jsonpath(data, jsonpath_expr)
        if value is not None:
            extracted[var_name] = value
            logger.debug(
                "Extracted variable",
                variable=var_name,
                jsonpath=jsonpath_expr,
                value=str(value)[:100],  # Limit log length
            )

    return extracted


def evaluate_condition(
    condition: dict,
    previous_status_code: int | None,
    previous_response_body: str | None,
) -> tuple[bool, str]:
    """Evaluate a step condition.

    Args:
        condition: Condition config dict
        previous_status_code: Status code from previous step
        previous_response_body: Response body from previous step

    Returns:
        Tuple of (condition_met: bool, details: str)
    """
    if not condition:
        return True, "No condition specified"

    operator = condition.get("operator", "").lower()
    field = condition.get("field")
    expected_value = condition.get("value")

    try:
        # Status code conditions
        if operator == "status_code_in":
            if not isinstance(expected_value, list):
                expected_value = [expected_value]
            met = previous_status_code in expected_value
            return met, f"Status code {previous_status_code} {'in' if met else 'not in'} {expected_value}"

        elif operator == "status_code_not_in":
            if not isinstance(expected_value, list):
                expected_value = [expected_value]
            met = previous_status_code not in expected_value
            return met, f"Status code {previous_status_code} {'not in' if met else 'in'} {expected_value}"

        elif operator == "status_code_equals":
            met = previous_status_code == expected_value
            return met, f"Status code {previous_status_code} {'==' if met else '!='} {expected_value}"

        # Value comparison conditions (require field)
        elif operator in ("equals", "not_equals", "contains", "not_contains", "regex"):
            if not field:
                return False, f"Operator '{operator}' requires 'field' parameter"

            if not previous_response_body:
                return False, "No response body to evaluate"

            try:
                data = json.loads(previous_response_body)
            except json.JSONDecodeError:
                return False, "Response body is not valid JSON"

            actual_value = extract_variable_from_jsonpath(data, field)

            if operator == "equals":
                met = actual_value == expected_value
                return met, f"{field} = {actual_value} {'==' if met else '!='} {expected_value}"

            elif operator == "not_equals":
                met = actual_value != expected_value
                return met, f"{field} = {actual_value} {'!=' if met else '=='} {expected_value}"

            elif operator == "contains":
                met = str(expected_value) in str(actual_value) if actual_value else False
                return met, f"{field} = {actual_value} {'contains' if met else 'does not contain'} {expected_value}"

            elif operator == "not_contains":
                met = str(expected_value) not in str(actual_value) if actual_value else True
                return met, f"{field} = {actual_value} {'does not contain' if met else 'contains'} {expected_value}"

            elif operator == "regex":
                try:
                    pattern = re.compile(str(expected_value))
                    met = bool(pattern.search(str(actual_value))) if actual_value else False
                    return (
                        met,
                        f"{field} = {actual_value} {'matches' if met else 'does not match'} regex {expected_value}",
                    )
                except re.error as e:
                    return False, f"Invalid regex pattern: {e}"

            # Should not reach here, but satisfy mypy
            return False, f"Unknown field operator: {operator}"

        # Existence conditions
        elif operator == "exists":
            if not field:
                return False, "Operator 'exists' requires 'field' parameter"
            if not previous_response_body:
                return False, "No response body to evaluate"
            try:
                data = json.loads(previous_response_body)
                actual_value = extract_variable_from_jsonpath(data, field)
                met = actual_value is not None
                return met, f"{field} {'exists' if met else 'does not exist'}"
            except json.JSONDecodeError:
                return False, "Response body is not valid JSON"

        elif operator == "not_exists":
            if not field:
                return False, "Operator 'not_exists' requires 'field' parameter"
            if not previous_response_body:
                return True, "No response body - field does not exist"
            try:
                data = json.loads(previous_response_body)
                actual_value = extract_variable_from_jsonpath(data, field)
                met = actual_value is None
                return met, f"{field} {'does not exist' if met else 'exists'}"
            except json.JSONDecodeError:
                return True, "Response body is not valid JSON - field does not exist"

        else:
            return False, f"Unknown condition operator: {operator}"

    except Exception as e:
        logger.error("Condition evaluation error", error=str(e), condition=condition)
        return False, f"Evaluation error: {str(e)}"


def determine_chain_status(completed: int, failed: int, skipped: int, total: int, stop_on_failure: bool) -> ChainStatus:
    """Determine overall chain status based on step results.

    Args:
        completed: Number of successfully completed steps
        failed: Number of failed steps
        skipped: Number of skipped steps
        total: Total number of steps
        stop_on_failure: Whether chain stops on first failure

    Returns:
        ChainStatus
    """
    if completed == total:
        return ChainStatus.SUCCESS
    elif failed > 0:
        if completed > 0:
            return ChainStatus.PARTIAL
        return ChainStatus.FAILED
    elif skipped == total:
        return ChainStatus.FAILED  # All steps skipped = failure
    else:
        return ChainStatus.PARTIAL


def prepare_step_request(step: ChainStep, variables: dict[str, Any]) -> tuple[str, dict[str, str], str | None]:
    """Prepare step request with variable substitution.

    Args:
        step: The chain step
        variables: Current accumulated variables

    Returns:
        Tuple of (url, headers, body)

    Raises:
        VariableSubstitutionError: If variable substitution fails
    """
    url = substitute_variables(step.url, variables)
    headers = substitute_variables_in_dict(step.headers or {}, variables)
    body = substitute_variables(step.body, variables) if step.body else None

    return url, headers, body


class ChainExecutionContext:
    """Context for chain execution."""

    def __init__(
        self,
        chain: TaskChain,
        initial_variables: dict[str, Any] | None = None,
    ):
        self.chain = chain
        self.variables: dict[str, Any] = initial_variables.copy() if initial_variables else {}
        self.completed_steps = 0
        self.failed_steps = 0
        self.skipped_steps = 0
        self.previous_status_code: int | None = None
        self.previous_response_body: str | None = None
        self.error_message: str | None = None
        self.started_at = datetime.utcnow()

    def update_from_step_result(
        self,
        status: StepStatus,
        status_code: int | None = None,
        response_body: str | None = None,
        extracted_variables: dict[str, Any] | None = None,
    ) -> None:
        """Update context after step execution."""
        if status == StepStatus.SUCCESS:
            self.completed_steps += 1
        elif status == StepStatus.FAILED:
            self.failed_steps += 1
        elif status == StepStatus.SKIPPED:
            self.skipped_steps += 1

        self.previous_status_code = status_code
        self.previous_response_body = response_body

        if extracted_variables:
            self.variables.update(extracted_variables)

    def should_continue(self, step: ChainStep, step_status: StepStatus) -> bool:
        """Check if chain execution should continue after this step."""
        if step_status == StepStatus.FAILED:
            # Continue if step allows it or chain doesn't stop on failure
            return step.continue_on_failure or not self.chain.stop_on_failure
        return True

    def get_final_status(self, total_steps: int) -> ChainStatus:
        """Get final chain status."""
        return determine_chain_status(
            completed=self.completed_steps,
            failed=self.failed_steps,
            skipped=self.skipped_steps,
            total=total_steps,
            stop_on_failure=self.chain.stop_on_failure,
        )


def log_chain_execution_start(chain: TaskChain, variables: dict[str, Any]) -> None:
    """Log chain execution start."""
    logger.info(
        "Starting chain execution",
        chain_id=str(chain.id),
        chain_name=chain.name,
        steps_count=len(chain.steps) if chain.steps else 0,
        initial_variables=list(variables.keys()),
    )


def log_step_execution(
    chain: TaskChain,
    step: ChainStep,
    step_index: int,
    url: str,
    status: StepStatus,
    duration_ms: int | None = None,
    error: str | None = None,
) -> None:
    """Log step execution."""
    log_data = {
        "chain_id": str(chain.id),
        "step_id": str(step.id),
        "step_order": step_index,
        "step_name": step.name,
        "url": sanitize_url_for_logging(url),
        "method": step.method.value,
        "status": status.value,
    }
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    if error:
        log_data["error"] = error[:200]  # Limit log length

    logger.info("Step execution completed", **log_data)


def log_chain_execution_complete(
    chain: TaskChain,
    status: ChainStatus,
    completed: int,
    failed: int,
    skipped: int,
    duration_ms: int,
) -> None:
    """Log chain execution completion."""
    logger.info(
        "Chain execution completed",
        chain_id=str(chain.id),
        chain_name=chain.name,
        status=status.value,
        completed_steps=completed,
        failed_steps=failed,
        skipped_steps=skipped,
        duration_ms=duration_ms,
    )
