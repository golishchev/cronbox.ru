import type { Metadata, Viewport } from 'next'
import Script from 'next/script'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { JsonLd } from '@/components/JsonLd'
import './globals.css'

const YANDEX_METRIKA_ID = 106267474

const inter = Inter({
  subsets: ['cyrillic', 'latin'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['cyrillic', 'latin'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
})

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#2563eb',
}

export const metadata: Metadata = {
  metadataBase: new URL('https://cronbox.ru'),
  title: {
    default: 'CronBox - Планирование HTTP-запросов',
    template: '%s | CronBox',
  },
  description:
    'CronBox - облачный сервис для планирования HTTP-запросов. Cron-задачи, отложенные запросы, мониторинг выполнения и уведомления.',
  keywords: [
    'cron',
    'scheduler',
    'http',
    'api',
    'задачи',
    'планировщик',
    'webhook',
    'уведомления',
    'автоматизация',
    'http запросы по расписанию',
  ],
  authors: [{ name: 'CronBox' }],
  creator: 'CronBox',
  publisher: 'CronBox',
  formatDetection: {
    email: false,
    telephone: false,
  },
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '32x32' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    shortcut: '/favicon.ico',
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },
  manifest: '/manifest.webmanifest',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'CronBox',
  },
  openGraph: {
    type: 'website',
    locale: 'ru_RU',
    url: 'https://cronbox.ru',
    siteName: 'CronBox',
    title: 'CronBox - Планирование HTTP-запросов',
    description:
      'Облачный сервис для планирования и автоматического выполнения HTTP-запросов',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'CronBox - Планирование HTTP-запросов',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CronBox - Планирование HTTP-запросов',
    description:
      'Облачный сервис для планирования и автоматического выполнения HTTP-запросов',
    images: ['/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    canonical: 'https://cronbox.ru',
  },
  verification: {
    yandex: 'YANDEX_VERIFICATION_CODE', // Получить в Яндекс.Вебмастер
    google: 'GOOGLE_VERIFICATION_CODE', // Получить в Google Search Console
  },
}

const organizationJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'CronBox',
  url: 'https://cronbox.ru',
  logo: 'https://cronbox.ru/logo.png',
  sameAs: ['https://t.me/cronbox'],
  contactPoint: {
    '@type': 'ContactPoint',
    email: 'support@cronbox.ru',
    contactType: 'customer support',
    availableLanguage: 'Russian',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <JsonLd data={organizationJsonLd} />
      </head>
      <body className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />

        {/* Yandex.Metrika counter */}
        <Script id="yandex-metrika" strategy="afterInteractive">
          {`
            (function(m,e,t,r,i,k,a){
              m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
              m[i].l=1*new Date();
              for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
              k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
            })(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');

            ym(${YANDEX_METRIKA_ID}, 'init', {
              ssr: true,
              webvisor: true,
              clickmap: true,
              ecommerce: 'dataLayer',
              accurateTrackBounce: true,
              trackLinks: true
            });
          `}
        </Script>
        <noscript>
          <div>
            <img
              src={`https://mc.yandex.ru/watch/${YANDEX_METRIKA_ID}`}
              style={{ position: 'absolute', left: '-9999px' }}
              alt=""
            />
          </div>
        </noscript>
      </body>
    </html>
  )
}
