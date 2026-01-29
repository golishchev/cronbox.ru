from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.ssl_monitor import SSLMonitorStatus
from app.schemas.cron_task import PaginationMeta


class SSLCertificateInfo(BaseModel):
    """SSL Certificate information."""

    issuer: str | None = None
    subject: str | None = None
    serial_number: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    days_until_expiry: int | None = None
    tls_version: str | None = None
    cipher_suite: str | None = None
    chain_valid: bool | None = None
    hostname_match: bool | None = None


class SSLCheckResult(BaseModel):
    """Result of an SSL certificate check."""

    success: bool
    status: SSLMonitorStatus
    certificate: SSLCertificateInfo | None = None
    error: str | None = None


class SSLMonitorBase(BaseModel):
    """Base SSL monitor schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    domain: str = Field(..., min_length=1, max_length=255, description="Domain to monitor (e.g., example.com)")
    port: int = Field(default=443, ge=1, le=65535)
    notify_on_expiring: bool = True
    notify_on_error: bool = True

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate and normalize domain name."""
        # Remove protocol if present
        v = v.strip().lower()
        if v.startswith("https://"):
            v = v[8:]
        elif v.startswith("http://"):
            v = v[7:]
        # Remove path if present
        v = v.split("/")[0]
        # Remove port if present (we have separate field)
        v = v.split(":")[0]
        # Basic validation
        if not v or len(v) > 255:
            raise ValueError("Invalid domain name")
        # Check for valid characters
        import re

        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$", v):
            raise ValueError("Invalid domain name format")
        return v


class SSLMonitorCreate(SSLMonitorBase):
    """Schema for creating an SSL monitor."""

    pass


class SSLMonitorUpdate(BaseModel):
    """Schema for updating an SSL monitor."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    notify_on_expiring: bool | None = None
    notify_on_error: bool | None = None


class SSLMonitorResponse(BaseModel):
    """Schema for SSL monitor response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    domain: str
    port: int
    status: SSLMonitorStatus
    is_paused: bool
    # Certificate info
    issuer: str | None
    subject: str | None
    serial_number: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    days_until_expiry: int | None
    # TLS info
    tls_version: str | None
    cipher_suite: str | None
    # Validation info
    chain_valid: bool | None
    hostname_match: bool | None
    # Check tracking
    last_check_at: datetime | None
    next_check_at: datetime | None
    last_error: str | None
    retry_count: int
    # Notifications
    notify_on_expiring: bool
    notify_on_error: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("valid_from", "valid_until", "last_check_at", "next_check_at", "created_at", "updated_at")
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        """Serialize datetime as UTC with 'Z' suffix for proper JS parsing."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class SSLMonitorListResponse(BaseModel):
    """Schema for SSL monitor list response."""

    monitors: list[SSLMonitorResponse]
    pagination: PaginationMeta
