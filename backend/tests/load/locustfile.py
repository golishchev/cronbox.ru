"""
CronBox Load Testing with Locust

Запуск:
    # Установка
    pip install locust

    # Web UI (рекомендуется)
    cd backend/tests/load
    locust -f locustfile.py --host=http://localhost:8000

    # Headless режим
    locust -f locustfile.py --host=http://localhost:8000 \
        --users 100 --spawn-rate 10 --run-time 5m --headless

    # С HTML отчётом
    locust -f locustfile.py --host=http://localhost:8000 \
        --users 100 --spawn-rate 10 --run-time 5m --headless \
        --html=report.html

Сценарии:
    - ReadHeavyUser: 80% чтение, 20% запись (типичный пользователь)
    - WriteHeavyUser: 50% чтение, 50% запись (активный пользователь)
    - APIUser: только API операции без UI (для тестирования API лимитов)
"""

import json
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from locust import HttpUser, TaskSet, between, events, task

# ============================================================================
# Конфигурация
# ============================================================================

# Тестовые пользователи (создайте заранее или используйте регистрацию)
TEST_USERS = [
    {"email": "loadtest1@example.com", "password": "LoadTest123!"},
    {"email": "loadtest2@example.com", "password": "LoadTest123!"},
    {"email": "loadtest3@example.com", "password": "LoadTest123!"},
    {"email": "loadtest4@example.com", "password": "LoadTest123!"},
    {"email": "loadtest5@example.com", "password": "LoadTest123!"},
]

# Тестовый webhook endpoint (используйте httpbin или свой сервис)
TEST_WEBHOOK_URL = "https://httpbin.org/post"

# API prefix
API_PREFIX = "/v1"


# ============================================================================
# Утилиты
# ============================================================================


def random_string(length: int = 8) -> str:
    """Генерация случайной строки."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_cron_schedule() -> str:
    """Генерация случайного cron расписания."""
    schedules = [
        "*/15 * * * *",  # каждые 15 минут
        "0 * * * *",  # каждый час
        "0 */2 * * *",  # каждые 2 часа
        "0 0 * * *",  # ежедневно в полночь
        "0 9 * * 1-5",  # будни в 9:00
    ]
    return random.choice(schedules)


def future_datetime(minutes: int = 30) -> str:
    """Генерация datetime в будущем."""
    dt = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# Base User Class
# ============================================================================


class CronBoxUser(HttpUser):
    """Базовый класс пользователя CronBox."""

    abstract = True
    host = "http://localhost:8000"  # Default host (можно переопределить через --host)
    wait_time = between(1, 3)  # Пауза между запросами 1-3 сек

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.workspace_id: Optional[str] = None
        self.cron_task_ids: list[str] = []
        self.delayed_task_ids: list[str] = []

    def on_start(self):
        """Выполняется при старте каждого виртуального пользователя."""
        self.login()
        if self.token:
            self.get_or_create_workspace()

    def login(self):
        """Авторизация пользователя."""
        user = random.choice(TEST_USERS)

        with self.client.post(
            f"{API_PREFIX}/auth/login", json=user, catch_response=True, name="POST /auth/login"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data["tokens"]["access_token"]
                self.refresh_token = data["tokens"]["refresh_token"]
                self.user_id = data["user"]["id"]
                response.success()
            elif response.status_code == 401:
                # Пользователь не существует - попробуем зарегистрировать
                self.register(user)
            else:
                response.failure(f"Login failed: {response.status_code}")

    def register(self, user: dict):
        """Регистрация нового пользователя."""
        with self.client.post(
            f"{API_PREFIX}/auth/register",
            json={"email": user["email"], "password": user["password"], "name": f"Load Test User {random_string(4)}"},
            catch_response=True,
            name="POST /auth/register",
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.token = data["tokens"]["access_token"]
                self.refresh_token = data["tokens"]["refresh_token"]
                self.user_id = data["user"]["id"]
                response.success()
            else:
                response.failure(f"Register failed: {response.status_code}")

    def get_headers(self) -> dict:
        """Получить заголовки с авторизацией."""
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get_or_create_workspace(self):
        """Получить или создать workspace."""
        # Сначала пробуем получить список
        with self.client.get(
            f"{API_PREFIX}/workspaces", headers=self.get_headers(), catch_response=True, name="GET /workspaces"
        ) as response:
            if response.status_code == 200:
                workspaces = response.json()
                if workspaces:
                    self.workspace_id = workspaces[0]["id"]
                    response.success()
                    return
                response.success()
            else:
                response.failure(f"Get workspaces failed: {response.status_code}")
                return

        # Если нет workspaces - создаём
        with self.client.post(
            f"{API_PREFIX}/workspaces",
            headers=self.get_headers(),
            json={
                "name": f"Load Test Workspace {random_string(6)}",
                "slug": f"load-test-{random_string(6)}",
                "default_timezone": "Europe/Moscow",
            },
            catch_response=True,
            name="POST /workspaces",
        ) as response:
            if response.status_code == 201:
                self.workspace_id = response.json()["id"]
                response.success()
            else:
                response.failure(f"Create workspace failed: {response.status_code}")


# ============================================================================
# Read-Heavy User (типичный пользователь)
# ============================================================================


class ReadHeavyUser(CronBoxUser):
    """
    Типичный пользователь: много чтения, мало записи.
    Соотношение: 80% чтение, 20% запись.
    """

    weight = 8  # 80% пользователей этого типа

    # === Операции чтения (высокий вес) ===

    @task(10)
    def list_cron_tasks(self):
        """Получить список cron задач."""
        if not self.workspace_id:
            return

        with self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron",
            headers=self.get_headers(),
            params={"page": 1, "limit": 20},
            catch_response=True,
            name="GET /workspaces/{id}/cron",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Сохраняем ID задач для других операций
                self.cron_task_ids = [t["id"] for t in data.get("tasks", [])]
                response.success()
            else:
                response.failure(f"List cron tasks failed: {response.status_code}")

    @task(10)
    def list_delayed_tasks(self):
        """Получить список отложенных задач."""
        if not self.workspace_id:
            return

        with self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/delayed",
            headers=self.get_headers(),
            params={"page": 1, "limit": 20},
            catch_response=True,
            name="GET /workspaces/{id}/delayed",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.delayed_task_ids = [t["id"] for t in data.get("tasks", [])]
                response.success()
            else:
                response.failure(f"List delayed tasks failed: {response.status_code}")

    @task(8)
    def list_executions(self):
        """Получить историю выполнений."""
        if not self.workspace_id:
            return

        with self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/executions",
            headers=self.get_headers(),
            params={"page": 1, "limit": 20},
            catch_response=True,
            name="GET /workspaces/{id}/executions",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List executions failed: {response.status_code}")

    @task(5)
    def get_execution_stats(self):
        """Получить статистику выполнений."""
        if not self.workspace_id:
            return

        with self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/executions/stats",
            headers=self.get_headers(),
            catch_response=True,
            name="GET /workspaces/{id}/executions/stats",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get stats failed: {response.status_code}")

    @task(5)
    def get_daily_stats(self):
        """Получить дневную статистику."""
        if not self.workspace_id:
            return

        with self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/executions/stats/daily",
            headers=self.get_headers(),
            params={"days": 7},
            catch_response=True,
            name="GET /workspaces/{id}/executions/stats/daily",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get daily stats failed: {response.status_code}")

    @task(3)
    def get_cron_task_detail(self):
        """Получить детали cron задачи."""
        if not self.workspace_id or not self.cron_task_ids:
            return

        task_id = random.choice(self.cron_task_ids)
        with self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron/{task_id}",
            headers=self.get_headers(),
            catch_response=True,
            name="GET /workspaces/{id}/cron/{task_id}",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                self.cron_task_ids.remove(task_id)
                response.success()  # Задача удалена - это нормально
            else:
                response.failure(f"Get cron task failed: {response.status_code}")

    @task(2)
    def get_user_profile(self):
        """Получить профиль пользователя."""
        with self.client.get(
            f"{API_PREFIX}/auth/me", headers=self.get_headers(), catch_response=True, name="GET /auth/me"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get profile failed: {response.status_code}")

    # === Операции записи (низкий вес) ===

    @task(2)
    def create_cron_task(self):
        """Создать cron задачу."""
        if not self.workspace_id:
            return

        with self.client.post(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron",
            headers=self.get_headers(),
            json={
                "name": f"Load Test Cron {random_string(6)}",
                "description": "Created by load test",
                "url": TEST_WEBHOOK_URL,
                "method": "POST",
                "headers": {"X-Test": "load-test"},
                "body": json.dumps({"test": True, "timestamp": datetime.now().isoformat()}),
                "schedule": random_cron_schedule(),
                "timezone": "Europe/Moscow",
                "timeout_seconds": 30,
                "retry_count": 2,
                "notify_on_failure": False,
            },
            catch_response=True,
            name="POST /workspaces/{id}/cron",
        ) as response:
            if response.status_code == 201:
                task_id = response.json()["id"]
                self.cron_task_ids.append(task_id)
                response.success()
            elif response.status_code == 403:
                response.success()  # Лимит плана - это нормально
            else:
                response.failure(f"Create cron task failed: {response.status_code}")

    @task(2)
    def create_delayed_task(self):
        """Создать отложенную задачу."""
        if not self.workspace_id:
            return

        with self.client.post(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/delayed",
            headers=self.get_headers(),
            json={
                "idempotency_key": f"load-test-{uuid.uuid4()}",
                "name": f"Load Test Delayed {random_string(6)}",
                "tags": ["load-test"],
                "url": TEST_WEBHOOK_URL,
                "method": "POST",
                "headers": {"X-Test": "load-test"},
                "body": json.dumps({"test": True}),
                "execute_at": future_datetime(random.randint(5, 60)),
                "timeout_seconds": 30,
                "retry_count": 2,
            },
            catch_response=True,
            name="POST /workspaces/{id}/delayed",
        ) as response:
            if response.status_code == 201:
                task_id = response.json()["id"]
                self.delayed_task_ids.append(task_id)
                response.success()
            elif response.status_code == 403:
                response.success()  # Лимит плана
            else:
                response.failure(f"Create delayed task failed: {response.status_code}")

    @task(1)
    def delete_cron_task(self):
        """Удалить cron задачу."""
        if not self.workspace_id or not self.cron_task_ids:
            return

        task_id = self.cron_task_ids.pop()
        with self.client.delete(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron/{task_id}",
            headers=self.get_headers(),
            catch_response=True,
            name="DELETE /workspaces/{id}/cron/{task_id}",
        ) as response:
            if response.status_code in [200, 204, 404]:
                response.success()
            else:
                response.failure(f"Delete cron task failed: {response.status_code}")


# ============================================================================
# Write-Heavy User (активный пользователь)
# ============================================================================


class WriteHeavyUser(CronBoxUser):
    """
    Активный пользователь: много создания задач.
    Соотношение: 50% чтение, 50% запись.
    """

    weight = 2  # 20% пользователей этого типа

    @task(5)
    def list_cron_tasks(self):
        """Получить список cron задач."""
        if not self.workspace_id:
            return

        with self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron",
            headers=self.get_headers(),
            catch_response=True,
            name="GET /workspaces/{id}/cron",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.cron_task_ids = [t["id"] for t in data.get("tasks", [])]
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(5)
    def list_executions(self):
        """Получить историю выполнений."""
        if not self.workspace_id:
            return

        with self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/executions",
            headers=self.get_headers(),
            catch_response=True,
            name="GET /workspaces/{id}/executions",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(5)
    def create_cron_task(self):
        """Создать cron задачу."""
        if not self.workspace_id:
            return

        with self.client.post(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron",
            headers=self.get_headers(),
            json={
                "name": f"Heavy Test Cron {random_string(6)}",
                "url": TEST_WEBHOOK_URL,
                "method": "POST",
                "schedule": random_cron_schedule(),
                "timezone": "Europe/Moscow",
                "timeout_seconds": 30,
            },
            catch_response=True,
            name="POST /workspaces/{id}/cron",
        ) as response:
            if response.status_code == 201:
                self.cron_task_ids.append(response.json()["id"])
                response.success()
            elif response.status_code == 403:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(5)
    def create_delayed_task(self):
        """Создать отложенную задачу."""
        if not self.workspace_id:
            return

        with self.client.post(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/delayed",
            headers=self.get_headers(),
            json={
                "idempotency_key": f"heavy-{uuid.uuid4()}",
                "name": f"Heavy Test Delayed {random_string(6)}",
                "url": TEST_WEBHOOK_URL,
                "method": "POST",
                "execute_at": future_datetime(random.randint(1, 30)),
                "timeout_seconds": 30,
            },
            catch_response=True,
            name="POST /workspaces/{id}/delayed",
        ) as response:
            if response.status_code == 201:
                self.delayed_task_ids.append(response.json()["id"])
                response.success()
            elif response.status_code == 403:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(3)
    def run_cron_task_manually(self):
        """Запустить cron задачу вручную."""
        if not self.workspace_id or not self.cron_task_ids:
            return

        task_id = random.choice(self.cron_task_ids)
        with self.client.post(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron/{task_id}/run",
            headers=self.get_headers(),
            catch_response=True,
            name="POST /workspaces/{id}/cron/{task_id}/run",
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            elif response.status_code == 404:
                self.cron_task_ids.remove(task_id)
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(2)
    def update_cron_task(self):
        """Обновить cron задачу."""
        if not self.workspace_id or not self.cron_task_ids:
            return

        task_id = random.choice(self.cron_task_ids)
        with self.client.patch(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron/{task_id}",
            headers=self.get_headers(),
            json={"name": f"Updated Cron {random_string(4)}", "timeout_seconds": random.choice([30, 60, 120])},
            catch_response=True,
            name="PATCH /workspaces/{id}/cron/{task_id}",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                self.cron_task_ids.remove(task_id)
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(2)
    def delete_cron_task(self):
        """Удалить cron задачу."""
        if not self.workspace_id or not self.cron_task_ids:
            return

        task_id = self.cron_task_ids.pop()
        with self.client.delete(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron/{task_id}",
            headers=self.get_headers(),
            catch_response=True,
            name="DELETE /workspaces/{id}/cron/{task_id}",
        ) as response:
            if response.status_code in [200, 204, 404]:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


# ============================================================================
# API-Only User (для тестирования rate limits)
# ============================================================================


class APIOnlyUser(CronBoxUser):
    """
    Пользователь для тестирования API rate limits.
    Быстрые последовательные запросы.
    """

    weight = 0  # По умолчанию выключен, включите вручную
    wait_time = between(0.1, 0.5)  # Быстрые запросы

    @task(10)
    def rapid_list_tasks(self):
        """Быстрые запросы списка задач."""
        if not self.workspace_id:
            return

        self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/cron",
            headers=self.get_headers(),
            name="GET /workspaces/{id}/cron [rapid]",
        )

    @task(5)
    def rapid_list_executions(self):
        """Быстрые запросы истории."""
        if not self.workspace_id:
            return

        self.client.get(
            f"{API_PREFIX}/workspaces/{self.workspace_id}/executions",
            headers=self.get_headers(),
            name="GET /workspaces/{id}/executions [rapid]",
        )


# ============================================================================
# Event Hooks (для отладки и метрик)
# ============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Выполняется при старте теста."""
    print("=" * 60)
    print("CronBox Load Test Started")
    print(f"Target: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Выполняется при остановке теста."""
    print("=" * 60)
    print("CronBox Load Test Completed")
    print("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Логирование ошибок (опционально)."""
    if exception:
        print(f"ERROR: {request_type} {name} - {exception}")
