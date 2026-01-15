import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { Calendar, Clock, ArrowLeft } from 'lucide-react'
import { getAllSlugs, getPostBySlug } from '@/lib/blog'
import { JsonLd } from '@/components/JsonLd'

interface Props {
  params: Promise<{ slug: string }>
}

export async function generateStaticParams() {
  const slugs = getAllSlugs()
  return slugs.map((slug) => ({ slug }))
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const post = getPostBySlug(slug)

  if (!post) {
    return {
      title: 'Статья не найдена',
    }
  }

  return {
    title: post.title,
    description: post.description,
    keywords: post.keywords,
    openGraph: {
      title: post.title,
      description: post.description,
      type: 'article',
      publishedTime: post.date,
      authors: ['CronBox'],
      tags: post.keywords,
    },
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.description,
    },
    alternates: {
      canonical: `https://cronbox.ru/blog/${slug}`,
    },
  }
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(`[^`]+`)/)
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={i}
          className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm font-mono text-gray-800 dark:text-gray-200"
        >
          {part.slice(1, -1)}
        </code>
      )
    }
    const boldParts = part.split(/(\*\*[^*]+\*\*)/)
    return boldParts.map((bp, j) => {
      if (bp.startsWith('**') && bp.endsWith('**')) {
        return <strong key={`${i}-${j}`}>{bp.slice(2, -2)}</strong>
      }
      const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
      const linkParts: React.ReactNode[] = []
      let lastIndex = 0
      let match
      while ((match = linkRegex.exec(bp)) !== null) {
        if (match.index > lastIndex) {
          linkParts.push(bp.slice(lastIndex, match.index))
        }
        linkParts.push(
          <a
            key={`link-${match.index}`}
            href={match[2]}
            className="text-blue-600 dark:text-blue-400 hover:underline"
            target={match[2].startsWith('http') ? '_blank' : undefined}
            rel={match[2].startsWith('http') ? 'noopener noreferrer' : undefined}
          >
            {match[1]}
          </a>
        )
        lastIndex = match.index + match[0].length
      }
      if (lastIndex < bp.length) {
        linkParts.push(bp.slice(lastIndex))
      }
      return linkParts.length > 0 ? linkParts : bp
    })
  })
}

function renderContent(content: string) {
  const lines = content.trim().split('\n')
  const elements: React.ReactNode[] = []
  let currentList: string[] = []
  let currentTable: string[][] = []
  let inCodeBlock = false
  let codeBlockContent: string[] = []

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={elements.length} className="list-disc pl-6 my-4 space-y-2">
          {currentList.map((item, i) => (
            <li key={i} className="text-gray-700 dark:text-gray-300">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      )
      currentList = []
    }
  }

  const flushTable = () => {
    if (currentTable.length > 0) {
      const headers = currentTable[0]
      const rows = currentTable.slice(2)
      elements.push(
        <div key={elements.length} className="my-6 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                {headers.map((header, i) => (
                  <th
                    key={i}
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider"
                  >
                    {header.trim()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
              {rows.map((row, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-900' : 'bg-gray-50 dark:bg-gray-800'}>
                  {row.map((cell, j) => (
                    <td key={j} className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
                      {renderInline(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      currentTable = []
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre
            key={elements.length}
            className="my-4 p-4 bg-gray-900 text-gray-100 rounded-lg overflow-x-auto text-sm"
          >
            <code>{codeBlockContent.join('\n')}</code>
          </pre>
        )
        codeBlockContent = []
        inCodeBlock = false
      } else {
        flushList()
        flushTable()
        inCodeBlock = true
      }
      continue
    }

    if (inCodeBlock) {
      codeBlockContent.push(line)
      continue
    }

    if (line.includes('|') && line.trim().startsWith('|')) {
      flushList()
      const cells = line.split('|').filter((c) => c.trim() !== '')
      currentTable.push(cells)
      continue
    } else if (currentTable.length > 0) {
      flushTable()
    }

    if (line.startsWith('## ')) {
      flushList()
      elements.push(
        <h2
          key={elements.length}
          className="text-2xl font-bold text-gray-900 dark:text-white mt-10 mb-4"
        >
          {line.slice(3)}
        </h2>
      )
      continue
    }

    if (line.startsWith('### ')) {
      flushList()
      elements.push(
        <h3
          key={elements.length}
          className="text-xl font-semibold text-gray-900 dark:text-white mt-8 mb-3"
        >
          {line.slice(4)}
        </h3>
      )
      continue
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      currentList.push(line.slice(2))
      continue
    }

    if (/^\d+\.\s/.test(line)) {
      currentList.push(line.replace(/^\d+\.\s/, ''))
      continue
    }

    flushList()

    if (line.trim() === '') {
      continue
    }

    elements.push(
      <p key={elements.length} className="text-gray-700 dark:text-gray-300 my-4 leading-relaxed">
        {renderInline(line)}
      </p>
    )
  }

  flushList()
  flushTable()

  return elements
}

export default async function BlogPostPage({ params }: Props) {
  const { slug } = await params
  const post = getPostBySlug(slug)

  if (!post) {
    notFound()
  }

  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.description,
    datePublished: post.date,
    dateModified: post.date,
    author: {
      '@type': 'Organization',
      name: 'CronBox',
      url: 'https://cronbox.ru',
    },
    publisher: {
      '@type': 'Organization',
      name: 'CronBox',
      logo: {
        '@type': 'ImageObject',
        url: 'https://cronbox.ru/logo.png',
      },
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `https://cronbox.ru/blog/${slug}`,
    },
    keywords: post.keywords.join(', '),
  }

  return (
    <>
      <JsonLd data={articleJsonLd} />

      <article className="py-12 sm:py-16 bg-white dark:bg-gray-900">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 mb-8"
          >
            <ArrowLeft className="h-4 w-4" />
            Все статьи
          </Link>

          <header className="mb-10">
            <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-4">
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

            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white leading-tight">
              {post.title}
            </h1>

            <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">{post.description}</p>

            <div className="mt-6 flex flex-wrap gap-2">
              {post.keywords.map((keyword) => (
                <span
                  key={keyword}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-50 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </header>

          <div className="prose prose-lg dark:prose-invert max-w-none">
            {renderContent(post.content)}
          </div>

          <div className="mt-16 p-8 bg-gradient-to-r from-blue-600 to-blue-700 rounded-2xl text-white text-center">
            <h2 className="text-2xl font-bold mb-3">
              Готовы автоматизировать задачи?
            </h2>
            <p className="text-blue-100 mb-6">
              Попробуйте CronBox бесплатно - настройка за 2 минуты
            </p>
            <a
              href="https://cp.cronbox.ru/#/register"
              className="inline-flex items-center px-6 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition-colors"
            >
              Начать бесплатно
            </a>
          </div>
        </div>
      </article>
    </>
  )
}
