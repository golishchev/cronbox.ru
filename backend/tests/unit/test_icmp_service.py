"""Tests for ICMP (ping) service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.icmp import IS_MACOS, IcmpResult, _parse_ping_output, execute_icmp_ping


class TestIcmpResult:
    """Tests for IcmpResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful ICMP result."""
        result = IcmpResult(
            success=True,
            packets_sent=3,
            packets_received=3,
            packet_loss=0.0,
            min_rtt=0.5,
            avg_rtt=1.0,
            max_rtt=1.5,
            duration_ms=100.0,
            error_message=None,
        )

        assert result.success is True
        assert result.packets_sent == 3
        assert result.packets_received == 3
        assert result.packet_loss == 0.0
        assert result.min_rtt == 0.5
        assert result.avg_rtt == 1.0
        assert result.max_rtt == 1.5
        assert result.duration_ms == 100.0
        assert result.error_message is None

    def test_failed_result(self):
        """Test creating a failed ICMP result."""
        result = IcmpResult(
            success=False,
            packets_sent=3,
            packets_received=0,
            packet_loss=100.0,
            min_rtt=None,
            avg_rtt=None,
            max_rtt=None,
            duration_ms=30000.0,
            error_message="No response",
        )

        assert result.success is False
        assert result.packets_received == 0
        assert result.packet_loss == 100.0
        assert result.error_message == "No response"

    def test_partial_loss_result(self):
        """Test creating a result with partial packet loss."""
        result = IcmpResult(
            success=True,
            packets_sent=3,
            packets_received=2,
            packet_loss=33.33,
            min_rtt=1.0,
            avg_rtt=2.0,
            max_rtt=3.0,
            duration_ms=150.0,
            error_message=None,
        )

        assert result.success is True
        assert result.packets_received == 2
        assert result.packet_loss == 33.33


class TestParsePingOutput:
    """Tests for _parse_ping_output function."""

    def test_parse_successful_ping(self):
        """Test parsing successful ping output."""
        output = """PING google.com (142.250.180.206) 56(84) bytes of data.
64 bytes from lhr25s33-in-f14.1e100.net (142.250.180.206): icmp_seq=1 ttl=117 time=10.3 ms
64 bytes from lhr25s33-in-f14.1e100.net (142.250.180.206): icmp_seq=2 ttl=117 time=9.50 ms
64 bytes from lhr25s33-in-f14.1e100.net (142.250.180.206): icmp_seq=3 ttl=117 time=9.83 ms

--- google.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 9.502/9.878/10.339/0.346 ms"""

        result = _parse_ping_output(output, 3, 2100.0)

        assert result.success is True
        assert result.packets_sent == 3
        assert result.packets_received == 3
        assert result.packet_loss == 0.0
        assert result.min_rtt == 9.502
        assert result.avg_rtt == 9.878
        assert result.max_rtt == 10.339
        assert result.error_message is None

    def test_parse_partial_loss(self):
        """Test parsing ping output with packet loss."""
        output = """PING 192.168.1.100 (192.168.1.100) 56(84) bytes of data.
64 bytes from 192.168.1.100: icmp_seq=1 ttl=64 time=0.5 ms

--- 192.168.1.100 ping statistics ---
3 packets transmitted, 1 received, 66.67% packet loss, time 2005ms
rtt min/avg/max/mdev = 0.500/0.500/0.500/0.000 ms"""

        result = _parse_ping_output(output, 3, 2100.0)

        assert result.success is True  # Some packets received
        assert result.packets_sent == 3
        assert result.packets_received == 1
        assert result.packet_loss == 66.67
        assert result.min_rtt == 0.500

    def test_parse_100_percent_loss(self):
        """Test parsing ping output with 100% packet loss."""
        output = """PING 10.255.255.1 (10.255.255.1) 56(84) bytes of data.

--- 10.255.255.1 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 2054ms"""

        result = _parse_ping_output(output, 3, 2100.0)

        assert result.success is False
        assert result.packets_sent == 3
        assert result.packets_received == 0
        assert result.packet_loss == 100.0
        assert result.min_rtt is None
        assert result.avg_rtt is None
        assert result.max_rtt is None
        assert result.error_message == "No response"

    def test_parse_unknown_host(self):
        """Test parsing ping output for unknown host."""
        output = """ping: unknown host nonexistent.invalid.domain"""

        result = _parse_ping_output(output, 3, 100.0)

        assert result.success is False
        assert result.error_message == "Unknown host"

    def test_parse_name_not_known(self):
        """Test parsing ping output when name is not known."""
        output = """ping: nonexistent.domain: Name or service not known"""

        result = _parse_ping_output(output, 3, 100.0)

        assert result.success is False
        assert result.error_message == "Unknown host"

    def test_parse_network_unreachable(self):
        """Test parsing ping output for network unreachable."""
        output = """ping: sendmsg: Network is unreachable
ping: sendmsg: Network is unreachable
ping: sendmsg: Network is unreachable

--- 192.0.2.1 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 2002ms"""

        result = _parse_ping_output(output, 3, 2100.0)

        assert result.success is False
        assert result.error_message == "Network unreachable"

    def test_parse_host_unreachable(self):
        """Test parsing ping output for host unreachable."""
        output = """PING 192.168.100.200 (192.168.100.200) 56(84) bytes of data.
From 192.168.1.1 icmp_seq=1 Destination Host Unreachable
From 192.168.1.1 icmp_seq=2 Destination Host Unreachable
From 192.168.1.1 icmp_seq=3 Destination Host Unreachable

--- 192.168.100.200 ping statistics ---
3 packets transmitted, 0 received, +3 errors, 100% packet loss, time 2006ms"""

        result = _parse_ping_output(output, 3, 2100.0)

        assert result.success is False
        assert result.error_message == "Host unreachable"

    def test_parse_with_mdev_format(self):
        """Test parsing ping output with mdev in RTT stats."""
        output = """--- test.example.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2002ms
rtt min/avg/max/mdev = 10.123/15.456/20.789/4.321 ms"""

        result = _parse_ping_output(output, 3, 2100.0)

        assert result.min_rtt == 10.123
        assert result.avg_rtt == 15.456
        assert result.max_rtt == 20.789

    def test_parse_with_stddev_format(self):
        """Test parsing ping output with stddev in RTT stats (BSD format)."""
        output = """--- test.example.com ping statistics ---
3 packets transmitted, 3 packets received, 0% packet loss
round-trip min/avg/max/stddev = 10.123/15.456/20.789/4.321 ms"""

        result = _parse_ping_output(output, 3, 2100.0)

        assert result.min_rtt == 10.123
        assert result.avg_rtt == 15.456
        assert result.max_rtt == 20.789

    def test_parse_empty_output(self):
        """Test parsing empty output."""
        result = _parse_ping_output("", 3, 100.0)

        assert result.success is False
        assert result.packets_received == 0
        assert result.error_message == "No response"

    def test_duration_passed_through(self):
        """Test that duration_ms is passed through correctly."""
        output = """--- test.example.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss"""

        result = _parse_ping_output(output, 3, 12345.67)

        assert result.duration_ms == 12345.67


class TestExecuteIcmpPing:
    """Tests for execute_icmp_ping function."""

    @pytest.mark.asyncio
    async def test_successful_ping(self):
        """Test successful ping execution."""
        mock_output = """PING test.com (1.2.3.4) 56(84) bytes of data.
64 bytes from test.com: icmp_seq=1 ttl=64 time=1.0 ms
64 bytes from test.com: icmp_seq=2 ttl=64 time=1.5 ms
64 bytes from test.com: icmp_seq=3 ttl=64 time=1.2 ms

--- test.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2002ms
rtt min/avg/max/mdev = 1.000/1.233/1.500/0.204 ms"""

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(mock_output.encode(), b""))

        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            result = await execute_icmp_ping("test.com", count=3, timeout=30.0)

            assert result.success is True
            assert result.packets_sent == 3
            assert result.packets_received == 3
            assert result.packet_loss == 0.0
            assert result.min_rtt == 1.0
            assert result.avg_rtt == 1.233
            assert result.max_rtt == 1.5

            # Verify ping command was called correctly
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0]
            assert "ping" in call_args
            assert "-c" in call_args
            assert "3" in call_args
            assert "test.com" in call_args

    @pytest.mark.asyncio
    async def test_ping_timeout(self):
        """Test ping timeout handling."""
        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = asyncio.TimeoutError()

            result = await execute_icmp_ping("slow.host.com", count=3, timeout=5.0)

            assert result.success is False
            assert result.packet_loss == 100.0
            assert result.error_message == "Ping timeout"

    @pytest.mark.asyncio
    async def test_ping_command_not_found(self):
        """Test when ping command is not found."""
        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = FileNotFoundError()

            result = await execute_icmp_ping("test.com", count=3)

            assert result.success is False
            assert result.error_message == "ping command not found"

    @pytest.mark.asyncio
    async def test_ping_generic_exception(self):
        """Test handling of generic exception during ping."""
        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Unexpected error")

            result = await execute_icmp_ping("test.com", count=3)

            assert result.success is False
            assert "Unexpected error" in result.error_message

    @pytest.mark.asyncio
    async def test_count_validation_min(self):
        """Test that count is clamped to minimum of 1."""
        mock_output = """3 packets transmitted, 3 received, 0% packet loss"""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(mock_output.encode(), b""))

        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            await execute_icmp_ping("test.com", count=0)  # Should be clamped to 1

            call_args = mock_create.call_args[0]
            assert "1" in call_args  # Count should be at least 1

    @pytest.mark.asyncio
    async def test_count_validation_max(self):
        """Test that count is clamped to maximum of 10."""
        mock_output = """10 packets transmitted, 10 received, 0% packet loss"""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(mock_output.encode(), b""))

        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            await execute_icmp_ping("test.com", count=20)  # Should be clamped to 10

            call_args = mock_create.call_args[0]
            assert "10" in call_args  # Count should be at most 10

    @pytest.mark.asyncio
    async def test_per_packet_timeout_calculation(self):
        """Test that per-packet timeout is calculated correctly."""
        mock_output = """3 packets transmitted, 3 received, 0% packet loss"""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(mock_output.encode(), b""))

        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            # 30 seconds total / 3 packets = 10 seconds per packet
            await execute_icmp_ping("test.com", count=3, timeout=30.0)

            call_args = mock_create.call_args[0]
            # Check for platform-specific timeout flag (-t on macOS, -W on Linux)
            timeout_flag = "-t" if IS_MACOS else "-W"
            assert timeout_flag in call_args
            flag_index = call_args.index(timeout_flag)
            assert call_args[flag_index + 1] == "10"  # 30/3 = 10

    @pytest.mark.asyncio
    async def test_minimum_per_packet_timeout(self):
        """Test that per-packet timeout is at least 1 second."""
        mock_output = """10 packets transmitted, 10 received, 0% packet loss"""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(mock_output.encode(), b""))

        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            # Very short total timeout should still give 1 second per packet
            await execute_icmp_ping("test.com", count=10, timeout=5.0)

            call_args = mock_create.call_args[0]
            # Check for platform-specific timeout flag (-t on macOS, -W on Linux)
            timeout_flag = "-t" if IS_MACOS else "-W"
            flag_index = call_args.index(timeout_flag)
            assert call_args[flag_index + 1] == "1"  # Minimum 1 second

    @pytest.mark.asyncio
    async def test_wait_for_process_timeout(self):
        """Test timeout during process.communicate()."""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            result = await execute_icmp_ping("test.com", count=3, timeout=5.0)

            assert result.success is False
            assert result.error_message == "Ping timeout"

    @pytest.mark.asyncio
    async def test_duration_measurement(self):
        """Test that duration is measured correctly."""
        mock_output = """3 packets transmitted, 3 received, 0% packet loss
rtt min/avg/max/mdev = 1.0/2.0/3.0/0.5 ms"""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(mock_output.encode(), b""))

        with patch("app.services.icmp.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            result = await execute_icmp_ping("test.com", count=3, timeout=30.0)

            # Duration should be measured and be >= 0
            assert result.duration_ms >= 0
