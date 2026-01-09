import { CheckCircle2 } from 'lucide-react'
import clsx from 'clsx'

const plans = [
  {
    name: 'Free',
    price: '0',
    description: 'Для тестирования и личных проектов',
    features: [
      'До 5 cron-задач',
      'До 10 отложенных задач в день',
      'Минимальный интервал: 15 минут',
      '100 выполнений в день',
      'Email-уведомления',
      'История за 7 дней',
    ],
    cta: 'Начать бесплатно',
    href: 'https://cp.cronbox.ru/#/register',
    featured: false,
  },
  {
    name: 'Starter',
    price: '490',
    description: 'Для небольших проектов и стартапов',
    features: [
      'До 25 cron-задач',
      'До 100 отложенных задач в день',
      'Минимальный интервал: 1 минута',
      '1 000 выполнений в день',
      'Email + Telegram уведомления',
      'История за 30 дней',
      'API-доступ',
      'Приоритетная поддержка',
    ],
    cta: 'Выбрать Starter',
    href: 'https://cp.cronbox.ru/#/register?plan=starter',
    featured: false,
  },
  {
    name: 'Professional',
    price: '1 490',
    description: 'Для растущих компаний',
    features: [
      'До 100 cron-задач',
      'До 500 отложенных задач в день',
      'Минимальный интервал: 30 секунд',
      '10 000 выполнений в день',
      'Все каналы уведомлений',
      'История за 90 дней',
      'Webhooks',
      'Приоритетная очередь',
      'SLA 99.9%',
    ],
    cta: 'Выбрать Professional',
    href: 'https://cp.cronbox.ru/#/register?plan=professional',
    featured: true,
  },
  {
    name: 'Enterprise',
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
    href: 'mailto:sales@cronbox.ru',
    featured: false,
  },
]

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
    question: 'Есть ли пробный период для платных тарифов?',
    answer:
      'Да, все платные тарифы включают 7-дневный пробный период. Оплата списывается только после окончания пробного периода.',
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

export function PricingPage() {
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
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={clsx(
                  'relative rounded-2xl border p-8',
                  plan.featured
                    ? 'border-primary-600 bg-primary-50 shadow-lg ring-2 ring-primary-600'
                    : 'border-gray-200 bg-white shadow-sm'
                )}
              >
                {plan.featured && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center rounded-full bg-primary-600 px-4 py-1 text-sm font-medium text-white">
                      Популярный
                    </span>
                  </div>
                )}

                <div className="text-center">
                  <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                  <div className="mt-4 flex items-baseline justify-center gap-x-1">
                    {plan.price === 'по запросу' ? (
                      <span className="text-2xl font-bold text-gray-900">{plan.price}</span>
                    ) : (
                      <>
                        <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                        <span className="text-gray-600">/мес</span>
                      </>
                    )}
                  </div>
                  <p className="mt-2 text-sm text-gray-600">{plan.description}</p>
                </div>

                <ul className="mt-8 space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-primary-600 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>

                <a
                  href={plan.href}
                  className={clsx(
                    'mt-8 block w-full rounded-lg px-4 py-3 text-center text-sm font-semibold transition-colors',
                    plan.featured
                      ? 'bg-primary-600 text-white hover:bg-primary-700'
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  )}
                >
                  {plan.cta}
                </a>
              </div>
            ))}
          </div>
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
            href="mailto:sales@cronbox.ru"
            className="mt-6 inline-flex items-center rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white hover:bg-primary-700 transition-colors"
          >
            Написать нам
          </a>
        </div>
      </section>
    </div>
  )
}
