"""TCP port check service for network monitoring."""

import asyncio
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TcpResult:
    """Result of a TCP port check operation."""

    success: bool
    connection_time: float | None  # ms
    duration_ms: float  # total execution time
    error_message: str | None = None


async def execute_tcp_check(
    host: str,
    port: int,
    timeout: float = 30.0,
) -> TcpResult:
    """
    Check if a TCP port is open by attempting to establish a connection.

    Args:
        host: Target host (IP address or domain name)
        port: Target port (1-65535)
        timeout: Connection timeout in seconds

    Returns:
        TcpResult with connection status and timing
    """
    start_time = time.monotonic()

    # Validate port
    if not 1 <= port <= 65535:
        return TcpResult(
            success=False,
            connection_time=None,
            duration_ms=0.0,
            error_message=f"Invalid port: {port}",
        )

    try:
        connection_start = time.monotonic()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        connection_time = (time.monotonic() - connection_start) * 1000

        # Close the connection
        writer.close()
        await writer.wait_closed()

        duration_ms = (time.monotonic() - start_time) * 1000

        return TcpResult(
            success=True,
            connection_time=connection_time,
            duration_ms=duration_ms,
            error_message=None,
        )

    except asyncio.TimeoutError:
        duration_ms = (time.monotonic() - start_time) * 1000
        return TcpResult(
            success=False,
            connection_time=None,
            duration_ms=duration_ms,
            error_message="Connection timeout",
        )
    except ConnectionRefusedError:
        duration_ms = (time.monotonic() - start_time) * 1000
        return TcpResult(
            success=False,
            connection_time=None,
            duration_ms=duration_ms,
            error_message="Connection refused (port closed)",
        )
    except OSError as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        error_msg = str(e)

        # Parse common errors
        if "Name or service not known" in error_msg or "nodename nor servname provided" in error_msg:
            error_msg = "Unknown host"
        elif "Network is unreachable" in error_msg:
            error_msg = "Network unreachable"
        elif "No route to host" in error_msg:
            error_msg = "No route to host"

        return TcpResult(
            success=False,
            connection_time=None,
            duration_ms=duration_ms,
            error_message=error_msg,
        )
    except Exception as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.exception(f"TCP check error for {host}:{port}: {e}")
        return TcpResult(
            success=False,
            connection_time=None,
            duration_ms=duration_ms,
            error_message=str(e),
        )
