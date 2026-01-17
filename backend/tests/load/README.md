# CronBox Load Testing

Нагрузочное тестирование с использованием Locust.

## Установка

```bash
pip install locust
# или
uv add locust --dev
```

## Подготовка

### 1. Создать тестовых пользователей

Отредактируйте `locustfile.py` и добавьте своих тестовых пользователей:

```python
TEST_USERS = [
    {"email": "loadtest1@example.com", "password": "LoadTest123!"},
    {"email": "loadtest2@example.com", "password": "LoadTest123!"},
    # добавьте больше для распределения нагрузки
]
```

Или создайте пользователей через API/админку заранее.

### 2. Настроить webhook URL

По умолчанию используется `https://httpbin.org/post`. Для реалистичного тестирования замените на свой тестовый эндпоинт.

## Запуск

### Web UI (рекомендуется)

```bash
cd backend/tests/load
locust -f locustfile.py --host=http://localhost:8000
```

Откройте http://localhost:8089 в браузере.

### Headless режим

```bash
# 50 пользователей, нарастание 5 users/sec, 5 минут
locust -f locustfile.py --host=http://localhost:8000 \
    --users 50 --spawn-rate 5 --run-time 5m --headless

# С HTML отчётом
locust -f locustfile.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 10m --headless \
    --html=report.html

# С CSV метриками
locust -f locustfile.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 10m --headless \
    --csv=results
```

## Сценарии тестирования

### 1. Baseline (проверка текущей производительности)

```bash
locust --users 10 --spawn-rate 1 --run-time 5m --headless --html=baseline.html
```

### 2. Нарастающая нагрузка

```bash
# Постепенное увеличение
locust --users 50 --spawn-rate 5 --run-time 10m --headless
locust --users 100 --spawn-rate 10 --run-time 10m --headless
locust --users 200 --spawn-rate 20 --run-time 10m --headless
```

### 3. Spike Test (всплеск нагрузки)

```bash
locust --users 200 --spawn-rate 50 --run-time 5m --headless
```

### 4. Soak Test (длительная нагрузка)

```bash
locust --users 50 --spawn-rate 5 --run-time 2h --headless --html=soak.html
```

## Типы пользователей

| Тип | Описание | Weight |
|-----|----------|--------|
| `ReadHeavyUser` | Типичный: 80% чтение, 20% запись | 8 (80%) |
| `WriteHeavyUser` | Активный: 50% чтение, 50% запись | 2 (20%) |
| `APIOnlyUser` | Rate limit тест: быстрые запросы | 0 (выкл) |

Чтобы включить `APIOnlyUser`, измените `weight = 0` на `weight = 1`.

## Метрики для анализа

### Ключевые показатели

| Метрика | Хорошо | Приемлемо | Плохо |
|---------|--------|-----------|-------|
| Median Response | < 100ms | < 300ms | > 500ms |
| p95 Response | < 300ms | < 1000ms | > 2000ms |
| p99 Response | < 1000ms | < 2000ms | > 5000ms |
| Failure Rate | < 0.1% | < 1% | > 5% |
| RPS (requests/sec) | зависит от ресурсов | | |

### На что обращать внимание

1. **Response Time растёт** → Достигнут предел CPU/DB
2. **Ошибки 429** → Rate limiting сработал
3. **Ошибки 503** → Очередь переполнена
4. **Ошибки 500** → Внутренние ошибки (логи!)
5. **Connection errors** → Превышен лимит соединений

## Мониторинг во время теста

### Серверные метрики

```bash
# CPU и память
htop

# PostgreSQL соединения
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Redis
redis-cli INFO clients
redis-cli INFO memory

# Docker stats
docker stats
```

### Prometheus метрики

Если настроен Prometheus: http://localhost:9090

```promql
# RPS
rate(http_requests_total[1m])

# Latency p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Ошибки
rate(http_requests_total{status=~"5.."}[1m])
```

## Рекомендуемые лимиты по пользователям

| Users | Min CPU | Min RAM | DB Pool | Redis | Workers |
|-------|---------|---------|---------|-------|---------|
| 10 | 2 cores | 4 GB | 20 | 256 MB | 1 |
| 50 | 2 cores | 4 GB | 20 | 256 MB | 2 |
| 100 | 4 cores | 8 GB | 30 | 512 MB | 3 |
| 500 | 8 cores | 16 GB | 50 | 1 GB | 5 |
| 1000 | 16 cores | 32 GB | 80 | 2 GB | 10 |

## Troubleshooting

### "Connection refused"
- Проверьте, что сервер запущен: `curl http://localhost:8000/health`

### "401 Unauthorized"
- Создайте тестовых пользователей заранее
- Проверьте правильность паролей

### "403 Forbidden"
- Превышены лимиты плана (cron tasks, delayed tasks)
- Это нормально для нагрузочного теста

### "429 Too Many Requests"
- Rate limiting работает корректно
- Уменьшите `spawn-rate` или добавьте больше пользователей

### Высокая latency
1. Проверьте CPU сервера
2. Проверьте соединения PostgreSQL: `pool_size` может быть мал
3. Проверьте Redis memory

## Пример отчёта

После теста в `report.html` будут:
- График RPS во времени
- Распределение latency
- Таблица с p50/p95/p99 по endpoint
- Ошибки и их типы
