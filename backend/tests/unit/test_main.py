"""Tests for FastAPI application main module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check returns ok status."""
        from app.main import health_check

        result = await health_check()

        assert result == {"status": "ok", "service": "cronbox"}


class TestRootEndpoint:
    """Tests for root endpoint."""

    @pytest.mark.asyncio
    async def test_root(self):
        """Test root endpoint returns service info."""
        from app.main import root

        result = await root()

        assert result["service"] == "CronBox API"
        assert result["version"] == "1.0.0"
        assert "docs" in result


class TestTagsMetadata:
    """Tests for OpenAPI tags metadata."""

    def test_tags_metadata_not_empty(self):
        """Test tags metadata is defined."""
        from app.main import tags_metadata

        assert len(tags_metadata) > 0

    def test_tags_metadata_has_required_fields(self):
        """Test all tags have name and description."""
        from app.main import tags_metadata

        for tag in tags_metadata:
            assert "name" in tag
            assert "description" in tag


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_allowed_methods(self):
        """Test allowed methods are defined."""
        from app.main import ALLOWED_METHODS

        assert "GET" in ALLOWED_METHODS
        assert "POST" in ALLOWED_METHODS
        assert "PUT" in ALLOWED_METHODS
        assert "DELETE" in ALLOWED_METHODS
        assert "OPTIONS" in ALLOWED_METHODS

    def test_allowed_headers(self):
        """Test allowed headers are defined."""
        from app.main import ALLOWED_HEADERS

        assert "Authorization" in ALLOWED_HEADERS
        assert "Content-Type" in ALLOWED_HEADERS
        assert "X-Worker-Key" in ALLOWED_HEADERS
        assert "X-API-Key" in ALLOWED_HEADERS


class TestAppConfiguration:
    """Tests for FastAPI app configuration."""

    def test_app_title(self):
        """Test app has correct title."""
        from app.main import app

        assert app.title == "CronBox API"

    def test_app_version(self):
        """Test app has version."""
        from app.main import app

        assert app.version == "1.0.0"

    def test_app_description(self):
        """Test app has description."""
        from app.main import app

        assert app.description is not None
        assert len(app.description) > 0
        assert "CronBox" in app.description


class TestCustomOpenAPI:
    """Tests for custom OpenAPI schema."""

    def test_custom_openapi_schema(self):
        """Test custom OpenAPI schema generation."""
        from app.main import app, custom_openapi

        # Clear cached schema
        app.openapi_schema = None

        schema = custom_openapi()

        assert schema is not None
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
        assert "BearerAuth" in schema["components"]["securitySchemes"]
        assert "APIKeyAuth" in schema["components"]["securitySchemes"]

    def test_custom_openapi_has_security(self):
        """Test custom OpenAPI has global security."""
        from app.main import app, custom_openapi

        # Clear cached schema
        app.openapi_schema = None

        schema = custom_openapi()

        assert "security" in schema
        assert len(schema["security"]) > 0

    def test_custom_openapi_has_servers(self):
        """Test custom OpenAPI has servers defined."""
        from app.main import app, custom_openapi

        # Clear cached schema
        app.openapi_schema = None

        schema = custom_openapi()

        assert "servers" in schema
        assert len(schema["servers"]) > 0

    def test_custom_openapi_caches_schema(self):
        """Test custom OpenAPI caches schema."""
        from app.main import app, custom_openapi

        # Clear cached schema
        app.openapi_schema = None

        schema1 = custom_openapi()
        schema2 = custom_openapi()

        # Should return same cached object
        assert schema1 is schema2
