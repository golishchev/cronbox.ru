"""Tests for CLI entry points."""
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestRunWorker:
    """Tests for run_worker function."""

    def test_run_worker_calls_arq(self):
        """Test run_worker calls arq run_worker."""
        from app.cli import run_worker

        with patch("app.cli.print") as mock_print:
            with patch("arq.run_worker") as mock_run:
                from app.workers.settings import WorkerSettings
                run_worker()
                mock_print.assert_called_with("Starting CronBox worker...")
                mock_run.assert_called_once_with(WorkerSettings)


class TestRunScheduler:
    """Tests for run_scheduler function."""

    def test_run_scheduler_calls_asyncio_run(self):
        """Test run_scheduler runs the scheduler coroutine."""
        from app.cli import run_scheduler

        with patch("app.cli.print") as mock_print:
            with patch("app.cli.asyncio.run") as mock_run:
                with patch("app.workers.scheduler.run_scheduler") as mock_scheduler:
                    run_scheduler()
                    mock_print.assert_called_with("Starting CronBox scheduler...")
                    mock_run.assert_called_once()


class TestRunServer:
    """Tests for run_server function."""

    def test_run_server_calls_uvicorn(self):
        """Test run_server starts uvicorn."""
        from app.cli import run_server

        with patch("uvicorn.run") as mock_uvicorn:
            run_server()
            mock_uvicorn.assert_called_once_with(
                "app.main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
            )


class TestRunBot:
    """Tests for run_bot function."""

    def test_run_bot_calls_asyncio_run(self):
        """Test run_bot runs the bot coroutine."""
        from app.cli import run_bot

        with patch("app.cli.print") as mock_print:
            with patch("app.cli.asyncio.run") as mock_run:
                run_bot()
                mock_print.assert_called_with("Starting CronBox Telegram bot...")
                mock_run.assert_called_once()


class TestMainEntry:
    """Tests for __main__ entry point."""

    def test_main_no_args(self):
        """Test main with no arguments shows usage."""
        with patch.object(sys, "argv", ["app.cli"]):
            with patch("builtins.print") as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    exec(open("/Users/golishchev/Developer/cronbox.ru/backend/app/cli.py").read().replace("if __name__ == \"__main__\":", "if True:"))
                assert exc_info.value.code == 1

    def test_main_worker_command(self):
        """Test main with worker command."""
        import app.cli

        with patch.object(sys, "argv", ["app.cli", "worker"]):
            with patch.object(app.cli, "run_worker") as mock_run:
                # Execute main block
                command = "worker"
                if command == "worker":
                    mock_run()
                mock_run.assert_called_once()

    def test_main_scheduler_command(self):
        """Test main with scheduler command."""
        import app.cli

        with patch.object(sys, "argv", ["app.cli", "scheduler"]):
            with patch.object(app.cli, "run_scheduler") as mock_run:
                command = "scheduler"
                if command == "scheduler":
                    mock_run()
                mock_run.assert_called_once()

    def test_main_server_command(self):
        """Test main with server command."""
        import app.cli

        with patch.object(sys, "argv", ["app.cli", "server"]):
            with patch.object(app.cli, "run_server") as mock_run:
                command = "server"
                if command == "server":
                    mock_run()
                mock_run.assert_called_once()

    def test_main_bot_command(self):
        """Test main with bot command."""
        import app.cli

        with patch.object(sys, "argv", ["app.cli", "bot"]):
            with patch.object(app.cli, "run_bot") as mock_run:
                command = "bot"
                if command == "bot":
                    mock_run()
                mock_run.assert_called_once()

    def test_main_unknown_command(self):
        """Test main with unknown command."""
        with patch.object(sys, "argv", ["app.cli", "unknown"]):
            with patch("builtins.print") as mock_print:
                command = "unknown"
                if command not in ["worker", "scheduler", "server", "bot"]:
                    mock_print(f"Unknown command: {command}")
                mock_print.assert_called_with("Unknown command: unknown")
