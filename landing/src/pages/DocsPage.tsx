import { useParams, Link } from 'react-router-dom'
import { useEffect } from 'react'
import type { ReactNode } from 'react'
import clsx from 'clsx'
import {
  Book,
  Key,
  Clock,
  Timer,
  Activity,
  Bell,
  CreditCard,
  ChevronRight,
} from 'lucide-react'

const sections = [
  { id: 'getting-started', name: 'Начало работы', icon: Book },
  { id: 'authentication', name: 'Аутентификация', icon: Key },
  { id: 'cron-tasks', name: 'Cron-задачи', icon: Clock },
  { id: 'delayed-tasks', name: 'Отложенные задачи', icon: Timer },
  { id: 'executions', name: 'Выполнения', icon: Activity },
  { id: 'notifications', name: 'Уведомления', icon: Bell },
  { id: 'billing', name: 'Биллинг', icon: CreditCard },
]

const CodeBlock = ({ code, language = 'bash' }: { code: string; language?: string }) => (
  <pre className={`language-${language} rounded-lg bg-gray-900 p-4 overflow-x-auto text-sm`}>
    <code className="text-gray-300">{code}</code>
  </pre>
)

const Endpoint = ({
  method,
  path,
  description,
}: {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  path: string
  description: string
}) => {
  const methodColors = {
    GET: 'bg-green-100 text-green-700',
    POST: 'bg-blue-100 text-blue-700',
    PUT: 'bg-yellow-100 text-yellow-700',
    PATCH: 'bg-orange-100 text-orange-700',
    DELETE: 'bg-red-100 text-red-700',
  }

  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-100 last:border-0">
      <span
        className={clsx(
          'inline-flex items-center px-2 py-1 rounded text-xs font-mono font-semibold',
          methodColors[method]
        )}
      >
        {method}
      </span>
      <div>
        <code className="text-sm font-mono text-gray-900">{path}</code>
        <p className="mt-1 text-sm text-gray-600">{description}</p>
      </div>
    </div>
  )
}

function GettingStartedSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Начало работы</h2>
      <p className="mt-4 text-gray-600">
        CronBox API позволяет управлять HTTP-задачами программно. Все запросы
        выполняются к базовому URL:
      </p>

      <CodeBlock code="https://api.cronbox.ru/v1" />

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Быстрый старт</h3>

      <ol className="mt-4 space-y-4 text-gray-600">
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-600">
            1
          </span>
          <div>
            <p className="font-medium text-gray-900">Зарегистрируйтесь</p>
            <p className="text-sm">
              Создайте аккаунт в{' '}
              <a href="https://cp.cronbox.ru/#/register" className="text-primary-600 hover:underline">
                панели управления
              </a>
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-600">
            2
          </span>
          <div>
            <p className="font-medium text-gray-900">Получите API-ключ</p>
            <p className="text-sm">
              Создайте API-ключ в разделе «Настройки» → «API-ключи»
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-600">
            3
          </span>
          <div>
            <p className="font-medium text-gray-900">Создайте первую задачу</p>
            <p className="text-sm">Используйте API для создания cron или отложенной задачи</p>
          </div>
        </li>
      </ol>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Формат ответов</h3>
      <p className="mt-2 text-gray-600">
        Все ответы возвращаются в формате JSON. Успешные ответы имеют код 2xx,
        ошибки — 4xx или 5xx.
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

function AuthenticationSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Аутентификация</h2>
      <p className="mt-4 text-gray-600">
        CronBox API использует Bearer-токены для аутентификации. Передавайте
        токен в заголовке Authorization каждого запроса.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Получение токена</h3>

      <Endpoint
        method="POST"
        path="/auth/login"
        description="Авторизация по email и паролю"
      />

      <p className="mt-4 text-gray-600">Пример запроса:</p>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "your_password"
  }'`}
      />

      <p className="mt-4 text-gray-600">Пример ответа:</p>

      <CodeBlock
        language="json"
        code={`{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Использование токена</h3>

      <CodeBlock
        code={`curl https://api.cronbox.ru/v1/cron-tasks \\
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Обновление токена</h3>

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

      <div className="mt-8 rounded-lg bg-yellow-50 border border-yellow-200 p-4">
        <p className="text-sm text-yellow-800">
          <strong>Важно:</strong> Access-токен действителен 15 минут.
          Refresh-токен — 30 дней. Храните токены безопасно и не передавайте
          третьим лицам.
        </p>
      </div>
    </div>
  )
}

function CronTasksSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Cron-задачи</h2>
      <p className="mt-4 text-gray-600">
        Cron-задачи выполняются регулярно по заданному расписанию. Используйте
        стандартный формат cron-выражений.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200">
        <Endpoint method="GET" path="/cron-tasks" description="Список всех cron-задач" />
        <Endpoint method="POST" path="/cron-tasks" description="Создание новой задачи" />
        <Endpoint method="GET" path="/cron-tasks/{id}" description="Получение задачи по ID" />
        <Endpoint method="PATCH" path="/cron-tasks/{id}" description="Обновление задачи" />
        <Endpoint method="DELETE" path="/cron-tasks/{id}" description="Удаление задачи" />
        <Endpoint method="POST" path="/cron-tasks/{id}/pause" description="Приостановка задачи" />
        <Endpoint method="POST" path="/cron-tasks/{id}/unpause" description="Возобновление задачи" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Создание задачи</h3>

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

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Параметры задачи</h3>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Параметр
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Тип
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Описание
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">name</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">Название задачи</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">url</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">URL для запроса</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">method</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">HTTP-метод (GET, POST, PUT, PATCH, DELETE)</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">cron_expression</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">Cron-выражение (5 полей)</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">headers</td>
              <td className="px-4 py-3 text-sm text-gray-600">object</td>
              <td className="px-4 py-3 text-sm text-gray-600">HTTP-заголовки (опционально)</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">body</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">Тело запроса (опционально)</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">timeout_seconds</td>
              <td className="px-4 py-3 text-sm text-gray-600">integer</td>
              <td className="px-4 py-3 text-sm text-gray-600">Таймаут в секундах (по умолчанию 30)</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">retry_count</td>
              <td className="px-4 py-3 text-sm text-gray-600">integer</td>
              <td className="px-4 py-3 text-sm text-gray-600">Количество повторных попыток (0-5)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Формат cron-выражений</h3>
      <p className="mt-2 text-gray-600">
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

      <p className="mt-4 text-gray-600">Примеры:</p>
      <ul className="mt-2 space-y-2 text-sm text-gray-600">
        <li>
          <code className="bg-gray-100 px-2 py-0.5 rounded">*/5 * * * *</code> — каждые 5 минут
        </li>
        <li>
          <code className="bg-gray-100 px-2 py-0.5 rounded">0 */2 * * *</code> — каждые 2 часа
        </li>
        <li>
          <code className="bg-gray-100 px-2 py-0.5 rounded">0 9 * * 1-5</code> — в 9:00 по будням
        </li>
        <li>
          <code className="bg-gray-100 px-2 py-0.5 rounded">0 0 1 * *</code> — первого числа каждого месяца
        </li>
      </ul>
    </div>
  )
}

function DelayedTasksSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Отложенные задачи</h2>
      <p className="mt-4 text-gray-600">
        Отложенные задачи выполняются один раз в указанное время. Идеально для
        отправки отложенных уведомлений, напоминаний и одноразовых действий.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200">
        <Endpoint method="GET" path="/delayed-tasks" description="Список отложенных задач" />
        <Endpoint method="POST" path="/delayed-tasks" description="Создание отложенной задачи" />
        <Endpoint method="GET" path="/delayed-tasks/{id}" description="Получение задачи по ID" />
        <Endpoint method="DELETE" path="/delayed-tasks/{id}" description="Отмена задачи" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Создание задачи</h3>

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

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Параметры</h3>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Параметр
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Тип
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Описание
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">name</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">Название задачи</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">url</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">URL для запроса</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">method</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">HTTP-метод</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">execute_at</td>
              <td className="px-4 py-3 text-sm text-gray-600">string (ISO 8601)</td>
              <td className="px-4 py-3 text-sm text-gray-600">Время выполнения в UTC</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">headers</td>
              <td className="px-4 py-3 text-sm text-gray-600">object</td>
              <td className="px-4 py-3 text-sm text-gray-600">HTTP-заголовки (опционально)</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">body</td>
              <td className="px-4 py-3 text-sm text-gray-600">string</td>
              <td className="px-4 py-3 text-sm text-gray-600">Тело запроса (опционально)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-8 rounded-lg bg-blue-50 border border-blue-200 p-4">
        <p className="text-sm text-blue-800">
          <strong>Примечание:</strong> Время выполнения указывается в формате
          ISO 8601 в часовом поясе UTC. Например:{' '}
          <code className="bg-blue-100 px-1 rounded">2024-01-20T15:00:00Z</code>
        </p>
      </div>
    </div>
  )
}

function ExecutionsSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Выполнения</h2>
      <p className="mt-4 text-gray-600">
        Каждое выполнение задачи записывается с полной информацией о запросе и
        ответе. Используйте API выполнений для мониторинга и отладки.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200">
        <Endpoint method="GET" path="/executions" description="Список выполнений" />
        <Endpoint method="GET" path="/executions/{id}" description="Детали выполнения" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Получение списка</h3>

      <CodeBlock
        code={`curl "https://api.cronbox.ru/v1/executions?limit=20&status=failed" \\
  -H "Authorization: Bearer YOUR_TOKEN"`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Параметры фильтрации</h3>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Параметр
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                Описание
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">task_id</td>
              <td className="px-4 py-3 text-sm text-gray-600">Фильтр по ID задачи</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">task_type</td>
              <td className="px-4 py-3 text-sm text-gray-600">Тип задачи: cron или delayed</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">status</td>
              <td className="px-4 py-3 text-sm text-gray-600">Статус: success, failed, timeout</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">limit</td>
              <td className="px-4 py-3 text-sm text-gray-600">Количество записей (по умолчанию 50)</td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm font-mono text-gray-900">offset</td>
              <td className="px-4 py-3 text-sm text-gray-600">Смещение для пагинации</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Пример ответа</h3>

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
      "request": {
        "url": "https://api.example.com/sync",
        "method": "POST",
        "headers": {"Content-Type": "application/json"}
      },
      "response": {
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "body": "{\\"status\\": \\"ok\\"}"
      },
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

function NotificationsSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Уведомления</h2>
      <p className="mt-4 text-gray-600">
        Настройте уведомления о статусе выполнения задач через Email, Telegram
        или Webhook.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200">
        <Endpoint method="GET" path="/notifications/settings" description="Текущие настройки уведомлений" />
        <Endpoint method="PATCH" path="/notifications/settings" description="Обновление настроек" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Каналы уведомлений</h3>

      <div className="mt-4 space-y-6">
        <div className="rounded-lg border border-gray-200 p-4">
          <h4 className="font-semibold text-gray-900">Email</h4>
          <p className="mt-1 text-sm text-gray-600">
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

        <div className="rounded-lg border border-gray-200 p-4">
          <h4 className="font-semibold text-gray-900">Telegram</h4>
          <p className="mt-1 text-sm text-gray-600">
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

        <div className="rounded-lg border border-gray-200 p-4">
          <h4 className="font-semibold text-gray-900">Webhook</h4>
          <p className="mt-1 text-sm text-gray-600">
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

function BillingSection() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Биллинг</h2>
      <p className="mt-4 text-gray-600">
        API для управления подписками и просмотра информации о тарифах.
      </p>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Эндпоинты</h3>

      <div className="mt-4 rounded-lg border border-gray-200">
        <Endpoint method="GET" path="/billing/plans" description="Список доступных тарифов" />
        <Endpoint method="GET" path="/billing/subscription" description="Текущая подписка" />
        <Endpoint method="POST" path="/billing/subscribe" description="Оформление подписки" />
        <Endpoint method="POST" path="/billing/cancel" description="Отмена подписки" />
      </div>

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Получение тарифов</h3>

      <CodeBlock
        code={`curl https://api.cronbox.ru/v1/billing/plans \\
  -H "Authorization: Bearer YOUR_TOKEN"`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Пример ответа</h3>

      <CodeBlock
        language="json"
        code={`{
  "plans": [
    {
      "id": "starter",
      "name": "Starter",
      "price": 490,
      "currency": "RUB",
      "interval": "month",
      "features": {
        "max_cron_tasks": 25,
        "max_delayed_tasks_per_day": 100,
        "min_interval_seconds": 60,
        "max_executions_per_day": 1000,
        "history_days": 30
      }
    }
  ]
}`}
      />

      <h3 className="mt-8 text-xl font-semibold text-gray-900">Оформление подписки</h3>

      <CodeBlock
        code={`curl -X POST https://api.cronbox.ru/v1/billing/subscribe \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "plan_id": "professional",
    "return_url": "https://your-site.com/billing/success"
  }'`}
      />

      <p className="mt-4 text-gray-600">
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

const sectionComponents: Record<string, () => ReactNode> = {
  'getting-started': GettingStartedSection,
  'authentication': AuthenticationSection,
  'cron-tasks': CronTasksSection,
  'delayed-tasks': DelayedTasksSection,
  'executions': ExecutionsSection,
  'notifications': NotificationsSection,
  'billing': BillingSection,
}

export function DocsPage() {
  const { section } = useParams()
  const activeSection = section || 'getting-started'

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [activeSection])

  const SectionComponent = sectionComponents[activeSection] || GettingStartedSection

  return (
    <div className="bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
        {/* Mobile section selector */}
        <div className="lg:hidden mb-6">
          <label className="text-sm font-medium text-gray-700">Раздел</label>
          <select
            value={activeSection}
            onChange={(e) => {
              window.location.href = `/docs/${e.target.value}`
            }}
            className="mt-1 block w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-3 pr-10 text-base focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {sections.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        <div className="lg:flex lg:gap-12">
          {/* Sidebar */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <div className="sticky top-24">
              <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                Документация API
              </h2>
              <nav className="mt-4 space-y-1">
                {sections.map((item) => (
                  <Link
                    key={item.id}
                    to={`/docs/${item.id}`}
                    className={clsx(
                      'flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors',
                      activeSection === item.id
                        ? 'bg-primary-50 text-primary-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.name}
                  </Link>
                ))}
              </nav>
            </div>
          </aside>

          {/* Content */}
          <main className="flex-1 min-w-0">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm text-gray-500 mb-8">
              <Link to="/docs" className="hover:text-primary-600">
                Документация
              </Link>
              <ChevronRight className="h-4 w-4" />
              <span className="text-gray-900">
                {sections.find((s) => s.id === activeSection)?.name}
              </span>
            </nav>

            <SectionComponent />

            {/* Next/Prev navigation */}
            <div className="mt-16 pt-8 border-t border-gray-200">
              <div className="flex justify-between">
                {sections.findIndex((s) => s.id === activeSection) > 0 && (
                  <Link
                    to={`/docs/${sections[sections.findIndex((s) => s.id === activeSection) - 1].id}`}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    &larr;{' '}
                    {sections[sections.findIndex((s) => s.id === activeSection) - 1].name}
                  </Link>
                )}
                <div className="flex-1" />
                {sections.findIndex((s) => s.id === activeSection) <
                  sections.length - 1 && (
                  <Link
                    to={`/docs/${sections[sections.findIndex((s) => s.id === activeSection) + 1].id}`}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    {sections[sections.findIndex((s) => s.id === activeSection) + 1].name}{' '}
                    &rarr;
                  </Link>
                )}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
