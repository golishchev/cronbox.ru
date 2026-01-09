import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X, Clock } from 'lucide-react'
import clsx from 'clsx'

const navigation = [
  { name: 'Возможности', href: '/#features' },
  { name: 'Тарифы', href: '/pricing' },
  { name: 'Документация', href: '/docs' },
]

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200">
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" aria-label="Top">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600">
                <Clock className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">CronBox</span>
            </Link>
          </div>

          {/* Desktop navigation */}
          <div className="hidden md:flex md:items-center md:gap-x-8">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'text-sm font-medium transition-colors',
                  location.pathname === item.href
                    ? 'text-primary-600'
                    : 'text-gray-700 hover:text-primary-600'
                )}
              >
                {item.name}
              </Link>
            ))}
          </div>

          <div className="hidden md:flex md:items-center md:gap-x-4">
            <a
              href="https://cp.cronbox.ru/#/login"
              className="text-sm font-medium text-gray-700 hover:text-primary-600 transition-colors"
            >
              Войти
            </a>
            <a
              href="https://cp.cronbox.ru/#/register"
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              Регистрация
            </a>
          </div>

          {/* Mobile menu button */}
          <div className="flex md:hidden">
            <button
              type="button"
              className="text-gray-700"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              <span className="sr-only">Открыть меню</span>
              {mobileMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-200">
            <div className="flex flex-col gap-4">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className="text-sm font-medium text-gray-700 hover:text-primary-600"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {item.name}
                </Link>
              ))}
              <div className="flex flex-col gap-2 pt-4 border-t border-gray-200">
                <a
                  href="https://cp.cronbox.ru/#/login"
                  className="text-sm font-medium text-gray-700 hover:text-primary-600"
                >
                  Войти
                </a>
                <a
                  href="https://cp.cronbox.ru/#/register"
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white text-center hover:bg-primary-700"
                >
                  Регистрация
                </a>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  )
}
