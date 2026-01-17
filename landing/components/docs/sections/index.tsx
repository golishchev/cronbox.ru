import type { ReactNode } from 'react'
import { CodeBlock } from '../CodeBlock'
import { Endpoint } from '../Endpoint'

export function GettingStartedSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white dark:text-white">Начало работы</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300 dark:text-gray-300">
        CronBox API позволяет управлять HTTP-задачами программно. Все запросы
        выполняются к базовому URL:
      </p>

      <CodeBlock code="https://api.cronbox.ru/v1" />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white dark:text-white">Быстрый старт</h3>

      <ol className="mt-4 space-y-4 text-gray-600 dark:text-gray-300 dark:text-gray-300">
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50 text-sm font-semibold text-primary-600 dark:text-primary-400">
            1
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-white dark:text-white">Зарегистрируйтесь</p>
            <p className="text-sm">
              Создайте аккаунт в{' '}
              <a
                href="https://cp.cronbox.ru/#/register"
                className="text-primary-600 dark:text-primary-400 hover:underline"
              >
                панели управления
              </a>
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50 text-sm font-semibold text-primary-600 dark:text-primary-400">
            2
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-white dark:text-white">Получите API-ключ</p>
            <p className="text-sm">
              Создайте API-ключ в разделе «Настройки» → «API-ключи»
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50 text-sm font-semibold text-primary-600 dark:text-primary-400">
            3
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-white dark:text-white">Создайте первую задачу</p>
            <p className="text-sm">
              Используйте API для создания cron или отложенной задачи
            </p>
          </div>
        </li>
      </ol>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white dark:text-white">Формат ответов</h3>
      <p className="mt-2 text-gray-600 dark:text-gray-300 dark:text-gray-300">
        Все ответы возвращаются в формате JSON. Успешные ответы имеют код 2xx,
        ошибки - 4xx или 5xx.
      </p>

      <CodeBlock
        language="json"
        code={`// Успешный ответ
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Моя задача",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z"
}

// Ответ с ошибкой
{
  "detail": "Задача не найдена"
}`}
      />
    </div>
  )
}

export function AuthenticationSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Аутентификация</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        CronBox API использует Bearer-токены для аутентификации. Передавайте токен
        в заголовке Authorization каждого запроса.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Получение токена</h3>

      <Endpoint
        method="POST"
        path="/auth/login"
        description="Авторизация по email и паролю"
      />

      <p className="mt-4 text-gray-600 dark:text-gray-300">Пример запроса:</p>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "your_password"
  }'`}
      />

      <p className="mt-4 text-gray-600 dark:text-gray-300">Пример ответа:</p>

      <CodeBlock
        language="json"
        code={`{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">
        Использование токена
      </h3>

      <CodeBlock
        code={`curl https://api.cronbox.ru/v1/cron-tasks \\
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Обновление токена</h3>

      <Endpoint
        method="POST"
        path="/auth/refresh"
        description="Обновление access-токена"
      />

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/auth/refresh \\
  -H "Content-Type: application/json" \\
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
  }'`}
      />

      <div className="mt-8 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4">
        <p className="text-sm text-yellow-800 dark:text-yellow-200">
          <strong>Важно:</strong> Access-токен действителен 15 минут. Refresh-токен
          - 30 дней. Храните токены безопасно и не передавайте третьим лицам.
        </p>
      </div>
    </div>
  )
}

export function CronTasksSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Cron-задачи</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        Cron-задачи выполняются регулярно по заданному расписанию. Используйте
        стандартный формат cron-выражений.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/cron-tasks" description="Список всех cron-задач" />
        <Endpoint method="POST" path="/cron-tasks" description="Создание новой задачи" />
        <Endpoint method="GET" path="/cron-tasks/{id}" description="Получение задачи по ID" />
        <Endpoint method="PATCH" path="/cron-tasks/{id}" description="Обновление задачи" />
        <Endpoint method="DELETE" path="/cron-tasks/{id}" description="Удаление задачи" />
        <Endpoint method="POST" path="/cron-tasks/{id}/pause" description="Приостановка задачи" />
        <Endpoint method="POST" path="/cron-tasks/{id}/unpause" description="Возобновление задачи" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Создание задачи</h3>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/cron-tasks \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Синхронизация данных",
    "url": "https://your-api.com/sync",
    "method": "POST",
    "cron_expression": "0 */6 * * *",
    "headers": {
      "Content-Type": "application/json",
      "X-API-Key": "your-api-key"
    },
    "body": "{\\"action\\": \\"sync\\"}",
    "timeout_seconds": 30,
    "retry_count": 3
  }'`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Формат cron-выражений</h3>
      <p className="mt-2 text-gray-600 dark:text-gray-300">
        Используется стандартный 5-полевой формат cron:
      </p>

      <CodeBlock
        code={`┌───────────── минута (0 - 59)
│ ┌───────────── час (0 - 23)
│ │ ┌───────────── день месяца (1 - 31)
│ │ │ ┌───────────── месяц (1 - 12)
│ │ │ │ ┌───────────── день недели (0 - 6, 0 = воскресенье)
│ │ │ │ │
* * * * *`}
      />

      <p className="mt-4 text-gray-600 dark:text-gray-300">Примеры:</p>
      <ul className="mt-2 space-y-2 text-sm text-gray-600 dark:text-gray-300">
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">*/5 * * * *</code> -
          каждые 5 минут
        </li>
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">0 */2 * * *</code> -
          каждые 2 часа
        </li>
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">0 9 * * 1-5</code> - в
          9:00 по будням
        </li>
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">0 0 1 * *</code> -
          первого числа каждого месяца
        </li>
      </ul>
    </div>
  )
}

export function DelayedTasksSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Отложенные задачи</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        Отложенные задачи выполняются один раз в указанное время. Идеально для
        отправки отложенных уведомлений, напоминаний и одноразовых действий.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/delayed-tasks" description="Список отложенных задач" />
        <Endpoint method="POST" path="/delayed-tasks" description="Создание отложенной задачи" />
        <Endpoint method="GET" path="/delayed-tasks/{id}" description="Получение задачи по ID" />
        <Endpoint method="DELETE" path="/delayed-tasks/{id}" description="Отмена задачи" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Создание задачи</h3>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/delayed-tasks \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Отправить напоминание",
    "url": "https://your-api.com/send-reminder",
    "method": "POST",
    "execute_at": "2024-01-20T15:00:00Z",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": "{\\"user_id\\": 123, \\"message\\": \\"Напоминание!\\"}"
  }'`}
      />

      <div className="mt-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <strong>Примечание:</strong> Время выполнения указывается в формате ISO
          8601 в часовом поясе UTC. Например:{' '}
          <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">2024-01-20T15:00:00Z</code>
        </p>
      </div>
    </div>
  )
}

export function ExecutionsSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Выполнения</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        Каждое выполнение задачи записывается с полной информацией о запросе и
        ответе. Используйте API выполнений для мониторинга и отладки.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/executions" description="Список выполнений" />
        <Endpoint method="GET" path="/executions/{id}" description="Детали выполнения" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Получение списка</h3>

      <CodeBlock
        code={`curl "https://api.cronbox.ru/v1/executions?limit=20&status=failed" \\
  -H "Authorization: Bearer YOUR_TOKEN"`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Пример ответа</h3>

      <CodeBlock
        language="json"
        code={`{
  "items": [
    {
      "id": "exec_123",
      "task_id": "task_456",
      "task_type": "cron",
      "status": "success",
      "status_code": 200,
      "duration_ms": 234,
      "executed_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}`}
      />
    </div>
  )
}

export function NotificationsSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Уведомления</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        Настройте уведомления о статусе выполнения задач через Email, Telegram или
        Webhook.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint
          method="GET"
          path="/notifications/settings"
          description="Текущие настройки уведомлений"
        />
        <Endpoint
          method="PATCH"
          path="/notifications/settings"
          description="Обновление настроек"
        />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Каналы уведомлений</h3>

      <div className="mt-4 space-y-6">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">Email</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Уведомления отправляются на email, указанный при регистрации.
          </p>
          <CodeBlock
            language="json"
            code={`{
  "email_enabled": true,
  "email_on_failure": true,
  "email_on_success": false
}`}
          />
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">Telegram</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Подключите Telegram-бота для мгновенных уведомлений.
          </p>
          <CodeBlock
            language="json"
            code={`{
  "telegram_enabled": true,
  "telegram_chat_id": "123456789",
  "telegram_on_failure": true
}`}
          />
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">Webhook</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Отправляйте уведомления на ваш сервер в формате JSON.
          </p>
          <CodeBlock
            language="json"
            code={`{
  "webhook_enabled": true,
  "webhook_url": "https://your-server.com/cronbox-webhook",
  "webhook_on_failure": true,
  "webhook_on_success": true
}`}
          />
        </div>
      </div>
    </div>
  )
}

export function TaskChainsSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Цепочки задач</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        Цепочки задач позволяют выполнять несколько HTTP-запросов последовательно,
        передавая данные между шагами. Идеально для сложных workflow, где результат
        одного запроса используется в следующем.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/chains" description="Список цепочек задач" />
        <Endpoint method="POST" path="/chains" description="Создание цепочки" />
        <Endpoint method="GET" path="/chains/{id}" description="Получение цепочки с шагами" />
        <Endpoint method="PATCH" path="/chains/{id}" description="Обновление цепочки" />
        <Endpoint method="DELETE" path="/chains/{id}" description="Удаление цепочки" />
        <Endpoint method="POST" path="/chains/{id}/run" description="Ручной запуск цепочки" />
        <Endpoint method="POST" path="/chains/{id}/pause" description="Приостановка цепочки" />
        <Endpoint method="POST" path="/chains/{id}/resume" description="Возобновление цепочки" />
        <Endpoint method="POST" path="/chains/{id}/copy" description="Копирование цепочки" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Типы триггеров</h3>

      <div className="mt-4 space-y-4">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">manual</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Запуск только вручную через API или панель управления.
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">cron</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Регулярный запуск по cron-расписанию. Требует параметр <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">schedule</code>.
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">delayed</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Однократный запуск в заданное время. Требует параметр <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">execute_at</code>.
          </p>
        </div>
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Создание цепочки</h3>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/workspaces/{workspace_id}/chains \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Обработка заказа",
    "trigger_type": "manual",
    "stop_on_failure": true,
    "steps": [
      {
        "name": "Получить заказ",
        "url": "https://api.example.com/orders/123",
        "method": "GET",
        "extract_variables": {
          "order_total": "$.total",
          "customer_id": "$.customer.id"
        }
      },
      {
        "name": "Списать средства",
        "url": "https://api.example.com/payments",
        "method": "POST",
        "body": "{\\"amount\\": \\"{{order_total}}\\", \\"customer_id\\": \\"{{customer_id}}\\"}"
      },
      {
        "name": "Отправить уведомление",
        "url": "https://api.example.com/notify",
        "method": "POST",
        "continue_on_failure": true
      }
    ]
  }'`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Шаги цепочки</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/chains/{id}/steps" description="Список шагов" />
        <Endpoint method="POST" path="/chains/{id}/steps" description="Добавление шага" />
        <Endpoint method="PATCH" path="/chains/{id}/steps/{step_id}" description="Обновление шага" />
        <Endpoint method="DELETE" path="/chains/{id}/steps/{step_id}" description="Удаление шага" />
        <Endpoint method="PUT" path="/chains/{id}/steps/reorder" description="Изменение порядка шагов" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Параметры шага</h3>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">Параметр</th>
              <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">Тип</th>
              <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">Описание</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-4 py-2 text-sm font-mono text-gray-600 dark:text-gray-300">extract_variables</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">object</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">JSONPath для извлечения переменных из ответа</td>
            </tr>
            <tr>
              <td className="px-4 py-2 text-sm font-mono text-gray-600 dark:text-gray-300">condition</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">object</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">Условие для выполнения шага</td>
            </tr>
            <tr>
              <td className="px-4 py-2 text-sm font-mono text-gray-600 dark:text-gray-300">continue_on_failure</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">boolean</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">Продолжить цепочку при ошибке шага</td>
            </tr>
            <tr>
              <td className="px-4 py-2 text-sm font-mono text-gray-600 dark:text-gray-300">retry_count</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">integer</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">Количество повторных попыток (0-5)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Переменные</h3>
      <p className="mt-2 text-gray-600 dark:text-gray-300">
        Используйте синтаксис <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">{'{{variable}}'}</code> для
        подстановки переменных в URL и тело запроса. Переменные извлекаются из предыдущих
        шагов через JSONPath.
      </p>

      <CodeBlock
        language="json"
        code={`{
  "extract_variables": {
    "user_id": "$.data.id",
    "user_email": "$.data.email",
    "order_items": "$.items[*].id"
  }
}`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Условия выполнения</h3>
      <p className="mt-2 text-gray-600 dark:text-gray-300">
        Шаги могут выполняться условно на основе результатов предыдущих шагов:
      </p>

      <CodeBlock
        language="json"
        code={`{
  "condition": {
    "operator": "status_code_in",
    "value": [200, 201]
  }
}

// Или проверка значения из ответа:
{
  "condition": {
    "operator": "equals",
    "field": "$.status",
    "value": "approved"
  }
}`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Выполнения цепочки</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/chains/{id}/executions" description="История выполнений" />
        <Endpoint method="GET" path="/chains/{id}/executions/{exec_id}" description="Детали выполнения с результатами шагов" />
      </div>

      <div className="mt-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <strong>Примечание:</strong> Цепочки поддерживают политику запуска (overlap prevention).
          Используйте параметры <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">overlap_policy</code>,{' '}
          <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">max_instances</code> для контроля
          параллельных выполнений.
        </p>
      </div>
    </div>
  )
}

export function HeartbeatsSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Heartbeat-мониторы</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        Heartbeat-мониторы позволяют отслеживать работу ваших cron-задач и сервисов.
        Создайте монитор, получите уникальный URL для пинга, и CronBox уведомит вас,
        если пинг не получен вовремя.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Как это работает</h3>

      <ol className="mt-4 space-y-4 text-gray-600 dark:text-gray-300">
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50 text-sm font-semibold text-primary-600 dark:text-primary-400">
            1
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-white">Создайте монитор</p>
            <p className="text-sm">
              Укажите ожидаемый интервал между пингами и grace period
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50 text-sm font-semibold text-primary-600 dark:text-primary-400">
            2
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-white">Получите URL для пинга</p>
            <p className="text-sm">
              Каждый монитор имеет уникальный URL вида{' '}
              <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">https://api.cronbox.ru/ping/abc123</code>
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50 text-sm font-semibold text-primary-600 dark:text-primary-400">
            3
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-white">Добавьте пинг в ваш cron</p>
            <p className="text-sm">
              В конце вашего скрипта отправьте GET-запрос на URL монитора
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50 text-sm font-semibold text-primary-600 dark:text-primary-400">
            4
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-white">Получайте уведомления</p>
            <p className="text-sm">
              CronBox уведомит вас, если пинг не получен в ожидаемое время
            </p>
          </div>
        </li>
      </ol>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/heartbeats" description="Список мониторов" />
        <Endpoint method="POST" path="/heartbeats" description="Создание монитора" />
        <Endpoint method="GET" path="/heartbeats/{id}" description="Получение монитора" />
        <Endpoint method="PATCH" path="/heartbeats/{id}" description="Обновление монитора" />
        <Endpoint method="DELETE" path="/heartbeats/{id}" description="Удаление монитора" />
        <Endpoint method="POST" path="/heartbeats/{id}/pause" description="Приостановка монитора" />
        <Endpoint method="POST" path="/heartbeats/{id}/resume" description="Возобновление монитора" />
        <Endpoint method="GET" path="/heartbeats/{id}/pings" description="История пингов" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Создание монитора</h3>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/workspaces/{workspace_id}/heartbeats \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Бэкап базы данных",
    "description": "Ежедневный бэкап в 3:00",
    "expected_interval": "24h",
    "grace_period": "30m",
    "notify_on_late": true,
    "notify_on_recovery": true
  }'`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Формат интервалов</h3>
      <p className="mt-2 text-gray-600 dark:text-gray-300">
        Интервалы указываются в удобном формате:
      </p>
      <ul className="mt-2 space-y-2 text-sm text-gray-600 dark:text-gray-300">
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">5m</code> - 5 минут
        </li>
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">1h</code> - 1 час
        </li>
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">24h</code> - 24 часа
        </li>
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">7d</code> - 7 дней
        </li>
        <li>
          <code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">1h30m</code> - 1 час 30 минут
        </li>
      </ul>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Пинг монитора</h3>
      <p className="mt-2 text-gray-600 dark:text-gray-300">
        Публичный эндпоинт для отправки пинга (не требует авторизации):
      </p>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/ping/{token}" description="Отправка пинга (публичный)" />
        <Endpoint method="POST" path="/ping/{token}" description="Отправка пинга с данными" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Пример использования в cron</h3>

      <CodeBlock
        code={`# Crontab: бэкап каждый день в 3:00
0 3 * * * /opt/scripts/backup.sh && curl -fsS https://api.cronbox.ru/ping/abc123

# Или с проверкой exit code
0 3 * * * /opt/scripts/backup.sh; curl https://api.cronbox.ru/ping/abc123?exit_code=$?`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Статусы монитора</h3>

      <div className="mt-4 space-y-4">
        <div className="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 p-4">
          <h4 className="font-semibold text-green-800 dark:text-green-200">healthy</h4>
          <p className="mt-1 text-sm text-green-700 dark:text-green-300">
            Пинг получен вовремя, всё работает нормально
          </p>
        </div>

        <div className="rounded-lg border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20 p-4">
          <h4 className="font-semibold text-yellow-800 dark:text-yellow-200">waiting</h4>
          <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
            Ожидание первого пинга или находится в grace period
          </p>
        </div>

        <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4">
          <h4 className="font-semibold text-red-800 dark:text-red-200">late</h4>
          <p className="mt-1 text-sm text-red-700 dark:text-red-300">
            Пинг не получен в ожидаемое время — возможна проблема
          </p>
        </div>
      </div>

      <div className="mt-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <strong>Совет:</strong> Используйте grace period для учёта возможных задержек
          выполнения. Например, если скрипт обычно выполняется 10 минут, установите
          grace period в 15-20 минут.
        </p>
      </div>
    </div>
  )
}

export function OverlapPreventionSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Политика запуска</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        Политика запуска позволяет контролировать поведение задач, когда новое выполнение
        запускается до завершения предыдущего. Это критически важно для задач, которые
        не должны выполняться параллельно.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Режимы запуска</h3>

      <div className="mt-4 space-y-4">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">allow (по умолчанию)</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Разрешает параллельное выполнение. Новые экземпляры запускаются независимо от
            состояния предыдущих.
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">skip</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Пропускает новое выполнение, если задача уже выполняется. Используется когда
            важно не допустить дублирования работы.
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">queue</h4>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Добавляет новое выполнение в очередь. После завершения текущего экземпляра,
            следующий из очереди запускается автоматически.
          </p>
        </div>
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Параметры</h3>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">Параметр</th>
              <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">Тип</th>
              <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">Описание</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-4 py-2 text-sm font-mono text-gray-600 dark:text-gray-300">overlap_policy</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">string</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">Политика: allow, skip, queue</td>
            </tr>
            <tr>
              <td className="px-4 py-2 text-sm font-mono text-gray-600 dark:text-gray-300">max_instances</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">integer</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">Макс. параллельных экземпляров (1-10)</td>
            </tr>
            <tr>
              <td className="px-4 py-2 text-sm font-mono text-gray-600 dark:text-gray-300">max_queue_size</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">integer</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">Макс. размер очереди (1-100)</td>
            </tr>
            <tr>
              <td className="px-4 py-2 text-sm font-mono text-gray-600 dark:text-gray-300">execution_timeout</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">integer</td>
              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300">Таймаут в секундах для авто-освобождения</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Пример использования</h3>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/cron-tasks \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Синхронизация базы данных",
    "url": "https://your-api.com/sync",
    "method": "POST",
    "cron_expression": "*/5 * * * *",
    "overlap_policy": "skip",
    "max_instances": 1,
    "execution_timeout": 300
  }'`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">API очереди</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/queue" description="Список задач в очереди" />
        <Endpoint method="DELETE" path="/queue/{id}" description="Удаление из очереди" />
        <Endpoint method="GET" path="/overlap-stats" description="Статистика перекрытий" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Метрики</h3>
      <p className="mt-2 text-gray-600 dark:text-gray-300">
        CronBox отслеживает следующие метрики для overlap prevention:
      </p>
      <ul className="mt-2 space-y-2 text-sm text-gray-600 dark:text-gray-300">
        <li><code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">executions_skipped</code> - количество пропущенных выполнений</li>
        <li><code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">executions_queued</code> - количество выполнений добавленных в очередь</li>
        <li><code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">overlap_rate</code> - процент перекрытий</li>
        <li><code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">running_instances</code> - текущее количество запущенных экземпляров</li>
      </ul>

      <div className="mt-8 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4">
        <p className="text-sm text-yellow-800 dark:text-yellow-200">
          <strong>Важно:</strong> При использовании политики queue, убедитесь что ваша задача
          завершается в разумное время. Используйте execution_timeout для автоматического
          освобождения зависших экземпляров.
        </p>
      </div>
    </div>
  )
}

export function BillingSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Биллинг</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        API для управления подписками и просмотра информации о тарифах.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <Endpoint method="GET" path="/billing/plans" description="Список доступных тарифов" />
        <Endpoint method="GET" path="/billing/subscription" description="Текущая подписка" />
        <Endpoint method="POST" path="/billing/subscribe" description="Оформление подписки" />
        <Endpoint method="POST" path="/billing/cancel" description="Отмена подписки" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Получение тарифов</h3>

      <CodeBlock
        code={`curl https://api.cronbox.ru/v1/billing/plans \\
  -H "Authorization: Bearer YOUR_TOKEN"`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900 dark:text-white">Оформление подписки</h3>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/billing/subscribe \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "plan_id": "professional",
    "return_url": "https://your-site.com/billing/success"
  }'`}
      />

      <p className="mt-4 text-gray-600 dark:text-gray-300">
        В ответе вы получите URL для оплаты через YooKassa:
      </p>

      <CodeBlock
        language="json"
        code={`{
  "payment_url": "https://yoomoney.ru/checkout/...",
  "payment_id": "pay_abc123"
}`}
      />
    </div>
  )
}

export const sectionComponents: Record<string, () => ReactNode> = {
  'getting-started': GettingStartedSection,
  authentication: AuthenticationSection,
  'cron-tasks': CronTasksSection,
  'delayed-tasks': DelayedTasksSection,
  'task-chains': TaskChainsSection,
  heartbeats: HeartbeatsSection,
  'overlap-prevention': OverlapPreventionSection,
  executions: ExecutionsSection,
  notifications: NotificationsSection,
  billing: BillingSection,
}
