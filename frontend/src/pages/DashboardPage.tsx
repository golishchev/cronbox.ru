import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getWorkspaces, getWorkspace, createWorkspace } from '@/api/workspaces'
import { getExecutions, getDailyExecutionStats } from '@/api/executions'
import { getErrorMessage } from '@/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Clock, Calendar, CheckCircle, XCircle, Loader2, Plus, TrendingUp, Activity } from 'lucide-react'
import { DashboardSkeleton } from '@/components/ui/skeleton'
import { toast } from '@/hooks/use-toast'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { WorkspaceWithStats, Execution, ExecutionStatus } from '@/types'

interface DailyStats {
  date: string
  success: number
  failed: number
  total: number
}

export function DashboardPage() {
  const { t, i18n } = useTranslation()
  const { workspaces, currentWorkspace, setWorkspaces, setCurrentWorkspace, isLoading, setLoading } = useWorkspaceStore()
  const [stats, setStats] = useState<WorkspaceWithStats | null>(null)
  const [recentExecutions, setRecentExecutions] = useState<Execution[]>([])
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([])
  const [error, setError] = useState('')

  // Create workspace dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState('')
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [newWorkspaceSlug, setNewWorkspaceSlug] = useState('')

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
  }

  const handleNameChange = (name: string) => {
    setNewWorkspaceName(name)
    setNewWorkspaceSlug(generateSlug(name))
  }

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newWorkspaceName.trim() || !newWorkspaceSlug.trim()) {
      setCreateError(t('workspace.nameRequired'))
      return
    }

    setCreateLoading(true)
    setCreateError('')

    try {
      const workspace = await createWorkspace({
        name: newWorkspaceName.trim(),
        slug: newWorkspaceSlug.trim(),
      })
      setWorkspaces([...workspaces, workspace])
      setCurrentWorkspace(workspace)
      setShowCreateDialog(false)
      setNewWorkspaceName('')
      setNewWorkspaceSlug('')
      toast({
        title: t('workspace.created'),
        description: t('workspace.createdDescription', { name: workspace.name }),
        variant: 'success',
      })
    } catch (err) {
      setCreateError(getErrorMessage(err))
    } finally {
      setCreateLoading(false)
    }
  }

  // Workspaces are loaded by LoginPage/App.tsx after authentication
  // Only reload if workspaces are empty (e.g., page refresh)
  useEffect(() => {
    const loadWorkspaces = async () => {
      if (workspaces.length > 0) return // Already loaded

      setLoading(true)
      try {
        const ws = await getWorkspaces()
        setWorkspaces(ws)
        if (ws.length > 0 && !currentWorkspace) {
          setCurrentWorkspace(ws[0])
        }
      } catch {
        setError(t('dashboard.failedToLoad'))
      } finally {
        setLoading(false)
      }
    }

    loadWorkspaces()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run on mount

  useEffect(() => {
    const loadStats = async () => {
      if (!currentWorkspace) return
      try {
        const workspaceStats = await getWorkspace(currentWorkspace.id)
        setStats(workspaceStats)
      } catch {
        // Ignore stats loading errors
      }
    }

    const loadRecentExecutions = async () => {
      if (!currentWorkspace) return
      try {
        const response = await getExecutions(currentWorkspace.id, { limit: 10 })
        setRecentExecutions(response.executions)
      } catch {
        // Ignore errors
      }
    }

    const loadDailyStats = async () => {
      if (!currentWorkspace) return
      try {
        const stats = await getDailyExecutionStats(currentWorkspace.id, 7)
        // Convert date to localized weekday name for chart display
        const locale = i18n.language === 'ru' ? 'ru-RU' : 'en-US'
        const formattedStats = stats.map((s) => ({
          ...s,
          date: new Date(s.date + 'T00:00:00').toLocaleDateString(locale, { weekday: 'short' }),
        }))
        setDailyStats(formattedStats)
      } catch {
        // Ignore errors
      }
    }

    loadStats()
    loadRecentExecutions()
    loadDailyStats()
  }, [currentWorkspace, i18n.language])

  const getStatusBadge = (status: ExecutionStatus) => {
    switch (status) {
      case 'success':
        return <Badge variant="success" className="gap-1"><CheckCircle className="h-3 w-3" />{t('common.success')}</Badge>
      case 'failed':
        return <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" />{t('common.failed')}</Badge>
      case 'running':
        return <Badge variant="default" className="gap-1"><Loader2 className="h-3 w-3 animate-spin" />{t('common.running')}</Badge>
      case 'pending':
        return <Badge variant="secondary" className="gap-1"><Clock className="h-3 w-3" />{t('common.pending')}</Badge>
      case 'partial':
        return <Badge variant="warning" className="gap-1"><XCircle className="h-3 w-3" />{t('executions.partial')}</Badge>
      case 'cancelled':
        return <Badge variant="secondary" className="gap-1"><XCircle className="h-3 w-3" />{t('executions.cancelled')}</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  if (isLoading) {
    return <DashboardSkeleton />
  }

  if (error) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <p className="text-destructive">{error}</p>
      </div>
    )
  }

  if (workspaces.length === 0) {
    return (
      <>
        <div className="flex h-[50vh] flex-col items-center justify-center gap-4">
          <Clock className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-2xl font-semibold">{t('dashboard.noWorkspacesYet')}</h2>
          <p className="text-muted-foreground">{t('dashboard.createFirstWorkspace')}</p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('workspace.create')}
          </Button>
        </div>

        {/* Create Workspace Dialog */}
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('workspace.createNew')}</DialogTitle>
              <DialogDescription>
                {t('workspace.createDescription')}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateWorkspace} className="space-y-4">
              {createError && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                  {createError}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="name">{t('workspace.name')}</Label>
                <Input
                  id="name"
                  value={newWorkspaceName}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder={t('workspace.namePlaceholder')}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="slug">{t('workspace.slug')}</Label>
                <Input
                  id="slug"
                  value={newWorkspaceSlug}
                  onChange={(e) => setNewWorkspaceSlug(e.target.value)}
                  placeholder={t('workspace.slugPlaceholder')}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  {t('workspace.slugDescription')}
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                  {t('common.cancel')}
                </Button>
                <Button type="submit" disabled={createLoading}>
                  {createLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t('common.create')}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('dashboard.title')}</h1>
        <p className="text-muted-foreground">
          {t('dashboard.subtitle')}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('dashboard.activeCronTasks')}</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.active_cron_tasks ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {t('dashboard.ofTotal', { total: stats?.cron_tasks_count ?? 0 })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('dashboard.pendingDelayedTasks')}</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.pending_delayed_tasks ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.delayed_tasks_this_month ?? 0} {t('dashboard.thisMonth')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('dashboard.executionsToday')}</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.executions_today ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {t('dashboard.tasksExecutedToday')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('dashboard.successRate7d')}</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.success_rate_7d !== undefined
                ? `${stats.success_rate_7d.toFixed(1)}%`
                : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              {t('dashboard.last7Days')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Chart and Recent Executions */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Executions Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              {t('dashboard.executionsLast7Days')}
            </CardTitle>
            <CardDescription>
              {t('dashboard.successAndFailureRate')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {dailyStats.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={dailyStats}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="date"
                    className="text-xs"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <YAxis
                    className="text-xs"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="success"
                    stackId="1"
                    stroke="hsl(var(--success))"
                    fill="hsl(142.1 76.2% 36.3% / 0.3)"
                    name={t('common.success')}
                  />
                  <Area
                    type="monotone"
                    dataKey="failed"
                    stackId="1"
                    stroke="hsl(var(--destructive))"
                    fill="hsl(0 84.2% 60.2% / 0.3)"
                    name={t('common.failed')}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                {t('dashboard.noExecutionDataYet')}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Executions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              {t('dashboard.recentExecutions')}
            </CardTitle>
            <CardDescription>
              {t('dashboard.latestTaskExecutions')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {recentExecutions.length > 0 ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('executions.task')}</TableHead>
                      <TableHead>{t('common.status')}</TableHead>
                      <TableHead className="text-right">{t('common.duration')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentExecutions.slice(0, 5).map((exec) => (
                      <TableRow key={exec.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium text-sm truncate max-w-[150px]">
                              {exec.task_name || t('executions.unnamedTask')}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(exec.started_at).toLocaleTimeString()}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(exec.status)}</TableCell>
                        <TableCell className="text-right text-sm">
                          {formatDuration(exec.duration_ms)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                {t('executions.noExecutionsYet')}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Current Workspace Info */}
      {currentWorkspace && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{currentWorkspace.name}</CardTitle>
                <CardDescription>/{currentWorkspace.slug}</CardDescription>
              </div>
              <Badge variant="secondary">{stats?.plan_name ?? t('billing.free')}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t('dashboard.timezone')}</span>
                <span>{currentWorkspace.default_timezone}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t('dashboard.created')}</span>
                <span>{new Date(currentWorkspace.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
