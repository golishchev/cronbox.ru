import type { Metadata, Viewport } from 'next'
import Script from 'next/script'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { JsonLd } from '@/components/JsonLd'
import { ThemeProvider } from '@/components/ThemeProvider'
import './globals.css'

const YANDEX_METRIKA_ID = 106267474
const VK_PIXEL_ID = '3734002'

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
    default: 'CronBox - Платформа мониторинга и автоматизации',
    template: '%s | CronBox',
  },
  description:
    'CronBox - платформа мониторинга и автоматизации для разработчиков. Heartbeat-мониторинг cron-задач, SSL-алерты, HTTP-автоматизация, цепочки запросов.',
  keywords: [
    'мониторинг',
    'heartbeat',
    'dead man switch',
    'ssl мониторинг',
    'cron',
    'scheduler',
    'http автоматизация',
    'api',
    'webhook',
    'уведомления',
    'алерты',
    'бэкап мониторинг',
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
    title: 'CronBox - Платформа мониторинга и автоматизации',
    description:
      'Heartbeat-мониторинг cron-задач, SSL-алерты, HTTP-автоматизация. Узнайте первым, когда что-то пойдёт не так.',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'CronBox - Платформа мониторинга и автоматизации',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CronBox - Платформа мониторинга и автоматизации',
    description:
      'Heartbeat-мониторинг cron-задач, SSL-алерты, HTTP-автоматизация. Узнайте первым, когда что-то пойдёт не так.',
    images: ['/opengraph-image'],
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
    <html lang="ru" className={`${inter.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <head>
        <JsonLd data={organizationJsonLd} />
      </head>
      <body className="min-h-screen flex flex-col">
        <ThemeProvider>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </ThemeProvider>

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
              clickmap: true,
              trackLinks: true,
              accurateTrackBounce: true,
              webvisor: true
            });
          `}
        </Script>
        <noscript>
          <div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`https://mc.yandex.ru/watch/${YANDEX_METRIKA_ID}`}
              style={{ position: 'absolute', left: '-9999px' }}
              alt=""
            />
          </div>
        </noscript>

        {/* Top.Mail.Ru (VK Pixel) counter */}
        <Script id="vk-pixel" strategy="afterInteractive">
          {`
            var _tmr = window._tmr || (window._tmr = []);
            _tmr.push({id: "${VK_PIXEL_ID}", type: "pageView", start: (new Date()).getTime()});
            (function (d, w, id) {
              if (d.getElementById(id)) return;
              var ts = d.createElement("script"); ts.type = "text/javascript"; ts.async = true; ts.id = id;
              ts.src = "https://top-fwz1.mail.ru/js/code.js";
              var f = function () {var s = d.getElementsByTagName("script")[0]; s.parentNode.insertBefore(ts, s);};
              if (w.opera == "[object Opera]") { d.addEventListener("DOMContentLoaded", f, false); } else { f(); }
            })(document, window, "tmr-code");
          `}
        </Script>
        <noscript>
          <div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`https://top-fwz1.mail.ru/counter?id=${VK_PIXEL_ID};js=na`}
              style={{ position: 'absolute', left: '-9999px' }}
              alt="Top.Mail.Ru"
            />
          </div>
        </noscript>
      </body>
    </html>
  )
}
