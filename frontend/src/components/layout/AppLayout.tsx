import { ReactNode, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Mail } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { sendEmailVerification } from '@/api/auth'

interface AppLayoutProps {
  children: ReactNode
  onNavigate: (route: string) => void
  currentRoute?: string
}

export function AppLayout({ children, onNavigate, currentRoute = 'dashboard' }: AppLayoutProps) {
  const { t } = useTranslation()
  const { user, logout } = useAuthStore()
  const { sidebarCollapsed } = useUIStore()
  const [resending, setResending] = useState(false)
  const [resent, setResent] = useState(false)

  const handleLogout = () => {
    logout()
    onNavigate('login')
  }

  const handleResendVerification = async () => {
    setResending(true)
    try {
      await sendEmailVerification()
      setResent(true)
      setTimeout(() => setResent(false), 5000)
    } catch {
      // Silently fail
    } finally {
      setResending(false)
    }
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

        {user && !user.email_verified && (
          <div className="px-6 pt-4">
            <Alert className="border-amber-500/50 bg-amber-50 dark:bg-amber-950/20">
              <Mail className="h-4 w-4 text-amber-600" />
              <AlertTitle className="text-amber-800 dark:text-amber-200">
                {t('auth.emailVerificationBanner.title')}
              </AlertTitle>
              <AlertDescription className="text-amber-700 dark:text-amber-300 flex items-center justify-between gap-4">
                <span>{t('auth.emailVerificationBanner.message')}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleResendVerification}
                  disabled={resending || resent}
                  className="shrink-0 border-amber-500 text-amber-700 hover:bg-amber-100"
                >
                  {resending
                    ? t('auth.emailVerificationBanner.sending')
                    : resent
                      ? t('auth.emailVerificationBanner.sent')
                      : t('auth.emailVerificationBanner.resend')}
                </Button>
              </AlertDescription>
            </Alert>
          </div>
        )}

        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
