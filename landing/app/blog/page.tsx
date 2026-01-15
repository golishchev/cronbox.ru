import type { Metadata } from 'next'
import Link from 'next/link'
import { Calendar, Clock } from 'lucide-react'
import { getAllPosts } from '@/lib/blog'
import { JsonLd } from '@/components/JsonLd'

export const metadata: Metadata = {
  title: 'Блог',
  description:
    'Статьи о планировании задач, автоматизации HTTP-запросов, cron и serverless решениях. Туториалы и best practices.',
  openGraph: {
    title: 'Блог | CronBox',
    description:
      'Статьи о планировании задач, автоматизации и cron',
  },
  alternates: {
    canonical: 'https://cronbox.ru/blog',
  },
}

const blogJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Blog',
  name: 'CronBox Блог',
  description: 'Статьи о планировании задач и автоматизации',
  url: 'https://cronbox.ru/blog',
  publisher: {
    '@type': 'Organization',
    name: 'CronBox',
    logo: {
      '@type': 'ImageObject',
      url: 'https://cronbox.ru/logo.png',
    },
  },
}

export default function BlogPage() {
  const posts = getAllPosts()

  return (
    <>
      <JsonLd data={blogJsonLd} />

      <div className="bg-gradient-to-b from-gray-50 to-white py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
              Блог
            </h1>
            <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
              Статьи о планировании задач, автоматизации HTTP-запросов и
              современных подходах к cron
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-2">
            {posts.map((post) => (
              <article
                key={post.slug}
                className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                <Link href={`/blog/${post.slug}`} className="block p-6 sm:p-8">
                  <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      {new Date(post.date).toLocaleDateString('ru-RU', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                      })}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {post.readingTime}
                    </span>
                  </div>

                  <h2 className="text-xl font-semibold text-gray-900 mb-3 group-hover:text-blue-600">
                    {post.title}
                  </h2>

                  <p className="text-gray-600 line-clamp-3">{post.description}</p>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {post.keywords.slice(0, 3).map((keyword) => (
                      <span
                        key={keyword}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>

                  <div className="mt-6 text-blue-600 font-medium text-sm">
                    Читать статью →
                  </div>
                </Link>
              </article>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
