import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getProcessMonitors, deleteProcessMonitor, pauseProcessMonitor, resumeProcessMonitor } from '@/api/processMonitors'
import { getSubscription, getPlans, Plan } from '@/api/billing'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from '@/hooks/use-toast'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Activity,
  Plus,
  Play,
  Pause,
  Trash2,
  Edit,
  Loader2,
  Copy,
  Lock,
  CreditCard,
} from 'lucide-react'
import { ProcessMonitorForm } from '@/components/process-monitors/ProcessMonitorForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { ProcessMonitor, ProcessMonitorStatus } from '@/types'

interface ProcessMonitorsPageProps {
  onNavigate: (route: string) => void
}

function formatInterval(seconds: number): string {
  if (seconds >= 86400) {
    const days = Math.floor(seconds / 86400)
    return `${days}d`
  }
  if (seconds >= 3600) {
    const hours = Math.floor(seconds / 3600)
    return `${hours}h`
  }
  if (seconds >= 60) {
    const minutes = Math.floor(seconds / 60)
    return `${minutes}m`
  }
  return `${seconds}s`
}

function formatDuration(ms: number | null): string {
  if (ms === null) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`
  return `${(ms / 3600000).toFixed(1)}h`
}

export function ProcessMonitorsPage({ onNavigate }: ProcessMonitorsPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
  const [monitors, setMonitors] = useState<ProcessMonitor[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingMonitor, setEditingMonitor] = useState<ProcessMonitor | null>(null)
  const [deletingMonitor, setDeletingMonitor] = useState<ProcessMonitor | null>(null)
  const [createdMonitor, setCreatedMonitor] = useState<ProcessMonitor | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null)

  const loadMonitors = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const response = await getProcessMonitors(currentWorkspace.id)
      setMonitors(response.process_monitors)
    } catch (err) {
      toast({
        title: t('processMonitors.errorLoading'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const loadPlan = async () => {
    try {
      const [subscription, plans] = await Promise.all([
        getSubscription(),
        getPlans(),
      ])
      const planId = subscription?.plan_id
      const plan = plans.find(p => p.id === planId) || plans.find(p => p.name === 'free')
      setCurrentPlan(plan || null)
    } catch (err) {
      console.error('Failed to load plan:', err)
    }
  }

  useEffect(() => {
    loadPlan()
  }, [])

  useEffect(() => {
    loadMonitors()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace])

  const handlePauseResume = async (monitor: ProcessMonitor) => {
    if (!currentWorkspace) return
    setActionLoading(monitor.id)
    try {
      if (monitor.is_paused) {
        await resumeProcessMonitor(currentWorkspace.id, monitor.id)
        toast({
          title: t('processMonitors.resumed'),
          description: t('processMonitors.resumedDescription', { name: monitor.name }),
          variant: 'success',
        })
      } else {
        await pauseProcessMonitor(currentWorkspace.id, monitor.id)
        toast({
          title: t('processMonitors.paused'),
          description: t('processMonitors.pausedDescription', { name: monitor.name }),
        })
      }
      await loadMonitors()
    } catch (err) {
      toast({
        title: t('processMonitors.actionFailed'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async () => {
    if (!currentWorkspace || !deletingMonitor) return
    const monitorName = deletingMonitor.name
    setActionLoading(deletingMonitor.id)
    try {
      await deleteProcessMonitor(currentWorkspace.id, deletingMonitor.id)
      setDeletingMonitor(null)
      toast({
        title: t('processMonitors.deleted'),
        description: t('processMonitors.deletedDescription', { name: monitorName }),
      })
      await loadMonitors()
    } catch (err) {
      toast({
        title: t('processMonitors.failedToDelete'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCopyUrl = async (url: string, type: 'start' | 'end') => {
    try {
      await navigator.clipboard.writeText(url)
      toast({
        title: type === 'start' ? t('processMonitors.startUrlCopied') : t('processMonitors.endUrlCopied'),
        description: type === 'start' ? t('processMonitors.startUrlCopiedDescription') : t('processMonitors.endUrlCopiedDescription'),
        variant: 'success',
      })
    } catch {
      toast({
        title: t('processMonitors.failedToCopy'),
        variant: 'destructive',
      })
    }
  }

  const getStatusBadge = (status: ProcessMonitorStatus) => {
    const variants: Record<ProcessMonitorStatus, 'success' | 'destructive' | 'warning' | 'secondary' | 'default'> = {
      waiting_start: 'secondary',
      running: 'default',
      completed: 'success',
      missed_start: 'destructive',
      missed_end: 'destructive',
      paused: 'secondary',
    }

    const labels: Record<ProcessMonitorStatus, string> = {
      waiting_start: t('processMonitors.statusWaitingStart'),
      running: t('processMonitors.statusRunning'),
      completed: t('processMonitors.statusCompleted'),
      missed_start: t('processMonitors.statusMissedStart'),
      missed_end: t('processMonitors.statusMissedEnd'),
      paused: t('processMonitors.statusPaused'),
    }

    return <Badge variant={variants[status]}>{labels[status]}</Badge>
  }

  const formatSchedule = (monitor: ProcessMonitor) => {
    if (monitor.schedule_type === 'cron' && monitor.schedule_cron) {
      return monitor.schedule_cron
    }
    if (monitor.schedule_type === 'interval' && monitor.schedule_interval) {
      return `${t('processMonitors.every')} ${formatInterval(monitor.schedule_interval)}`
    }
    if (monitor.schedule_type === 'exact_time' && monitor.schedule_exact_time) {
      return `${t('processMonitors.daily')} ${monitor.schedule_exact_time}`
    }
    return '-'
  }

  const formatLastRun = (monitor: ProcessMonitor) => {
    if (!monitor.last_start_at) return t('processMonitors.neverRun')
    const date = new Date(monitor.last_start_at)
    return date.toLocaleString()
  }

  if (workspaces.length === 0) {
    return <NoWorkspaceState />
  }

  if (!currentWorkspace) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <p className="text-muted-foreground">{t('common.selectWorkspace')}</p>
      </div>
    )
  }

  const isProcessMonitorsAvailable = currentPlan ? currentPlan.max_process_monitors > 0 : true

  if (!isProcessMonitorsAvailable && !isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('processMonitors.title')}</h1>
        </div>
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Lock className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('processMonitors.notAvailableOnPlan')}</h2>
          <p className="text-muted-foreground text-center max-w-md">
            {t('processMonitors.upgradeToUnlock')}
          </p>
          <Button onClick={() => onNavigate('billing')}>
            <CreditCard className="mr-2 h-4 w-4" />
            {t('processMonitors.viewPlans')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('processMonitors.title')}</h1>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 sm:mr-2" />
          <span className="hidden sm:inline">{t('processMonitors.create')}</span>
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : monitors.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Activity className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('processMonitors.noMonitorsYet')}</h2>
          <p className="text-muted-foreground text-center max-w-md">
            {t('processMonitors.createFirstMonitor')}
          </p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('processMonitors.create')}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('common.name')}</TableHead>
                <TableHead>{t('processMonitors.schedule')}</TableHead>
                <TableHead>{t('processMonitors.lastRun')}</TableHead>
                <TableHead>{t('processMonitors.duration')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {monitors.map((monitor) => (
                <TableRow key={monitor.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{monitor.name}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <button
                          onClick={() => handleCopyUrl(monitor.start_url, 'start')}
                          className="hover:text-foreground flex items-center gap-1 cursor-pointer"
                          title={t('processMonitors.copyStartUrl')}
                        >
                          <Copy className="h-3 w-3" />
                          <span>start</span>
                        </button>
                        <span>|</span>
                        <button
                          onClick={() => handleCopyUrl(monitor.end_url, 'end')}
                          className="hover:text-foreground flex items-center gap-1 cursor-pointer"
                          title={t('processMonitors.copyEndUrl')}
                        >
                          <Copy className="h-3 w-3" />
                          <span>end</span>
                        </button>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <span className="text-sm">{formatSchedule(monitor)}</span>
                      <p className="text-xs text-muted-foreground">
                        {t('processMonitors.timeout')}: {formatInterval(monitor.end_timeout)}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {formatLastRun(monitor)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {formatDuration(monitor.last_duration_ms)}
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(monitor.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handlePauseResume(monitor)}
                        disabled={actionLoading === monitor.id}
                        title={monitor.is_paused ? t('common.resume') : t('common.pause')}
                      >
                        {actionLoading === monitor.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : monitor.is_paused ? (
                          <Play className="h-4 w-4" />
                        ) : (
                          <Pause className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditingMonitor(monitor)}
                        title={t('common.edit')}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingMonitor(monitor)}
                        title={t('common.delete')}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('processMonitors.createMonitor')}</DialogTitle>
            <DialogDescription>
              {t('processMonitors.createDescription')}
            </DialogDescription>
          </DialogHeader>
          <ProcessMonitorForm
            workspaceId={currentWorkspace.id}
            onSuccess={(monitor) => {
              setShowCreateDialog(false)
              if (monitor) {
                setCreatedMonitor(monitor)
              }
              loadMonitors()
            }}
            onCancel={() => setShowCreateDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingMonitor} onOpenChange={() => setEditingMonitor(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('processMonitors.editMonitor')}</DialogTitle>
            <DialogDescription>
              {t('processMonitors.editDescription')}
            </DialogDescription>
          </DialogHeader>
          {editingMonitor && (
            <ProcessMonitorForm
              workspaceId={currentWorkspace.id}
              monitor={editingMonitor}
              onSuccess={() => {
                setEditingMonitor(null)
                loadMonitors()
              }}
              onCancel={() => setEditingMonitor(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingMonitor} onOpenChange={() => setDeletingMonitor(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('processMonitors.deleteMonitor')}</DialogTitle>
            <DialogDescription>
              {t('processMonitors.deleteConfirm', { name: deletingMonitor?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingMonitor(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading === deletingMonitor?.id}
            >
              {actionLoading === deletingMonitor?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Created Success Dialog */}
      <Dialog open={!!createdMonitor} onOpenChange={() => setCreatedMonitor(null)}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{t('processMonitors.createdSuccessTitle')}</DialogTitle>
            <DialogDescription>
              {t('processMonitors.createdSuccessDescription', { name: createdMonitor?.name })}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('processMonitors.startUrl')}</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded bg-muted px-3 py-2 text-sm break-all">
                  {createdMonitor?.start_url}
                </code>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => createdMonitor && handleCopyUrl(createdMonitor.start_url, 'start')}
                  title={t('processMonitors.copyStartUrl')}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('processMonitors.endUrl')}</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded bg-muted px-3 py-2 text-sm break-all">
                  {createdMonitor?.end_url}
                </code>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => createdMonitor && handleCopyUrl(createdMonitor.end_url, 'end')}
                  title={t('processMonitors.copyEndUrl')}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="rounded-md bg-muted/50 p-3">
              <p className="text-sm text-muted-foreground mb-2">
                {t('processMonitors.usageHint')}
              </p>
              <code className="block text-xs bg-background rounded p-2 break-all">
                {`# ${t('processMonitors.atProcessStart')}`}<br />
                curl {createdMonitor?.start_url}<br /><br />
                {`# ${t('processMonitors.atProcessEnd')}`}<br />
                curl {createdMonitor?.end_url}
              </code>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setCreatedMonitor(null)}>
              {t('common.close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
