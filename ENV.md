# Environment Variables Guide

## 📁 Файловая структура

CronBox использует **один мастер-файл** для всех environment переменных:

```
/
├── .env                    # ✅ МАСТЕР-ФАЙЛ - ВСЕ переменные здесь
├── .env.example            # Шаблон для копирования
│
├── backend/
│   ├── (NO .env here!)     # ❌ Удалён - больше не нужен
│   └── app/config.py       # Читает из корневого .env
│
└── frontend/
    ├── .env                # Только VITE_* для локальной разработки
    └── .env.example        # Шаблон
```

## 🎯 Зачем один файл?

### Раньше (было 3 файла):
```
❌ /.env              - для docker-compose
❌ /backend/.env      - для Python app
❌ /frontend/.env     - для Vite
```

**Проблемы:**
- ❌ Дубликаты переменных
- ❌ Разные значения в разных файлах
- ❌ Сложно синхронизировать
- ❌ Легко забыть обновить один из файлов
- ❌ Непонятно какой файл главный

### Сейчас (один мастер-файл):
```
✅ /.env              - ВСЕ переменные
✅ /frontend/.env     - Только VITE_* для dev
```

**Преимущества:**
- ✅ Единственный источник истины
- ✅ Нет дубликатов
- ✅ Легко управлять
- ✅ Работает везде (dev, prod, docker)

## 🚀 Быстрый старт

### 1. Первоначальная настройка

```bash
# Скопировать шаблон
cp .env.example .env

# Отредактировать значения
nano .env  # или vim, или IDE

# Для frontend (опционально, если нужны другие значения для dev)
cp frontend/.env.example frontend/.env
```

### 2. Заполнить обязательные переменные

В корневом `.env`:

```bash
# Secrets
SECRET_KEY=ваш-случайный-секретный-ключ
JWT_SECRET=другой-случайный-ключ

# Database (production)
POSTGRES_PASSWORD=надежный-пароль

# Redis (production)
REDIS_PASSWORD=надежный-пароль

# Telegram Bot
TELEGRAM_BOT_TOKEN=ваш_токен_бота
ADMIN_TELEGRAM_ID=ваш_chat_id

# Sentry (опционально)
SENTRY_DSN=https://...@sentry.serpdev.ru/11
VITE_SENTRY_DSN=https://...@sentry.serpdev.ru/12
```

## 🔧 Как это работает

### Локальная разработка (`make dev`)

1. **docker-compose.yml** (PostgreSQL, Redis):
   ```yaml
   # Автоматически читает .env из корня (стандартное поведение)
   ```

2. **Backend** (Python FastAPI):
   ```python
   # backend/app/config.py
   PROJECT_ROOT = Path(__file__).parent.parent.parent
   ENV_FILE = PROJECT_ROOT / ".env"  # Читает корневой .env
   ```

3. **Frontend** (Vite):
   ```bash
   # Читает frontend/.env для VITE_* переменных
   # Все остальное из корневого .env через Vite proxy
   ```

### Production (`docker-compose.prod.yml`)

1. **docker-compose.prod.yml**:
   ```yaml
   # Читает корневой .env для подстановки ${ПЕРЕМЕННЫХ}
   services:
     api:
       environment:
         DATABASE_URL: ${DATABASE_URL}
         REDIS_URL: ${REDIS_URL}
         # ... все переменные прокидываются сюда
   ```

2. **Backend в Docker**:
   - Получает переменные через `environment:` блоки в docker-compose
   - Файл `.env` НЕ копируется в Docker image
   - Всё настраивается через docker-compose environment

3. **Frontend build**:
   ```yaml
   # docker-compose.prod.yml
   frontend:
     build:
       args:
         VITE_API_URL: https://api.cronbox.ru/v1
   ```

## 📝 Какие переменные где используются

### Корневой `.env` используется для:

**Infrastructure (docker-compose):**
- `POSTGRES_*` - PostgreSQL настройки
- `REDIS_PASSWORD` - Redis пароль
- `TRAEFIK_*` - Reverse proxy (production)
- `GRAFANA_*` - Мониторинг (production)

**Backend (Python):**
- `SECRET_KEY`, `JWT_SECRET` - Безопасность
- `DATABASE_URL`, `REDIS_URL` - Подключения к БД
- `TELEGRAM_BOT_TOKEN` - Telegram бот
- `YOOKASSA_*` - Платежи
- `SMTP_*` - Email
- `SENTRY_DSN` - Error tracking
- `CORS_ORIGINS`, `FRONTEND_URL`, `API_URL` - URLs

**Frontend (через build-args или runtime):**
- `VITE_API_URL` - API endpoint
- `VITE_SENTRY_DSN` - Error tracking

### Frontend `.env` (только для dev):

- `VITE_API_URL` - Для локальной разработки
- `VITE_SENTRY_DSN` - Для тестирования Sentry

**Важно:** В production эти значения прокидываются через docker-compose `build-args`!

## 🔐 Production Deployment

### На сервере (/opt/cronbox)

Корневой `.env` содержит все секреты:

```bash
ssh cronbox
cd /opt/cronbox

# Отредактировать production значения
nano .env

# Убедиться что установлен ENVIRONMENT=production
grep ENVIRONMENT .env
# Должно быть: ENVIRONMENT=production

# Перезапустить сервисы
docker compose -f docker-compose.prod.yml up -d
```

### Важные production переменные

```bash
# Backend
ENVIRONMENT=production  # ОБЯЗАТЕЛЬНО!
SECRET_KEY=<сильный-рандомный-ключ>
JWT_SECRET=<другой-сильный-ключ>

# Database
POSTGRES_PASSWORD=<надежный-пароль>

# Redis
REDIS_PASSWORD=<надежный-пароль>

# Telegram (production бот)
TELEGRAM_BOT_TOKEN=8417319353:...

# URLs
CORS_ORIGINS=["https://cronbox.ru","https://cp.cronbox.ru"]
FRONTEND_URL=https://cp.cronbox.ru
API_URL=https://api.cronbox.ru

# Sentry
SENTRY_DSN=https://...@sentry.serpdev.ru/11
VITE_SENTRY_DSN=https://...@sentry.serpdev.ru/12
```

## 🧪 Тестирование

### Проверка что backend читает правильные значения:

```bash
cd backend
uv run python -c "
from app.config import settings
print(f'Environment: {settings.environment}')
print(f'Telegram token: {settings.telegram_bot_token[:20]}...')
print(f'Sentry enabled: {bool(settings.sentry_dsn)}')
"
```

### Проверка docker-compose:

```bash
# Проверить какие переменные видит docker-compose
docker compose config | grep -A 5 "environment:"
```

## 🔄 Миграция (если у вас старая версия)

Бэкапы старых файлов сохранены в `.env.backup/`:

```bash
ls -la .env.backup/
# .env.root.20260130_133020
# .env.backend.20260130_133020
# .env.frontend.20260130_133020
```

Если нужно откатиться:

```bash
# Восстановить из бэкапа
cp .env.backup/.env.root.20260130_133020 .env
cp .env.backup/.env.backend.20260130_133020 backend/.env
```

## ❓ FAQ

### Q: Где хранить секреты для production?

**A:** В корневом `.env` на сервере (`/opt/cronbox/.env`). Этот файл в `.gitignore` и не попадает в git.

### Q: Как CI/CD получает секреты?

**A:** Через GitHub Secrets. В workflow файле они прокидываются через SSH в команды деплоя.

### Q: Что если мне нужны разные значения для dev и prod?

**A:**
- **Dev:** Используйте корневой `.env` локально
- **Prod:** Тот же корневой `.env`, но с другими значениями на сервере
- Переменная `ENVIRONMENT` помогает различать окружения

### Q: Почему frontend всё ещё имеет свой .env?

**A:** Только для **локальной разработки**. Vite требует `VITE_*` префикс для переменных. В production они передаются через docker-compose `build-args`.

### Q: Как добавить новую переменную?

1. Добавьте в корневой `.env`
2. Добавьте в `.env.example` (без значения)
3. Если нужна в backend - добавьте в `backend/app/config.py` в класс `Settings`
4. Если нужна в docker-compose - добавьте в `environment:` блок нужного сервиса

## 📚 См. также

- [CLAUDE.md](./CLAUDE.md) - Общая документация проекта
- [SENTRY_QUICKSTART.md](./SENTRY_QUICKSTART.md) - Настройка Sentry
- [docker-compose.prod.yml](./docker-compose.prod.yml) - Production конфигурация
