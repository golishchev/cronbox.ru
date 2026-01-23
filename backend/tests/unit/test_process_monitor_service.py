"""Unit tests for ProcessMonitorService."""

from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytz

from app.models.process_monitor import ConcurrencyPolicy, ProcessMonitor, ProcessMonitorStatus, ScheduleType


class TestProcessMonitorServiceCalculateNextExpectedStart:
    """Tests for ProcessMonitorService.calculate_next_expected_start method."""

    def test_cron_schedule_next_run(self):
        """Test calculating next expected start for cron schedule."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.CRON
        monitor.schedule_cron = "0 2 * * *"  # 2 AM daily
        monitor.timezone = "UTC"

        # Current time: Jan 19, 2026, 10:00 UTC
        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        # Next run should be Jan 20, 2026, 2:00 UTC
        assert result is not None
        assert result.day == 20
        assert result.hour == 2
        assert result.minute == 0

    def test_cron_schedule_same_day(self):
        """Test cron schedule when next run is same day."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.CRON
        monitor.schedule_cron = "0 18 * * *"  # 6 PM daily
        monitor.timezone = "UTC"

        # Current time: Jan 19, 2026, 10:00 UTC
        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        # Next run should be Jan 19, 2026, 18:00 UTC (same day)
        assert result is not None
        assert result.day == 19
        assert result.hour == 18

    def test_interval_schedule(self):
        """Test calculating next expected start for interval schedule."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 21600  # 6 hours
        monitor.timezone = "UTC"

        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        # Next run should be 6 hours later
        assert result is not None
        assert result == datetime(2026, 1, 19, 16, 0, 0)

    def test_exact_time_schedule_next_day(self):
        """Test calculating next expected start for exact time (next day)."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.EXACT_TIME
        monitor.schedule_exact_time = "09:00"
        monitor.timezone = "UTC"

        # Current time: Jan 19, 2026, 10:00 UTC (after 9 AM)
        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        # Next run should be Jan 20, 2026, 09:00 UTC (next day)
        assert result is not None
        assert result.day == 20
        assert result.hour == 9
        assert result.minute == 0

    def test_exact_time_schedule_same_day(self):
        """Test calculating next expected start for exact time (same day)."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.EXACT_TIME
        monitor.schedule_exact_time = "14:00"
        monitor.timezone = "UTC"

        # Current time: Jan 19, 2026, 10:00 UTC (before 2 PM)
        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        # Next run should be Jan 19, 2026, 14:00 UTC (same day)
        assert result is not None
        assert result.day == 19
        assert result.hour == 14
        assert result.minute == 0

    def test_cron_schedule_missing_expression(self):
        """Test cron schedule with missing expression returns None."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.CRON
        monitor.schedule_cron = None
        monitor.timezone = "UTC"

        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        assert result is None

    def test_interval_schedule_missing_interval(self):
        """Test interval schedule with missing interval returns None."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = None
        monitor.timezone = "UTC"

        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        assert result is None

    def test_exact_time_schedule_missing_time(self):
        """Test exact time schedule with missing time returns None."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.EXACT_TIME
        monitor.schedule_exact_time = None
        monitor.timezone = "UTC"

        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        assert result is None

    def test_timezone_conversion_moscow(self):
        """Test schedule calculation respects Moscow timezone."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.EXACT_TIME
        monitor.schedule_exact_time = "12:00"  # Noon Moscow time
        monitor.timezone = "Europe/Moscow"

        # Current UTC time: Jan 19, 2026, 10:00 UTC (= 13:00 Moscow)
        # So 12:00 Moscow has already passed
        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = service.calculate_next_expected_start(monitor, from_time)

        # Next run should be Jan 20, 2026, 12:00 Moscow = 09:00 UTC
        assert result is not None
        assert result.hour == 9  # 12:00 Moscow = 09:00 UTC

    def test_invalid_timezone_fallback(self):
        """Test that invalid timezone falls back to Moscow."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 3600  # 1 hour
        monitor.timezone = "Invalid/Timezone"

        from_time = datetime(2026, 1, 19, 10, 0, 0, tzinfo=timezone.utc)

        # Should not raise, should fall back to Moscow timezone
        result = service.calculate_next_expected_start(monitor, from_time)

        assert result is not None


class TestProcessMonitorServiceFormatDatetime:
    """Tests for ProcessMonitorService._format_datetime method."""

    def test_format_datetime_utc(self):
        """Test formatting UTC datetime in Russian format."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "UTC")

        assert result == "19.01.2026 14:50:04"

    def test_format_datetime_moscow_timezone(self):
        """Test formatting datetime with Moscow timezone conversion."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        # UTC time
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "Europe/Moscow")

        # Moscow is UTC+3, so 14:50 UTC = 17:50 MSK
        assert result == "19.01.2026 17:50:04"

    def test_format_datetime_naive_datetime(self):
        """Test formatting naive datetime (treated as UTC)."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        # Naive datetime without timezone
        dt = datetime(2026, 1, 19, 14, 50, 4)

        result = service._format_datetime(dt, "Europe/Moscow")

        # Should be treated as UTC and converted to Moscow (UTC+3)
        assert result == "19.01.2026 17:50:04"

    def test_format_datetime_invalid_timezone_fallback(self):
        """Test formatting datetime with invalid timezone falls back to Moscow."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "Invalid/Timezone")

        # Should fall back to Moscow timezone
        assert result == "19.01.2026 17:50:04"

    def test_format_datetime_new_york_timezone(self):
        """Test formatting datetime with New York timezone conversion."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        # UTC time
        dt = datetime(2026, 1, 19, 14, 50, 4, tzinfo=timezone.utc)

        result = service._format_datetime(dt, "America/New_York")

        # New York is UTC-5 in January, so 14:50 UTC = 09:50 EST
        assert result == "19.01.2026 09:50:04"


class TestProcessMonitorServiceFormatDuration:
    """Tests for ProcessMonitorService._format_duration method."""

    def test_format_duration_milliseconds(self):
        """Test formatting duration in milliseconds."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        assert service._format_duration(500) == "500ms"
        assert service._format_duration(999) == "999ms"

    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        assert service._format_duration(1000) == "1.0s"
        assert service._format_duration(5500) == "5.5s"
        assert service._format_duration(59000) == "59.0s"

    def test_format_duration_minutes(self):
        """Test formatting duration in minutes."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        assert service._format_duration(60000) == "1.0m"
        assert service._format_duration(90000) == "1.5m"
        assert service._format_duration(3540000) == "59.0m"

    def test_format_duration_hours(self):
        """Test formatting duration in hours."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        assert service._format_duration(3600000) == "1.0h"
        assert service._format_duration(5400000) == "1.5h"
        assert service._format_duration(36000000) == "10.0h"


class TestProcessMonitorServiceGetWorkspaceSettings:
    """Tests for ProcessMonitorService._get_workspace_settings method."""

    @pytest.mark.asyncio
    async def test_get_workspace_settings_with_owner(self):
        """Test getting workspace settings when owner exists."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
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
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
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
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
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


class TestProcessMonitorStateMachine:
    """Tests for ProcessMonitorService state machine logic."""

    @pytest.mark.asyncio
    async def test_process_start_ping_from_waiting_start(self):
        """Test processing start ping from waiting_start state."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.status = ProcessMonitorStatus.WAITING_START
        monitor.notify_on_recovery = False

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.mark_running = AsyncMock()
            mock_event_repo = MockEventRepo.return_value

            mock_event = MagicMock()
            mock_event_repo.create_start_event = AsyncMock(return_value=mock_event)
            mock_event_repo.delete_old_events = AsyncMock()

            event = await service.process_start_ping(mock_db, monitor)

            # Should create start event
            mock_event_repo.create_start_event.assert_called_once()
            # Should mark as running
            mock_repo.mark_running.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_start_ping_from_running_raises_error(self):
        """Test processing start ping from running state raises error with SKIP policy."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.status = ProcessMonitorStatus.RUNNING
        monitor.concurrency_policy = ConcurrencyPolicy.SKIP

        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="already running"):
            await service.process_start_ping(mock_db, monitor)

    @pytest.mark.asyncio
    async def test_process_start_ping_from_running_with_replace_policy(self):
        """Test processing start ping from running state with REPLACE policy creates timeout event."""
        from app.db.repositories.process_monitors import ProcessMonitorEventRepository, ProcessMonitorRepository
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.status = ProcessMonitorStatus.RUNNING
        monitor.concurrency_policy = ConcurrencyPolicy.REPLACE
        monitor.current_run_id = str(uuid4())
        monitor.notify_on_missed_end = True
        monitor.workspace_id = uuid4()

        mock_db = AsyncMock()
        mock_event_repo = AsyncMock(spec=ProcessMonitorEventRepository)
        mock_monitor_repo = AsyncMock(spec=ProcessMonitorRepository)

        mock_event = MagicMock()
        mock_event.run_id = str(uuid4())
        mock_event_repo.create_start_event.return_value = mock_event
        mock_event_repo.create_timeout_event.return_value = None
        mock_event_repo.delete_old_events.return_value = None

        with patch("app.services.process_monitor.ProcessMonitorEventRepository", return_value=mock_event_repo):
            with patch("app.services.process_monitor.ProcessMonitorRepository", return_value=mock_monitor_repo):
                with patch.object(service, "_send_missed_end_notification", return_value=None):
                    result = await service.process_start_ping(mock_db, monitor)

        # Verify timeout event was created for old run
        mock_event_repo.create_timeout_event.assert_called_once_with(
            monitor_id=monitor.id,
            run_id=monitor.current_run_id,
        )

        # Verify new start event was created
        assert mock_event_repo.create_start_event.called

        # Verify monitor was marked as running
        assert mock_monitor_repo.mark_running.called

    @pytest.mark.asyncio
    async def test_process_start_ping_from_paused_raises_error(self):
        """Test processing start ping from paused state raises error."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.status = ProcessMonitorStatus.PAUSED

        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="paused"):
            await service.process_start_ping(mock_db, monitor)

    @pytest.mark.asyncio
    async def test_process_end_ping_from_running(self):
        """Test processing end ping from running state."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.status = ProcessMonitorStatus.RUNNING
        monitor.current_run_id = str(uuid4())
        monitor.last_start_at = datetime.utcnow() - timedelta(minutes=5)
        monitor.notify_on_success = False
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 3600
        monitor.timezone = "UTC"

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.mark_completed = AsyncMock()
            mock_event_repo = MockEventRepo.return_value

            mock_event = MagicMock()
            mock_event_repo.create_end_event = AsyncMock(return_value=mock_event)

            event = await service.process_end_ping(mock_db, monitor)

            # Should create end event
            mock_event_repo.create_end_event.assert_called_once()
            # Should mark as completed
            mock_repo.mark_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_end_ping_not_running_raises_error(self):
        """Test processing end ping when not running raises error."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.status = ProcessMonitorStatus.WAITING_START

        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="not running"):
            await service.process_end_ping(mock_db, monitor)

    @pytest.mark.asyncio
    async def test_process_start_ping_sends_recovery_notification(self):
        """Test that recovery notification is sent when recovering from failure."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.status = ProcessMonitorStatus.MISSED_START  # Was in failure state
        monitor.notify_on_recovery = True

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
            patch.object(service, "_send_recovery_notification", new_callable=AsyncMock) as mock_send_recovery,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.mark_running = AsyncMock()
            mock_event_repo = MockEventRepo.return_value
            mock_event_repo.create_start_event = AsyncMock(return_value=MagicMock())
            mock_event_repo.delete_old_events = AsyncMock()

            await service.process_start_ping(mock_db, monitor)

            # Should have sent recovery notification
            mock_send_recovery.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_end_ping_without_run_id_raises_error(self):
        """Test processing end ping without current_run_id raises error."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.status = ProcessMonitorStatus.RUNNING
        monitor.current_run_id = None  # No active run

        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="no active run"):
            await service.process_end_ping(mock_db, monitor)

    @pytest.mark.asyncio
    async def test_process_end_ping_with_provided_duration(self):
        """Test processing end ping with explicitly provided duration."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.status = ProcessMonitorStatus.RUNNING
        monitor.current_run_id = str(uuid4())
        monitor.last_start_at = datetime.utcnow() - timedelta(minutes=5)
        monitor.notify_on_success = False
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 3600
        monitor.timezone = "UTC"

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.mark_completed = AsyncMock()
            mock_event_repo = MockEventRepo.return_value

            mock_event = MagicMock()
            mock_event_repo.create_end_event = AsyncMock(return_value=mock_event)

            # Provide explicit duration
            await service.process_end_ping(mock_db, monitor, duration_ms=12345)

            # Should use provided duration
            call_args = mock_event_repo.create_end_event.call_args
            assert call_args.kwargs.get("duration_ms") == 12345

    @pytest.mark.asyncio
    async def test_process_end_ping_sends_success_notification(self):
        """Test that success notification is sent when enabled."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.status = ProcessMonitorStatus.RUNNING
        monitor.current_run_id = str(uuid4())
        monitor.last_start_at = datetime.utcnow() - timedelta(minutes=5)
        monitor.notify_on_success = True  # Success notifications enabled
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 3600
        monitor.timezone = "UTC"

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
            patch.object(service, "_send_success_notification", new_callable=AsyncMock) as mock_send_success,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.mark_completed = AsyncMock()
            mock_event_repo = MockEventRepo.return_value
            mock_event_repo.create_end_event = AsyncMock(return_value=MagicMock())

            await service.process_end_ping(mock_db, monitor)

            # Should have sent success notification
            mock_send_success.assert_called_once()


class TestProcessMonitorCheckMissed:
    """Tests for check_missed_starts and check_missed_ends methods."""

    @pytest.mark.asyncio
    async def test_check_missed_starts_no_monitors(self):
        """Test check_missed_starts when no monitors are waiting."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        mock_db = AsyncMock()

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository"),
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_monitors_waiting_for_start = AsyncMock(return_value=[])

            result = await service.check_missed_starts(mock_db)

            assert result == 0

    @pytest.mark.asyncio
    async def test_check_missed_starts_with_monitors(self):
        """Test check_missed_starts processes monitors correctly."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.notify_on_missed_start = False
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 3600
        monitor.timezone = "UTC"
        monitor.start_grace_period = 300

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_monitors_waiting_for_start = AsyncMock(return_value=[monitor])
            mock_repo.mark_missed_start = AsyncMock()

            mock_event_repo = MockEventRepo.return_value
            mock_event_repo.create_missed_event = AsyncMock()

            result = await service.check_missed_starts(mock_db)

            assert result == 1
            mock_event_repo.create_missed_event.assert_called_once()
            mock_repo.mark_missed_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_missed_starts_sends_notification(self):
        """Test check_missed_starts sends notification when enabled."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.notify_on_missed_start = True  # Notifications enabled
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 3600
        monitor.timezone = "UTC"
        monitor.start_grace_period = 300

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
            patch.object(service, "_send_missed_start_notification", new_callable=AsyncMock) as mock_send,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_monitors_waiting_for_start = AsyncMock(return_value=[monitor])
            mock_repo.mark_missed_start = AsyncMock()

            mock_event_repo = MockEventRepo.return_value
            mock_event_repo.create_missed_event = AsyncMock()

            await service.check_missed_starts(mock_db)

            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_missed_ends_no_monitors(self):
        """Test check_missed_ends when no monitors are waiting."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        mock_db = AsyncMock()

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository"),
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_monitors_waiting_for_end = AsyncMock(return_value=[])

            result = await service.check_missed_ends(mock_db)

            assert result == 0

    @pytest.mark.asyncio
    async def test_check_missed_ends_with_monitors(self):
        """Test check_missed_ends processes monitors correctly."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.current_run_id = str(uuid4())
        monitor.notify_on_missed_end = False
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 3600
        monitor.timezone = "UTC"
        monitor.start_grace_period = 300

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_monitors_waiting_for_end = AsyncMock(return_value=[monitor])
            mock_repo.mark_missed_end = AsyncMock()

            mock_event_repo = MockEventRepo.return_value
            mock_event_repo.create_timeout_event = AsyncMock()

            result = await service.check_missed_ends(mock_db)

            assert result == 1
            mock_event_repo.create_timeout_event.assert_called_once()
            mock_repo.mark_missed_end.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_missed_ends_sends_notification(self):
        """Test check_missed_ends sends notification when enabled."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.current_run_id = str(uuid4())
        monitor.notify_on_missed_end = True  # Notifications enabled
        monitor.schedule_type = ScheduleType.INTERVAL
        monitor.schedule_interval = 3600
        monitor.timezone = "UTC"
        monitor.start_grace_period = 300

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
            patch.object(service, "_send_missed_end_notification", new_callable=AsyncMock) as mock_send,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_monitors_waiting_for_end = AsyncMock(return_value=[monitor])
            mock_repo.mark_missed_end = AsyncMock()

            mock_event_repo = MockEventRepo.return_value
            mock_event_repo.create_timeout_event = AsyncMock()

            await service.check_missed_ends(mock_db)

            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_missed_starts_handles_exception(self):
        """Test check_missed_starts handles exceptions gracefully."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_monitors_waiting_for_start = AsyncMock(return_value=[monitor])

            mock_event_repo = MockEventRepo.return_value
            mock_event_repo.create_missed_event = AsyncMock(side_effect=Exception("DB Error"))

            result = await service.check_missed_starts(mock_db)

            # Should rollback on error
            mock_db.rollback.assert_called_once()
            assert result == 0

    @pytest.mark.asyncio
    async def test_check_missed_ends_handles_exception(self):
        """Test check_missed_ends handles exceptions gracefully."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.current_run_id = str(uuid4())

        with (
            patch("app.services.process_monitor.ProcessMonitorRepository") as MockRepo,
            patch("app.services.process_monitor.ProcessMonitorEventRepository") as MockEventRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_monitors_waiting_for_end = AsyncMock(return_value=[monitor])

            mock_event_repo = MockEventRepo.return_value
            mock_event_repo.create_timeout_event = AsyncMock(side_effect=Exception("DB Error"))

            result = await service.check_missed_ends(mock_db)

            # Should rollback on error
            mock_db.rollback.assert_called_once()
            assert result == 0


class TestProcessMonitorNotifications:
    """Tests for notification methods."""

    @pytest.mark.asyncio
    async def test_send_missed_start_notification(self):
        """Test _send_missed_start_notification calls notification service."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.next_expected_start = datetime.utcnow()

        mock_db = AsyncMock()

        with (
            patch.object(service, "_get_workspace_settings", new_callable=AsyncMock) as mock_settings,
            patch("app.services.process_monitor.notification_service") as mock_notif,
        ):
            mock_settings.return_value = ("en", "UTC")
            mock_notif.send_task_failure = AsyncMock()

            await service._send_missed_start_notification(mock_db, monitor)

            mock_notif.send_task_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_missed_end_notification(self):
        """Test _send_missed_end_notification calls notification service."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.id = uuid4()
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"
        monitor.last_start_at = datetime.utcnow() - timedelta(hours=1)
        monitor.end_timeout = 3600

        mock_db = AsyncMock()

        with (
            patch.object(service, "_get_workspace_settings", new_callable=AsyncMock) as mock_settings,
            patch("app.services.process_monitor.notification_service") as mock_notif,
        ):
            mock_settings.return_value = ("en", "UTC")
            mock_notif.send_task_failure = AsyncMock()

            await service._send_missed_end_notification(mock_db, monitor)

            mock_notif.send_task_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_recovery_notification(self):
        """Test _send_recovery_notification calls notification service."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"

        mock_db = AsyncMock()

        with patch("app.services.process_monitor.notification_service") as mock_notif:
            mock_notif.send_task_recovery = AsyncMock()

            await service._send_recovery_notification(mock_db, monitor)

            mock_notif.send_task_recovery.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_success_notification(self):
        """Test _send_success_notification calls notification service."""
        from app.services.process_monitor import ProcessMonitorService

        service = ProcessMonitorService()

        monitor = MagicMock(spec=ProcessMonitor)
        monitor.workspace_id = uuid4()
        monitor.name = "Test Monitor"

        mock_db = AsyncMock()

        with patch("app.services.process_monitor.notification_service") as mock_notif:
            mock_notif.send_task_success = AsyncMock()

            await service._send_success_notification(mock_db, monitor, 5000)

            mock_notif.send_task_success.assert_called_once()
