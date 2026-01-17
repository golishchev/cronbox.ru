import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getTaskChains, deleteTaskChain, pauseTaskChain, resumeTaskChain, runTaskChain, copyTaskChain } from '@/api/taskChains'
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
  Link2,
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
import { ChainForm } from '@/components/chains/ChainForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { TaskChain, TriggerType } from '@/types/chains'
import cronstrue from 'cronstrue/i18n'
import i18n from 'i18next'

interface ChainsPageProps {
  onNavigate: (route: string) => void
}

export function ChainsPage({ onNavigate }: ChainsPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
  const [chains, setChains] = useState<TaskChain[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingChain, setEditingChain] = useState<TaskChain | null>(null)
  const [deletingChain, setDeletingChain] = useState<TaskChain | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null)

  const loadChains = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const response = await getTaskChains(currentWorkspace.id)
      setChains(response.chains)
    } catch (err) {
      toast({
        title: t('chains.errorLoading'),
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
      // Find current plan - either from subscription or default to free plan
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
    loadChains()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace])

  const handlePauseResume = async (chain: TaskChain) => {
    if (!currentWorkspace) return
    setActionLoading(chain.id)
    try {
      if (chain.is_paused) {
        await resumeTaskChain(currentWorkspace.id, chain.id)
        toast({
          title: t('chains.chainResumed'),
          description: t('chains.chainResumedDescription', { name: chain.name }),
          variant: 'success',
        })
      } else {
        await pauseTaskChain(currentWorkspace.id, chain.id)
        toast({
          title: t('chains.chainPaused'),
          description: t('chains.chainPausedDescription', { name: chain.name }),
        })
      }
      await loadChains()
    } catch (err) {
      toast({
        title: t('chains.actionFailed'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleRun = async (chain: TaskChain) => {
    if (!currentWorkspace) return
    setActionLoading(chain.id)
    try {
      await runTaskChain(currentWorkspace.id, chain.id)
      toast({
        title: t('chains.chainTriggered'),
        description: t('chains.chainTriggeredDescription', { name: chain.name }),
        variant: 'success',
      })
      await loadChains()
    } catch (err) {
      toast({
        title: t('chains.failedToRunChain'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async () => {
    if (!currentWorkspace || !deletingChain) return
    const chainName = deletingChain.name
    setActionLoading(deletingChain.id)
    try {
      await deleteTaskChain(currentWorkspace.id, deletingChain.id)
      setDeletingChain(null)
      toast({
        title: t('chains.chainDeleted'),
        description: t('chains.chainDeletedDescription', { name: chainName }),
      })
      await loadChains()
    } catch (err) {
      toast({
        title: t('chains.failedToDeleteChain'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCopy = async (chain: TaskChain) => {
    if (!currentWorkspace) return
    setActionLoading(chain.id)
    try {
      const newChain = await copyTaskChain(currentWorkspace.id, chain.id)
      toast({
        title: t('chains.chainCopied'),
        description: t('chains.chainCopiedDescription', { name: newChain.name }),
        variant: 'success',
      })
      await loadChains()
    } catch (err) {
      toast({
        title: t('chains.failedToCopyChain'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (chain: TaskChain) => {
    if (!chain.is_active) {
      return <Badge variant="secondary">{t('common.inactive')}</Badge>
    }
    if (chain.is_paused) {
      return <Badge variant="warning">{t('chains.paused')}</Badge>
    }
    if (chain.last_status === 'failed') {
      return <Badge variant="destructive">{t('common.failed')}</Badge>
    }
    if (chain.last_status === 'partial') {
      return <Badge variant="warning">{t('chains.partial')}</Badge>
    }
    if (chain.last_status === 'success') {
      return <Badge variant="success">{t('common.active')}</Badge>
    }
    return <Badge variant="secondary">{t('common.active')}</Badge>
  }

  const getTriggerTypeBadge = (triggerType: TriggerType) => {
    switch (triggerType) {
      case 'cron':
        return <Badge variant="outline">{t('chains.triggerCron')}</Badge>
      case 'delayed':
        return <Badge variant="outline">{t('chains.triggerDelayed')}</Badge>
      case 'manual':
        return <Badge variant="outline">{t('chains.triggerManual')}</Badge>
    }
  }

  const formatCronExpression = (schedule: string | null) => {
    if (!schedule) return '-'
    try {
      const locale = i18n.language === 'ru' ? 'ru' : 'en'
      return cronstrue.toString(schedule, { use24HourTimeFormat: true, locale })
    } catch {
      return schedule
    }
  }

  const formatNextRun = (nextRunAt: string | null) => {
    if (!nextRunAt) return t('chains.notScheduled')
    const date = new Date(nextRunAt)
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

  // Check if task chains are available for the current plan
  const isChainsAvailable = currentPlan ? currentPlan.max_task_chains > 0 : true

  // Show upgrade prompt if chains are not available
  if (!isChainsAvailable && !isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('chains.title')}</h1>
          <p className="text-muted-foreground">
            {t('chains.subtitle')}
          </p>
        </div>
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Lock className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('chains.notAvailableOnPlan')}</h2>
          <p className="text-muted-foreground text-center max-w-md">
            {t('chains.upgradeToUnlock')}
          </p>
          <Button onClick={() => onNavigate('billing')}>
            <CreditCard className="mr-2 h-4 w-4" />
            {t('chains.viewPlans')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('chains.title')}</h1>
          <p className="text-muted-foreground">
            {t('chains.subtitle')}
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t('chains.createChain')}
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : chains.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Link2 className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('chains.noChainsYet')}</h2>
          <p className="text-muted-foreground">{t('chains.createFirstChain')}</p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('chains.createChain')}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('common.name')}</TableHead>
                <TableHead>{t('chains.trigger')}</TableHead>
                <TableHead>{t('chains.nextRun')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {chains.map((chain) => (
                <TableRow key={chain.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{chain.name}</p>
                      {chain.description && (
                        <p className="text-sm text-muted-foreground truncate max-w-[300px]">
                          {chain.description}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      {getTriggerTypeBadge(chain.trigger_type)}
                      {chain.trigger_type === 'cron' && chain.schedule && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatCronExpression(chain.schedule)}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {formatNextRun(chain.next_run_at)}
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(chain)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onNavigate(`chains/${chain.id}`)}
                      >
                        {t('chains.steps')}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRun(chain)}
                        disabled={actionLoading === chain.id || !chain.is_active}
                        title={t('chains.runNow')}
                      >
                        {actionLoading === chain.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handlePauseResume(chain)}
                        disabled={actionLoading === chain.id || !chain.is_active}
                        title={chain.is_paused ? t('chains.resume') : t('chains.pause')}
                      >
                        {chain.is_paused ? (
                          <Play className="h-4 w-4" />
                        ) : (
                          <Pause className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditingChain(chain)}
                        title={t('common.edit')}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCopy(chain)}
                        disabled={actionLoading === chain.id}
                        title={t('chains.copyChain')}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingChain(chain)}
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
            <DialogTitle>{t('chains.createTaskChain')}</DialogTitle>
            <DialogDescription>
              {t('chains.createDescription')}
            </DialogDescription>
          </DialogHeader>
          <ChainForm
            workspaceId={currentWorkspace.id}
            onSuccess={() => {
              setShowCreateDialog(false)
              loadChains()
            }}
            onCancel={() => setShowCreateDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingChain} onOpenChange={() => setEditingChain(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('chains.editTaskChain')}</DialogTitle>
            <DialogDescription>
              {t('chains.editDescription')}
            </DialogDescription>
          </DialogHeader>
          {editingChain && (
            <ChainForm
              workspaceId={currentWorkspace.id}
              chain={editingChain}
              onSuccess={() => {
                setEditingChain(null)
                loadChains()
              }}
              onCancel={() => setEditingChain(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingChain} onOpenChange={() => setDeletingChain(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('chains.deleteChain')}</DialogTitle>
            <DialogDescription>
              {t('chains.deleteConfirm', { name: deletingChain?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingChain(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading === deletingChain?.id}
            >
              {actionLoading === deletingChain?.id ? (
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
