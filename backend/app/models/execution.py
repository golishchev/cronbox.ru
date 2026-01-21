from datetime import datetime
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin
from app.models.cron_task import HttpMethod, ProtocolType, TaskStatus


class Execution(Base, UUIDMixin):
    """Execution log model - stores results of task executions."""

    __tablename__ = "executions"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    # Task reference
    task_type: Mapped[str] = mapped_column(String(20))  # 'cron', 'delayed', 'chain', 'heartbeat', 'ssl'
    task_id: Mapped[UUID] = mapped_column(index=True)
    task_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Cron task relationship (optional)
    cron_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cron_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # SSL monitor relationship (optional)
    ssl_monitor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ssl_monitors.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Execution details
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus))
    started_at: Mapped[datetime] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_attempt: Mapped[int] = mapped_column(Integer, default=0)

    # Request (for HTTP protocol)
    request_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    request_method: Mapped[HttpMethod | None] = mapped_column(SQLEnum(HttpMethod), nullable=True)
    request_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Response
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)  # Limited
    response_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Protocol type (http, icmp, tcp)
    protocol_type: Mapped[ProtocolType | None] = mapped_column(
        SQLEnum(ProtocolType, values_callable=lambda x: [e.value for e in x], create_type=False),
        nullable=True,
    )

    # ICMP/TCP target info
    target_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ICMP results
    icmp_packets_sent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    icmp_packets_received: Mapped[int | None] = mapped_column(Integer, nullable=True)
    icmp_packet_loss: Mapped[float | None] = mapped_column(Float, nullable=True)  # percentage
    icmp_min_rtt: Mapped[float | None] = mapped_column(Float, nullable=True)  # ms
    icmp_avg_rtt: Mapped[float | None] = mapped_column(Float, nullable=True)  # ms
    icmp_max_rtt: Mapped[float | None] = mapped_column(Float, nullable=True)  # ms

    # TCP results
    tcp_connection_time: Mapped[float | None] = mapped_column(Float, nullable=True)  # ms

    # Overlap prevention
    skipped_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    cron_task: Mapped["CronTask | None"] = relationship(back_populates="executions")
