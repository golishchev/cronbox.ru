#!/usr/bin/env python3
"""
CronBox External Worker Client

This script runs as a worker that polls the CronBox API for tasks
assigned to it and executes them. Run this on your own infrastructure
to execute tasks against internal APIs.

Usage:
    1. Register a worker in CronBox UI and get the API key
    2. Set the environment variables:
       - CRONBOX_API_URL: Your CronBox API URL (e.g., https://api.cronbox.ru)
       - CRONBOX_WORKER_KEY: Your worker API key (wk_...)
    3. Run: python worker_client.py

Requirements:
    pip install httpx
"""

import asyncio
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

# Configuration
API_URL = os.environ.get("CRONBOX_API_URL", "http://localhost:8000/v1")
WORKER_KEY = os.environ.get("CRONBOX_WORKER_KEY", "")
POLL_INTERVAL = int(os.environ.get("CRONBOX_POLL_INTERVAL", "5"))
MAX_CONCURRENT_TASKS = int(os.environ.get("CRONBOX_MAX_CONCURRENT", "5"))
HEARTBEAT_INTERVAL = 30


class CronBoxWorker:
    """CronBox external worker client."""

    def __init__(self, api_url: str, worker_key: str):
        self.api_url = api_url.rstrip("/")
        self.worker_key = worker_key
        self.running = False
        self.current_tasks = 0
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

        self.client = httpx.AsyncClient(
            headers={"X-Worker-Key": worker_key},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    async def start(self):
        """Start the worker."""
        self.running = True
        print("[Worker] Starting CronBox worker...")
        print(f"[Worker] API URL: {self.api_url}")
        print(f"[Worker] Poll interval: {POLL_INTERVAL}s")
        print(f"[Worker] Max concurrent tasks: {MAX_CONCURRENT_TASKS}")

        # Verify connection
        try:
            info = await self.get_worker_info()
            print(f"[Worker] Connected as: {info['name']} ({info['id']})")
        except Exception as e:
            print(f"[Worker] Failed to connect: {e}")
            return

        # Run main loops
        await asyncio.gather(
            self._poll_loop(),
            self._heartbeat_loop(),
        )

    async def stop(self):
        """Stop the worker."""
        self.running = False
        await self.client.aclose()
        print("[Worker] Stopped")

    async def get_worker_info(self) -> dict:
        """Get worker information from API."""
        response = await self.client.get(f"{self.api_url}/worker/info")
        response.raise_for_status()
        return response.json()

    async def send_heartbeat(self):
        """Send heartbeat to API."""
        try:
            response = await self.client.post(
                f"{self.api_url}/worker/heartbeat",
                json={
                    "status": "busy" if self.current_tasks > 0 else "online",
                    "current_tasks": self.current_tasks,
                },
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[Worker] Heartbeat failed: {e}")

    async def poll_tasks(self) -> list[dict]:
        """Poll for pending tasks."""
        try:
            response = await self.client.get(
                f"{self.api_url}/worker/tasks",
                params={"max_tasks": MAX_CONCURRENT_TASKS - self.current_tasks},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("tasks", [])
        except Exception as e:
            print(f"[Worker] Poll failed: {e}")
            return []

    async def submit_result(self, result: dict):
        """Submit task execution result."""
        try:
            response = await self.client.post(
                f"{self.api_url}/worker/tasks/result",
                json=result,
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[Worker] Failed to submit result: {e}")

    async def execute_task(self, task: dict):
        """Execute a single HTTP task."""
        task_id = task["task_id"]
        task_name = task.get("task_name") or task_id[:8]

        print(f"[Task {task_name}] Starting: {task['method']} {task['url']}")

        started_at = datetime.now(timezone.utc)
        result: dict[str, Any] = {
            "task_id": task_id,
            "task_type": task["task_type"],
            "started_at": started_at.isoformat(),
        }

        try:
            async with self.semaphore:
                self.current_tasks += 1

                # Execute HTTP request
                response = await self.client.request(
                    method=task["method"],
                    url=task["url"],
                    headers=task.get("headers", {}),
                    content=task.get("body"),
                    timeout=task.get("timeout_seconds", 30),
                )

                finished_at = datetime.now(timezone.utc)
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)

                result.update({
                    "status_code": response.status_code,
                    "response_body": response.text[:10000] if response.text else None,
                    "response_headers": dict(response.headers),
                    "finished_at": finished_at.isoformat(),
                    "duration_ms": duration_ms,
                })

                print(f"[Task {task_name}] Completed: {response.status_code} ({duration_ms}ms)")

        except httpx.TimeoutException:
            finished_at = datetime.now(timezone.utc)
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            result.update({
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
                "error": "Request timed out",
                "error_type": "timeout",
            })
            print(f"[Task {task_name}] Timeout after {duration_ms}ms")

        except httpx.ConnectError as e:
            finished_at = datetime.now(timezone.utc)
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            result.update({
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
                "error": str(e),
                "error_type": "connection_error",
            })
            print(f"[Task {task_name}] Connection error: {e}")

        except Exception as e:
            finished_at = datetime.now(timezone.utc)
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            result.update({
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
                "error": str(e),
                "error_type": "unknown",
            })
            print(f"[Task {task_name}] Error: {e}")

        finally:
            self.current_tasks -= 1

        # Submit result
        await self.submit_result(result)

    async def _poll_loop(self):
        """Main polling loop."""
        while self.running:
            try:
                # Only poll if we have capacity
                if self.current_tasks < MAX_CONCURRENT_TASKS:
                    tasks = await self.poll_tasks()

                    for task in tasks:
                        # Execute tasks concurrently
                        asyncio.create_task(self.execute_task(task))

            except Exception as e:
                print(f"[Worker] Poll loop error: {e}")

            await asyncio.sleep(POLL_INTERVAL)

    async def _heartbeat_loop(self):
        """Heartbeat loop."""
        while self.running:
            await self.send_heartbeat()
            await asyncio.sleep(HEARTBEAT_INTERVAL)


async def main():
    """Main entry point."""
    if not WORKER_KEY:
        print("Error: CRONBOX_WORKER_KEY environment variable is required")
        print("\nUsage:")
        print("  export CRONBOX_API_URL=https://api.cronbox.ru/v1")
        print("  export CRONBOX_WORKER_KEY=wk_your_api_key_here")
        print("  python worker_client.py")
        sys.exit(1)

    worker = CronBoxWorker(API_URL, WORKER_KEY)

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n[Worker] Shutting down...")
        asyncio.create_task(worker.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
