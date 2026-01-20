"""Unit tests for HeartbeatService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytz


class TestHeartbeatServiceFormatDatetime:
    """Tests for HeartbeatService._format_datetime method."""

    def test_format_datetime_utc(self):
        """Test formatting UTC datetime in Russian format."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "UTC")

        assert result == "19.01.2026 14:50:04"

    def test_format_datetime_moscow_timezone(self):
        """Test formatting datetime with Moscow timezone conversion."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        # UTC time
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "Europe/Moscow")

        # Moscow is UTC+3, so 14:50 UTC = 17:50 MSK
        assert result == "19.01.2026 17:50:04"

    def test_format_datetime_vladivostok_timezone(self):
        """Test formatting datetime with Vladivostok timezone conversion."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        # UTC time
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "Asia/Vladivostok")

        # Vladivostok is UTC+10, so 14:50 UTC = 00:50+1day VLAT
        assert result == "20.01.2026 00:50:04"

    def test_format_datetime_naive_datetime(self):
        """Test formatting naive datetime (treated as UTC)."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        # Naive datetime without timezone
        dt = datetime(2026, 1, 19, 14, 50, 4)

        result = service._format_datetime(dt, "Europe/Moscow")

        # Should be treated as UTC and converted to Moscow (UTC+3)
        assert result == "19.01.2026 17:50:04"

    def test_format_datetime_invalid_timezone_fallback(self):
        """Test formatting datetime with invalid timezone falls back to Moscow."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "Invalid/Timezone")

        # Should fall back to Moscow timezone
        assert result == "19.01.2026 17:50:04"

    def test_format_datetime_new_york_timezone(self):
        """Test formatting datetime with New York timezone conversion."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        # UTC time
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "America/New_York")

        # New York is UTC-5 in January, so 14:50 UTC = 09:50 EST
        assert result == "19.01.2026 09:50:04"

    def test_format_datetime_russian_format(self):
        """Test that output format is DD.MM.YYYY HH:MM:SS."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        dt = datetime(2026, 5, 7, 8, 5, 3, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "UTC")

        # Should have leading zeros
        assert result == "07.05.2026 08:05:03"


class TestHeartbeatServiceGetWorkspaceSettings:
    """Tests for HeartbeatService._get_workspace_settings method."""

    @pytest.mark.asyncio
    async def test_get_workspace_settings_with_owner(self):
        """Test getting workspace settings when owner exists."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        workspace_id = uuid4()

        # Create mock owner
        mock_owner = MagicMock()
        mock_owner.preferred_language = "ru"

        # Create mock workspace
        mock_workspace = MagicMock()
        mock_workspace.default_timezone = "Europe/Kaliningrad"
        mock_workspace.owner = mock_owner

        # Create mock db session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        lang, tz = await service._get_workspace_settings(mock_db, workspace_id)

        assert lang == "ru"
        assert tz == "Europe/Kaliningrad"

    @pytest.mark.asyncio
    async def test_get_workspace_settings_without_owner(self):
        """Test getting workspace settings when no owner."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        workspace_id = uuid4()

        # Create mock workspace without owner
        mock_workspace = MagicMock()
        mock_workspace.default_timezone = "Asia/Tokyo"
        mock_workspace.owner = None

        # Create mock db session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        lang, tz = await service._get_workspace_settings(mock_db, workspace_id)

        # Should return default language but workspace timezone
        assert lang == "en"
        assert tz == "Asia/Tokyo"

    @pytest.mark.asyncio
    async def test_get_workspace_settings_no_workspace(self):
        """Test getting workspace settings when workspace doesn't exist."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        workspace_id = uuid4()

        # Create mock db session returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        lang, tz = await service._get_workspace_settings(mock_db, workspace_id)

        # Should return defaults
        assert lang == "en"
        assert tz == "Europe/Moscow"

    @pytest.mark.asyncio
    async def test_get_workspace_settings_owner_no_language(self):
        """Test getting workspace settings when owner has no preferred language."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        workspace_id = uuid4()

        # Create mock owner without preferred_language
        mock_owner = MagicMock()
        mock_owner.preferred_language = None

        # Create mock workspace
        mock_workspace = MagicMock()
        mock_workspace.default_timezone = "Europe/Moscow"
        mock_workspace.owner = mock_owner

        # Create mock db session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        lang, tz = await service._get_workspace_settings(mock_db, workspace_id)

        # Should return default language
        assert lang == "en"
        assert tz == "Europe/Moscow"

    @pytest.mark.asyncio
    async def test_get_workspace_settings_no_timezone(self):
        """Test getting workspace settings when workspace has no timezone."""
        from app.services.heartbeat import HeartbeatService

        service = HeartbeatService()
        workspace_id = uuid4()

        # Create mock owner
        mock_owner = MagicMock()
        mock_owner.preferred_language = "en"

        # Create mock workspace without timezone
        mock_workspace = MagicMock()
        mock_workspace.default_timezone = None
        mock_workspace.owner = mock_owner

        # Create mock db session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workspace

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        lang, tz = await service._get_workspace_settings(mock_db, workspace_id)

        # Should return default timezone
        assert lang == "en"
        assert tz == "Europe/Moscow"
