"""SSL Certificate Monitor service."""

import socket
import ssl
from datetime import datetime

import structlog
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.ssl_monitors import SSLMonitorRepository
from app.models.cron_task import HttpMethod, TaskStatus
from app.models.execution import Execution
from app.models.ssl_monitor import SSLMonitor, SSLMonitorStatus
from app.schemas.ssl_monitor import SSLCertificateInfo, SSLCheckResult
from app.services.notifications import notification_service

logger = structlog.get_logger()

# Notification thresholds (days before expiry)
NOTIFICATION_THRESHOLDS = [14, 7, 3, 1]


class SSLMonitorService:
    """Service for SSL certificate monitoring."""

    async def check_certificate(
        self,
        domain: str,
        port: int = 443,
        timeout: int = 10,
    ) -> SSLCheckResult:
        """Check SSL certificate for a domain.

        Returns SSLCheckResult with certificate info or error.
        """
        try:
            # Create SSL context
            context = ssl.create_default_context()

            # Connect and get certificate
            with socket.create_connection((domain, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    # Get certificate in DER format
                    der_cert = ssock.getpeercert(binary_form=True)
                    pem_cert_dict = ssock.getpeercert()

                    # Get TLS info
                    tls_version = ssock.version()
                    cipher_info = ssock.cipher()
                    cipher_suite = cipher_info[0] if cipher_info else None

                    # Parse certificate using cryptography
                    cert = x509.load_der_x509_certificate(der_cert, default_backend())

                    # Extract certificate info
                    issuer = self._format_name(cert.issuer)
                    subject = self._format_name(cert.subject)
                    serial_number = format(cert.serial_number, "x").upper()
                    valid_from = cert.not_valid_before_utc.replace(tzinfo=None)
                    valid_until = cert.not_valid_after_utc.replace(tzinfo=None)

                    # Calculate days until expiry
                    now = datetime.utcnow()
                    days_until_expiry = (valid_until - now).days

                    # Check hostname match
                    hostname_match = self._check_hostname(pem_cert_dict, domain)

                    # Chain is valid if we got here without SSL errors
                    chain_valid = True

                    # Determine status
                    if days_until_expiry < 0:
                        status = SSLMonitorStatus.EXPIRED
                    elif days_until_expiry <= 14:
                        status = SSLMonitorStatus.EXPIRING
                    else:
                        status = SSLMonitorStatus.VALID

                    # Check for validation issues
                    if not hostname_match:
                        status = SSLMonitorStatus.INVALID

                    cert_info = SSLCertificateInfo(
                        issuer=issuer,
                        subject=subject,
                        serial_number=serial_number,
                        valid_from=valid_from,
                        valid_until=valid_until,
                        days_until_expiry=days_until_expiry,
                        tls_version=tls_version,
                        cipher_suite=cipher_suite,
                        chain_valid=chain_valid,
                        hostname_match=hostname_match,
                    )

                    return SSLCheckResult(
                        success=True,
                        status=status,
                        certificate=cert_info,
                    )

        except ssl.SSLCertVerificationError as e:
            # Certificate validation failed (expired, untrusted, etc.)
            logger.warning("SSL verification error", domain=domain, error=str(e))
            return SSLCheckResult(
                success=False,
                status=SSLMonitorStatus.INVALID,
                error=f"SSL verification failed: {e}",
            )
        except ssl.SSLError as e:
            logger.warning("SSL error", domain=domain, error=str(e))
            return SSLCheckResult(
                success=False,
                status=SSLMonitorStatus.ERROR,
                error=f"SSL error: {e}",
            )
        except socket.timeout:
            logger.warning("Connection timeout", domain=domain)
            return SSLCheckResult(
                success=False,
                status=SSLMonitorStatus.ERROR,
                error="Connection timeout",
            )
        except socket.gaierror as e:
            logger.warning("DNS resolution failed", domain=domain, error=str(e))
            return SSLCheckResult(
                success=False,
                status=SSLMonitorStatus.ERROR,
                error=f"DNS resolution failed: {e}",
            )
        except ConnectionRefusedError:
            logger.warning("Connection refused", domain=domain, port=port)
            return SSLCheckResult(
                success=False,
                status=SSLMonitorStatus.ERROR,
                error=f"Connection refused on port {port}",
            )
        except Exception as e:
            logger.error("Unexpected error checking SSL", domain=domain, error=str(e))
            return SSLCheckResult(
                success=False,
                status=SSLMonitorStatus.ERROR,
                error=f"Unexpected error: {e}",
            )

    def _format_name(self, name: x509.Name) -> str:
        """Format X.509 name to string."""
        parts = []
        for attr in name:
            oid_name = attr.oid._name
            parts.append(f"{oid_name}={attr.value}")
        return ", ".join(parts)

    def _check_hostname(self, cert_dict: dict, hostname: str) -> bool:
        """Check if hostname matches certificate."""
        try:
            # Check subject alternative names
            san = cert_dict.get("subjectAltName", [])
            for type_, value in san:
                if type_ == "DNS":
                    if self._hostname_matches(value, hostname):
                        return True

            # Check common name as fallback
            subject = cert_dict.get("subject", ())
            for entry in subject:
                for key, value in entry:
                    if key == "commonName":
                        if self._hostname_matches(value, hostname):
                            return True

            return False
        except Exception:
            return False

    def _hostname_matches(self, pattern: str, hostname: str) -> bool:
        """Check if hostname matches a pattern (supports wildcards)."""
        pattern = pattern.lower()
        hostname = hostname.lower()

        if pattern.startswith("*."):
            # Wildcard certificate - include the dot in suffix
            # e.g., *.example.com -> suffix = ".example.com"
            suffix = pattern[1:]
            # Hostname should end with suffix and have at least one subdomain
            if hostname.endswith(suffix):
                prefix = hostname[: -len(suffix)]
                # Check there's exactly one level of subdomain (no dots in prefix)
                return prefix.count(".") == 0 and prefix != ""
            return False
        else:
            return pattern == hostname

    async def process_check(
        self,
        db: AsyncSession,
        monitor: SSLMonitor,
    ) -> SSLMonitor:
        """Check SSL certificate and update monitor with result."""
        ssl_repo = SSLMonitorRepository(db)

        # Track execution time
        started_at = datetime.utcnow()

        # Perform the check
        result = await self.check_certificate(monitor.domain, monitor.port)

        # Calculate duration
        finished_at = datetime.utcnow()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        # Create execution record
        is_success = result.success and result.status in (
            SSLMonitorStatus.VALID,
            SSLMonitorStatus.EXPIRING,
        )
        execution = Execution(
            workspace_id=monitor.workspace_id,
            task_type="ssl",
            task_id=monitor.id,
            task_name=monitor.name,
            ssl_monitor_id=monitor.id,
            status=TaskStatus.SUCCESS if is_success else TaskStatus.FAILED,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            request_url=f"https://{monitor.domain}:{monitor.port}",
            request_method=HttpMethod.GET,
            response_status_code=None,
            error_message=result.error if not is_success else None,
            error_type="ssl_error" if not is_success and result.error else None,
        )
        db.add(execution)

        # Update monitor with result
        if result.certificate:
            monitor = await ssl_repo.update_check_result(
                monitor=monitor,
                status=result.status,
                issuer=result.certificate.issuer,
                subject=result.certificate.subject,
                serial_number=result.certificate.serial_number,
                valid_from=result.certificate.valid_from,
                valid_until=result.certificate.valid_until,
                days_until_expiry=result.certificate.days_until_expiry,
                tls_version=result.certificate.tls_version,
                cipher_suite=result.certificate.cipher_suite,
                chain_valid=result.certificate.chain_valid,
                hostname_match=result.certificate.hostname_match,
            )
        else:
            monitor = await ssl_repo.update_check_result(
                monitor=monitor,
                status=result.status,
                error=result.error,
            )

        # Send notifications if needed
        await self._send_notifications_if_needed(db, monitor, result)

        logger.info(
            "SSL check completed",
            monitor_id=str(monitor.id),
            domain=monitor.domain,
            status=result.status.value,
            days_until_expiry=result.certificate.days_until_expiry if result.certificate else None,
        )

        return monitor

    async def _send_notifications_if_needed(
        self,
        db: AsyncSession,
        monitor: SSLMonitor,
        result: SSLCheckResult,
    ) -> None:
        """Send notifications based on check result."""
        # Check if notifications are enabled
        if not monitor.notify_on_expiring and not monitor.notify_on_error:
            return

        # Error notification
        if result.status == SSLMonitorStatus.ERROR and monitor.notify_on_error:
            await notification_service.send_ssl_error(
                db=db,
                workspace_id=monitor.workspace_id,
                monitor_name=monitor.name,
                domain=monitor.domain,
                error=result.error or "Unknown error",
            )
            return

        # Invalid certificate notification
        if result.status == SSLMonitorStatus.INVALID and monitor.notify_on_error:
            await notification_service.send_ssl_invalid(
                db=db,
                workspace_id=monitor.workspace_id,
                monitor_name=monitor.name,
                domain=monitor.domain,
                error=result.error or "Certificate validation failed",
            )
            return

        # Expiring/expired notifications
        if result.status in (SSLMonitorStatus.EXPIRING, SSLMonitorStatus.EXPIRED) and monitor.notify_on_expiring:
            days = result.certificate.days_until_expiry if result.certificate else 0

            # Check if we should send notification (at threshold days)
            should_notify = False
            notification_days = None

            for threshold in NOTIFICATION_THRESHOLDS:
                if days <= threshold:
                    # Check if we already sent notification for this threshold
                    if monitor.last_notification_days is None or monitor.last_notification_days > threshold:
                        should_notify = True
                        notification_days = threshold
                    break

            if should_notify and notification_days is not None:
                ssl_repo = SSLMonitorRepository(db)
                await ssl_repo.update_notification_sent(monitor, notification_days)

                await notification_service.send_ssl_expiring(
                    db=db,
                    workspace_id=monitor.workspace_id,
                    monitor_name=monitor.name,
                    domain=monitor.domain,
                    days_until_expiry=days,
                    valid_until=result.certificate.valid_until if result.certificate else None,
                )

    async def check_due_monitors(self, db: AsyncSession) -> int:
        """Check all monitors that are due for their daily check.

        Returns the number of monitors checked.
        """
        ssl_repo = SSLMonitorRepository(db)
        now = datetime.utcnow()

        # Get monitors due for regular check
        due_monitors = await ssl_repo.get_due_for_check(now, limit=50)
        count = 0

        for monitor in due_monitors:
            try:
                await self.process_check(db, monitor)
                count += 1
            except Exception as e:
                logger.error(
                    "Error processing SSL monitor",
                    monitor_id=str(monitor.id),
                    domain=monitor.domain,
                    error=str(e),
                )

        await db.commit()
        return count

    async def check_due_retries(self, db: AsyncSession) -> int:
        """Check all monitors that are due for retry.

        Returns the number of monitors checked.
        """
        ssl_repo = SSLMonitorRepository(db)
        now = datetime.utcnow()

        # Get monitors due for retry
        retry_monitors = await ssl_repo.get_due_for_retry(now, limit=50)
        count = 0

        for monitor in retry_monitors:
            try:
                await self.process_check(db, monitor)
                count += 1
            except Exception as e:
                logger.error(
                    "Error processing SSL monitor retry",
                    monitor_id=str(monitor.id),
                    domain=monitor.domain,
                    error=str(e),
                )

        await db.commit()
        return count


# Global instance
ssl_monitor_service = SSLMonitorService()
