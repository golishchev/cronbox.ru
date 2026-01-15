import { Link } from 'react-router-dom'
import {
  Clock,
  Zap,
  Shield,
  Bell,
  BarChart3,
  Code2,
  Globe,
  RefreshCw,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react'

const features = [
  {
    name: 'Cron-задачи',
    description: 'Планируйте регулярные HTTP-запросы по расписанию cron. Поддержка всех стандартных выражений cron.',
    icon: Clock,
  },
  {
    name: 'Отложенные запросы',
    description: 'Выполняйте одноразовые HTTP-запросы в указанное время. Идеально для отложенных уведомлений и действий.',
    icon: Zap,
  },
  {
    name: 'Мониторинг',
    description: 'Отслеживайте статус и время выполнения каждого запроса. Полная история с деталями ответов.',
    icon: BarChart3,
  },
  {
    name: 'Уведомления',
    description: 'Получайте уведомления об ошибках через Email, Telegram или Webhook. Настраиваемые условия.',
    icon: Bell,
  },
  {
    name: 'API-доступ',
    description: 'Полноценный REST API для интеграции. Управляйте задачами программно из вашего приложения.',
    icon: Code2,
  },
  {
    name: 'Надежность',
    description: 'Архитектура с автоматическими повторными попытками. SLA 99% uptime.',
    icon: Shield,
  },
]

const useCases = [
  {
    title: 'Интеграция сервисов',
    description: 'Синхронизируйте данные между системами по расписанию',
    icon: RefreshCw,
  },
  {
    title: 'Мониторинг API',
    description: 'Проверяйте доступность ваших сервисов регулярно',
    icon: Globe,
  },
  {
    title: 'Автоматизация',
    description: 'Запускайте бизнес-процессы по расписанию',
    icon: Zap,
  },
]

const benefits = [
  'Без установки на сервер',
  'Надежное выполнение',
  'Детальная статистика',
  'Мгновенные уведомления',
  'REST API',
]

export function HomePage() {
  return (
    <div>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary-50 to-white py-20 sm:py-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              Планирование HTTP-запросов{' '}
              <span className="text-primary-600">по расписанию</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              CronBox — облачный сервис для планирования и автоматического выполнения
              HTTP-запросов. Создавайте cron-задачи, отложенные запросы,
              отслеживайте результаты и получайте уведомления.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <a
                href="https://cp.cronbox.ru/#/register"
                className="rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors"
              >
                Начать бесплатно
              </a>
              <Link
                to="/docs"
                className="flex items-center gap-2 text-base font-semibold text-gray-900 hover:text-primary-600 transition-colors"
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
    "headers": {"X-API-Key": "secret"}
  }'`}</code>
              </pre>
            </div>
          </div>
          <h2 className="mx-auto mt-16 max-w-4xl text-lg leading-8 text-gray-600 text-center">
            Облачное решение, которое работает 24/7 без вашего участия
          </h2>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 sm:py-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Все необходимое для автоматизации
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Мощные инструменты для планирования и мониторинга HTTP-запросов
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.name}
                className="relative rounded-2xl border border-gray-200 bg-white p-8 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                  <feature.icon className="h-6 w-6 text-primary-600" />
                </div>
                <h3 className="mt-6 text-lg font-semibold text-gray-900">
                  {feature.name}
                </h3>
                <p className="mt-2 text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="bg-gray-50 py-20 sm:py-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Сценарии использования
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              CronBox подходит для любых задач автоматизации
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-4xl grid-cols-1 gap-8 sm:grid-cols-3">
            {useCases.map((useCase) => (
              <div
                key={useCase.title}
                className="text-center"
              >
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary-600">
                  <useCase.icon className="h-8 w-8 text-white" />
                </div>
                <h3 className="mt-6 text-lg font-semibold text-gray-900">
                  {useCase.title}
                </h3>
                <p className="mt-2 text-gray-600">{useCase.description}</p>
              </div>
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
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <a
              href="https://cp.cronbox.ru/#/register"
              className="rounded-lg bg-white px-6 py-3 text-base font-semibold text-primary-600 shadow-sm hover:bg-primary-50 transition-colors"
            >
              Создать аккаунт
            </a>
            <Link
              to="/docs"
              className="rounded-lg border-2 border-white px-6 py-3 text-base font-semibold text-white hover:bg-primary-700 transition-colors"
            >
              Читать документацию
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
