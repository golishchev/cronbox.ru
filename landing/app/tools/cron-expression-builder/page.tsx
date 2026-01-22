import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { CronBuilder } from '@/components/tools/CronBuilder'
import { JsonLd } from '@/components/JsonLd'

export const metadata: Metadata = {
  title: 'Бесплатный онлайн конструктор Cron-выражений | CronBox',
  description:
    'Создавайте cron-выражения с помощью визуального конструктора. Готовые шаблоны, предпросмотр следующих запусков, шпаргалка по синтаксису. Бесплатно и без регистрации.',
  keywords: [
    'cron expression builder',
    'cron generator',
    'конструктор cron',
    'генератор cron',
    'cron онлайн',
    'cron выражение',
    'crontab generator',
    'cron schedule builder',
    'планировщик cron',
  ],
  openGraph: {
    title: 'Бесплатный онлайн конструктор Cron-выражений',
    description:
      'Создавайте cron-выражения с помощью визуального конструктора. Готовые шаблоны и предпросмотр следующих запусков.',
    type: 'website',
    url: 'https://cronbox.ru/tools/cron-expression-builder',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Бесплатный онлайн конструктор Cron-выражений',
    description:
      'Создавайте cron-выражения с помощью визуального конструктора. Готовые шаблоны и предпросмотр следующих запусков.',
  },
  alternates: {
    canonical: 'https://cronbox.ru/tools/cron-expression-builder',
  },
}

const CRON_EXAMPLES = [
  { expression: '* * * * *', description: 'Каждую минуту' },
  { expression: '*/5 * * * *', description: 'Каждые 5 минут' },
  { expression: '0 * * * *', description: 'В начале каждого часа' },
  { expression: '0 0 * * *', description: 'Ежедневно в полночь' },
  { expression: '0 9 * * 1-5', description: 'В 9:00 по будням' },
  { expression: '0 0 1 * *', description: '1-го числа каждого месяца' },
  { expression: '30 4 1,15 * *', description: '1-го и 15-го числа в 4:30' },
  { expression: '0 22 * * 1-5', description: 'В 22:00 по будням' },
]

const FAQ_ITEMS = [
  {
    question: 'Что такое cron-выражение?',
    answer:
      'Cron-выражение - это строка из 5 полей, которая описывает расписание выполнения задачи. Формат: минута (0-59), час (0-23), день месяца (1-31), месяц (1-12), день недели (0-6, где 0 - воскресенье).',
  },
  {
    question: 'Что означает символ * в cron?',
    answer:
      'Звёздочка (*) означает "любое значение". Например, * в поле "час" означает "каждый час", а в поле "день недели" - "каждый день".',
  },
  {
    question: 'Как настроить задачу каждые 5 минут?',
    answer:
      'Используйте выражение */5 * * * *. Символ / означает "шаг", поэтому */5 в поле минут означает "каждые 5 минут".',
  },
  {
    question: 'Как запустить задачу только в будние дни?',
    answer:
      'Используйте диапазон 1-5 в поле дня недели. Например, 0 9 * * 1-5 запустит задачу в 9:00 с понедельника по пятницу.',
  },
  {
    question: 'Можно ли запускать задачу несколько раз в час?',
    answer:
      'Да, используйте список значений через запятую. Например, 0,15,30,45 * * * * запустит задачу в 0, 15, 30 и 45 минут каждого часа.',
  },
  {
    question: 'Как запустить cron-задачу без сервера?',
    answer:
      'Используйте облачный сервис CronBox. Он выполняет HTTP-запросы по расписанию без необходимости настраивать и поддерживать собственный сервер.',
  },
]

export default function CronExpressionBuilderPage() {
  const toolJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: 'Конструктор Cron-выражений',
    description: 'Бесплатный онлайн инструмент для создания cron-выражений',
    url: 'https://cronbox.ru/tools/cron-expression-builder',
    applicationCategory: 'DeveloperApplication',
    operatingSystem: 'Any',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'RUB',
    },
    provider: {
      '@type': 'Organization',
      name: 'CronBox',
      url: 'https://cronbox.ru',
    },
  }

  const faqJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQ_ITEMS.map((item) => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.answer,
      },
    })),
  }

  return (
    <>
      <JsonLd data={toolJsonLd} />
      <JsonLd data={faqJsonLd} />

      <div className="min-h-screen bg-white dark:bg-gray-900">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 mb-8"
          >
            <ArrowLeft className="h-4 w-4" />
            На главную
          </Link>

          <header className="text-center mb-12">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 dark:text-white mb-4">
              Конструктор Cron-выражений
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
              Создавайте cron-выражения с помощью визуального конструктора.
              Бесплатно и без регистрации.
            </p>
          </header>

          <CronBuilder />

          {/* Syntax Reference */}
          <section className="mt-16">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
              Формат cron-выражений
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="py-3 px-4 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Поле
                    </th>
                    <th className="py-3 px-4 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Допустимые значения
                    </th>
                    <th className="py-3 px-4 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Специальные символы
                    </th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  <tr className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">
                      Минута
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">0-59</td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      <code>* , - /</code>
                    </td>
                  </tr>
                  <tr className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">Час</td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">0-23</td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      <code>* , - /</code>
                    </td>
                  </tr>
                  <tr className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">
                      День месяца
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">1-31</td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      <code>* , - /</code>
                    </td>
                  </tr>
                  <tr className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">Месяц</td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">1-12</td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      <code>* , - /</code>
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">
                      День недели
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      0-6 (0 = воскресенье)
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      <code>* , - /</code>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Examples */}
          <section className="mt-16">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
              Примеры cron-выражений
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {CRON_EXAMPLES.map((example, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-4 rounded-xl bg-gray-50 dark:bg-gray-800"
                >
                  <span className="text-gray-700 dark:text-gray-300">{example.description}</span>
                  <code className="text-sm px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 font-mono">
                    {example.expression}
                  </code>
                </div>
              ))}
            </div>
          </section>

          {/* FAQ */}
          <section className="mt-16">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
              Часто задаваемые вопросы
            </h2>
            <div className="space-y-4">
              {FAQ_ITEMS.map((item, i) => (
                <details
                  key={i}
                  className="group p-4 rounded-xl bg-gray-50 dark:bg-gray-800"
                >
                  <summary className="font-medium text-gray-900 dark:text-white cursor-pointer list-none flex items-center justify-between">
                    {item.question}
                    <svg
                      className="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </summary>
                  <p className="mt-3 text-gray-600 dark:text-gray-400">{item.answer}</p>
                </details>
              ))}
            </div>
          </section>

          {/* Final CTA */}
          <section className="mt-16 p-8 rounded-2xl bg-gradient-to-r from-blue-600 to-blue-700 text-center">
            <h2 className="text-2xl font-bold text-white mb-3">
              Автоматизируйте HTTP-запросы по расписанию
            </h2>
            <p className="text-blue-100 mb-6 max-w-xl mx-auto">
              CronBox выполняет ваши HTTP-запросы по расписанию. Мониторинг, уведомления и история
              выполнений - всё включено. Бесплатный тариф для старта.
            </p>
            <a
              href="https://cp.cronbox.ru/#/register"
              className="inline-flex items-center px-6 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition-colors"
            >
              Попробовать бесплатно
            </a>
          </section>
        </div>
      </div>
    </>
  )
}
