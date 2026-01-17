"""Tests for overlap prevention models."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.models.cron_task import CronTask, OverlapPolicy, HttpMethod
from app.models.task_chain import TaskChain, TriggerType
from app.models.task_queue import TaskQueue
from app.models.execution import Execution


class TestOverlapPolicyEnum:
    """Tests for OverlapPolicy enum."""

    def test_overlap_policy_values(self):
        """Test OverlapPolicy enum values."""
        assert OverlapPolicy.ALLOW.value == "allow"
        assert OverlapPolicy.SKIP.value == "skip"
        assert OverlapPolicy.QUEUE.value == "queue"

    def test_overlap_policy_is_string_enum(self):
        """Test OverlapPolicy is a string enum."""
        assert isinstance(OverlapPolicy.ALLOW, str)
        assert OverlapPolicy.ALLOW == "allow"


class TestCronTaskOverlapFields:
    """Tests for CronTask overlap prevention fields."""

    def test_cron_task_default_overlap_policy(self):
        """Test CronTask default overlap policy."""
        task = CronTask(
            workspace_id=uuid4(),
            name="Test Task",
            url="https://example.com",
            schedule="0 * * * *",
        )

        assert task.overlap_policy == OverlapPolicy.ALLOW
        assert task.max_instances == 1
        assert task.max_queue_size == 10
        assert task.execution_timeout is None
        assert task.running_instances == 0

    def test_cron_task_custom_overlap_settings(self):
        """Test CronTask with custom overlap settings."""
        task = CronTask(
            workspace_id=uuid4(),
            name="Test Task",
            url="https://example.com",
            schedule="0 * * * *",
            overlap_policy=OverlapPolicy.SKIP,
            max_instances=3,
            max_queue_size=50,
            execution_timeout=3600,
            running_instances=1,
        )

        assert task.overlap_policy == OverlapPolicy.SKIP
        assert task.max_instances == 3
        assert task.max_queue_size == 50
        assert task.execution_timeout == 3600
        assert task.running_instances == 1


class TestTaskChainOverlapFields:
    """Tests for TaskChain overlap prevention fields."""

    def test_task_chain_default_overlap_policy(self):
        """Test TaskChain default overlap policy."""
        chain = TaskChain(
            workspace_id=uuid4(),
            name="Test Chain",
        )

        assert chain.overlap_policy == OverlapPolicy.ALLOW
        assert chain.max_instances == 1
        assert chain.max_queue_size == 10
        assert chain.execution_timeout is None
        assert chain.running_instances == 0

    def test_task_chain_custom_overlap_settings(self):
        """Test TaskChain with custom overlap settings."""
        chain = TaskChain(
            workspace_id=uuid4(),
            name="Test Chain",
            overlap_policy=OverlapPolicy.QUEUE,
            max_instances=2,
            max_queue_size=20,
            execution_timeout=7200,
            running_instances=1,
        )

        assert chain.overlap_policy == OverlapPolicy.QUEUE
        assert chain.max_instances == 2
        assert chain.max_queue_size == 20
        assert chain.execution_timeout == 7200
        assert chain.running_instances == 1


class TestTaskQueueModel:
    """Tests for TaskQueue model."""

    def test_task_queue_creation(self):
        """Test TaskQueue model creation."""
        workspace_id = uuid4()
        task_id = uuid4()

        queue_item = TaskQueue(
            workspace_id=workspace_id,
            task_type="cron",
            task_id=task_id,
            task_name="Test Task",
            priority=0,
            retry_attempt=0,
            initial_variables={"key": "value"},
        )

        assert queue_item.workspace_id == workspace_id
        assert queue_item.task_type == "cron"
        assert queue_item.task_id == task_id
        assert queue_item.task_name == "Test Task"
        assert queue_item.priority == 0
        assert queue_item.retry_attempt == 0
        assert queue_item.initial_variables == {"key": "value"}

    def test_task_queue_defaults(self):
        """Test TaskQueue default values."""
        queue_item = TaskQueue(
            workspace_id=uuid4(),
            task_type="chain",
            task_id=uuid4(),
        )

        assert queue_item.task_name is None
        assert queue_item.priority == 0
        assert queue_item.retry_attempt == 0
        assert queue_item.scheduled_for is None

    def test_task_queue_with_priority(self):
        """Test TaskQueue with priority."""
        queue_item = TaskQueue(
            workspace_id=uuid4(),
            task_type="cron",
            task_id=uuid4(),
            priority=5,
        )

        assert queue_item.priority == 5


class TestExecutionSkippedReason:
    """Tests for Execution skipped_reason field."""

    def test_execution_default_skipped_reason(self):
        """Test Execution default skipped_reason is None."""
        execution = Execution(
            workspace_id=uuid4(),
            task_type="cron",
            task_id=uuid4(),
            status="success",
            started_at=datetime.utcnow(),
            request_url="https://example.com",
            request_method=HttpMethod.GET,
        )

        assert execution.skipped_reason is None

    def test_execution_with_skipped_reason(self):
        """Test Execution with skipped_reason."""
        execution = Execution(
            workspace_id=uuid4(),
            task_type="cron",
            task_id=uuid4(),
            status="success",
            started_at=datetime.utcnow(),
            request_url="https://example.com",
            request_method=HttpMethod.GET,
            skipped_reason="overlap_skipped",
        )

        assert execution.skipped_reason == "overlap_skipped"
