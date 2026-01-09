"""Tests for worker tasks module."""
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.workers.tasks import execute_http_task
from app.core.url_validator import SSRFError


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
