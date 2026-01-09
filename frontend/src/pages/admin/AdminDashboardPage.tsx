import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getAdminStats, AdminStats } from '@/api/admin'
import { getErrorMessage } from '@/api/client'
import { toast } from '@/hooks/use-toast'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DashboardSkeleton } from '@/components/ui/skeleton'
import {
  Users,
  Building2,
  Clock,
  Calendar,
  Activity,
  TrendingUp,
  CreditCard,
  DollarSign,
} from 'lucide-react'

interface AdminDashboardPageProps {
  onNavigate: (route: string) => void
}

export function AdminDashboardPage({ onNavigate }: AdminDashboardPageProps) {
  const { t } = useTranslation()
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await getAdminStats()
        setStats(data)
      } catch (err) {
        toast({
          title: t('admin.errorLoadingStats'),
          description: getErrorMessage(err),
          variant: 'destructive',
        })
      } finally {
        setIsLoading(false)
      }
    }

    loadStats()
  }, [])

  if (isLoading) {
    return <DashboardSkeleton />
  }

  if (!stats) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <p className="text-destructive">{t('admin.failedToLoadStats')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('admin.title')}</h1>
        <p className="text-muted-foreground">
          {t('admin.subtitle')}
        </p>
      </div>

      {/* Users Stats */}
      <div>
        <h2 className="text-lg font-semibold mb-4">{t('admin.users')}</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card
            className="cursor-pointer hover:border-primary transition-colors"
            onClick={() => onNavigate('admin-users')}
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.totalUsers')}</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_users}</div>
              <p className="text-xs text-muted-foreground">
                {stats.active_users} {t('admin.active').toLowerCase()}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.verifiedUsers')}</CardTitle>
              <Users className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.verified_users}</div>
              <p className="text-xs text-muted-foreground">
                {stats.total_users > 0 ? Math.round(stats.verified_users / stats.total_users * 100) : 0}% {t('admin.verified').toLowerCase()}
              </p>
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer hover:border-primary transition-colors"
            onClick={() => onNavigate('admin-workspaces')}
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.workspaces')}</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_workspaces}</div>
              <p className="text-xs text-muted-foreground">
                {t('admin.totalWorkspaces')}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.activeSubscriptions')}</CardTitle>
              <CreditCard className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.active_subscriptions}</div>
              <p className="text-xs text-muted-foreground">
                {t('admin.paidPlans')}
              </p>
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer hover:border-primary transition-colors"
            onClick={() => onNavigate('admin-plans')}
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.plans.title')}</CardTitle>
              <CreditCard className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">&rarr;</div>
              <p className="text-xs text-muted-foreground">
                {t('admin.plans.manage')}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Tasks Stats */}
      <div>
        <h2 className="text-lg font-semibold mb-4">{t('admin.tasks')}</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.cronTasks')}</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_cron_tasks}</div>
              <p className="text-xs text-muted-foreground">
                {stats.active_cron_tasks} {t('admin.active').toLowerCase()}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.delayedTasks')}</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_delayed_tasks}</div>
              <p className="text-xs text-muted-foreground">
                {stats.pending_delayed_tasks} {t('admin.pending')}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.executionsToday')}</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.executions_today}</div>
              <p className="text-xs text-muted-foreground">
                {stats.executions_this_week} {t('admin.thisWeek')}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.successRate7d')}</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.success_rate}%</div>
              <p className="text-xs text-muted-foreground">
                {stats.total_executions} {t('admin.totalExecutions')}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Revenue Stats */}
      <div>
        <h2 className="text-lg font-semibold mb-4">{t('admin.revenue')}</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('admin.revenueThisMonth')}</CardTitle>
              <DollarSign className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.revenue_this_month.toLocaleString('ru-RU')} ₽
              </div>
              <p className="text-xs text-muted-foreground">
                {t('admin.fromSubscriptions', { count: stats.active_subscriptions })}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
