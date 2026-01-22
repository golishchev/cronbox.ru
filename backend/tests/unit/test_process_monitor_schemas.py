"""Unit tests for ProcessMonitor schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.process_monitor import (
    ProcessMonitorBase,
    ProcessMonitorCreate,
    ProcessMonitorResponse,
    ProcessMonitorUpdate,
    format_seconds_to_interval,
    parse_interval_to_seconds,
)


class TestParseIntervalToSeconds:
    """Tests for parse_interval_to_seconds function."""

    def test_parse_seconds(self):
        """Test parsing seconds."""
        assert parse_interval_to_seconds("60s") == 60
        assert parse_interval_to_seconds("120s") == 120

    def test_parse_minutes(self):
        """Test parsing minutes."""
        assert parse_interval_to_seconds("5m") == 300
        assert parse_interval_to_seconds("30m") == 1800

    def test_parse_hours(self):
        """Test parsing hours."""
        assert parse_interval_to_seconds("1h") == 3600
        assert parse_interval_to_seconds("6h") == 21600

    def test_parse_days(self):
        """Test parsing days."""
        assert parse_interval_to_seconds("1d") == 86400
        assert parse_interval_to_seconds("7d") == 604800

    def test_parse_integer_string(self):
        """Test parsing integer string (treated as seconds)."""
        assert parse_interval_to_seconds("300") == 300
        assert parse_interval_to_seconds("3600") == 3600


class TestFormatSecondsToInterval:
    """Tests for format_seconds_to_interval function."""

    def test_format_seconds(self):
        """Test formatting seconds (not divisible by 60)."""
        assert format_seconds_to_interval(45) == "45s"
        assert format_seconds_to_interval(90) == "90s"

    def test_format_minutes(self):
        """Test formatting minutes (divisible by 60)."""
        assert format_seconds_to_interval(60) == "1m"
        assert format_seconds_to_interval(120) == "2m"
        assert format_seconds_to_interval(1800) == "30m"

    def test_format_hours(self):
        """Test formatting hours."""
        assert format_seconds_to_interval(3600) == "1h"
        assert format_seconds_to_interval(21600) == "6h"

    def test_format_days(self):
        """Test formatting days."""
        assert format_seconds_to_interval(86400) == "1d"
        assert format_seconds_to_interval(604800) == "7d"


class TestProcessMonitorBaseValidation:
    """Tests for ProcessMonitorBase validation."""

    def test_valid_cron_schedule(self):
        """Test valid cron schedule."""
        monitor = ProcessMonitorCreate(
            name="Test Monitor",
            schedule_type="cron",
            schedule_cron="0 2 * * *",
            start_grace_period="5m",
            end_timeout="1h",
        )
        assert monitor.name == "Test Monitor"
        assert monitor.schedule_type.value == "cron"

    def test_valid_interval_schedule(self):
        """Test valid interval schedule."""
        monitor = ProcessMonitorCreate(
            name="Test Monitor",
            schedule_type="interval",
            schedule_interval="6h",
            start_grace_period="5m",
            end_timeout="1h",
        )
        assert monitor.schedule_interval == "6h"

    def test_valid_exact_time_schedule(self):
        """Test valid exact time schedule."""
        monitor = ProcessMonitorCreate(
            name="Test Monitor",
            schedule_type="exact_time",
            schedule_exact_time="09:00",
            start_grace_period="5m",
            end_timeout="1h",
        )
        assert monitor.schedule_exact_time == "09:00"

    def test_exact_time_normalizes_format(self):
        """Test that exact time is normalized to HH:MM format."""
        monitor = ProcessMonitorCreate(
            name="Test Monitor",
            schedule_type="exact_time",
            schedule_exact_time="9:5",  # Will be normalized to 09:05
            start_grace_period="5m",
            end_timeout="1h",
        )
        assert monitor.schedule_exact_time == "09:05"

    def test_invalid_exact_time_hour(self):
        """Test invalid hour in exact time."""
        with pytest.raises(ValidationError):
            ProcessMonitorCreate(
                name="Test Monitor",
                schedule_type="exact_time",
                schedule_exact_time="25:00",  # Invalid hour
                start_grace_period="5m",
                end_timeout="1h",
            )

    def test_invalid_exact_time_minute(self):
        """Test invalid minute in exact time."""
        with pytest.raises(ValidationError):
            ProcessMonitorCreate(
                name="Test Monitor",
                schedule_type="exact_time",
                schedule_exact_time="12:60",  # Invalid minute
                start_grace_period="5m",
                end_timeout="1h",
            )

    def test_invalid_exact_time_format(self):
        """Test invalid format for exact time."""
        with pytest.raises(ValidationError):
            ProcessMonitorCreate(
                name="Test Monitor",
                schedule_type="exact_time",
                schedule_exact_time="12:00:00",  # HH:MM:SS not allowed
                start_grace_period="5m",
                end_timeout="1h",
            )

    def test_interval_too_short(self):
        """Test interval that's too short (< 60 seconds)."""
        with pytest.raises(ValidationError):
            ProcessMonitorCreate(
                name="Test Monitor",
                schedule_type="interval",
                schedule_interval="30s",  # Too short
                start_grace_period="5m",
                end_timeout="1h",
            )

    def test_interval_too_long(self):
        """Test interval that's too long (> 30 days)."""
        with pytest.raises(ValidationError):
            ProcessMonitorCreate(
                name="Test Monitor",
                schedule_type="interval",
                schedule_interval="31d",  # Too long
                start_grace_period="5m",
                end_timeout="1h",
            )

    def test_invalid_interval_format(self):
        """Test invalid interval format."""
        with pytest.raises(ValidationError):
            ProcessMonitorCreate(
                name="Test Monitor",
                schedule_type="interval",
                schedule_interval="invalid",
                start_grace_period="5m",
                end_timeout="1h",
            )


class TestProcessMonitorUpdateValidation:
    """Tests for ProcessMonitorUpdate validation."""

    def test_partial_update(self):
        """Test partial update with only name."""
        update = ProcessMonitorUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.schedule_type is None

    def test_valid_interval_update(self):
        """Test valid interval in update."""
        update = ProcessMonitorUpdate(schedule_interval="2h")
        assert update.schedule_interval == "2h"

    def test_invalid_interval_update(self):
        """Test invalid interval format in update."""
        with pytest.raises(ValidationError):
            ProcessMonitorUpdate(schedule_interval="invalid")

    def test_valid_exact_time_update(self):
        """Test valid exact time in update."""
        update = ProcessMonitorUpdate(schedule_exact_time="14:30")
        assert update.schedule_exact_time == "14:30"

    def test_invalid_exact_time_update(self):
        """Test invalid exact time in update."""
        with pytest.raises(ValidationError):
            ProcessMonitorUpdate(schedule_exact_time="25:00")
