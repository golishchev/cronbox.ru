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
  executions: ExecutionsSection,
  notifications: NotificationsSection,
  billing: BillingSection,
}
