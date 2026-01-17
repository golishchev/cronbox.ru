"""Tests for overlap prevention schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.cron_task import OverlapPolicy


class TestCronTaskOverlapSchemas:
    """Tests for CronTask overlap prevention schemas."""

    def test_cron_task_base_default_overlap_policy(self):
        """Test default overlap policy is ALLOW."""
        from app.schemas.cron_task import CronTaskBase

        data = {
            "name": "Test Task",
            "url": "https://example.com/api",
            "schedule": "0 * * * *",
        }
        schema = CronTaskBase(**data)

        assert schema.overlap_policy == OverlapPolicy.ALLOW
        assert schema.max_instances == 1
        assert schema.max_queue_size == 10
        assert schema.execution_timeout is None

    def test_cron_task_base_custom_overlap_settings(self):
        """Test custom overlap settings."""
        from app.schemas.cron_task import CronTaskBase

        data = {
            "name": "Test Task",
            "url": "https://example.com/api",
            "schedule": "0 * * * *",
            "overlap_policy": OverlapPolicy.SKIP,
            "max_instances": 3,
            "max_queue_size": 50,
            "execution_timeout": 3600,
        }
        schema = CronTaskBase(**data)

        assert schema.overlap_policy == OverlapPolicy.SKIP
        assert schema.max_instances == 3
        assert schema.max_queue_size == 50
        assert schema.execution_timeout == 3600

    def test_cron_task_base_max_instances_validation(self):
        """Test max_instances validation."""
        from app.schemas.cron_task import CronTaskBase

        # Too low
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="0 * * * *",
                max_instances=0,
            )

        # Too high
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="0 * * * *",
                max_instances=11,
            )

    def test_cron_task_base_max_queue_size_validation(self):
        """Test max_queue_size validation."""
        from app.schemas.cron_task import CronTaskBase

        # Too low
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="0 * * * *",
                max_queue_size=0,
            )

        # Too high
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="0 * * * *",
                max_queue_size=101,
            )

    def test_cron_task_base_execution_timeout_validation(self):
        """Test execution_timeout validation."""
        from app.schemas.cron_task import CronTaskBase

        # Too low
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="0 * * * *",
                execution_timeout=59,
            )

        # Too high
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="0 * * * *",
                execution_timeout=86401,
            )

    def test_cron_task_update_overlap_fields(self):
        """Test CronTaskUpdate with overlap fields."""
        from app.schemas.cron_task import CronTaskUpdate

        data = {
            "overlap_policy": OverlapPolicy.QUEUE,
            "max_instances": 5,
        }
        schema = CronTaskUpdate(**data)

        assert schema.overlap_policy == OverlapPolicy.QUEUE
        assert schema.max_instances == 5

    def test_cron_task_response_overlap_fields(self):
        """Test CronTaskResponse includes overlap fields."""
        from app.schemas.cron_task import CronTaskResponse

        # Verify the model has the expected fields
        fields = CronTaskResponse.model_fields
        assert "overlap_policy" in fields
        assert "max_instances" in fields
        assert "max_queue_size" in fields
        assert "execution_timeout" in fields
        assert "running_instances" in fields


class TestTaskChainOverlapSchemas:
    """Tests for TaskChain overlap prevention schemas."""

    def test_task_chain_base_default_overlap_policy(self):
        """Test default overlap policy is ALLOW."""
        from app.schemas.task_chain import TaskChainBase

        data = {
            "name": "Test Chain",
        }
        schema = TaskChainBase(**data)

        assert schema.overlap_policy == OverlapPolicy.ALLOW
        assert schema.max_instances == 1
        assert schema.max_queue_size == 10
        assert schema.execution_timeout is None

    def test_task_chain_base_custom_overlap_settings(self):
        """Test custom overlap settings for chain."""
        from app.schemas.task_chain import TaskChainBase

        data = {
            "name": "Test Chain",
            "overlap_policy": OverlapPolicy.QUEUE,
            "max_instances": 2,
            "max_queue_size": 20,
            "execution_timeout": 7200,
        }
        schema = TaskChainBase(**data)

        assert schema.overlap_policy == OverlapPolicy.QUEUE
        assert schema.max_instances == 2
        assert schema.max_queue_size == 20
        assert schema.execution_timeout == 7200

    def test_task_chain_update_overlap_fields(self):
        """Test TaskChainUpdate with overlap fields."""
        from app.schemas.task_chain import TaskChainUpdate

        data = {
            "overlap_policy": OverlapPolicy.SKIP,
            "max_instances": 3,
        }
        schema = TaskChainUpdate(**data)

        assert schema.overlap_policy == OverlapPolicy.SKIP
        assert schema.max_instances == 3

    def test_task_chain_response_overlap_fields(self):
        """Test TaskChainResponse includes overlap fields."""
        from app.schemas.task_chain import TaskChainResponse

        fields = TaskChainResponse.model_fields
        assert "overlap_policy" in fields
        assert "max_instances" in fields
        assert "max_queue_size" in fields
        assert "execution_timeout" in fields
        assert "running_instances" in fields


class TestTaskQueueSchemas:
    """Tests for TaskQueue schemas."""

    def test_task_queue_response_model(self):
        """Test TaskQueueResponse model."""
        from app.schemas.task_queue import TaskQueueResponse

        fields = TaskQueueResponse.model_fields
        assert "id" in fields
        assert "workspace_id" in fields
        assert "task_type" in fields
        assert "task_id" in fields
        assert "task_name" in fields
        assert "priority" in fields
        assert "queued_at" in fields
        assert "retry_attempt" in fields
        assert "initial_variables" in fields

    def test_task_queue_list_response_model(self):
        """Test TaskQueueListResponse model."""
        from app.schemas.task_queue import TaskQueueListResponse

        fields = TaskQueueListResponse.model_fields
        assert "items" in fields
        assert "total" in fields

    def test_overlap_stats_response_model(self):
        """Test OverlapStatsResponse model."""
        from app.schemas.task_queue import OverlapStatsResponse

        data = {
            "executions_skipped": 10,
            "executions_queued": 20,
            "current_queue_size": 5,
            "overlap_rate": 33.33,
        }
        schema = OverlapStatsResponse(**data)

        assert schema.executions_skipped == 10
        assert schema.executions_queued == 20
        assert schema.current_queue_size == 5
        assert schema.overlap_rate == 33.33

    def test_task_overlap_status_response_model(self):
        """Test TaskOverlapStatusResponse model."""
        from app.schemas.task_queue import TaskOverlapStatusResponse

        data = {
            "task_id": uuid4(),
            "task_type": "cron",
            "overlap_policy": "skip",
            "running_instances": 1,
            "max_instances": 2,
            "queue_size": 0,
            "max_queue_size": 10,
            "can_execute": True,
        }
        schema = TaskOverlapStatusResponse(**data)

        assert schema.task_type == "cron"
        assert schema.overlap_policy == "skip"
        assert schema.running_instances == 1
        assert schema.can_execute is True


class TestChainExecutionSkippedReason:
    """Tests for ChainExecutionResponse with skipped_reason."""

    def test_chain_execution_response_has_skipped_reason(self):
        """Test ChainExecutionResponse includes skipped_reason field."""
        from app.schemas.task_chain import ChainExecutionResponse

        fields = ChainExecutionResponse.model_fields
        assert "skipped_reason" in fields
