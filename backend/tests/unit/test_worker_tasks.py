"""Tests for worker tasks module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.core.url_validator import SSRFError
from app.workers.tasks import execute_http_task


class TestExecuteHttpTask:
    """Tests for execute_http_task function."""

    @pytest.mark.asyncio
    async def test_ssrf_blocked_url(self):
        """Test SSRF blocked URLs return error."""
        ctx = {}

        result = await execute_http_task(
            ctx,
            url="http://localhost/api",
            method="GET",
        )

        assert result["success"] is False
        assert result["error_type"] == "ssrf_blocked"
        assert "validation failed" in result["error"].lower()
        assert result["status_code"] is None

    @pytest.mark.asyncio
    async def test_ssrf_blocked_private_ip(self):
        """Test private IPs are blocked."""
        ctx = {}

        result = await execute_http_task(
            ctx,
            url="http://192.168.1.1/api",
            method="GET",
        )

        assert result["success"] is False
        assert result["error_type"] == "ssrf_blocked"

    @pytest.mark.asyncio
    async def test_ssrf_blocked_metadata_endpoint(self):
        """Test cloud metadata endpoint is blocked."""
        ctx = {}

        result = await execute_http_task(
            ctx,
            url="http://169.254.169.254/latest/meta-data/",
            method="GET",
        )

        assert result["success"] is False
        assert result["error_type"] == "ssrf_blocked"

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_successful_request(self, mock_client_class):
        """Test successful HTTP request."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"status": "ok"}'
        mock_response.content = b'{"status": "ok"}'

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://api.example.com/test",
            method="GET",
        )

        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["error"] is None
        assert result["body"] == '{"status": "ok"}'
        assert "duration_ms" in result

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_request_with_headers_and_body(self, mock_client_class):
        """Test request with custom headers and body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.content = b""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://api.example.com/webhook",
            method="POST",
            headers={"Authorization": "Bearer token"},
            body='{"event": "test"}',
        )

        assert result["success"] is True
        assert result["status_code"] == 201

        # Verify the request was made with correct params
        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["headers"]["Authorization"] == "Bearer token"
        assert call_kwargs["content"] == b'{"event": "test"}'

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_client_error_response(self, mock_client_class):
        """Test handling of 4xx responses."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.text = "Not Found"
        mock_response.content = b"Not Found"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://api.example.com/missing",
            method="GET",
        )

        assert result["success"] is False
        assert result["status_code"] == 404
        assert result["error"] is None  # No error for HTTP responses

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_server_error_response(self, mock_client_class):
        """Test handling of 5xx responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_response.text = "Internal Server Error"
        mock_response.content = b"Internal Server Error"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://api.example.com/error",
            method="GET",
        )

        assert result["success"] is False
        assert result["status_code"] == 500

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_timeout_exception(self, mock_client_class):
        """Test handling of timeout."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.TimeoutException("Connection timed out")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://slow.example.com/api",
            method="GET",
            timeout_seconds=5,
        )

        assert result["success"] is False
        assert result["status_code"] is None
        assert result["error_type"] == "timeout"
        assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_request_error(self, mock_client_class):
        """Test handling of request errors."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.RequestError("Connection refused")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://unreachable.example.com/api",
            method="GET",
        )

        assert result["success"] is False
        assert result["status_code"] is None
        assert result["error_type"] == "request_error"

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_generic_exception(self, mock_client_class):
        """Test handling of generic exceptions."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = Exception("Something went wrong")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://api.example.com/api",
            method="GET",
        )

        assert result["success"] is False
        assert result["error_type"] == "unknown"
        assert "Something went wrong" in result["error"]

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_response_body_size_limit(self, mock_client_class):
        """Test response body is limited to 64KB."""
        large_body = "x" * 100000  # 100KB

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = large_body
        mock_response.content = large_body.encode()

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://api.example.com/large",
            method="GET",
        )

        assert result["success"] is True
        # Body should be truncated to 64KB
        assert len(result["body"]) == 65536

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_duration_measurement(self, mock_client_class):
        """Test duration is measured correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.content = b""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://api.example.com/test",
            method="GET",
        )

        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], int)
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_redirect_response_considered_success(self, mock_client_class):
        """Test 3xx redirects are considered success."""
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"Location": "https://other.example.com"}
        mock_response.text = ""
        mock_response.content = b""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        result = await execute_http_task(
            ctx,
            url="https://api.example.com/redirect",
            method="GET",
        )

        assert result["success"] is True
        assert result["status_code"] == 302

    @pytest.mark.asyncio
    async def test_default_headers_empty(self):
        """Test default headers are empty dict."""
        ctx = {}

        # SSRF will block localhost, but we're checking headers handling
        with patch("app.workers.tasks.validate_url_for_ssrf"):
            with patch("app.workers.tasks.httpx.AsyncClient") as mock_client_class:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.headers = {}
                mock_response.text = ""
                mock_response.content = b""

                mock_client = AsyncMock()
                mock_client.request.return_value = mock_response
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = await execute_http_task(
                    ctx,
                    url="https://api.example.com/test",
                    method="GET",
                    headers=None,  # None headers
                )

                # Should work with None headers
                assert result["success"] is True


class TestHTTPMethods:
    """Tests for different HTTP methods."""

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_get_method(self, mock_client_class):
        """Test GET method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.content = b""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        await execute_http_task(ctx, url="https://api.example.com", method="GET")

        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "GET"

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_post_method(self, mock_client_class):
        """Test POST method."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.content = b""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        await execute_http_task(ctx, url="https://api.example.com", method="POST")

        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "POST"

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_put_method(self, mock_client_class):
        """Test PUT method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.content = b""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        await execute_http_task(ctx, url="https://api.example.com", method="PUT")

        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "PUT"

    @pytest.mark.asyncio
    @patch("app.workers.tasks.httpx.AsyncClient")
    async def test_delete_method(self, mock_client_class):
        """Test DELETE method."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.content = b""

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        ctx = {}

        await execute_http_task(ctx, url="https://api.example.com", method="DELETE")

        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "DELETE"


class TestExecuteCronTask:
    """Tests for execute_cron_task function."""

    @pytest.fixture
    def mock_db_context(self):
        """Create mock database context."""
        mock_db = AsyncMock()
        mock_db_factory = MagicMock()
        mock_db_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=None)
        return {"db_factory": mock_db_factory, "db": mock_db, "redis": mock_redis}

    @pytest.mark.asyncio
    async def test_task_not_found(self, mock_db_context):
        """Test execute_cron_task when task not found."""
        from app.workers.tasks import execute_cron_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        with patch("app.workers.tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            result = await execute_cron_task(ctx, task_id=str(uuid4()))

            assert result["success"] is False
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_task_not_active(self, mock_db_context):
        """Test execute_cron_task when task is not active."""
        from app.workers.tasks import execute_cron_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        mock_task = MagicMock()
        mock_task.is_active = False
        mock_task.is_paused = False

        with patch("app.workers.tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_task
            mock_repo_class.return_value = mock_repo

            result = await execute_cron_task(ctx, task_id=str(uuid4()))

            assert result["success"] is False
            assert "not active" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_task_paused(self, mock_db_context):
        """Test execute_cron_task when task is paused."""
        from app.workers.tasks import execute_cron_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        mock_task = MagicMock()
        mock_task.is_active = True
        mock_task.is_paused = True

        with patch("app.workers.tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_task
            mock_repo_class.return_value = mock_repo

            result = await execute_cron_task(ctx, task_id=str(uuid4()))

            assert result["success"] is False
            assert "not active" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_db_context):
        """Test successful cron task execution."""
        from app.models.cron_task import HttpMethod, ProtocolType
        from app.workers.tasks import execute_cron_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Task"
        mock_task.protocol_type = ProtocolType.HTTP
        mock_task.url = "https://api.example.com/test"
        mock_task.method = HttpMethod.GET
        mock_task.headers = {}
        mock_task.body = None
        mock_task.timeout_seconds = 30
        mock_task.is_active = True
        mock_task.is_paused = False
        mock_task.schedule = "*/5 * * * *"
        mock_task.timezone = "UTC"
        mock_task.retry_count = 0
        mock_task.last_status = None
        mock_task.overlap_policy = MagicMock()
        mock_task.overlap_policy.value = "allow"

        mock_execution = MagicMock()
        mock_execution.id = uuid4()

        with patch("app.workers.tasks.CronTaskRepository") as mock_cron_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_http_task") as mock_execute:
                    mock_cron_repo = AsyncMock()
                    mock_cron_repo.get_by_id.return_value = mock_task
                    mock_cron_repo_class.return_value = mock_cron_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute.return_value = {
                        "success": True,
                        "status_code": 200,
                        "headers": {},
                        "body": "OK",
                        "size_bytes": 2,
                        "duration_ms": 100,
                        "error": None,
                    }

                    result = await execute_cron_task(ctx, task_id=str(task_id))

                    assert result["success"] is True
                    assert result["status_code"] == 200
                    mock_exec_repo.create_execution.assert_called_once()
                    mock_exec_repo.complete_execution.assert_called_once()
                    mock_cron_repo.update_last_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_execution_with_retry(self, mock_db_context):
        """Test failed cron task execution schedules retry."""
        from app.models.cron_task import HttpMethod
        from app.workers.tasks import execute_cron_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Task"
        mock_task.url = "https://api.example.com/test"
        mock_task.method = HttpMethod.GET
        mock_task.headers = {}
        mock_task.body = None
        mock_task.timeout_seconds = 30
        mock_task.is_active = True
        mock_task.is_paused = False
        mock_task.schedule = "*/5 * * * *"
        mock_task.timezone = "UTC"
        mock_task.retry_count = 3
        mock_task.retry_delay_seconds = 60

        mock_execution = MagicMock()
        mock_execution.id = uuid4()

        mock_redis = mock_db_context["redis"]

        with patch("app.workers.tasks.CronTaskRepository") as mock_cron_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_http_task") as mock_execute:
                    mock_cron_repo = AsyncMock()
                    mock_cron_repo.get_by_id.return_value = mock_task
                    mock_cron_repo_class.return_value = mock_cron_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute.return_value = {
                        "success": False,
                        "status_code": 500,
                        "headers": {},
                        "body": "Error",
                        "size_bytes": 5,
                        "duration_ms": 100,
                        "error": "Server error",
                        "error_type": "server_error",
                    }

                    result = await execute_cron_task(ctx, task_id=str(task_id), retry_attempt=0)

                    assert result["success"] is False
                    # Verify retry was scheduled (enqueue_job called for retry)
                    mock_redis.enqueue_job.assert_called()
                    # Find the retry call
                    retry_calls = [
                        call for call in mock_redis.enqueue_job.call_args_list if call[0][0] == "execute_cron_task"
                    ]
                    assert len(retry_calls) == 1
                    assert retry_calls[0][1]["retry_attempt"] == 1


class TestExecuteDelayedTask:
    """Tests for execute_delayed_task function."""

    @pytest.fixture
    def mock_db_context(self):
        """Create mock database context."""
        mock_db = AsyncMock()
        mock_db_factory = MagicMock()
        mock_db_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=None)
        return {"db_factory": mock_db_factory, "db": mock_db, "redis": mock_redis}

    @pytest.mark.asyncio
    async def test_task_not_found(self, mock_db_context):
        """Test execute_delayed_task when task not found."""
        from app.workers.tasks import execute_delayed_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        with patch("app.workers.tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            result = await execute_delayed_task(ctx, task_id=str(uuid4()))

            assert result["success"] is False
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_task_not_pending(self, mock_db_context):
        """Test execute_delayed_task when task is not pending."""
        from app.models.cron_task import TaskStatus
        from app.workers.tasks import execute_delayed_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        mock_task = MagicMock()
        mock_task.status = TaskStatus.SUCCESS  # Already completed

        with patch("app.workers.tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_task
            mock_repo_class.return_value = mock_repo

            result = await execute_delayed_task(ctx, task_id=str(uuid4()))

            assert result["success"] is False
            assert "not pending" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_db_context):
        """Test successful delayed task execution."""
        from app.models.cron_task import HttpMethod, ProtocolType, TaskStatus
        from app.workers.tasks import execute_delayed_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Delayed Task"
        mock_task.protocol_type = ProtocolType.HTTP
        mock_task.url = "https://api.example.com/callback"
        mock_task.method = HttpMethod.POST
        mock_task.headers = {"Content-Type": "application/json"}
        mock_task.body = '{"event": "test"}'
        mock_task.timeout_seconds = 30
        mock_task.status = TaskStatus.PENDING
        mock_task.retry_count = 0
        mock_task.callback_url = None

        mock_execution = MagicMock()
        mock_execution.id = uuid4()

        with patch("app.workers.tasks.DelayedTaskRepository") as mock_delayed_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_http_task") as mock_execute:
                    mock_delayed_repo = AsyncMock()
                    mock_delayed_repo.get_by_id.return_value = mock_task
                    mock_delayed_repo_class.return_value = mock_delayed_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute.return_value = {
                        "success": True,
                        "status_code": 200,
                        "headers": {},
                        "body": "OK",
                        "size_bytes": 2,
                        "duration_ms": 50,
                        "error": None,
                    }

                    result = await execute_delayed_task(ctx, task_id=str(task_id))

                    assert result["success"] is True
                    assert result["status_code"] == 200
                    mock_delayed_repo.mark_running.assert_called_once()
                    mock_delayed_repo.mark_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_already_running(self, mock_db_context):
        """Test delayed task that is already running."""
        from app.models.cron_task import HttpMethod, ProtocolType, TaskStatus
        from app.workers.tasks import execute_delayed_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Task"
        mock_task.protocol_type = ProtocolType.HTTP
        mock_task.url = "https://api.example.com/test"
        mock_task.method = HttpMethod.GET
        mock_task.headers = {}
        mock_task.body = None
        mock_task.timeout_seconds = 30
        mock_task.status = TaskStatus.RUNNING  # Already running
        mock_task.retry_count = 0
        mock_task.callback_url = None

        mock_execution = MagicMock()

        with patch("app.workers.tasks.DelayedTaskRepository") as mock_delayed_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_http_task") as mock_execute:
                    mock_delayed_repo = AsyncMock()
                    mock_delayed_repo.get_by_id.return_value = mock_task
                    mock_delayed_repo_class.return_value = mock_delayed_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute.return_value = {
                        "success": True,
                        "status_code": 200,
                        "headers": {},
                        "body": "OK",
                        "size_bytes": 2,
                        "duration_ms": 50,
                        "error": None,
                    }

                    result = await execute_delayed_task(ctx, task_id=str(task_id))

                    assert result["success"] is True
                    # Should NOT call mark_running since already running
                    mock_delayed_repo.mark_running.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_execution_with_retry(self, mock_db_context):
        """Test failed delayed task execution schedules retry."""
        from app.models.cron_task import HttpMethod, TaskStatus
        from app.workers.tasks import execute_delayed_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Task"
        mock_task.url = "https://api.example.com/test"
        mock_task.method = HttpMethod.GET
        mock_task.headers = {}
        mock_task.body = None
        mock_task.timeout_seconds = 30
        mock_task.status = TaskStatus.PENDING
        mock_task.retry_count = 3
        mock_task.retry_delay_seconds = 60
        mock_task.callback_url = None

        mock_execution = MagicMock()

        mock_redis = mock_db_context["redis"]

        with patch("app.workers.tasks.DelayedTaskRepository") as mock_delayed_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_http_task") as mock_execute:
                    mock_delayed_repo = AsyncMock()
                    mock_delayed_repo.get_by_id.return_value = mock_task
                    mock_delayed_repo_class.return_value = mock_delayed_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute.return_value = {
                        "success": False,
                        "status_code": 500,
                        "headers": {},
                        "body": "Error",
                        "size_bytes": 5,
                        "duration_ms": 100,
                        "error": "Server error",
                    }

                    result = await execute_delayed_task(ctx, task_id=str(task_id), retry_attempt=0)

                    assert result["success"] is False
                    mock_delayed_repo.increment_retry.assert_called_once()
                    # Verify retry was scheduled
                    retry_calls = [
                        call for call in mock_redis.enqueue_job.call_args_list if call[0][0] == "execute_delayed_task"
                    ]
                    assert len(retry_calls) == 1

    @pytest.mark.asyncio
    async def test_failed_execution_max_retries(self, mock_db_context):
        """Test failed delayed task with max retries reached."""
        from app.models.cron_task import HttpMethod, TaskStatus
        from app.workers.tasks import execute_delayed_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Task"
        mock_task.url = "https://api.example.com/test"
        mock_task.method = HttpMethod.GET
        mock_task.headers = {}
        mock_task.body = None
        mock_task.timeout_seconds = 30
        mock_task.status = TaskStatus.PENDING
        mock_task.retry_count = 3
        mock_task.callback_url = None

        mock_execution = MagicMock()

        with patch("app.workers.tasks.DelayedTaskRepository") as mock_delayed_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_http_task") as mock_execute:
                    mock_delayed_repo = AsyncMock()
                    mock_delayed_repo.get_by_id.return_value = mock_task
                    mock_delayed_repo_class.return_value = mock_delayed_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute.return_value = {
                        "success": False,
                        "status_code": 500,
                        "headers": {},
                        "body": "Error",
                        "size_bytes": 5,
                        "duration_ms": 100,
                        "error": "Server error",
                    }

                    # Max retries reached
                    result = await execute_delayed_task(ctx, task_id=str(task_id), retry_attempt=3)

                    assert result["success"] is False
                    # Should mark as failed, not increment retry
                    mock_delayed_repo.mark_completed.assert_called_once()
                    mock_delayed_repo.increment_retry.assert_not_called()


class TestExecuteIcmpTask:
    """Tests for execute_icmp_task function."""

    @pytest.mark.asyncio
    async def test_successful_icmp_task(self):
        """Test successful ICMP task execution."""
        from app.workers.tasks import execute_icmp_task

        ctx = {}

        with patch("app.workers.tasks.execute_icmp_ping") as mock_ping:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.packets_sent = 3
            mock_result.packets_received = 3
            mock_result.packet_loss = 0.0
            mock_result.min_rtt = 1.0
            mock_result.avg_rtt = 2.0
            mock_result.max_rtt = 3.0
            mock_result.duration_ms = 100.0
            mock_result.error_message = None
            mock_ping.return_value = mock_result

            result = await execute_icmp_task(ctx, host="test.example.com", count=3, timeout_seconds=30)

            assert result["success"] is True
            assert result["packets_sent"] == 3
            assert result["packets_received"] == 3
            assert result["packet_loss"] == 0.0
            assert result["min_rtt"] == 1.0
            assert result["avg_rtt"] == 2.0
            assert result["max_rtt"] == 3.0
            assert result["duration_ms"] == 100
            assert result["error"] is None
            assert result["error_type"] is None

            mock_ping.assert_called_once_with("test.example.com", 3, 30)

    @pytest.mark.asyncio
    async def test_failed_icmp_task(self):
        """Test failed ICMP task execution."""
        from app.workers.tasks import execute_icmp_task

        ctx = {}

        with patch("app.workers.tasks.execute_icmp_ping") as mock_ping:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.packets_sent = 3
            mock_result.packets_received = 0
            mock_result.packet_loss = 100.0
            mock_result.min_rtt = None
            mock_result.avg_rtt = None
            mock_result.max_rtt = None
            mock_result.duration_ms = 30000.0
            mock_result.error_message = "No response"
            mock_ping.return_value = mock_result

            result = await execute_icmp_task(ctx, host="unreachable.host", count=3)

            assert result["success"] is False
            assert result["packets_received"] == 0
            assert result["packet_loss"] == 100.0
            assert result["error"] == "No response"
            assert result["error_type"] == "icmp_error"

    @pytest.mark.asyncio
    async def test_icmp_task_partial_loss(self):
        """Test ICMP task with partial packet loss."""
        from app.workers.tasks import execute_icmp_task

        ctx = {}

        with patch("app.workers.tasks.execute_icmp_ping") as mock_ping:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.packets_sent = 3
            mock_result.packets_received = 2
            mock_result.packet_loss = 33.33
            mock_result.min_rtt = 1.5
            mock_result.avg_rtt = 2.5
            mock_result.max_rtt = 3.5
            mock_result.duration_ms = 200.0
            mock_result.error_message = None
            mock_ping.return_value = mock_result

            result = await execute_icmp_task(ctx, host="flaky.host", count=3)

            assert result["success"] is True
            assert result["packets_received"] == 2
            assert result["packet_loss"] == 33.33
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_icmp_task_default_params(self):
        """Test ICMP task with default parameters."""
        from app.workers.tasks import execute_icmp_task

        ctx = {}

        with patch("app.workers.tasks.execute_icmp_ping") as mock_ping:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.packets_sent = 3
            mock_result.packets_received = 3
            mock_result.packet_loss = 0.0
            mock_result.min_rtt = 1.0
            mock_result.avg_rtt = 2.0
            mock_result.max_rtt = 3.0
            mock_result.duration_ms = 100.0
            mock_result.error_message = None
            mock_ping.return_value = mock_result

            await execute_icmp_task(ctx, host="test.com")

            # Verify defaults: count=3, timeout_seconds=30
            mock_ping.assert_called_once_with("test.com", 3, 30)


class TestExecuteTcpTask:
    """Tests for execute_tcp_task function."""

    @pytest.mark.asyncio
    async def test_successful_tcp_task(self):
        """Test successful TCP task execution."""
        from app.workers.tasks import execute_tcp_task

        ctx = {}

        with patch("app.workers.tasks.execute_tcp_check") as mock_tcp:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.connection_time = 15.5
            mock_result.duration_ms = 20.0
            mock_result.error_message = None
            mock_tcp.return_value = mock_result

            result = await execute_tcp_task(ctx, host="example.com", port=443, timeout_seconds=30)

            assert result["success"] is True
            assert result["connection_time"] == 15.5
            assert result["duration_ms"] == 20
            assert result["error"] is None
            assert result["error_type"] is None

            mock_tcp.assert_called_once_with("example.com", 443, 30)

    @pytest.mark.asyncio
    async def test_failed_tcp_task_refused(self):
        """Test TCP task with connection refused."""
        from app.workers.tasks import execute_tcp_task

        ctx = {}

        with patch("app.workers.tasks.execute_tcp_check") as mock_tcp:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.connection_time = None
            mock_result.duration_ms = 50.0
            mock_result.error_message = "Connection refused (port closed)"
            mock_tcp.return_value = mock_result

            result = await execute_tcp_task(ctx, host="example.com", port=12345)

            assert result["success"] is False
            assert result["connection_time"] is None
            assert result["error"] == "Connection refused (port closed)"
            assert result["error_type"] == "tcp_error"

    @pytest.mark.asyncio
    async def test_failed_tcp_task_timeout(self):
        """Test TCP task with connection timeout."""
        from app.workers.tasks import execute_tcp_task

        ctx = {}

        with patch("app.workers.tasks.execute_tcp_check") as mock_tcp:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.connection_time = None
            mock_result.duration_ms = 30000.0
            mock_result.error_message = "Connection timeout"
            mock_tcp.return_value = mock_result

            result = await execute_tcp_task(ctx, host="slow.host.com", port=443, timeout_seconds=30)

            assert result["success"] is False
            assert result["error"] == "Connection timeout"
            assert result["error_type"] == "tcp_error"

    @pytest.mark.asyncio
    async def test_tcp_task_default_params(self):
        """Test TCP task with default parameters."""
        from app.workers.tasks import execute_tcp_task

        ctx = {}

        with patch("app.workers.tasks.execute_tcp_check") as mock_tcp:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.connection_time = 10.0
            mock_result.duration_ms = 15.0
            mock_result.error_message = None
            mock_tcp.return_value = mock_result

            await execute_tcp_task(ctx, host="example.com", port=80)

            # Verify default timeout_seconds=30
            mock_tcp.assert_called_once_with("example.com", 80, 30)


class TestCronTaskWithProtocols:
    """Tests for execute_cron_task with different protocol types."""

    @pytest.fixture
    def mock_db_context(self):
        """Create mock database context."""
        mock_db = AsyncMock()
        mock_db_factory = MagicMock()
        mock_db_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=None)
        return {"db_factory": mock_db_factory, "db": mock_db, "redis": mock_redis}

    @pytest.mark.asyncio
    async def test_cron_task_icmp_protocol(self, mock_db_context):
        """Test cron task execution with ICMP protocol."""
        from app.models.cron_task import ProtocolType
        from app.workers.tasks import execute_cron_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "ICMP Test Task"
        mock_task.protocol_type = ProtocolType.ICMP
        mock_task.host = "ping.example.com"
        mock_task.icmp_count = 5
        mock_task.timeout_seconds = 30
        mock_task.is_active = True
        mock_task.is_paused = False
        mock_task.schedule = "*/5 * * * *"
        mock_task.timezone = "UTC"
        mock_task.retry_count = 0
        mock_task.last_status = None
        mock_task.overlap_policy = MagicMock()
        mock_task.overlap_policy.value = "allow"

        mock_execution = MagicMock()
        mock_execution.id = uuid4()

        with patch("app.workers.tasks.CronTaskRepository") as mock_cron_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_icmp_task") as mock_execute_icmp:
                    mock_cron_repo = AsyncMock()
                    mock_cron_repo.get_by_id.return_value = mock_task
                    mock_cron_repo_class.return_value = mock_cron_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute_icmp.return_value = {
                        "success": True,
                        "packets_sent": 5,
                        "packets_received": 5,
                        "packet_loss": 0.0,
                        "min_rtt": 1.0,
                        "avg_rtt": 2.0,
                        "max_rtt": 3.0,
                        "duration_ms": 500,
                        "error": None,
                        "error_type": None,
                    }

                    result = await execute_cron_task(ctx, task_id=str(task_id))

                    assert result["success"] is True
                    mock_execute_icmp.assert_called_once_with(
                        ctx,
                        host="ping.example.com",
                        count=5,
                        timeout_seconds=30,
                    )
                    mock_exec_repo.complete_icmp_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_cron_task_tcp_protocol(self, mock_db_context):
        """Test cron task execution with TCP protocol."""
        from app.models.cron_task import ProtocolType
        from app.workers.tasks import execute_cron_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "TCP Test Task"
        mock_task.protocol_type = ProtocolType.TCP
        mock_task.host = "db.example.com"
        mock_task.port = 5432
        mock_task.timeout_seconds = 30
        mock_task.is_active = True
        mock_task.is_paused = False
        mock_task.schedule = "*/5 * * * *"
        mock_task.timezone = "UTC"
        mock_task.retry_count = 0
        mock_task.last_status = None
        mock_task.overlap_policy = MagicMock()
        mock_task.overlap_policy.value = "allow"

        mock_execution = MagicMock()
        mock_execution.id = uuid4()

        with patch("app.workers.tasks.CronTaskRepository") as mock_cron_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_tcp_task") as mock_execute_tcp:
                    mock_cron_repo = AsyncMock()
                    mock_cron_repo.get_by_id.return_value = mock_task
                    mock_cron_repo_class.return_value = mock_cron_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute_tcp.return_value = {
                        "success": True,
                        "connection_time": 15.5,
                        "duration_ms": 20,
                        "error": None,
                        "error_type": None,
                    }

                    result = await execute_cron_task(ctx, task_id=str(task_id))

                    assert result["success"] is True
                    mock_execute_tcp.assert_called_once_with(
                        ctx,
                        host="db.example.com",
                        port=5432,
                        timeout_seconds=30,
                    )
                    mock_exec_repo.complete_tcp_execution.assert_called_once()


class TestDelayedTaskWithProtocols:
    """Tests for execute_delayed_task with different protocol types."""

    @pytest.fixture
    def mock_db_context(self):
        """Create mock database context."""
        mock_db = AsyncMock()
        mock_db_factory = MagicMock()
        mock_db_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=None)
        return {"db_factory": mock_db_factory, "db": mock_db, "redis": mock_redis}

    @pytest.mark.asyncio
    async def test_delayed_task_icmp_protocol(self, mock_db_context):
        """Test delayed task execution with ICMP protocol."""
        from app.models.cron_task import ProtocolType, TaskStatus
        from app.workers.tasks import execute_delayed_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "ICMP Delayed Task"
        mock_task.protocol_type = ProtocolType.ICMP
        mock_task.host = "ping.example.com"
        mock_task.icmp_count = 3
        mock_task.timeout_seconds = 30
        mock_task.status = TaskStatus.PENDING
        mock_task.retry_count = 0
        mock_task.callback_url = None

        mock_execution = MagicMock()
        mock_execution.id = uuid4()

        with patch("app.workers.tasks.DelayedTaskRepository") as mock_delayed_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_icmp_task") as mock_execute_icmp:
                    mock_delayed_repo = AsyncMock()
                    mock_delayed_repo.get_by_id.return_value = mock_task
                    mock_delayed_repo_class.return_value = mock_delayed_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute_icmp.return_value = {
                        "success": True,
                        "packets_sent": 3,
                        "packets_received": 3,
                        "packet_loss": 0.0,
                        "min_rtt": 1.0,
                        "avg_rtt": 2.0,
                        "max_rtt": 3.0,
                        "duration_ms": 300,
                        "error": None,
                        "error_type": None,
                    }

                    result = await execute_delayed_task(ctx, task_id=str(task_id))

                    assert result["success"] is True
                    mock_execute_icmp.assert_called_once()
                    mock_exec_repo.complete_icmp_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_delayed_task_tcp_protocol(self, mock_db_context):
        """Test delayed task execution with TCP protocol."""
        from app.models.cron_task import ProtocolType, TaskStatus
        from app.workers.tasks import execute_delayed_task

        ctx = {"db_factory": mock_db_context["db_factory"], "redis": mock_db_context["redis"]}

        task_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.workspace_id = uuid4()
        mock_task.name = "TCP Delayed Task"
        mock_task.protocol_type = ProtocolType.TCP
        mock_task.host = "api.example.com"
        mock_task.port = 443
        mock_task.timeout_seconds = 30
        mock_task.status = TaskStatus.PENDING
        mock_task.retry_count = 0
        mock_task.callback_url = None

        mock_execution = MagicMock()
        mock_execution.id = uuid4()

        with patch("app.workers.tasks.DelayedTaskRepository") as mock_delayed_repo_class:
            with patch("app.workers.tasks.ExecutionRepository") as mock_exec_repo_class:
                with patch("app.workers.tasks.execute_tcp_task") as mock_execute_tcp:
                    mock_delayed_repo = AsyncMock()
                    mock_delayed_repo.get_by_id.return_value = mock_task
                    mock_delayed_repo_class.return_value = mock_delayed_repo

                    mock_exec_repo = AsyncMock()
                    mock_exec_repo.create_execution.return_value = mock_execution
                    mock_exec_repo_class.return_value = mock_exec_repo

                    mock_execute_tcp.return_value = {
                        "success": True,
                        "connection_time": 25.0,
                        "duration_ms": 30,
                        "error": None,
                        "error_type": None,
                    }

                    result = await execute_delayed_task(ctx, task_id=str(task_id))

                    assert result["success"] is True
                    mock_execute_tcp.assert_called_once()
                    mock_exec_repo.complete_tcp_execution.assert_called_once()
