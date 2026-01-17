# CronBox

Сервис планирования HTTP-запросов по расписанию. Позволяет создавать повторяющиеся (cron) и отложенные задачи для автоматизации вызовов внешних API.

## Возможности

- **Cron-задачи** - повторяющиеся HTTP-запросы по cron-выражению (например, каждые 5 минут, ежедневно в 9:00)
- **Отложенные задачи** - одноразовые HTTP-запросы, выполняемые в указанное время
- **Воркспейсы** - организация задач для командной работы
- **История выполнений** - детальные логи и статусы всех запросов
- **Уведомления** - Email, Telegram, Slack, Webhooks
- **Биллинг** - тарифные планы и управление подписками (YooKassa)

## Технологический стек

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy + asyncpg (PostgreSQL)
- Redis (кеширование, очереди)
- APScheduler / ARQ (планировщик)
- Alembic (миграции)

### Frontend
- React 19 + TypeScript
- Vite
- TailwindCSS + Radix UI
- TanStack Query + Router
- Zustand (стейт)
- i18next (интернационализация)

### Инфраструктура
- Docker + Docker Compose
- GitHub Actions (CI/CD)
- Prometheus (метрики)

## Быстрый старт

### Требования
- Docker и Docker Compose
- Python 3.12+ (для локальной разработки)
- Node.js 20+ (для локальной разработки)
- uv (менеджер пакетов Python)

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-org/cronbox.ru.git
cd cronbox.ru
```

2. Скопируйте файлы окружения:
```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

3. Настройте переменные окружения в `.env` и `backend/.env`

4. Запустите инфраструктуру (PostgreSQL + Redis):
```bash
make infra
```

5. Установите зависимости бэкенда:
```bash
cd backend
uv sync
```

6. Примените миграции:
```bash
uv run alembic upgrade head
```

7. Установите зависимости фронтенда:
```bash
cd ../frontend
npm install
```

### Запуск для разработки

Запуск всех сервисов одной командой:
```bash
make dev
```

Или по отдельности:
```bash
# Бэкенд (порт 8000)
make dev-backend

# Фронтенд (порт 3000)
make dev-frontend
```

Остановка всех сервисов:
```bash
make stop
```

## API

После запуска документация API доступна по адресам:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

### Аутентификация

API использует JWT-токены. Добавьте заголовок:
```
Authorization: Bearer <access_token>
```

### Основные эндпоинты

| Модуль | Путь | Описание |
|--------|------|----------|
| Auth | `/api/v1/auth` | Регистрация и авторизация |
| Workspaces | `/api/v1/workspaces` | Управление воркспейсами |
| Cron Tasks | `/api/v1/cron-tasks` | CRUD для cron-задач |
| Delayed Tasks | `/api/v1/delayed-tasks` | CRUD для отложенных задач |
| Executions | `/api/v1/executions` | История выполнений |
| Notifications | `/api/v1/notifications` | Настройки уведомлений |
| Billing | `/api/v1/billing` | Тарифы и подписки |
| Workers | `/api/v1/workers` | API-ключи для воркеров |

## Структура проекта

```
cronbox.ru/
├── backend/                 # FastAPI приложение
│   ├── app/
│   │   ├── api/            # API эндпоинты
│   │   ├── core/           # Безопасность, Redis, rate limiter
│   │   ├── db/             # База данных и репозитории
│   │   ├── models/         # SQLAlchemy модели
│   │   ├── schemas/        # Pydantic схемы
│   │   ├── services/       # Бизнес-логика
│   │   └── main.py         # Точка входа
│   ├── alembic/            # Миграции БД
│   └── Dockerfile
├── frontend/               # React приложение
│   ├── src/
│   │   ├── api/           # API клиент
│   │   ├── components/    # UI компоненты
│   │   ├── pages/         # Страницы
│   │   ├── stores/        # Zustand сторы
│   │   └── locales/       # Переводы (ru, en)
│   └── Dockerfile
├── docker-compose.yml      # Dev инфраструктура
├── docker-compose.prod.yml # Production конфигурация
├── Makefile               # Команды разработки
└── .github/workflows/     # CI/CD пайплайны
```

## Скрипты и команды

### Makefile
```bash
make dev            # Запуск всех сервисов
make dev-backend    # Только бэкенд
make dev-frontend   # Только фронтенд
make infra          # PostgreSQL + Redis
make stop           # Остановить всё
```

### Backend CLI
```bash
cronbox-server      # Запуск API сервера
cronbox-worker      # Запуск воркера задач
cronbox-scheduler   # Запуск планировщика
```

### Миграции
```bash
cd backend
uv run alembic upgrade head      # Применить миграции
uv run alembic revision --autogenerate -m "description"  # Создать миграцию
uv run alembic downgrade -1      # Откатить последнюю миграцию
```

## Переменные окружения

### Основные (`.env`)
| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | URL подключения к PostgreSQL |
| `REDIS_URL` | URL подключения к Redis |
| `SECRET_KEY` | Секретный ключ приложения |
| `JWT_SECRET` | Секрет для JWT токенов |

### Интеграции
| Переменная | Описание |
|------------|----------|
| `YOOKASSA_SHOP_ID` | ID магазина YooKassa |
| `YOOKASSA_SECRET_KEY` | Секретный ключ YooKassa |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота |
| `POSTAL_API_URL` | URL Postal сервера (email) |
| `POSTAL_API_KEY` | API ключ Postal |

## Разработка

### Линтинг и типы

Backend:
```bash
cd backend
uv run ruff check .          # Линтер
uv run ruff format .         # Форматирование
uv run mypy app              # Проверка типов
```

Frontend:
```bash
cd frontend
npm run lint                 # ESLint
npm run typecheck            # TypeScript
```

### Тесты
```bash
cd backend
uv run pytest tests -v --cov=app
```

## Production

Для production используйте `docker-compose.prod.yml`:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Лицензия

Proprietary. Все права защищены.


  # Создать пользователей
  cd backend && uv run python scripts/seed_loadtest_users.py

  # Удалить пользователей после тестирования
  cd backend && uv run python scripts/seed_loadtest_users.py --cleanup

  Скрипт создаст 5 пользователей:
  - loadtest1@example.com — loadtest5@example.com
  - Пароль: LoadTest123!
  - Email уже верифицирован
  - У каждого создан workspace


  uv run locust -f /Users/golishchev/Developer/cronbox.ru/backend/tests/load/locustfile.py --users 10 --spawn-rate 1 --run-time 5m --headless --html=baseline.html