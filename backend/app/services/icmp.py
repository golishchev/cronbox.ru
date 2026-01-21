"""ICMP (ping) service for network monitoring."""

import asyncio
import logging
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IcmpResult:
    """Result of an ICMP ping operation."""

    success: bool
    packets_sent: int
    packets_received: int
    packet_loss: float  # percentage
    min_rtt: float | None  # ms
    avg_rtt: float | None  # ms
    max_rtt: float | None  # ms
    duration_ms: float  # total execution time
    error_message: str | None = None


async def execute_icmp_ping(
    host: str,
    count: int = 3,
    timeout: float = 30.0,
) -> IcmpResult:
    """
    Execute ICMP ping using system ping command.

    Uses subprocess instead of raw sockets (doesn't require root/CAP_NET_RAW).

    Args:
        host: Target host (IP address or domain name)
        count: Number of ping packets to send (1-10)
        timeout: Total timeout in seconds

    Returns:
        IcmpResult with ping statistics
    """
    start_time = time.monotonic()

    # Validate inputs
    count = max(1, min(10, count))

    # Calculate per-packet timeout (total timeout / count, minimum 1 second)
    packet_timeout = max(1, int(timeout / count))

    # Build ping command (Linux compatible)
    # -c: count, -W: timeout per packet in seconds
    cmd = ["ping", "-c", str(count), "-W", str(packet_timeout), host]

    try:
        process = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=timeout,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        output = stdout.decode("utf-8", errors="replace")

        # Parse ping output
        return _parse_ping_output(output, count, duration_ms)

    except asyncio.TimeoutError:
        duration_ms = (time.monotonic() - start_time) * 1000
        return IcmpResult(
            success=False,
            packets_sent=count,
            packets_received=0,
            packet_loss=100.0,
            min_rtt=None,
            avg_rtt=None,
            max_rtt=None,
            duration_ms=duration_ms,
            error_message="Ping timeout",
        )
    except FileNotFoundError:
        duration_ms = (time.monotonic() - start_time) * 1000
        return IcmpResult(
            success=False,
            packets_sent=count,
            packets_received=0,
            packet_loss=100.0,
            min_rtt=None,
            avg_rtt=None,
            max_rtt=None,
            duration_ms=duration_ms,
            error_message="ping command not found",
        )
    except Exception as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.exception(f"ICMP ping error for {host}: {e}")
        return IcmpResult(
            success=False,
            packets_sent=count,
            packets_received=0,
            packet_loss=100.0,
            min_rtt=None,
            avg_rtt=None,
            max_rtt=None,
            duration_ms=duration_ms,
            error_message=str(e),
        )


def _parse_ping_output(output: str, count: int, duration_ms: float) -> IcmpResult:
    """
    Parse ping command output.

    Handles Linux ping output format:
    - Packet stats: "3 packets transmitted, 3 received, 0% packet loss"
    - RTT stats: "rtt min/avg/max/mdev = 0.123/0.234/0.345/0.056 ms"
    """
    packets_sent = count
    packets_received = 0
    packet_loss = 100.0
    min_rtt = None
    avg_rtt = None
    max_rtt = None
    error_message = None

    # Parse packet statistics
    # Example: "3 packets transmitted, 3 received, 0% packet loss"
    packet_match = re.search(
        r"(\d+)\s+packets?\s+transmitted,\s+(\d+)\s+(?:packets?\s+)?received",
        output,
        re.IGNORECASE,
    )
    if packet_match:
        packets_sent = int(packet_match.group(1))
        packets_received = int(packet_match.group(2))

    # Parse packet loss percentage
    loss_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:packet\s+)?loss", output, re.IGNORECASE)
    if loss_match:
        packet_loss = float(loss_match.group(1))
    elif packets_sent > 0:
        packet_loss = ((packets_sent - packets_received) / packets_sent) * 100

    # Parse RTT statistics
    # Example: "rtt min/avg/max/mdev = 0.123/0.234/0.345/0.056 ms"
    rtt_match = re.search(
        r"(?:rtt|round-trip)\s+min/avg/max(?:/mdev|/stddev)?\s*=\s*"
        r"([\d.]+)/([\d.]+)/([\d.]+)",
        output,
        re.IGNORECASE,
    )
    if rtt_match:
        min_rtt = float(rtt_match.group(1))
        avg_rtt = float(rtt_match.group(2))
        max_rtt = float(rtt_match.group(3))

    # Check for common errors
    if "unknown host" in output.lower() or "name or service not known" in output.lower():
        error_message = "Unknown host"
    elif "network is unreachable" in output.lower():
        error_message = "Network unreachable"
    elif "host unreachable" in output.lower():
        error_message = "Host unreachable"
    elif packets_received == 0:
        error_message = "No response"

    success = packets_received > 0 and packet_loss < 100.0

    return IcmpResult(
        success=success,
        packets_sent=packets_sent,
        packets_received=packets_received,
        packet_loss=packet_loss,
        min_rtt=min_rtt,
        avg_rtt=avg_rtt,
        max_rtt=max_rtt,
        duration_ms=duration_ms,
        error_message=error_message,
    )
