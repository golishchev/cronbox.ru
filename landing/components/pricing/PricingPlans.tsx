'use client'

import { useState, useEffect } from 'react'
import { CheckCircle2, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { type Plan } from '@/lib/api'

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
    'Неограниченные SSL-мониторы',
    'Все каналы уведомлений',
    'Бессрочная история',
    'Выделенные воркеры',
    'Персональный менеджер',
    'SLA 99.99%',
    'On-premise установка',
  ],
  cta: 'Связаться с нами',
  href: 'mailto:support@cronbox.ru',
}

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

function pluralize(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}

function generateFeatures(plan: Plan): string[] {
  const features: string[] = []

  features.push(`До ${plan.max_cron_tasks} cron-задач`)
  features.push(`До ${plan.max_delayed_tasks_per_month} отложенных задач в месяц`)

  if (plan.max_task_chains > 0) {
    features.push(
      `До ${plan.max_task_chains} ${pluralize(plan.max_task_chains, 'цепочки задач', 'цепочек задач', 'цепочек задач')}`
    )
  }

  if (plan.max_heartbeats > 0) {
    features.push(
      `До ${plan.max_heartbeats} heartbeat-${pluralize(plan.max_heartbeats, 'монитора', 'мониторов', 'мониторов')}`
    )
  }

  if (plan.max_ssl_monitors > 0) {
    features.push(
      `До ${plan.max_ssl_monitors} SSL-${pluralize(plan.max_ssl_monitors, 'монитора', 'мониторов', 'мониторов')}`
    )
  }

  features.push(
    `${plan.max_workspaces} ${pluralize(plan.max_workspaces, 'рабочее пространство', 'рабочих пространства', 'рабочих пространств')}`
  )
  features.push(
    `История за ${plan.max_execution_history_days} ${pluralize(plan.max_execution_history_days, 'день', 'дня', 'дней')}`
  )
  features.push(`Минимальный интервал: ${formatInterval(plan.min_cron_interval_minutes)}`)

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

export function PricingPlans() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchPlans() {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'https://api.cronbox.ru/v1'}/billing/plans`
        )
        if (!response.ok) {
          throw new Error('Failed to fetch plans')
        }
        const data: Plan[] = await response.json()
        const sortedPlans = data.sort((a, b) => a.sort_order - b.sort_order)
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

  const featuredPlanName =
    plans.length >= 2 ? plans[Math.floor(plans.length / 2)]?.name : null

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400 dark:text-gray-500" />
      </div>
    )
  }

  if (error) {
    return <div className="text-center py-20 text-red-600 dark:text-red-400">{error}</div>
  }

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
      {plans.map((plan) => {
        const isFree = plan.price_monthly === 0
        const isFeatured = plan.name === featuredPlanName
        const features = generateFeatures(plan)

        return (
          <div
            key={plan.id}
            className={clsx(
              'relative rounded-2xl border p-8 flex flex-col',
              isFeatured
                ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/30 shadow-lg ring-2 ring-primary-600'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm'
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
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {plan.display_name}
              </h3>
              <div className="mt-4 flex items-baseline justify-center gap-x-1">
                {isFree ? (
                  <span className="text-4xl font-bold text-gray-900 dark:text-white">0</span>
                ) : (
                  <>
                    <span className="text-4xl font-bold text-gray-900 dark:text-white">
                      {formatPrice(plan.price_monthly)}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">/мес</span>
                  </>
                )}
              </div>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{plan.description}</p>
            </div>

            <ul className="mt-8 space-y-3 flex-1">
              {features.map((feature) => (
                <li key={feature} className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-gray-700 dark:text-gray-300">{feature}</span>
                </li>
              ))}
            </ul>

            <a
              href={getPlanHref(plan)}
              className={clsx(
                'mt-8 block w-full rounded-lg px-4 py-3 text-center text-sm font-semibold transition-colors',
                isFeatured
                  ? 'bg-primary-600 text-white hover:bg-primary-700'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-200 dark:hover:bg-gray-600'
              )}
            >
              {getPlanCta(plan)}
            </a>
          </div>
        )
      })}

      {/* Enterprise plan */}
      <div className="relative rounded-2xl border p-8 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm flex flex-col">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {enterprisePlan.display_name}
          </h3>
          <div className="mt-4 flex items-baseline justify-center gap-x-1">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {enterprisePlan.price}
            </span>
          </div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{enterprisePlan.description}</p>
        </div>

        <ul className="mt-8 space-y-3 flex-1">
          {enterprisePlan.features.map((feature) => (
            <li key={feature} className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-gray-700 dark:text-gray-300">{feature}</span>
            </li>
          ))}
        </ul>

        <a
          href={enterprisePlan.href}
          className="mt-8 block w-full rounded-lg px-4 py-3 text-center text-sm font-semibold transition-colors bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-200 dark:hover:bg-gray-600"
        >
          {enterprisePlan.cta}
        </a>
      </div>
    </div>
  )
}
