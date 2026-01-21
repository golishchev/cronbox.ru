"""Tests for Pydantic schemas."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.cron_task import HttpMethod, TaskStatus
from app.schemas.cron_task import (
    CronTaskBase,
    CronTaskCreate,
    CronTaskResponse,
    CronTaskUpdate,
    PaginationMeta,
)


class TestCronTaskBase:
    """Tests for CronTaskBase schema."""

    def test_valid_cron_task(self):
        """Test creating valid cron task."""
        task = CronTaskBase(
            name="Test Task",
            url="https://api.example.com/webhook",
            schedule="0 * * * *",
        )

        assert task.name == "Test Task"
        assert str(task.url) == "https://api.example.com/webhook"
        assert task.schedule == "0 * * * *"
        assert task.method == HttpMethod.GET  # default

    def test_all_fields(self):
        """Test cron task with all fields."""
        task = CronTaskBase(
            name="Full Task",
            description="A task with all fields",
            url="https://api.example.com/endpoint",
            method=HttpMethod.POST,
            headers={"Authorization": "Bearer token"},
            body='{"key": "value"}',
            schedule="*/5 * * * *",
            timezone="America/New_York",
            timeout_seconds=60,
            retry_count=3,
            retry_delay_seconds=120,
            notify_on_failure=False,
            notify_on_recovery=True,
            worker_id=uuid4(),
        )

        assert task.description == "A task with all fields"
        assert task.method == HttpMethod.POST
        assert task.headers["Authorization"] == "Bearer token"
        assert task.body == '{"key": "value"}'
        assert task.timezone == "America/New_York"
        assert task.timeout_seconds == 60
        assert task.retry_count == 3
        assert task.retry_delay_seconds == 120
        assert task.notify_on_failure is False

    def test_name_min_length(self):
        """Test name minimum length validation."""
        with pytest.raises(ValidationError) as exc:
            CronTaskBase(
                name="",
                url="https://example.com",
                schedule="* * * * *",
            )
        assert "name" in str(exc.value)

    def test_name_max_length(self):
        """Test name maximum length validation."""
        with pytest.raises(ValidationError) as exc:
            CronTaskBase(
                name="x" * 256,
                url="https://example.com",
                schedule="* * * * *",
            )
        assert "name" in str(exc.value)

    def test_invalid_url(self):
        """Test invalid URL validation."""
        with pytest.raises(ValidationError) as exc:
            CronTaskBase(
                name="Test",
                url="not-a-valid-url",
                schedule="* * * * *",
            )
        assert "url" in str(exc.value).lower()

    def test_valid_cron_expressions(self):
        """Test various valid cron expressions."""
        valid_schedules = [
            "* * * * *",  # every minute
            "0 * * * *",  # every hour
            "0 0 * * *",  # every day at midnight
            "0 0 * * 0",  # every Sunday
            "*/5 * * * *",  # every 5 minutes
            "0 9-17 * * 1-5",  # work hours
            "0 0 1,15 * *",  # 1st and 15th of month
            "0 0 1 1 *",  # once a year
        ]

        for schedule in valid_schedules:
            task = CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule=schedule,
            )
            assert task.schedule == schedule

    def test_invalid_cron_expression(self):
        """Test invalid cron expressions are rejected."""
        invalid_schedules = [
            "invalid",
            "* * *",  # too few fields
            "60 * * * *",  # invalid minute
            "* 25 * * *",  # invalid hour
            "* * 32 * *",  # invalid day
            "* * * 13 *",  # invalid month
            "* * * * 8",  # invalid weekday
        ]

        for schedule in invalid_schedules:
            with pytest.raises(ValidationError):
                CronTaskBase(
                    name="Test",
                    url="https://example.com",
                    schedule=schedule,
                )

    def test_valid_timezones(self):
        """Test valid timezone values."""
        valid_timezones = [
            "Europe/Moscow",
            "America/New_York",
            "UTC",
            "Asia/Tokyo",
            "Pacific/Auckland",
        ]

        for tz in valid_timezones:
            task = CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="* * * * *",
                timezone=tz,
            )
            assert task.timezone == tz

    def test_invalid_timezone(self):
        """Test invalid timezone is rejected."""
        with pytest.raises(ValidationError) as exc:
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="* * * * *",
                timezone="Not/A/Timezone",
            )
        assert "timezone" in str(exc.value).lower()

    def test_timeout_bounds(self):
        """Test timeout_seconds bounds."""
        # Valid min
        task = CronTaskBase(
            name="Test",
            url="https://example.com",
            schedule="* * * * *",
            timeout_seconds=1,
        )
        assert task.timeout_seconds == 1

        # Valid max
        task = CronTaskBase(
            name="Test",
            url="https://example.com",
            schedule="* * * * *",
            timeout_seconds=300,
        )
        assert task.timeout_seconds == 300

        # Invalid below min
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="* * * * *",
                timeout_seconds=0,
            )

        # Invalid above max
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="* * * * *",
                timeout_seconds=301,
            )

    def test_retry_count_bounds(self):
        """Test retry_count bounds."""
        # Valid min
        task = CronTaskBase(
            name="Test",
            url="https://example.com",
            schedule="* * * * *",
            retry_count=0,
        )
        assert task.retry_count == 0

        # Valid max
        task = CronTaskBase(
            name="Test",
            url="https://example.com",
            schedule="* * * * *",
            retry_count=10,
        )
        assert task.retry_count == 10

        # Invalid
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="* * * * *",
                retry_count=11,
            )

    def test_retry_delay_bounds(self):
        """Test retry_delay_seconds bounds."""
        # Valid min
        task = CronTaskBase(
            name="Test",
            url="https://example.com",
            schedule="* * * * *",
            retry_delay_seconds=10,
        )
        assert task.retry_delay_seconds == 10

        # Valid max
        task = CronTaskBase(
            name="Test",
            url="https://example.com",
            schedule="* * * * *",
            retry_delay_seconds=3600,
        )
        assert task.retry_delay_seconds == 3600

        # Invalid below min
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="* * * * *",
                retry_delay_seconds=9,
            )

        # Invalid above max
        with pytest.raises(ValidationError):
            CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="* * * * *",
                retry_delay_seconds=3601,
            )


class TestCronTaskCreate:
    """Tests for CronTaskCreate schema."""

    def test_inherits_from_base(self):
        """Test CronTaskCreate inherits from CronTaskBase."""
        assert issubclass(CronTaskCreate, CronTaskBase)

    def test_create_task(self):
        """Test creating a task."""
        task = CronTaskCreate(
            name="My Task",
            url="https://api.example.com",
            schedule="0 0 * * *",
        )
        assert task.name == "My Task"


class TestCronTaskUpdate:
    """Tests for CronTaskUpdate schema."""

    def test_all_fields_optional(self):
        """Test all fields are optional."""
        update = CronTaskUpdate()
        assert update.name is None
        assert update.url is None
        assert update.schedule is None

    def test_partial_update(self):
        """Test partial update with some fields."""
        update = CronTaskUpdate(
            name="New Name",
            is_active=False,
        )
        assert update.name == "New Name"
        assert update.is_active is False
        assert update.url is None

    def test_schedule_validation_optional(self):
        """Test schedule validation when provided."""
        # Valid schedule
        update = CronTaskUpdate(schedule="0 0 * * *")
        assert update.schedule == "0 0 * * *"

        # Invalid schedule
        with pytest.raises(ValidationError):
            CronTaskUpdate(schedule="invalid")

    def test_none_schedule_allowed(self):
        """Test None schedule is allowed."""
        update = CronTaskUpdate(schedule=None)
        assert update.schedule is None


class TestPaginationMeta:
    """Tests for PaginationMeta schema."""

    def test_pagination_meta(self):
        """Test pagination metadata."""
        meta = PaginationMeta(
            page=1,
            limit=10,
            total=100,
            total_pages=10,
        )

        assert meta.page == 1
        assert meta.limit == 10
        assert meta.total == 100
        assert meta.total_pages == 10

    def test_first_page(self):
        """Test first page metadata."""
        meta = PaginationMeta(
            page=1,
            limit=25,
            total=50,
            total_pages=2,
        )
        assert meta.page == 1

    def test_empty_result(self):
        """Test empty result pagination."""
        meta = PaginationMeta(
            page=1,
            limit=10,
            total=0,
            total_pages=0,
        )
        assert meta.total == 0
        assert meta.total_pages == 0


class TestHttpMethod:
    """Tests for HttpMethod enum."""

    def test_all_methods(self):
        """Test all HTTP methods are defined."""
        methods = [m.value for m in HttpMethod]

        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "PATCH" in methods
        assert "DELETE" in methods

    def test_method_in_schema(self):
        """Test HTTP method in schema."""
        for method in HttpMethod:
            task = CronTaskBase(
                name="Test",
                url="https://example.com",
                schedule="* * * * *",
                method=method,
            )
            assert task.method == method


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses(self):
        """Test all task statuses are defined."""
        statuses = [s.value for s in TaskStatus]

        assert "pending" in statuses
        assert "running" in statuses
        assert "success" in statuses
        assert "failed" in statuses


class TestProtocolType:
    """Tests for ProtocolType enum and protocol-aware schema validation."""

    def test_all_protocol_types(self):
        """Test all protocol types are defined."""
        from app.models.cron_task import ProtocolType

        protocol_types = [p.value for p in ProtocolType]

        assert "http" in protocol_types
        assert "icmp" in protocol_types
        assert "tcp" in protocol_types

    def test_default_protocol_is_http(self):
        """Test default protocol type is HTTP."""
        task = CronTaskCreate(
            name="Test Task",
            url="https://api.example.com",
            schedule="* * * * *",
        )

        from app.models.cron_task import ProtocolType

        assert task.protocol_type == ProtocolType.HTTP

    def test_http_protocol_requires_url(self):
        """Test HTTP protocol requires URL."""
        from app.models.cron_task import ProtocolType

        with pytest.raises(ValidationError) as exc:
            CronTaskCreate(
                name="Test Task",
                protocol_type=ProtocolType.HTTP,
                schedule="* * * * *",
            )
        assert "url is required for HTTP protocol" in str(exc.value)

    def test_icmp_protocol_requires_host(self):
        """Test ICMP protocol requires host."""
        from app.models.cron_task import ProtocolType

        with pytest.raises(ValidationError) as exc:
            CronTaskCreate(
                name="Test Task",
                protocol_type=ProtocolType.ICMP,
                schedule="* * * * *",
            )
        assert "host is required for ICMP protocol" in str(exc.value)

    def test_tcp_protocol_requires_host_and_port(self):
        """Test TCP protocol requires host and port."""
        from app.models.cron_task import ProtocolType

        # Missing host
        with pytest.raises(ValidationError) as exc:
            CronTaskCreate(
                name="Test Task",
                protocol_type=ProtocolType.TCP,
                port=443,
                schedule="* * * * *",
            )
        assert "host is required for TCP protocol" in str(exc.value)

        # Missing port
        with pytest.raises(ValidationError) as exc:
            CronTaskCreate(
                name="Test Task",
                protocol_type=ProtocolType.TCP,
                host="example.com",
                schedule="* * * * *",
            )
        assert "port is required for TCP protocol" in str(exc.value)

    def test_valid_icmp_task(self):
        """Test creating valid ICMP task."""
        from app.models.cron_task import ProtocolType

        task = CronTaskCreate(
            name="Ping Test",
            protocol_type=ProtocolType.ICMP,
            host="example.com",
            icmp_count=5,
            schedule="*/5 * * * *",
        )

        assert task.protocol_type == ProtocolType.ICMP
        assert task.host == "example.com"
        assert task.icmp_count == 5

    def test_valid_tcp_task(self):
        """Test creating valid TCP task."""
        from app.models.cron_task import ProtocolType

        task = CronTaskCreate(
            name="Port Check",
            protocol_type=ProtocolType.TCP,
            host="db.example.com",
            port=5432,
            schedule="*/5 * * * *",
        )

        assert task.protocol_type == ProtocolType.TCP
        assert task.host == "db.example.com"
        assert task.port == 5432

    def test_icmp_count_bounds(self):
        """Test icmp_count bounds validation."""
        from app.models.cron_task import ProtocolType

        # Valid min
        task = CronTaskCreate(
            name="Test",
            protocol_type=ProtocolType.ICMP,
            host="example.com",
            icmp_count=1,
            schedule="* * * * *",
        )
        assert task.icmp_count == 1

        # Valid max
        task = CronTaskCreate(
            name="Test",
            protocol_type=ProtocolType.ICMP,
            host="example.com",
            icmp_count=10,
            schedule="* * * * *",
        )
        assert task.icmp_count == 10

        # Invalid below min
        with pytest.raises(ValidationError):
            CronTaskCreate(
                name="Test",
                protocol_type=ProtocolType.ICMP,
                host="example.com",
                icmp_count=0,
                schedule="* * * * *",
            )

        # Invalid above max
        with pytest.raises(ValidationError):
            CronTaskCreate(
                name="Test",
                protocol_type=ProtocolType.ICMP,
                host="example.com",
                icmp_count=11,
                schedule="* * * * *",
            )

    def test_port_bounds(self):
        """Test port bounds validation."""
        from app.models.cron_task import ProtocolType

        # Valid min
        task = CronTaskCreate(
            name="Test",
            protocol_type=ProtocolType.TCP,
            host="example.com",
            port=1,
            schedule="* * * * *",
        )
        assert task.port == 1

        # Valid max
        task = CronTaskCreate(
            name="Test",
            protocol_type=ProtocolType.TCP,
            host="example.com",
            port=65535,
            schedule="* * * * *",
        )
        assert task.port == 65535

        # Invalid below min
        with pytest.raises(ValidationError):
            CronTaskCreate(
                name="Test",
                protocol_type=ProtocolType.TCP,
                host="example.com",
                port=0,
                schedule="* * * * *",
            )

        # Invalid above max
        with pytest.raises(ValidationError):
            CronTaskCreate(
                name="Test",
                protocol_type=ProtocolType.TCP,
                host="example.com",
                port=65536,
                schedule="* * * * *",
            )

    def test_host_validation(self):
        """Test host field validation."""
        from app.models.cron_task import ProtocolType

        # Empty host is rejected
        with pytest.raises(ValidationError):
            CronTaskCreate(
                name="Test",
                protocol_type=ProtocolType.ICMP,
                host="",
                schedule="* * * * *",
            )

        # Whitespace-only host is rejected
        with pytest.raises(ValidationError):
            CronTaskCreate(
                name="Test",
                protocol_type=ProtocolType.ICMP,
                host="   ",
                schedule="* * * * *",
            )

    def test_host_whitespace_stripped(self):
        """Test that host whitespace is stripped."""
        from app.models.cron_task import ProtocolType

        task = CronTaskCreate(
            name="Test",
            protocol_type=ProtocolType.ICMP,
            host="  example.com  ",
            schedule="* * * * *",
        )
        assert task.host == "example.com"

    def test_icmp_default_count(self):
        """Test ICMP default count value."""
        from app.models.cron_task import ProtocolType

        task = CronTaskCreate(
            name="Test",
            protocol_type=ProtocolType.ICMP,
            host="example.com",
            schedule="* * * * *",
        )
        assert task.icmp_count == 3  # default

    def test_update_protocol_type(self):
        """Test updating protocol type in CronTaskUpdate."""
        from app.models.cron_task import ProtocolType

        # Update to ICMP
        update = CronTaskUpdate(
            protocol_type=ProtocolType.ICMP,
            host="ping.example.com",
        )
        assert update.protocol_type == ProtocolType.ICMP
        assert update.host == "ping.example.com"

        # Update to TCP
        update = CronTaskUpdate(
            protocol_type=ProtocolType.TCP,
            host="db.example.com",
            port=3306,
        )
        assert update.protocol_type == ProtocolType.TCP
        assert update.port == 3306

    def test_common_tcp_ports(self):
        """Test common TCP port values."""
        from app.models.cron_task import ProtocolType

        common_ports = [22, 80, 443, 3306, 5432, 6379, 27017]

        for port in common_ports:
            task = CronTaskCreate(
                name=f"Port {port} Check",
                protocol_type=ProtocolType.TCP,
                host="example.com",
                port=port,
                schedule="* * * * *",
            )
            assert task.port == port

    def test_http_task_can_have_host_and_port(self):
        """Test HTTP task can optionally have host and port without affecting HTTP behavior."""
        from app.models.cron_task import ProtocolType

        # HTTP task with extra fields (shouldn't fail)
        task = CronTaskCreate(
            name="Test HTTP",
            protocol_type=ProtocolType.HTTP,
            url="https://api.example.com",
            host="optional.host.com",  # ignored for HTTP
            port=8080,  # ignored for HTTP
            schedule="* * * * *",
        )

        assert task.protocol_type == ProtocolType.HTTP
        assert str(task.url) == "https://api.example.com/"
