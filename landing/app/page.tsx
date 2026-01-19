import type { Metadata } from 'next'
import Link from 'next/link'
import {
  Clock,
  Zap,
  Bell,
  BarChart3,
  Code2,
  Globe,
  RefreshCw,
  ArrowRight,
  Link2,
  HeartPulse,
  Layers,
  Users,
  Server,
  Mail,
  MessageSquare,
  Webhook,
  ChevronDown,
  ShieldCheck,
} from 'lucide-react'
import { JsonLd } from '@/components/JsonLd'

export const metadata: Metadata = {
  title: 'CronBox - Планирование HTTP-запросов по расписанию',
  description:
    'CronBox - облачный сервис для планирования HTTP-запросов. Создавайте cron-задачи, цепочки запросов, heartbeat и SSL-мониторы. Получайте уведомления через Email, Telegram, Webhook.',
  alternates: {
    canonical: 'https://cronbox.ru',
  },
}

const softwareJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'CronBox',
  applicationCategory: 'DeveloperApplication',
  operatingSystem: 'Web',
  description:
    'Облачный сервис для планирования HTTP-запросов по расписанию cron и мониторинга SSL-сертификатов',
  url: 'https://cronbox.ru',
  offers: {
    '@type': 'AggregateOffer',
    lowPrice: '0',
    highPrice: '2990',
    priceCurrency: 'RUB',
    offerCount: '4',
  },
  provider: {
    '@type': 'Organization',
    name: 'CronBox',
    url: 'https://cronbox.ru',
  },
}

const features = [
  {
    name: 'Cron-задачи',
    description:
      'Планируйте регулярные HTTP-запросы по расписанию cron. Поддержка всех стандартных выражений с интервалом от 1 минуты.',
    icon: Clock,
  },
  {
    name: 'Отложенные запросы',
    description:
      'Выполняйте одноразовые HTTP-запросы в указанное время. Идеально для отложенных уведомлений и напоминаний.',
    icon: Zap,
  },
  {
    name: 'Цепочки задач',
    description:
      'Создавайте сложные workflow из нескольких шагов. Передавайте данные между запросами через переменные.',
    icon: Link2,
  },
  {
    name: 'Heartbeat-мониторы',
    description:
      'Отслеживайте работу ваших cron-задач и сервисов. Получайте уведомления, если задача не отработала вовремя.',
    icon: HeartPulse,
  },
  {
    name: 'SSL-мониторинг',
    description:
      'Отслеживайте срок действия SSL-сертификатов. Получайте уведомления до истечения срока, чтобы избежать простоев.',
    icon: ShieldCheck,
  },
  {
    name: 'Политика запуска',
    description:
      'Контролируйте параллельные выполнения. Пропускайте, ставьте в очередь или разрешайте overlap задач.',
    icon: Layers,
  },
  {
    name: 'Уведомления',
    description:
      'Получайте уведомления об ошибках через Email, Telegram или Webhook. Гибкая настройка условий.',
    icon: Bell,
  },
  {
    name: 'История выполнений',
    description:
      'Полная история с деталями каждого запроса и ответа. Фильтрация по статусу и типу задачи.',
    icon: BarChart3,
  },
  {
    name: 'REST API',
    description:
      'Полноценный API для интеграции. Управляйте задачами программно из вашего приложения.',
    icon: Code2,
  },
  {
    name: 'Рабочие пространства',
    description:
      'Разделяйте проекты по workspace. Приглашайте коллег и работайте вместе над задачами.',
    icon: Users,
  },
]

const useCases = [
  {
    title: 'Синхронизация данных',
    description: 'Автоматическая синхронизация между CRM, складом и бухгалтерией каждые 15 минут',
    icon: RefreshCw,
    example: '*/15 * * * *',
  },
  {
    title: 'Мониторинг API',
    description: 'Проверка доступности ваших сервисов и API каждую минуту с уведомлениями при сбоях',
    icon: Globe,
    example: '* * * * *',
  },
  {
    title: 'Рассылка отчётов',
    description: 'Автоматическая генерация и отправка ежедневных отчётов клиентам в 9:00',
    icon: Mail,
    example: '0 9 * * *',
  },
  {
    title: 'Очистка данных',
    description: 'Регулярное удаление устаревших записей и очистка кеша каждую ночь',
    icon: Server,
    example: '0 3 * * *',
  },
  {
    title: 'Обработка заказов',
    description: 'Цепочка задач: проверка оплаты → резервирование товара → отправка уведомления',
    icon: Link2,
    example: 'workflow',
  },
  {
    title: 'Контроль бэкапов',
    description: 'Heartbeat-мониторы: убедитесь, что ваш скрипт бэкапа отработал успешно',
    icon: HeartPulse,
    example: 'heartbeat',
  },
  {
    title: 'SSL-сертификаты',
    description: 'Мониторинг SSL: узнайте об истечении сертификата за 30, 14 и 7 дней',
    icon: ShieldCheck,
    example: 'ssl',
  },
]

const benefits = [
  { value: '99.9%', label: 'Uptime SLA', description: 'Гарантированная доступность сервиса' },
  { value: '< 1 сек', label: 'Точность запуска', description: 'Задачи запускаются вовремя' },
  { value: '24/7', label: 'Мониторинг', description: 'Круглосуточный контроль выполнения' },
  { value: '0 ₽', label: 'Старт', description: 'Бесплатный тариф навсегда' },
]

const faqItems = [
  {
    question: 'Чем CronBox отличается от системного cron?',
    answer: 'CronBox работает в облаке и не зависит от состояния вашего сервера. Вы получаете уведомления об ошибках, историю выполнений, retry при сбоях и удобную панель управления. Не нужно настраивать сервер и следить за его работой.',
  },
  {
    question: 'Какой минимальный интервал между запусками?',
    answer: 'На бесплатном тарифе — 5 минут. На платных тарифах — от 1 минуты. Для Enterprise-клиентов доступен интервал от 10 секунд.',
  },
  {
    question: 'Как работают Heartbeat-мониторы?',
    answer: 'Вы создаёте монитор и получаете уникальный URL. Добавляете вызов этого URL в конец вашего скрипта (curl). Если пинг не приходит в ожидаемое время — вы получаете уведомление. Идеально для контроля cron-задач на ваших серверах.',
  },
  {
    question: 'Что такое цепочки задач?',
    answer: 'Цепочки позволяют выполнять несколько HTTP-запросов последовательно, передавая данные между шагами. Например: получить заказ → списать оплату → отправить уведомление. Результат каждого шага доступен в следующем через переменные.',
  },
  {
    question: 'Какие каналы уведомлений поддерживаются?',
    answer: 'Email, Telegram и Webhook. Вы можете настроить разные каналы для разных событий: ошибки, успешные выполнения, восстановление после сбоя.',
  },
  {
    question: 'Есть ли API для интеграции?',
    answer: 'Да, полноценный REST API с документацией. Вы можете создавать, обновлять и удалять задачи программно, получать историю выполнений и управлять настройками.',
  },
  {
    question: 'Как работает SSL-мониторинг?',
    answer: 'Вы указываете домен для мониторинга, и CronBox регулярно проверяет срок действия SSL-сертификата. Вы получите уведомления за 30, 14 и 7 дней до истечения срока, а также при обнаружении проблем с сертификатом (невалидная цепочка, несовпадение домена и др.).',
  },
]

export default function HomePage() {
  return (
    <>
      <JsonLd data={softwareJsonLd} />

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary-50 to-white dark:from-gray-800 dark:to-gray-900 py-20 sm:py-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl">
              Планирование HTTP-запросов{' '}
              <span className="text-primary-600 dark:text-primary-400">по расписанию</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600 dark:text-gray-300">
              Облачный сервис для автоматизации HTTP-запросов. Cron-задачи, цепочки запросов,
              heartbeat-мониторинг — всё в одном месте. Работает 24/7 без вашего сервера.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <a
                href="https://cp.cronbox.ru/#/register"
                className="rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors"
              >
                Начать бесплатно
              </a>
              <Link
                href="/docs"
                className="flex items-center gap-2 text-base font-semibold text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
              >
                Документация <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>

          {/* Code example */}
          <div className="mx-auto mt-16 max-w-4xl">
            <div className="rounded-xl bg-gray-900 p-6 shadow-2xl">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <div className="h-3 w-3 rounded-full bg-yellow-500" />
                <div className="h-3 w-3 rounded-full bg-green-500" />
              </div>
              <pre className="text-sm text-gray-300 overflow-x-auto">
                <code>{`# Создание cron-задачи через API
curl -X POST https://api.cronbox.ru/v1/cron-tasks \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Синхронизация данных",
    "url": "https://your-api.com/sync",
    "method": "POST",
    "cron_expression": "0 */6 * * *",
    "overlap_policy": "skip"
  }'`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            {benefits.map((benefit) => (
              <div key={benefit.label} className="text-center">
                <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
                  {benefit.value}
                </div>
                <div className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
                  {benefit.label}
                </div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {benefit.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 sm:py-32 bg-white dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
              Всё для автоматизации HTTP-запросов
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
              Мощные инструменты для планирования, мониторинга и управления задачами
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-6xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.name}
                className="relative rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 transition-all"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/50">
                  <feature.icon className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-gray-900 dark:text-white">
                  {feature.name}
                </h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Notifications Section */}
      <section className="py-20 sm:py-32 bg-gray-50 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
                Уведомления там, где вам удобно
              </h2>
              <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
                Получайте мгновенные уведомления об ошибках и успешных выполнениях через
                привычные каналы связи.
              </p>
              <div className="mt-8 space-y-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/50">
                    <MessageSquare className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">Telegram</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Мгновенные уведомления в чат</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-red-100 dark:bg-red-900/50">
                    <Mail className="h-6 w-6 text-red-600 dark:text-red-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">Email</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Подробные отчёты на почту</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/50">
                    <Webhook className="h-6 w-6 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">Webhook</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Интеграция с любой системой</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="rounded-xl bg-gray-900 p-6 shadow-2xl">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <div className="h-3 w-3 rounded-full bg-yellow-500" />
                <div className="h-3 w-3 rounded-full bg-green-500" />
              </div>
              <pre className="text-sm text-gray-300 overflow-x-auto">
                <code>{`{
  "event": "task.failed",
  "task": {
    "id": "550e8400-e29b-41d4...",
    "name": "Синхронизация данных",
    "status": "failed"
  },
  "execution": {
    "status_code": 500,
    "duration_ms": 1234,
    "error": "Internal Server Error"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20 sm:py-32 bg-white dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
              Сценарии использования
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
              CronBox подходит для любых задач автоматизации HTTP-запросов
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {useCases.map((useCase) => (
              <div
                key={useCase.title}
                className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50">
                    <useCase.icon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  {useCase.example !== 'workflow' && useCase.example !== 'heartbeat' && useCase.example !== 'ssl' && (
                    <code className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-600 dark:text-gray-400">
                      {useCase.example}
                    </code>
                  )}
                  {useCase.example === 'workflow' && (
                    <span className="text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 px-2 py-1 rounded">
                      цепочка
                    </span>
                  )}
                  {useCase.example === 'heartbeat' && (
                    <span className="text-xs bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 px-2 py-1 rounded">
                      heartbeat
                    </span>
                  )}
                  {useCase.example === 'ssl' && (
                    <span className="text-xs bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 px-2 py-1 rounded">
                      ssl
                    </span>
                  )}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                  {useCase.title}
                </h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{useCase.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 sm:py-32 bg-gray-50 dark:bg-gray-800">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
              Часто задаваемые вопросы
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
              Ответы на популярные вопросы о CronBox
            </p>
          </div>

          <div className="mt-12 space-y-4">
            {faqItems.map((item, index) => (
              <details
                key={index}
                className="group rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
              >
                <summary className="flex cursor-pointer items-center justify-between p-4 text-left font-semibold text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors">
                  {item.question}
                  <ChevronDown className="h-5 w-5 text-gray-500 transition-transform group-open:rotate-180" />
                </summary>
                <div className="px-4 pb-4 text-gray-600 dark:text-gray-300">
                  {item.answer}
                </div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-primary-600 py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Готовы автоматизировать ваши задачи?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-primary-100">
            Начните использовать CronBox бесплатно. Регистрация занимает меньше минуты.
            Кредитная карта не требуется.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <a
              href="https://cp.cronbox.ru/#/register"
              className="rounded-lg bg-white px-6 py-3 text-base font-semibold text-primary-600 shadow-sm hover:bg-primary-50 transition-colors"
            >
              Создать аккаунт бесплатно
            </a>
            <Link
              href="/pricing"
              className="rounded-lg border-2 border-white px-6 py-3 text-base font-semibold text-white hover:bg-primary-700 transition-colors"
            >
              Посмотреть тарифы
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}
