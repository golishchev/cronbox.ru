import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <p className="text-sm font-semibold text-primary-600">404</p>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-gray-900 sm:text-5xl">
          Страница не найдена
        </h1>
        <p className="mt-6 text-base leading-7 text-gray-600">
          К сожалению, запрошенная страница не существует.
        </p>
        <div className="mt-10 flex items-center justify-center gap-x-6">
          <Link
            href="/"
            className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 transition-colors"
          >
            На главную
          </Link>
          <Link
            href="/docs"
            className="text-sm font-semibold text-gray-900 hover:text-primary-600 transition-colors"
          >
            Документация <span aria-hidden="true">&rarr;</span>
          </Link>
        </div>
      </div>
    </div>
  )
}
