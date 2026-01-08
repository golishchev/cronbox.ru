import { ReactNode } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { cn } from '@/lib/utils'

interface AppLayoutProps {
  children: ReactNode
  onNavigate: (route: string) => void
  currentRoute?: string
}

export function AppLayout({ children, onNavigate, currentRoute = 'dashboard' }: AppLayoutProps) {
  const { logout } = useAuthStore()
  const { sidebarCollapsed } = useUIStore()

  const handleLogout = () => {
    logout()
    onNavigate('login')
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <Sidebar currentRoute={currentRoute} onNavigate={onNavigate} />

      <div
        className={cn(
          'transition-all duration-300',
          sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-64'
        )}
      >
        <Header onNavigate={onNavigate} onLogout={handleLogout} />

        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
