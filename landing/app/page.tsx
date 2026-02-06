import type { Metadata } from 'next'
import Link from 'next/link'
import {
  Clock,
  Bell,
  BarChart3,
  Code2,
  ArrowRight,
  HeartPulse,
  Layers,
  Users,
  Mail,
  MessageSquare,
  Webhook,
  ChevronDown,
  ShieldCheck,
  Activity,
  Timer,
  GitBranch,
  Radio,
  Plug,
  MessageCircle,
} from 'lucide-react'
import { JsonLd } from '@/components/JsonLd'

export const metadata: Metadata = {
  title: 'CronBox - Платформа мониторинга и автоматизации',
  description:
    'CronBox - платформа мониторинга и автоматизации для разработчиков. Heartbeat-мониторинг cron-задач, SSL-алерты, ICMP ping и TCP порты, HTTP-автоматизация, цепочки запросов. Узнайте первым, когда что-то пойдёт не так.',
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
    'Платформа мониторинга и автоматизации для разработчиков. Heartbeat-мониторинг, SSL-алерты, HTTP-автоматизация.',
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

const monitoringFeatures = [
  {
    name: 'Heartbeat-мониторинг',
    description:
      'Отслеживайте работу cron-задач, бэкапов и скриптов на ваших серверах. Если задача не отработала - вы узнаете первым.',
    icon: HeartPulse,
    tag: 'Dead Man\'s Switch',
  },
  {
    name: 'SSL-мониторинг',
    description:
      'Отслеживайте срок действия SSL-сертификатов. Получайте уведомления за 30, 14 и 7 дней до истечения.',
    icon: ShieldCheck,
    tag: 'Сертификаты',
  },
  {
    name: 'ICMP (Ping) мониторинг',
    description:
      'Проверяйте доступность серверов и сетевых устройств. Отслеживайте время отклика и потерю пакетов.',
    icon: Radio,
    tag: 'Ping',
  },
  {
    name: 'TCP-мониторинг',
    description:
      'Проверяйте открытость портов на серверах. Мониторьте базы данных, почтовые серверы и другие TCP-сервисы.',
    icon: Plug,
    tag: 'Порты',
  },
]

const automationFeatures = [
  {
    name: 'Cron-задачи',
    description:
      'Планируйте HTTP-запросы по расписанию. Синхронизация данных, отправка отчётов, очистка кеша - всё автоматически.',
    icon: Clock,
  },
  {
    name: 'Отложенные запросы',
    description:
      'Выполняйте одноразовые HTTP-запросы в указанное время. Идеально для отложенных уведомлений и напоминаний.',
    icon: Timer,
  },
  {
    name: 'Цепочки задач',
    description:
      'Создавайте workflow из нескольких шагов. Передавайте данные между запросами через переменные.',
    icon: GitBranch,
  },
  {
    name: 'Политика запуска',
    description:
      'Контролируйте параллельные выполнения. Пропускайте, ставьте в очередь или разрешайте overlap.',
    icon: Layers,
  },
]

const additionalFeatures = [
  {
    name: 'Мгновенные уведомления',
    description: 'Email, Telegram, MAX, Webhook - выберите удобный канал для алертов.',
    icon: Bell,
  },
  {
    name: 'История выполнений',
    description: 'Полная история с деталями каждого запроса и ответа.',
    icon: BarChart3,
  },
  {
    name: 'REST API',
    description: 'Управляйте задачами программно из вашего приложения.',
    icon: Code2,
  },
  {
    name: 'Рабочие пространства',
    description: 'Разделяйте проекты по workspace. Работайте в команде.',
    icon: Users,
  },
]

const useCases = [
  {
    title: 'Мониторинг бэкапов',
    description: 'Убедитесь, что ваш скрипт резервного копирования отработал успешно. Если пинг не пришёл - получите алерт.',
    icon: HeartPulse,
    type: 'heartbeat',
    color: 'green',
  },
  {
    title: 'SSL-сертификаты',
    description: 'Никогда не пропустите истечение сертификата. Уведомления за 30, 14 и 7 дней до дедлайна.',
    icon: ShieldCheck,
    type: 'ssl',
    color: 'purple',
  },
  {
    title: 'Доступность серверов',
    description: 'Ping-мониторинг серверов и сетевых устройств. Отслеживайте время отклика и потерю пакетов.',
    icon: Radio,
    type: 'ping',
    color: 'cyan',
  },
  {
    title: 'Проверка портов',
    description: 'Мониторьте открытость портов баз данных, почтовых серверов и других TCP-сервисов.',
    icon: Plug,
    type: 'tcp',
    color: 'cyan',
  },
  {
    title: 'Контроль cron-задач',
    description: 'Мониторьте системные cron-задачи на серверах. Узнайте, если задача зависла или не запустилась.',
    icon: Activity,
    type: 'heartbeat',
    color: 'green',
  },
  {
    title: 'Синхронизация данных',
    description: 'Автоматическая синхронизация между CRM, складом и бухгалтерией по расписанию.',
    icon: Clock,
    type: 'cron',
    color: 'blue',
  },
  {
    title: 'Обработка заказов',
    description: 'Цепочка: проверка оплаты → резервирование → отправка уведомления клиенту.',
    icon: GitBranch,
    type: 'chain',
    color: 'orange',
  },
  {
    title: 'Рассылка отчётов',
    description: 'Автоматическая генерация и отправка ежедневных отчётов в 9:00.',
    icon: Mail,
    type: 'cron',
    color: 'blue',
  },
]

const benefits = [
  { value: '99.9%', label: 'Uptime SLA', description: 'Гарантированная доступность' },
  { value: '< 1 сек', label: 'Скорость алертов', description: 'Мгновенные уведомления' },
  { value: '24/7', label: 'Мониторинг', description: 'Круглосуточный контроль' },
  { value: '0 ₽', label: 'Старт', description: 'Бесплатный тариф навсегда' },
]

const faqItems = [
  {
    question: 'Как работают Heartbeat-мониторы?',
    answer:
      'Вы создаёте монитор и получаете уникальный URL. Добавляете вызов этого URL (curl) в конец вашего скрипта. Если пинг не приходит в ожидаемое время - вы получаете уведомление. Это идеальный способ контролировать cron-задачи, бэкапы и любые регулярные процессы на ваших серверах.',
  },
  {
    question: 'Что такое SSL-мониторинг?',
    answer:
      'Вы указываете домен, и CronBox регулярно проверяет срок действия SSL-сертификата. Вы получите уведомления за 30, 14, 7 и 1 день до истечения, а также при обнаружении проблем: невалидная цепочка сертификатов, несовпадение домена, использование устаревших протоколов.',
  },
  {
    question: 'Чем CronBox отличается от системного cron?',
    answer:
      'CronBox работает в облаке и не зависит от состояния вашего сервера. Вы получаете уведомления об ошибках, полную историю выполнений, retry при сбоях и удобную панель управления. Главное - вы можете мониторить сам системный cron через Heartbeat-мониторы.',
  },
  {
    question: 'Что такое цепочки задач?',
    answer:
      'Цепочки позволяют выполнять несколько HTTP-запросов последовательно, передавая данные между шагами через переменные. Например: получить заказ → проверить оплату → отправить уведомление. Можно задавать условия выполнения для каждого шага.',
  },
  {
    question: 'Какие каналы уведомлений поддерживаются?',
    answer:
      'Email, Telegram, MAX и Webhook. Вы можете настроить разные каналы для разных событий: ошибки выполнения, пропущенные heartbeat-пинги, истекающие сертификаты, восстановление после сбоя.',
  },
  {
    question: 'Есть ли API для интеграции?',
    answer:
      'Да, полноценный REST API с документацией. Вы можете создавать и управлять задачами, мониторами, получать историю выполнений и статистику программно.',
  },
  {
    question: 'Что такое ICMP и TCP мониторинг?',
    answer:
      'ICMP (ping) мониторинг проверяет доступность серверов и сетевых устройств, показывая время отклика и потерю пакетов. TCP мониторинг проверяет открытость портов на серверах - это позволяет мониторить базы данных (3306, 5432), почтовые серверы (25, 587), веб-серверы (80, 443) и другие TCP-сервисы.',
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
            <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-green-100 dark:bg-green-900/30 px-4 py-2 text-sm font-medium text-green-700 dark:text-green-300">
              <Activity className="h-4 w-4" />
              Платформа мониторинга и автоматизации
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl leading-tight sm:leading-tight">
              Узнайте первым, когда{' '}
              <span className="text-primary-600 dark:text-primary-400">что-то пойдёт не так</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600 dark:text-gray-300">
              Heartbeat-мониторинг cron-задач и бэкапов. SSL-алерты до истечения сертификатов.
              Ping и TCP-мониторинг серверов. HTTP-автоматизация и цепочки запросов. Всё в одном месте.
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

          {/* Visual: Monitoring Dashboard Preview */}
          <div className="mx-auto mt-16 max-w-4xl">
            <div className="rounded-xl bg-gray-900 p-6 shadow-2xl">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <div className="h-3 w-3 rounded-full bg-yellow-500" />
                <div className="h-3 w-3 rounded-full bg-green-500" />
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-lg bg-gray-800 p-3">
                  <div className="flex items-center gap-3">
                    <HeartPulse className="h-5 w-5 text-green-400" />
                    <span className="text-sm text-gray-300">backup-database</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-green-400">Работает</span>
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-gray-800 p-3">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-yellow-400" />
                    <span className="text-sm text-gray-300">example.com</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-yellow-400">Истекает через 12 дней</span>
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-gray-800 p-3">
                  <div className="flex items-center gap-3">
                    <Clock className="h-5 w-5 text-blue-400" />
                    <span className="text-sm text-gray-300">sync-crm</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Следующий запуск: 14:30</span>
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-red-900/30 p-3 border border-red-500/30">
                  <div className="flex items-center gap-3">
                    <HeartPulse className="h-5 w-5 text-red-400" />
                    <span className="text-sm text-gray-300">cleanup-job</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-red-400">Не отвечает</span>
                  </div>
                </div>
              </div>
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

      {/* Monitoring Features Section */}
      <section id="features" className="py-20 sm:py-32 bg-white dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
              Мониторинг критичных процессов
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
              Контролируйте cron-задачи, бэкапы и SSL-сертификаты. Получайте алерты, когда что-то идёт не так.
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-2">
            {monitoringFeatures.map((feature) => (
              <div
                key={feature.name}
                className="relative rounded-2xl border-2 border-primary-200 dark:border-primary-800 bg-gradient-to-br from-primary-50 to-white dark:from-gray-800 dark:to-gray-900 p-8 shadow-sm hover:shadow-lg transition-all"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary-100 dark:bg-primary-900/50">
                    <feature.icon className="h-7 w-7 text-primary-600 dark:text-primary-400" />
                  </div>
                  <span className="text-xs font-medium bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 px-3 py-1 rounded-full">
                    {feature.tag}
                  </span>
                </div>
                <h3 className="mt-6 text-xl font-semibold text-gray-900 dark:text-white">
                  {feature.name}
                </h3>
                <p className="mt-3 text-gray-600 dark:text-gray-300">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Automation Features Section */}
      <section className="py-20 sm:py-32 bg-gray-50 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
              Автоматизация HTTP-запросов
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
              Планируйте задачи, создавайте цепочки запросов, управляйте выполнением
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-2">
            {automationFeatures.map((feature) => (
              <div
                key={feature.name}
                className="relative rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 shadow-sm hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 transition-all"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/50">
                  <feature.icon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
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
      <section className="py-20 sm:py-32 bg-white dark:bg-gray-900">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
                Алерты там, где вам удобно
              </h2>
              <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
                Мгновенные уведомления о проблемах через привычные каналы связи.
                Настройте разные каналы для разных типов событий.
              </p>
              <div className="mt-8 space-y-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/50">
                    <MessageSquare className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">Telegram</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Мгновенные алерты в чат</p>
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
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/50">
                    <MessageCircle className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">MAX</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Уведомления в мессенджер MAX</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/50">
                    <Webhook className="h-6 w-6 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">Webhook</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Интеграция с PagerDuty, Slack и другими</p>
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
  "event": "heartbeat.dead",
  "monitor": {
    "id": "550e8400-e29b...",
    "name": "backup-daily",
    "status": "dead"
  },
  "alert": {
    "missed_pings": 3,
    "last_ping": "2024-01-15T03:00:00Z",
    "expected_at": "2024-01-16T03:00:00Z"
  },
  "message": "Бэкап не выполнился 3 раза подряд"
}`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Additional Features */}
      <section className="py-16 bg-gray-50 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            {additionalFeatures.map((feature) => (
              <div key={feature.name} className="text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-gray-200 dark:bg-gray-700">
                  <feature.icon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
                </div>
                <h3 className="mt-4 text-sm font-semibold text-gray-900 dark:text-white">
                  {feature.name}
                </h3>
                <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{feature.description}</p>
              </div>
            ))}
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
              От мониторинга бэкапов до автоматизации бизнес-процессов
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {useCases.map((useCase) => (
              <div
                key={useCase.title}
                className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center gap-4">
                  <div
                    className={`flex h-12 w-12 items-center justify-center rounded-full ${
                      useCase.color === 'green'
                        ? 'bg-green-100 dark:bg-green-900/50'
                        : useCase.color === 'purple'
                        ? 'bg-purple-100 dark:bg-purple-900/50'
                        : useCase.color === 'blue'
                        ? 'bg-blue-100 dark:bg-blue-900/50'
                        : useCase.color === 'cyan'
                        ? 'bg-cyan-100 dark:bg-cyan-900/50'
                        : 'bg-orange-100 dark:bg-orange-900/50'
                    }`}
                  >
                    <useCase.icon
                      className={`h-6 w-6 ${
                        useCase.color === 'green'
                          ? 'text-green-600 dark:text-green-400'
                          : useCase.color === 'purple'
                          ? 'text-purple-600 dark:text-purple-400'
                          : useCase.color === 'blue'
                          ? 'text-blue-600 dark:text-blue-400'
                          : useCase.color === 'cyan'
                          ? 'text-cyan-600 dark:text-cyan-400'
                          : 'text-orange-600 dark:text-orange-400'
                      }`}
                    />
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      useCase.type === 'heartbeat'
                        ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
                        : useCase.type === 'ssl'
                        ? 'bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300'
                        : useCase.type === 'cron'
                        ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
                        : useCase.type === 'ping' || useCase.type === 'tcp'
                        ? 'bg-cyan-100 dark:bg-cyan-900/50 text-cyan-700 dark:text-cyan-300'
                        : 'bg-orange-100 dark:bg-orange-900/50 text-orange-700 dark:text-orange-300'
                    }`}
                  >
                    {useCase.type}
                  </span>
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
                <div className="px-4 pb-4 text-gray-600 dark:text-gray-300">{item.answer}</div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-primary-600 py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Начните мониторить уже сегодня
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-primary-100">
            Бесплатный тариф включает heartbeat-мониторы, SSL-проверки и cron-задачи.
            Регистрация занимает меньше минуты.
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
