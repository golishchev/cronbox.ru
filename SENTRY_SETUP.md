# Sentry Release Tracking Setup

Этот документ описывает как настроена интеграция с Sentry и как использовать release tracking в CI/CD.

## Что уже настроено

### Backend
- ✅ Sentry SDK установлен (`sentry-sdk[fastapi]`)
- ✅ Инициализация в `backend/app/main.py` с версией из `pyproject.toml`
- ✅ Release format: `cronbox-backend@{version}` (например, `cronbox-backend@0.1.0`)
- ✅ Environment tracking (development, staging, production)
- ✅ Performance monitoring (10% транзакций)
- ✅ Profiling (10% транзакций)

### Frontend
- ✅ Sentry SDK установлен (`@sentry/react`)
- ✅ Vite plugin для автоматической загрузки source maps
- ✅ Инициализация в `frontend/src/main.tsx` с версией из `package.json`
- ✅ Release format: `cronbox-frontend@{version}` (например, `cronbox-frontend@0.1.0`)
- ✅ Error Boundary для обработки React ошибок
- ✅ Session Replay (10% сессий, 100% при ошибках)
- ✅ Performance monitoring (10% транзакций)

## Настройка Sentry CLI

### 1. Установка sentry-cli

**Linux / macOS:**
```bash
curl -sL https://sentry.io/get-cli/ | bash
```

**npm (глобально):**
```bash
npm install -g @sentry/cli
```

**Проверка:**
```bash
sentry-cli --version
```

### 2. Получение Auth Token

1. Перейдите на https://sentry.serpdev.ru/settings/account/api/auth-tokens/
2. Нажмите "Create New Token"
3. Выберите scopes:
   - `project:read`
   - `project:releases`
   - `org:read`
4. Скопируйте токен

### 3. Настройка переменных окружения

**Backend** (`backend/.env`):
```bash
SENTRY_DSN=https://677c3eb97fc2c507e93f732f4c5ed3fa@sentry.serpdev.ru/11
ENVIRONMENT=production  # или staging
SENTRY_AUTH_TOKEN=your_auth_token_here
SENTRY_ORG=sentry
SENTRY_PROJECT=cronbox-backend
```

**Frontend** (`frontend/.env` или `.env.production`):
```bash
VITE_SENTRY_DSN=https://8c3ddae247009c9495cb44511ec3518f@sentry.serpdev.ru/12
SENTRY_AUTH_TOKEN=your_auth_token_here
SENTRY_ORG=sentry
SENTRY_PROJECT=cronbox-frontend
```

**Или настройте `.sentryclirc`** в корне проекта:
```ini
[auth]
token=your_auth_token_here

[defaults]
url=https://sentry.serpdev.ru
org=sentry
project=cronbox-backend
```

## Использование в CI/CD

### Готовые скрипты

Проект содержит два скрипта для работы с releases:

#### 1. Создание release

```bash
# Backend
./scripts/sentry-release.sh backend 0.1.0

# Frontend
./scripts/sentry-release.sh frontend 0.1.0
```

Скрипт:
- Создает новый release в Sentry
- Связывает с git commits (автоматически)
- Финализирует release

#### 2. Уведомление о деплое

```bash
# Backend в production
./scripts/sentry-deploy.sh backend 0.1.0 production

# Frontend в staging
./scripts/sentry-deploy.sh frontend 0.1.0 staging
```

### Пример интеграции в GitHub Actions

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Важно для git history

      - name: Get version
        id: version
        run: echo "version=$(grep 'version' backend/pyproject.toml | head -1 | cut -d'"' -f2)" >> $GITHUB_OUTPUT

      - name: Install sentry-cli
        run: curl -sL https://sentry.io/get-cli/ | bash

      - name: Create Sentry release
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
          SENTRY_ORG: sentry
          SENTRY_PROJECT: cronbox-backend
        run: |
          sentry-cli releases new "cronbox-backend@${{ steps.version.outputs.version }}"
          sentry-cli releases set-commits "cronbox-backend@${{ steps.version.outputs.version }}" --auto
          sentry-cli releases finalize "cronbox-backend@${{ steps.version.outputs.version }}"

      # ... deploy steps ...

      - name: Notify Sentry about deployment
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
          SENTRY_ORG: sentry
          SENTRY_PROJECT: cronbox-backend
        run: |
          sentry-cli releases deploys "cronbox-backend@${{ steps.version.outputs.version }}" new -e production

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Build with source maps
        working-directory: frontend
        env:
          VITE_SENTRY_DSN: ${{ secrets.VITE_SENTRY_DSN }}
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
          SENTRY_ORG: sentry
          SENTRY_PROJECT: cronbox-frontend
        run: npm run build
        # Vite plugin автоматически загрузит source maps при production build

      # ... deploy steps ...

      - name: Notify Sentry about deployment
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
          SENTRY_ORG: sentry
          SENTRY_PROJECT: cronbox-frontend
        run: |
          VERSION=$(node -p "require('./frontend/package.json').version")
          sentry-cli releases deploys "cronbox-frontend@$VERSION" new -e production
```

### Пример для GitLab CI

```yaml
deploy:backend:
  stage: deploy
  script:
    - curl -sL https://sentry.io/get-cli/ | bash
    - VERSION=$(grep 'version' backend/pyproject.toml | head -1 | cut -d'"' -f2)
    - export SENTRY_ORG=sentry
    - export SENTRY_PROJECT=cronbox-backend
    - sentry-cli releases new "cronbox-backend@$VERSION"
    - sentry-cli releases set-commits "cronbox-backend@$VERSION" --auto
    - sentry-cli releases finalize "cronbox-backend@$VERSION"
    # ... deploy commands ...
    - sentry-cli releases deploys "cronbox-backend@$VERSION" new -e production
  only:
    - main

deploy:frontend:
  stage: deploy
  script:
    - cd frontend
    - npm ci
    - npm run build  # Vite plugin загрузит source maps
    # ... deploy commands ...
    - VERSION=$(node -p "require('./package.json').version")
    - curl -sL https://sentry.io/get-cli/ | bash
    - export SENTRY_ORG=sentry
    - export SENTRY_PROJECT=cronbox-frontend
    - sentry-cli releases deploys "cronbox-frontend@$VERSION" new -e production
  only:
    - main
```

### Ручной деплой (текущая настройка)

Если у вас SSH деплой на сервер:

```bash
# На сервере после деплоя
ssh cronbox

# Backend
cd /opt/cronbox/backend
VERSION=$(grep 'version' pyproject.toml | head -1 | cut -d'"' -f2)
docker exec cronbox-api sentry-cli releases new "cronbox-backend@$VERSION"
docker exec cronbox-api sentry-cli releases set-commits "cronbox-backend@$VERSION" --auto
docker exec cronbox-api sentry-cli releases finalize "cronbox-backend@$VERSION"
docker exec cronbox-api sentry-cli releases deploys "cronbox-backend@$VERSION" new -e production

# Frontend
cd /opt/cronbox/frontend
VERSION=$(node -p "require('./package.json').version")
# Source maps уже загружены при build
sentry-cli releases deploys "cronbox-frontend@$VERSION" new -e production
```

## Что даёт Release Tracking

### 1. Связь ошибок с релизами
- Видно в каком релизе впервые появилась ошибка
- Можно фильтровать ошибки по релизам
- Автоматический suspect commits (кто вероятно сломал)

### 2. Health monitoring
- Процент crash-free sessions по релизам
- Сравнение стабильности версий
- Rollback рекомендации

### 3. Deploy tracking
- История деплоев по окружениям
- Время между релизами
- Кто задеплоил и когда

### 4. Source maps (frontend)
- Читаемые stack traces вместо minified кода
- Точные номера строк в исходном коде
- Подсветка проблемного кода в Sentry UI

## Проверка работы

### 1. Локальная проверка

**Backend:**
```bash
cd backend
uv run python -c "
from app import __version__
import sentry_sdk
from app.config import settings

sentry_sdk.init(dsn=settings.sentry_dsn, release=f'cronbox-backend@{__version__}')
sentry_sdk.capture_message(f'Test from release {__version__}')
"
```

**Frontend:**
```bash
cd frontend
npm run build  # Source maps будут в dist/
# В production они автоматически загрузятся на Sentry
```

### 2. Проверка в Sentry

1. Перейдите на https://sentry.serpdev.ru
2. Выберите проект (cronbox-backend или cronbox-frontend)
3. Перейдите в "Releases" в левом меню
4. Убедитесь что ваш release появился
5. Проверьте что commits связаны

### 3. Тестирование ошибки

**Backend:**
Временно добавьте в любой эндпоинт:
```python
raise Exception("Test error from release 0.1.0")
```

**Frontend:**
В консоли браузера:
```javascript
throw new Error("Test error from release 0.1.0")
```

В Sentry Issue вы увидите:
- Release: `cronbox-backend@0.1.0` или `cronbox-frontend@0.1.0`
- Commits associated with this release
- Suspect commits (если есть)

## Troubleshooting

### Source maps не загружаются

**Проблема:** Stack traces в production показывают minified код

**Решение:**
1. Проверьте что `SENTRY_AUTH_TOKEN` установлен при build
2. Проверьте логи build - должна быть строка "Uploading source maps"
3. Убедитесь что `VITE_SENTRY_DSN` установлен при production build
4. Проверьте что `sourcemap: true` в `vite.config.ts`

### Release не создаётся

**Проблема:** `sentry-cli releases new` падает с ошибкой

**Решение:**
1. Проверьте `SENTRY_AUTH_TOKEN`
2. Убедитесь что токен имеет необходимые scopes
3. Проверьте что `SENTRY_ORG` и `SENTRY_PROJECT` правильные
4. Проверьте `.sentryclirc` конфигурацию

### Commits не связываются

**Проблема:** В release нет связанных коммитов

**Решение:**
1. Убедитесь что у вас есть `.git` директория
2. Используйте `fetch-depth: 0` в GitHub Actions checkout
3. Проверьте что git remote настроен правильно
4. Можно указать коммиты вручную: `--commit "repo@sha"`

## Ресурсы

- Sentry Dashboard: https://sentry.serpdev.ru
- Backend проект: https://sentry.serpdev.ru/organizations/sentry/projects/cronbox-backend/
- Frontend проект: https://sentry.serpdev.ru/organizations/sentry/projects/cronbox-frontend/
- Sentry CLI docs: https://docs.sentry.io/product/cli/
- Release tracking docs: https://docs.sentry.io/product/releases/
