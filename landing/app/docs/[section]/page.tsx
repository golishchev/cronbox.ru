import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ChevronRight } from 'lucide-react'
import { sections, getSectionById } from '@/lib/docs'
import { DocsSidebar } from '@/components/docs/DocsSidebar'
import { sectionComponents } from '@/components/docs/sections'

type Props = {
  params: Promise<{ section: string }>
}

export function generateStaticParams() {
  return sections.map((section) => ({
    section: section.id,
  }))
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { section } = await params
  const sectionData = getSectionById(section)
  if (!sectionData) return {}

  return {
    title: `${sectionData.name} - Документация`,
    description: `Документация CronBox API: ${sectionData.name}. Примеры использования и описание эндпоинтов.`,
    alternates: {
      canonical: `https://cronbox.ru/docs/${section}`,
    },
  }
}

export default async function DocsPage({ params }: Props) {
  const { section } = await params
  const sectionData = getSectionById(section)

  if (!sectionData) {
    notFound()
  }

  const SectionComponent = sectionComponents[section]
  if (!SectionComponent) {
    notFound()
  }

  const currentIndex = sections.findIndex((s) => s.id === section)
  const prevSection = currentIndex > 0 ? sections[currentIndex - 1] : null
  const nextSection = currentIndex < sections.length - 1 ? sections[currentIndex + 1] : null

  return (
    <div className="bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
        <div className="lg:flex lg:gap-12">
          <DocsSidebar activeSection={section} />

          <main className="flex-1 min-w-0">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm text-gray-500 mb-8">
              <Link href="/docs" className="hover:text-primary-600">
                Документация
              </Link>
              <ChevronRight className="h-4 w-4" />
              <span className="text-gray-900">{sectionData.name}</span>
            </nav>

            <SectionComponent />

            {/* Next/Prev navigation */}
            <div className="mt-16 pt-8 border-t border-gray-200">
              <div className="flex justify-between">
                {prevSection && (
                  <Link
                    href={`/docs/${prevSection.id}`}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    &larr; {prevSection.name}
                  </Link>
                )}
                <div className="flex-1" />
                {nextSection && (
                  <Link
                    href={`/docs/${nextSection.id}`}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    {nextSection.name} &rarr;
                  </Link>
                )}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
