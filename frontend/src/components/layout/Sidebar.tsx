import {
  Clock,
  Calendar,
  History,
  Settings,
  Key,
  Bell,
  ChevronLeft,
  LayoutDashboard,
  CreditCard,
  Shield,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'

interface NavItem {
  titleKey: string
  route: string
  icon: React.ComponentType<{ className?: string }>
}

const mainNav: NavItem[] = [
  { titleKey: 'nav.dashboard', route: 'dashboard', icon: LayoutDashboard },
  { titleKey: 'nav.cronTasks', route: 'cron', icon: Clock },
  { titleKey: 'nav.delayedTasks', route: 'delayed', icon: Calendar },
  { titleKey: 'nav.executions', route: 'executions', icon: History },
]

const settingsNav: NavItem[] = [
  { titleKey: 'nav.billing', route: 'billing', icon: CreditCard },
  { titleKey: 'nav.notifications', route: 'notifications', icon: Bell },
  { titleKey: 'nav.apiKeys', route: 'api-keys', icon: Key },
  { titleKey: 'nav.settings', route: 'settings', icon: Settings },
]

const adminNav: NavItem[] = [
  { titleKey: 'nav.adminDashboard', route: 'admin', icon: Shield },
]

interface SidebarProps {
  currentRoute: string
  onNavigate: (route: string) => void
}

export function Sidebar({ currentRoute, onNavigate }: SidebarProps) {
  const { t } = useTranslation()
  const { sidebarCollapsed, setSidebarCollapsed } = useUIStore()
  const { user } = useAuthStore()

  const NavLink = ({ item }: { item: NavItem }) => {
    const isActive = currentRoute === item.route
    const Icon = item.icon

    return (
      <button
        onClick={() => onNavigate(item.route)}
        className={cn(
          'flex w-full items-center gap-3 px-3 py-2 rounded-lg transition-colors text-left',
          isActive
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
        )}
      >
        <Icon className="h-5 w-5 shrink-0" />
        {!sidebarCollapsed && <span className="text-sm font-medium">{t(item.titleKey)}</span>}
      </button>
    )
  }

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen bg-background border-r transition-all duration-300 hidden lg:block',
        sidebarCollapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b">
        {!sidebarCollapsed && (
          <button onClick={() => onNavigate('dashboard')} className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <Clock className="h-5 w-5 text-white" />
            </div>
            <span className="font-bold text-xl">CronBox</span>
          </button>
        )}
        {sidebarCollapsed && (
          <button onClick={() => onNavigate('dashboard')} className="mx-auto">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <Clock className="h-5 w-5 text-white" />
            </div>
          </button>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className={cn(sidebarCollapsed && 'mx-auto')}
        >
          <ChevronLeft
            className={cn(
              'h-5 w-5 transition-transform',
              sidebarCollapsed && 'rotate-180'
            )}
          />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-6">
        <div className="space-y-1">
          {!sidebarCollapsed && (
            <p className="text-xs font-medium text-muted-foreground uppercase px-3 mb-2">
              {t('nav.main')}
            </p>
          )}
          {mainNav.map((item) => (
            <NavLink key={item.route} item={item} />
          ))}
        </div>

        <div className="space-y-1">
          {!sidebarCollapsed && (
            <p className="text-xs font-medium text-muted-foreground uppercase px-3 mb-2">
              {t('nav.settings')}
            </p>
          )}
          {settingsNav.map((item) => (
            <NavLink key={item.route} item={item} />
          ))}
        </div>

        {user?.is_superuser && (
          <div className="space-y-1">
            {!sidebarCollapsed && (
              <p className="text-xs font-medium text-muted-foreground uppercase px-3 mb-2">
                Admin
              </p>
            )}
            {adminNav.map((item) => (
              <NavLink key={item.route} item={item} />
            ))}
          </div>
        )}
      </nav>
    </aside>
  )
}
