"""CLI entry points for CronBox."""

import asyncio
import sys


def run_worker():
    """Run the arq worker."""
    from arq import run_worker as arq_run_worker

    from app.workers.settings import WorkerSettings

    print("Starting CronBox worker...")
    arq_run_worker(WorkerSettings)


def run_scheduler():
    """Run the task scheduler."""
    from app.workers.scheduler import run_scheduler as scheduler_main

    print("Starting CronBox scheduler...")
    asyncio.run(scheduler_main())


def run_server():
    """Run the API server."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


def run_bot():
    """Run the Telegram bot."""
    from app.bot.handlers import run_bot as bot_main

    print("Starting CronBox Telegram bot...")
    asyncio.run(bot_main())


def run_max_bot():
    """Run the MAX bot."""
    from app.bot.max_handlers import run_max_bot as max_bot_main

    print("Starting CronBox MAX bot...")
    asyncio.run(max_bot_main())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli <command>")
        print("Commands: worker, scheduler, server, bot, max-bot")
        sys.exit(1)

    command = sys.argv[1]

    if command == "worker":
        run_worker()
    elif command == "scheduler":
        run_scheduler()
    elif command == "server":
        run_server()
    elif command == "bot":
        run_bot()
    elif command == "max-bot":
        run_max_bot()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
