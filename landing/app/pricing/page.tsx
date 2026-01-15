import type { Metadata } from 'next'
import { PricingPlans } from '@/components/pricing/PricingPlans'
import { JsonLd } from '@/components/JsonLd'

export const metadata: Metadata = {
  title: 'Тарифы',
  description:
    'Выберите подходящий тариф CronBox. Бесплатный тариф для начала, гибкие платные планы для роста.',
  alternates: {
    canonical: 'https://cronbox.ru/pricing',
  },
  openGraph: {
    title: 'Тарифы CronBox',
    description: 'Простые и прозрачные тарифы для планирования HTTP-запросов',
    url: 'https://cronbox.ru/pricing',
  },
}

const faqs = [
  {
    question: 'Что такое выполнение?',
    answer:
      'Выполнение - это один HTTP-запрос, отправленный на ваш сервер. Каждый раз, когда срабатывает cron-задача или отложенный запрос, это считается одним выполнением.',
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

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: faqs.map((faq) => ({
    '@type': 'Question',
    name: faq.question,
    acceptedAnswer: {
      '@type': 'Answer',
      text: faq.answer,
    },
  })),
}

export default function PricingPage() {
  return (
    <>
      <JsonLd data={faqJsonLd} />

      <div className="bg-white dark:bg-gray-900">
        {/* Header */}
        <section className="bg-gradient-to-b from-primary-50 to-white dark:from-gray-800 dark:to-gray-900 py-16 sm:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-5xl">
              Простые и прозрачные тарифы
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-600 dark:text-gray-300">
              Выберите подходящий тариф для ваших задач. Начните бесплатно и
              масштабируйтесь по мере роста.
            </p>
          </div>
        </section>

        {/* Pricing Cards */}
        <section className="py-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <PricingPlans />
          </div>
        </section>

        {/* FAQ */}
        <section className="bg-gray-50 dark:bg-gray-800 py-16 sm:py-24">
          <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
            <h2 className="text-center text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
              Часто задаваемые вопросы
            </h2>

            <dl className="mt-12 space-y-8">
              {faqs.map((faq) => (
                <div key={faq.question}>
                  <dt className="text-lg font-semibold text-gray-900 dark:text-white">
                    {faq.question}
                  </dt>
                  <dd className="mt-2 text-gray-600 dark:text-gray-300">{faq.answer}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Остались вопросы по тарифам?
            </h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
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
    </>
  )
}
