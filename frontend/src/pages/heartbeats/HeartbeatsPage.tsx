import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getHeartbeats, deleteHeartbeat, pauseHeartbeat, resumeHeartbeat } from '@/api/heartbeats'
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
  Heart,
  Plus,
  Play,
  Pause,
  Trash2,
  Edit,
  Loader2,
  Copy,
  ExternalLink,
  Lock,
  CreditCard,
} from 'lucide-react'
import { HeartbeatForm } from '@/components/heartbeats/HeartbeatForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { Heartbeat, HeartbeatStatus } from '@/types'

interface HeartbeatsPageProps {
  onNavigate: (route: string) => void
}

// Format seconds to human-readable string
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

export function HeartbeatsPage({ onNavigate }: HeartbeatsPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
  const [heartbeats, setHeartbeats] = useState<Heartbeat[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingHeartbeat, setEditingHeartbeat] = useState<Heartbeat | null>(null)
  const [deletingHeartbeat, setDeletingHeartbeat] = useState<Heartbeat | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null)

  const loadHeartbeats = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const response = await getHeartbeats(currentWorkspace.id)
      setHeartbeats(response.heartbeats)
    } catch (err) {
      toast({
        title: t('heartbeats.errorLoading'),
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
    loadHeartbeats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace])

  const handlePauseResume = async (heartbeat: Heartbeat) => {
    if (!currentWorkspace) return
    setActionLoading(heartbeat.id)
    try {
      if (heartbeat.is_paused) {
        await resumeHeartbeat(currentWorkspace.id, heartbeat.id)
        toast({
          title: t('heartbeats.resumed'),
          description: t('heartbeats.resumedDescription', { name: heartbeat.name }),
          variant: 'success',
        })
      } else {
        await pauseHeartbeat(currentWorkspace.id, heartbeat.id)
        toast({
          title: t('heartbeats.paused'),
          description: t('heartbeats.pausedDescription', { name: heartbeat.name }),
        })
      }
      await loadHeartbeats()
    } catch (err) {
      toast({
        title: t('heartbeats.actionFailed'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async () => {
    if (!currentWorkspace || !deletingHeartbeat) return
    const heartbeatName = deletingHeartbeat.name
    setActionLoading(deletingHeartbeat.id)
    try {
      await deleteHeartbeat(currentWorkspace.id, deletingHeartbeat.id)
      setDeletingHeartbeat(null)
      toast({
        title: t('heartbeats.deleted'),
        description: t('heartbeats.deletedDescription', { name: heartbeatName }),
      })
      await loadHeartbeats()
    } catch (err) {
      toast({
        title: t('heartbeats.failedToDelete'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCopyPingUrl = async (pingUrl: string) => {
    try {
      await navigator.clipboard.writeText(pingUrl)
      toast({
        title: t('heartbeats.pingUrlCopied'),
        description: t('heartbeats.pingUrlCopiedDescription'),
        variant: 'success',
      })
    } catch {
      toast({
        title: t('heartbeats.failedToCopy'),
        variant: 'destructive',
      })
    }
  }

  const getStatusBadge = (status: HeartbeatStatus) => {
    const variants: Record<HeartbeatStatus, 'success' | 'destructive' | 'warning' | 'secondary'> = {
      healthy: 'success',
      waiting: 'secondary',
      late: 'warning',
      dead: 'destructive',
      paused: 'secondary',
    }

    const labels: Record<HeartbeatStatus, string> = {
      healthy: t('heartbeats.statusHealthy'),
      waiting: t('heartbeats.statusWaiting'),
      late: t('heartbeats.statusLate'),
      dead: t('heartbeats.statusDead'),
      paused: t('heartbeats.statusPaused'),
    }

    return <Badge variant={variants[status]}>{labels[status]}</Badge>
  }

  const formatLastPing = (lastPingAt: string | null) => {
    if (!lastPingAt) return t('heartbeats.neverPinged')
    const date = new Date(lastPingAt)
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

  // Check if heartbeats are available for the current plan
  const isHeartbeatsAvailable = currentPlan ? currentPlan.max_heartbeats > 0 : true

  // Show upgrade prompt if heartbeats are not available
  if (!isHeartbeatsAvailable && !isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('heartbeats.title')}</h1>
          <p className="text-muted-foreground">
            {t('heartbeats.subtitle')}
          </p>
        </div>
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Lock className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('heartbeats.notAvailableOnPlan')}</h2>
          <p className="text-muted-foreground text-center max-w-md">
            {t('heartbeats.upgradeToUnlock')}
          </p>
          <Button onClick={() => onNavigate('billing')}>
            <CreditCard className="mr-2 h-4 w-4" />
            {t('heartbeats.viewPlans')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('heartbeats.title')}</h1>
          <p className="text-muted-foreground">
            {t('heartbeats.subtitle')}
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 sm:mr-2" />
          <span className="hidden sm:inline">{t('heartbeats.create')}</span>
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : heartbeats.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Heart className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('heartbeats.noHeartbeatsYet')}</h2>
          <p className="text-muted-foreground text-center max-w-md">
            {t('heartbeats.createFirstHeartbeat')}
          </p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('heartbeats.create')}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('common.name')}</TableHead>
                <TableHead>{t('heartbeats.interval')}</TableHead>
                <TableHead>{t('heartbeats.lastPing')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {heartbeats.map((heartbeat) => (
                <TableRow key={heartbeat.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{heartbeat.name}</p>
                      <button
                        onClick={() => handleCopyPingUrl(heartbeat.ping_url)}
                        className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer"
                        title={t('heartbeats.clickToCopy')}
                      >
                        <Copy className="h-3 w-3" />
                        <span className="truncate max-w-[200px]">{heartbeat.ping_url}</span>
                      </button>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <span className="text-sm">{formatInterval(heartbeat.expected_interval)}</span>
                      <p className="text-xs text-muted-foreground">
                        +{formatInterval(heartbeat.grace_period)} {t('heartbeats.grace')}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {formatLastPing(heartbeat.last_ping_at)}
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(heartbeat.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handlePauseResume(heartbeat)}
                        disabled={actionLoading === heartbeat.id}
                        title={heartbeat.is_paused ? t('common.resume') : t('common.pause')}
                      >
                        {actionLoading === heartbeat.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : heartbeat.is_paused ? (
                          <Play className="h-4 w-4" />
                        ) : (
                          <Pause className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditingHeartbeat(heartbeat)}
                        title={t('common.edit')}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        asChild
                        title={t('heartbeats.openPingUrl')}
                      >
                        <a href={heartbeat.ping_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingHeartbeat(heartbeat)}
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
            <DialogTitle>{t('heartbeats.createHeartbeat')}</DialogTitle>
            <DialogDescription>
              {t('heartbeats.createDescription')}
            </DialogDescription>
          </DialogHeader>
          <HeartbeatForm
            workspaceId={currentWorkspace.id}
            onSuccess={() => {
              setShowCreateDialog(false)
              loadHeartbeats()
            }}
            onCancel={() => setShowCreateDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingHeartbeat} onOpenChange={() => setEditingHeartbeat(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('heartbeats.editHeartbeat')}</DialogTitle>
            <DialogDescription>
              {t('heartbeats.editDescription')}
            </DialogDescription>
          </DialogHeader>
          {editingHeartbeat && (
            <HeartbeatForm
              workspaceId={currentWorkspace.id}
              heartbeat={editingHeartbeat}
              onSuccess={() => {
                setEditingHeartbeat(null)
                loadHeartbeats()
              }}
              onCancel={() => setEditingHeartbeat(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingHeartbeat} onOpenChange={() => setDeletingHeartbeat(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('heartbeats.deleteHeartbeat')}</DialogTitle>
            <DialogDescription>
              {t('heartbeats.deleteConfirm', { name: deletingHeartbeat?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingHeartbeat(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading === deletingHeartbeat?.id}
            >
              {actionLoading === deletingHeartbeat?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
