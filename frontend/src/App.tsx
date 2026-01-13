import { useEffect, useState, Suspense, lazy } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getCurrentUser } from '@/api/auth'
import { getWorkspaces } from '@/api/workspaces'
import { AppLayout } from '@/components/layout/AppLayout'
import { Toaster } from '@/components/ui/toaster'
import { Loader2 } from 'lucide-react'

// Lazy load pages for code splitting
const LoginPage = lazy(() => import('@/pages/auth/LoginPage').then(m => ({ default: m.LoginPage })))
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage').then(m => ({ default: m.RegisterPage })))
const VerifyEmailPage = lazy(() => import('@/pages/auth/VerifyEmailPage').then(m => ({ default: m.VerifyEmailPage })))
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const CronTasksPage = lazy(() => import('@/pages/cron/CronTasksPage').then(m => ({ default: m.CronTasksPage })))
const DelayedTasksPage = lazy(() => import('@/pages/delayed/DelayedTasksPage').then(m => ({ default: m.DelayedTasksPage })))
const ExecutionsPage = lazy(() => import('@/pages/executions/ExecutionsPage').then(m => ({ default: m.ExecutionsPage })))
const NotificationsPage = lazy(() => import('@/pages/settings/NotificationsPage').then(m => ({ default: m.NotificationsPage })))
const ProfilePage = lazy(() => import('@/pages/settings/ProfilePage').then(m => ({ default: m.ProfilePage })))
const BillingPage = lazy(() => import('@/pages/billing/BillingPage').then(m => ({ default: m.BillingPage })))
const ApiKeysPage = lazy(() => import('@/pages/settings/ApiKeysPage').then(m => ({ default: m.ApiKeysPage })))

// Admin pages
const AdminDashboardPage = lazy(() => import('@/pages/admin/AdminDashboardPage').then(m => ({ default: m.AdminDashboardPage })))
const AdminUsersPage = lazy(() => import('@/pages/admin/AdminUsersPage').then(m => ({ default: m.AdminUsersPage })))
const AdminWorkspacesPage = lazy(() => import('@/pages/admin/AdminWorkspacesPage').then(m => ({ default: m.AdminWorkspacesPage })))
const AdminPlansPage = lazy(() => import('@/pages/admin/AdminPlansPage').then(m => ({ default: m.AdminPlansPage })))
const AdminNotificationTemplatesPage = lazy(() => import('@/pages/admin/AdminNotificationTemplatesPage').then(m => ({ default: m.AdminNotificationTemplatesPage })))

type Route = 'login' | 'register' | 'verify-email' | 'dashboard' | 'cron' | 'delayed' | 'executions' | 'api-keys' | 'notifications' | 'settings' | 'billing' | 'profile' | 'admin' | 'admin-users' | 'admin-workspaces' | 'admin-plans' | 'admin-templates'

const AUTH_ROUTES = ['login', 'register', 'verify-email']
const PROTECTED_ROUTES = ['dashboard', 'cron', 'delayed', 'executions', 'api-keys', 'notifications', 'settings', 'billing', 'profile', 'admin', 'admin-users', 'admin-workspaces', 'admin-plans', 'admin-templates']

function PageLoader() {
  return (
    <div className="flex h-[50vh] items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  )
}

function App() {
  const { isAuthenticated, isLoading, setUser, setLoading, logout } = useAuthStore()
  const { setWorkspaces, setCurrentWorkspace, currentWorkspace } = useWorkspaceStore()
  const [route, setRoute] = useState<Route>('login')
  const [verifyEmailToken, setVerifyEmailToken] = useState<string>('')

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token')
      if (token) {
        try {
          const user = await getCurrentUser()
          setUser(user)

          // Load workspaces after successful auth
          const workspaces = await getWorkspaces()
          setWorkspaces(workspaces)
          if (workspaces.length > 0 && !currentWorkspace) {
            setCurrentWorkspace(workspaces[0])
          }

          const hash = window.location.hash.slice(1) || 'dashboard'
          if (PROTECTED_ROUTES.includes(hash)) {
            setRoute(hash as Route)
          } else {
            setRoute('dashboard')
          }
        } catch {
          logout()
          setRoute('login')
        }
      }
      setLoading(false)
    }

    checkAuth()
  }, [setUser, setLoading, logout, setWorkspaces, setCurrentWorkspace, currentWorkspace])

  // Handle hash-based routing
  useEffect(() => {
    const handleHashChange = () => {
      const fullHash = window.location.hash.slice(1) || 'login'
      // Parse route and query params (e.g., "verify-email?token=abc")
      const [hash, queryString] = fullHash.split('?')
      const routePath = hash.split('/').filter(Boolean)[0] || 'login'

      const allRoutes = [...AUTH_ROUTES, ...PROTECTED_ROUTES]
      if (allRoutes.includes(routePath)) {
        setRoute(routePath as Route)
        window.scrollTo(0, 0)

        // Extract token for verify-email route
        if (routePath === 'verify-email' && queryString) {
          const params = new URLSearchParams(queryString)
          const token = params.get('token')
          if (token) {
            setVerifyEmailToken(token)
          }
        }
      }
    }

    handleHashChange()
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  // Redirect based on auth state
  useEffect(() => {
    if (!isLoading) {
      // Don't redirect verify-email - it works both authenticated and not
      if (isAuthenticated && AUTH_ROUTES.includes(route) && route !== 'verify-email') {
        setRoute('dashboard')
        window.location.hash = 'dashboard'
      } else if (!isAuthenticated && PROTECTED_ROUTES.includes(route)) {
        setRoute('login')
        window.location.hash = 'login'
      }
    }
  }, [isAuthenticated, isLoading, route])

  if (isLoading) {
    return (
      <>
        <div className="flex h-screen items-center justify-center">
          <div className="text-lg">Loading...</div>
        </div>
        <Toaster />
      </>
    )
  }

  const navigate = (to: string) => {
    setRoute(to as Route)
    window.location.hash = to
    window.scrollTo(0, 0)
  }

  // Show verify-email page for both authenticated and non-authenticated users
  if (route === 'verify-email') {
    return (
      <>
        <Suspense fallback={<PageLoader />}>
          <VerifyEmailPage token={verifyEmailToken} onNavigate={navigate} />
        </Suspense>
        <Toaster />
      </>
    )
  }

  if (!isAuthenticated) {
    return (
      <>
        <Suspense fallback={<PageLoader />}>
          {route === 'register' ? (
            <RegisterPage onNavigate={navigate} />
          ) : (
            <LoginPage onNavigate={navigate} />
          )}
        </Suspense>
        <Toaster />
      </>
    )
  }

  const renderPage = () => {
    switch (route) {
      case 'cron':
        return <CronTasksPage onNavigate={navigate} />
      case 'delayed':
        return <DelayedTasksPage onNavigate={navigate} />
      case 'executions':
        return <ExecutionsPage onNavigate={navigate} />
      case 'api-keys':
        return <ApiKeysPage onNavigate={navigate} />
      case 'notifications':
        return <NotificationsPage onNavigate={navigate} />
      case 'settings':
        return <ProfilePage onNavigate={navigate} />
      case 'profile':
        return <ProfilePage onNavigate={navigate} />
      case 'billing':
        return <BillingPage onNavigate={navigate} />
      case 'admin':
        return <AdminDashboardPage onNavigate={navigate} />
      case 'admin-users':
        return <AdminUsersPage onNavigate={navigate} />
      case 'admin-workspaces':
        return <AdminWorkspacesPage onNavigate={navigate} />
      case 'admin-plans':
        return <AdminPlansPage onNavigate={navigate} />
      case 'admin-templates':
        return <AdminNotificationTemplatesPage onNavigate={navigate} />
      default:
        return <DashboardPage />
    }
  }

  return (
    <>
      <AppLayout onNavigate={navigate} currentRoute={route}>
        <Suspense fallback={<PageLoader />}>
          {renderPage()}
        </Suspense>
      </AppLayout>
      <Toaster />
    </>
  )
}

export default App
