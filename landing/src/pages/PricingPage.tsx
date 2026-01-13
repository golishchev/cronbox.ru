import { useState, useEffect } from 'react'
import { CheckCircle2, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { getPlans, type Plan } from '@/api/billing'

// Enterprise plan - not stored in DB, always shown
const enterprisePlan = {
  name: 'Enterprise',
  display_name: 'Enterprise',
  price: 'по запросу',
  description: 'Для крупных компаний',
  features: [
    'Неограниченные cron-задачи',
    'Неограниченные отложенные задачи',
    'Минимальный интервал: 10 секунд',
    'Неограниченные выполнения',
    'Все каналы уведомлений',
    'Бессрочная история',
    'Выделенные воркеры',
    'Персональный менеджер',
    'SLA 99.99%',
    'On-premise установка',
  ],
  cta: 'Связаться с нами',
  href: 'mailto:support@cronbox.ru',
  featured: false,
}

const faqs = [
  {
    question: 'Что такое выполнение?',
    answer:
      'Выполнение — это один HTTP-запрос, отправленный на ваш сервер. Каждый раз, когда срабатывает cron-задача или отложенный запрос, это считается одним выполнением.',
  },
  {
    question: 'Можно ли менять тариф?',
    answer:
      'Да, вы можете повысить или понизить тариф в любой момент. При повышении разница будет рассчитана пропорционально. При понижении изменения вступят в силу со следующего периода.',
  },
  {
    question: 'Какие способы оплаты поддерживаются?',
    answer:
      'Мы принимаем оплату банковскими картами (Visa, MasterCard, МИР), через СБП (Система быстрых платежей), а также для юридических лиц возможна оплата по счету.',
  },
  {
    question: 'Что происходит при превышении лимитов?',
    answer:
      'При превышении лимита выполнений задачи ставятся в очередь и выполняются в следующий период. Мы отправим уведомление о превышении лимита, чтобы вы могли вовремя перейти на более высокий тариф.',
  },
]

function formatPrice(priceInKopeks: number): string {
  const priceInRubles = priceInKopeks / 100
  return priceInRubles.toLocaleString('ru-RU')
}

function formatInterval(minutes: number): string {
  if (minutes < 1) {
    return `${Math.round(minutes * 60)} секунд`
  }
  if (minutes === 1) {
    return '1 минута'
  }
  return `${minutes} минут`
}

function generateFeatures(plan: Plan): string[] {
  const features: string[] = []

  features.push(`До ${plan.max_cron_tasks} cron-задач`)
  features.push(`До ${plan.max_delayed_tasks_per_month} отложенных задач в месяц`)
  features.push(`Минимальный интервал: ${formatInterval(plan.min_cron_interval_minutes)}`)
  features.push(`До ${plan.max_workspaces} ${plan.max_workspaces === 1 ? 'рабочее пространство' : 'рабочих пространств'}`)
  features.push(`История за ${plan.max_execution_history_days} дней`)

  if (plan.email_notifications && plan.telegram_notifications) {
    features.push('Email + Telegram уведомления')
  } else if (plan.email_notifications) {
    features.push('Email-уведомления')
  }

  if (plan.webhook_callbacks) {
    features.push('Webhooks')
  }

  if (plan.retry_on_failure) {
    features.push('Авто-повтор при ошибке')
  }

  return features
}

function getPlanCta(plan: Plan): string {
  if (plan.price_monthly === 0) {
    return 'Начать бесплатно'
  }
  return `Выбрать ${plan.display_name}`
}

function getPlanHref(plan: Plan): string {
  if (plan.price_monthly === 0) {
    return 'https://cp.cronbox.ru/#/register'
  }
  return `https://cp.cronbox.ru/#/register?plan=${plan.name.toLowerCase()}`
}

export function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchPlans() {
      try {
        const data = await getPlans()
        // Sort by sort_order and filter only public active plans
        const sortedPlans = data
          .filter((p) => p.is_active && p.is_public)
          .sort((a, b) => a.sort_order - b.sort_order)
        setPlans(sortedPlans)
      } catch (err) {
        console.error('Failed to fetch plans:', err)
        setError('Не удалось загрузить тарифы')
      } finally {
        setLoading(false)
      }
    }
    fetchPlans()
  }, [])

  // Determine which plan should be featured (middle plan or highest non-enterprise)
  const featuredPlanName = plans.length >= 2 ? plans[Math.floor(plans.length / 2)]?.name : null

  return (
    <div className="bg-white">
      {/* Header */}
      <section className="bg-gradient-to-b from-primary-50 to-white py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            Простые и прозрачные тарифы
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-600">
            Выберите подходящий тариф для ваших задач. Начните бесплатно и масштабируйтесь по мере роста.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : error ? (
            <div className="text-center py-20 text-red-600">{error}</div>
          ) : (
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
              {plans.map((plan) => {
                const isFree = plan.price_monthly === 0
                const isFeatured = plan.name === featuredPlanName
                const features = generateFeatures(plan)

                return (
                  <div
                    key={plan.id}
                    className={clsx(
                      'relative rounded-2xl border p-8',
                      isFeatured
                        ? 'border-primary-600 bg-primary-50 shadow-lg ring-2 ring-primary-600'
                        : 'border-gray-200 bg-white shadow-sm'
                    )}
                  >
                    {isFeatured && (
                      <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                        <span className="inline-flex items-center rounded-full bg-primary-600 px-4 py-1 text-sm font-medium text-white">
                          Популярный
                        </span>
                      </div>
                    )}

                    <div className="text-center">
                      <h3 className="text-lg font-semibold text-gray-900">{plan.display_name}</h3>
                      <div className="mt-4 flex items-baseline justify-center gap-x-1">
                        {isFree ? (
                          <span className="text-4xl font-bold text-gray-900">0</span>
                        ) : (
                          <>
                            <span className="text-4xl font-bold text-gray-900">
                              {formatPrice(plan.price_monthly)}
                            </span>
                            <span className="text-gray-600">₽/мес</span>
                          </>
                        )}
                      </div>
                      <p className="mt-2 text-sm text-gray-600">{plan.description}</p>
                    </div>

                    <ul className="mt-8 space-y-3">
                      {features.map((feature) => (
                        <li key={feature} className="flex items-start gap-3">
                          <CheckCircle2 className="h-5 w-5 text-primary-600 flex-shrink-0 mt-0.5" />
                          <span className="text-sm text-gray-700">{feature}</span>
                        </li>
                      ))}
                    </ul>

                    <a
                      href={getPlanHref(plan)}
                      className={clsx(
                        'mt-8 block w-full rounded-lg px-4 py-3 text-center text-sm font-semibold transition-colors',
                        isFeatured
                          ? 'bg-primary-600 text-white hover:bg-primary-700'
                          : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                      )}
                    >
                      {getPlanCta(plan)}
                    </a>
                  </div>
                )
              })}

              {/* Enterprise plan - always shown */}
              <div className="relative rounded-2xl border p-8 border-gray-200 bg-white shadow-sm">
                <div className="text-center">
                  <h3 className="text-lg font-semibold text-gray-900">{enterprisePlan.display_name}</h3>
                  <div className="mt-4 flex items-baseline justify-center gap-x-1">
                    <span className="text-2xl font-bold text-gray-900">{enterprisePlan.price}</span>
                  </div>
                  <p className="mt-2 text-sm text-gray-600">{enterprisePlan.description}</p>
                </div>

                <ul className="mt-8 space-y-3">
                  {enterprisePlan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-primary-600 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>

                <a
                  href={enterprisePlan.href}
                  className="mt-8 block w-full rounded-lg px-4 py-3 text-center text-sm font-semibold transition-colors bg-gray-100 text-gray-900 hover:bg-gray-200"
                >
                  {enterprisePlan.cta}
                </a>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-gray-50 py-16 sm:py-24">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-center text-3xl font-bold tracking-tight text-gray-900">
            Часто задаваемые вопросы
          </h2>

          <dl className="mt-12 space-y-8">
            {faqs.map((faq) => (
              <div key={faq.question}>
                <dt className="text-lg font-semibold text-gray-900">{faq.question}</dt>
                <dd className="mt-2 text-gray-600">{faq.answer}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-gray-900">
            Остались вопросы по тарифам?
          </h2>
          <p className="mt-4 text-gray-600">
            Свяжитесь с нами, и мы поможем выбрать подходящий тариф
          </p>
          <a
            href="mailto:support@cronbox.ru"
            className="mt-6 inline-flex items-center rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white hover:bg-primary-700 transition-colors"
          >
            Написать нам
          </a>
        </div>
      </section>
    </div>
  )
}
