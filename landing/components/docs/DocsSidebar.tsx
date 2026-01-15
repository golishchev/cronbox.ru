'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import clsx from 'clsx'
import { sections } from '@/lib/docs'

type DocsSidebarProps = {
  activeSection: string
}

export function DocsSidebar({ activeSection }: DocsSidebarProps) {
  const router = useRouter()

  return (
    <>
      {/* Mobile section selector */}
      <div className="lg:hidden mb-6">
        <label className="text-sm font-medium text-gray-700">Раздел</label>
        <select
          value={activeSection}
          onChange={(e) => router.push(`/docs/${e.target.value}`)}
          className="mt-1 block w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-3 pr-10 text-base focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          {sections.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </div>

      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-64 flex-shrink-0">
        <div className="sticky top-24">
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
            Документация API
          </h2>
          <nav className="mt-4 space-y-1">
            {sections.map((item) => (
              <Link
                key={item.id}
                href={`/docs/${item.id}`}
                className={clsx(
                  'flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors',
                  activeSection === item.id
                    ? 'bg-primary-50 text-primary-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </aside>
    </>
  )
}
