import { Link } from 'react-router-dom'
import { Clock, Mail, MessageCircle } from 'lucide-react'

const navigation = {
  product: [
    { name: 'Возможности', href: '/#features' },
    { name: 'Тарифы', href: '/pricing' },
    { name: 'Документация', href: '/docs' },
  ],
  legal: [
    { name: 'Политика конфиденциальности', href: '/privacy' },
    { name: 'Условия использования', href: '/terms' },
    { name: 'Публичная оферта', href: '/offer' },
  ],
  support: [
    { name: 'support@cronbox.ru', href: 'mailto:support@cronbox.ru', icon: Mail },
    { name: 'Telegram', href: 'https://t.me/cronbox', icon: MessageCircle },
  ],
}

export function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="md:col-span-1">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600">
                <Clock className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white">CronBox</span>
            </Link>
            <p className="mt-4 text-sm text-gray-400">
              Надежный сервис планирования HTTP-запросов для вашего бизнеса
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="text-sm font-semibold text-white">Продукт</h3>
            <ul className="mt-4 space-y-3">
              {navigation.product.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className="text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-sm font-semibold text-white">Правовая информация</h3>
            <ul className="mt-4 space-y-3">
              {navigation.legal.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className="text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Support */}
          <div>
            <h3 className="text-sm font-semibold text-white">Поддержка</h3>
            <ul className="mt-4 space-y-3">
              {navigation.support.map((item) => (
                <li key={item.name}>
                  <a
                    href={item.href}
                    className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
                    target={item.href.startsWith('http') ? '_blank' : undefined}
                    rel={item.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-800">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-gray-400">
              &copy; {new Date().getFullYear()} CronBox. Все права защищены.
            </p>
            <p className="text-sm text-gray-400">
              ИП Голищев Дмитрий Викторович, ИНН 263107925047
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
