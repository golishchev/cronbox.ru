# Sentry Quick Start

## 🚀 Быстрый старт

Release tracking уже настроен! Следуйте этим шагам для начала работы.

### 1. Получите Auth Token

1. Перейдите: https://sentry.serpdev.ru/settings/account/api/auth-tokens/
2. Нажмите "Create New Token"
3. Выберите scopes: `project:read`, `project:releases`, `org:read`
4. Скопируйте токен

### 2. Настройте переменные окружения

**Для продакшена (на сервере):**

```bash
# Backend
export SENTRY_AUTH_TOKEN="your_token_here"
export SENTRY_ORG="sentry"
export SENTRY_PROJECT="cronbox-backend"

# Frontend (для build)
export SENTRY_AUTH_TOKEN="your_token_here"
export SENTRY_ORG="sentry"
export SENTRY_PROJECT="cronbox-frontend"
```

### 3. Использование при деплое

#### Вариант A: Автоматические скрипты (рекомендуется)

```bash
# После деплоя backend
./scripts/sentry-release.sh backend 0.1.0
./scripts/sentry-deploy.sh backend 0.1.0 production

# После деплоя frontend
./scripts/sentry-release.sh frontend 0.1.0
./scripts/sentry-deploy.sh frontend 0.1.0 production
```

#### Вариант B: Вручную

**Установите sentry-cli:**
```bash
curl -sL https://sentry.io/get-cli/ | bash
```

**Backend:**
```bash
cd backend
VERSION=$(grep 'version' pyproject.toml | head -1 | cut -d'"' -f2)
sentry-cli releases new "cronbox-backend@$VERSION"
sentry-cli releases set-commits "cronbox-backend@$VERSION" --auto
sentry-cli releases finalize "cronbox-backend@$VERSION"
sentry-cli releases deploys "cronbox-backend@$VERSION" new -e production
```

**Frontend:**
```bash
cd frontend
# Source maps автоматически загружаются при production build
npm run build

VERSION=$(node -p "require('./package.json').version")
sentry-cli releases deploys "cronbox-frontend@$VERSION" new -e production
```

## 📊 Проверка

Зайдите в Sentry и убедитесь что release появился:
- Backend: https://sentry.serpdev.ru/organizations/sentry/projects/cronbox-backend/releases/
- Frontend: https://sentry.serpdev.ru/organizations/sentry/projects/cronbox-frontend/releases/

## 📖 Полная документация

См. [SENTRY_SETUP.md](./SENTRY_SETUP.md) для подробных инструкций и примеров CI/CD.

## ✨ Что это даёт

- 🔗 Связь ошибок с конкретными релизами
- 📈 Health monitoring по версиям
- 🎯 Suspect commits (кто вероятно сломал)
- 🗺️ Source maps для читаемых stack traces (frontend)
- 📅 История деплоев
