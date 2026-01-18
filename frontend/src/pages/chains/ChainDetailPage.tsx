import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import {
  getTaskChain,
  runTaskChain,
  pauseTaskChain,
  resumeTaskChain,
  createChainStep,
  updateChainStep,
  deleteChainStep,
  reorderChainSteps,
  getChainExecutions,
  getChainExecution,
} from '@/api/taskChains'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from '@/hooks/use-toast'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  ArrowLeft,
  Play,
  Pause,
  Plus,
  Loader2,
  Trash2,
  Edit,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Eye,
} from 'lucide-react'
import { ChainStepForm } from '@/components/chains/ChainStepForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type {
  TaskChainDetail,
  ChainStep,
  ChainExecution,
  ChainExecutionDetail,
  ChainStatus,
  StepStatus,
  CreateChainStepRequest,
} from '@/types/chains'
import cronstrue from 'cronstrue/i18n'
import i18n from 'i18next'

interface ChainDetailPageProps {
  chainId: string
  onNavigate: (route: string) => void
}

export function ChainDetailPage({ chainId, onNavigate }: ChainDetailPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace } = useWorkspaceStore()
  const [chain, setChain] = useState<TaskChainDetail | null>(null)
  const [executions, setExecutions] = useState<ChainExecution[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [executionsLoading, setExecutionsLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [showAddStepDialog, setShowAddStepDialog] = useState(false)
  const [editingStep, setEditingStep] = useState<ChainStep | null>(null)
  const [deletingStep, setDeletingStep] = useState<ChainStep | null>(null)
  const [expandedStep, setExpandedStep] = useState<string | null>(null)
  const [selectedExecution, setSelectedExecution] = useState<ChainExecutionDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const loadChain = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const data = await getTaskChain(currentWorkspace.id, chainId)
      setChain(data)
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

  const loadExecutions = async () => {
    if (!currentWorkspace) return
    setExecutionsLoading(true)
    try {
      const response = await getChainExecutions(currentWorkspace.id, chainId)
      setExecutions(response.executions)
    } catch (err) {
      toast({
        title: t('chains.errorLoadingExecutions'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setExecutionsLoading(false)
    }
  }

  useEffect(() => {
    loadChain()
    loadExecutions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace, chainId])

  const handleRun = async () => {
    if (!currentWorkspace || !chain) return
    setActionLoading('run')
    try {
      await runTaskChain(currentWorkspace.id, chain.id)
      toast({
        title: t('chains.chainTriggered'),
        description: t('chains.chainTriggeredDescription', { name: chain.name }),
        variant: 'success',
      })
      await loadChain()
      await loadExecutions()
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

  const handlePauseResume = async () => {
    if (!currentWorkspace || !chain) return
    setActionLoading('pause')
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
      await loadChain()
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

  const handleAddStep = async (data: CreateChainStepRequest) => {
    if (!currentWorkspace || !chain) return
    try {
      await createChainStep(currentWorkspace.id, chain.id, data)
      toast({
        title: t('chains.stepAdded'),
        description: t('chains.stepAddedDescription', { name: data.name }),
        variant: 'success',
      })
      setShowAddStepDialog(false)
      await loadChain()
    } catch (err) {
      toast({
        title: t('chains.failedToAddStep'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    }
  }

  const handleUpdateStep = async (stepId: string, data: CreateChainStepRequest) => {
    if (!currentWorkspace || !chain) return
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { step_order, ...updateData } = data
    try {
      await updateChainStep(currentWorkspace.id, chain.id, stepId, updateData)
      toast({
        title: t('chains.stepUpdated'),
        description: t('chains.stepUpdatedDescription'),
        variant: 'success',
      })
      setEditingStep(null)
      await loadChain()
    } catch (err) {
      toast({
        title: t('chains.failedToUpdateStep'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    }
  }

  const handleDeleteStep = async () => {
    if (!currentWorkspace || !chain || !deletingStep) return
    setActionLoading(deletingStep.id)
    try {
      await deleteChainStep(currentWorkspace.id, chain.id, deletingStep.id)
      toast({
        title: t('chains.stepDeleted'),
        description: t('chains.stepDeletedDescription', { name: deletingStep.name }),
      })
      setDeletingStep(null)
      await loadChain()
    } catch (err) {
      toast({
        title: t('chains.failedToDeleteStep'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleToggleStepEnabled = async (step: ChainStep) => {
    if (!currentWorkspace || !chain) return
    try {
      await updateChainStep(currentWorkspace.id, chain.id, step.id, {
        is_enabled: !step.is_enabled,
      })
      await loadChain()
    } catch (err) {
      toast({
        title: t('chains.failedToUpdateStep'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    }
  }

  const handleViewExecution = async (execution: ChainExecution) => {
    if (!currentWorkspace || !chain) return
    setLoadingDetail(true)
    try {
      const detail = await getChainExecution(currentWorkspace.id, chain.id, execution.id)
      setSelectedExecution(detail)
    } catch (err) {
      toast({
        title: t('chains.errorLoadingExecutions'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setLoadingDetail(false)
    }
  }

  const moveStep = async (stepId: string, direction: 'up' | 'down') => {
    if (!currentWorkspace || !chain) return

    const steps = [...chain.steps].sort((a, b) => a.step_order - b.step_order)
    const currentIndex = steps.findIndex(s => s.id === stepId)
    if (currentIndex === -1) return

    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
    if (newIndex < 0 || newIndex >= steps.length) return

    // Swap orders
    const reorderedSteps = steps.map((step, idx) => {
      if (idx === currentIndex) return { [step.id]: steps[newIndex].step_order }
      if (idx === newIndex) return { [step.id]: steps[currentIndex].step_order }
      return { [step.id]: step.step_order }
    })

    try {
      await reorderChainSteps(currentWorkspace.id, chain.id, { step_orders: reorderedSteps })
      await loadChain()
    } catch (err) {
      toast({
        title: t('chains.failedToReorderSteps'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    }
  }

  const getStepStatusBadge = (status: StepStatus) => {
    switch (status) {
      case 'pending':
        return <Badge variant="secondary" className="gap-1"><Clock className="h-3 w-3" />{t('common.pending')}</Badge>
      case 'running':
        return <Badge variant="default" className="gap-1"><Loader2 className="h-3 w-3 animate-spin" />{t('common.running')}</Badge>
      case 'success':
        return <Badge variant="success" className="gap-1"><CheckCircle className="h-3 w-3" />{t('common.success')}</Badge>
      case 'failed':
        return <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" />{t('common.failed')}</Badge>
      case 'skipped':
        return <Badge variant="outline" className="gap-1"><AlertCircle className="h-3 w-3" />{t('chains.skipped')}</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  const getChainStatusBadge = (status: ChainStatus) => {
    switch (status) {
      case 'pending':
        return (
          <Badge variant="secondary" className="gap-1">
            <Clock className="h-3 w-3" />
            {t('common.pending')}
          </Badge>
        )
      case 'running':
        return (
          <Badge variant="default" className="gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            {t('common.running')}
          </Badge>
        )
      case 'success':
        return (
          <Badge variant="success" className="gap-1">
            <CheckCircle className="h-3 w-3" />
            {t('common.success')}
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="h-3 w-3" />
            {t('common.failed')}
          </Badge>
        )
      case 'partial':
        return (
          <Badge variant="warning" className="gap-1">
            <AlertCircle className="h-3 w-3" />
            {t('chains.partial')}
          </Badge>
        )
      case 'cancelled':
        return (
          <Badge variant="outline" className="gap-1">
            <AlertCircle className="h-3 w-3" />
            {t('common.cancelled')}
          </Badge>
        )
      default:
        return <Badge variant="secondary">{status}</Badge>
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

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
    return `${(ms / 60000).toFixed(2)}m`
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => onNavigate('chains')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="h-8 w-48 bg-muted animate-pulse rounded" />
        </div>
        <TableSkeleton rows={5} columns={4} />
      </div>
    )
  }

  if (!chain) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => onNavigate('chains')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">{t('chains.chainNotFound')}</h1>
        </div>
      </div>
    )
  }

  const sortedSteps = [...chain.steps].sort((a, b) => a.step_order - b.step_order)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => onNavigate('chains')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{chain.name}</h1>
            {chain.description && (
              <p className="text-muted-foreground">{chain.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handlePauseResume}
            disabled={actionLoading === 'pause' || !chain.is_active}
          >
            {actionLoading === 'pause' ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : chain.is_paused ? (
              <Play className="mr-2 h-4 w-4" />
            ) : (
              <Pause className="mr-2 h-4 w-4" />
            )}
            {chain.is_paused ? t('chains.resume') : t('chains.pause')}
          </Button>
          <Button
            onClick={handleRun}
            disabled={actionLoading === 'run' || !chain.is_active}
          >
            {actionLoading === 'run' ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            {t('chains.runNow')}
          </Button>
        </div>
      </div>

      {/* Chain Info Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t('chains.trigger')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold capitalize">{chain.trigger_type}</p>
            {chain.trigger_type === 'cron' && chain.schedule && (
              <p className="text-sm text-muted-foreground">
                {formatCronExpression(chain.schedule)}
              </p>
            )}
            {chain.trigger_type === 'delayed' && chain.execute_at && (
              <p className="text-sm text-muted-foreground">
                {formatDateTime(chain.execute_at)}
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t('chains.lastStatus')}</CardTitle>
          </CardHeader>
          <CardContent>
            {chain.last_status ? (
              getChainStatusBadge(chain.last_status)
            ) : (
              <Badge variant="secondary">{t('chains.neverRun')}</Badge>
            )}
            {chain.last_run_at && (
              <p className="text-sm text-muted-foreground mt-1">
                {formatDateTime(chain.last_run_at)}
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t('chains.nextRun')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">
              {chain.next_run_at ? formatDateTime(chain.next_run_at) : t('chains.notScheduled')}
            </p>
            {chain.is_paused && (
              <Badge variant="warning" className="mt-1">{t('chains.paused')}</Badge>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="steps">
        <TabsList>
          <TabsTrigger value="steps">
            {t('chains.steps')} ({chain.steps.length})
          </TabsTrigger>
          <TabsTrigger value="executions">
            {t('chains.executions')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="steps" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setShowAddStepDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              {t('chains.addStep')}
            </Button>
          </div>

          {sortedSteps.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-8 gap-4">
                <p className="text-muted-foreground">{t('chains.noStepsYet')}</p>
                <Button onClick={() => setShowAddStepDialog(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  {t('chains.addFirstStep')}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {sortedSteps.map((step, index) => (
                <Card key={step.id} className={!step.is_enabled ? 'opacity-60' : ''}>
                  <CardHeader className="py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex flex-col gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5"
                            disabled={index === 0}
                            onClick={() => moveStep(step.id, 'up')}
                          >
                            <ChevronUp className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5"
                            disabled={index === sortedSteps.length - 1}
                            onClick={() => moveStep(step.id, 'down')}
                          >
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{index + 1}</Badge>
                            <CardTitle className="text-base">{step.name}</CardTitle>
                            <Badge variant="secondary">{step.method}</Badge>
                          </div>
                          <CardDescription className="truncate max-w-md">
                            {step.url}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={step.is_enabled}
                          onCheckedChange={() => handleToggleStepEnabled(step)}
                          title={step.is_enabled ? t('chains.disableStep') : t('chains.enableStep')}
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                        >
                          {expandedStep === step.id ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setEditingStep(step)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeletingStep(step)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  {expandedStep === step.id && (
                    <CardContent className="pt-0 border-t">
                      <div className="grid gap-4 md:grid-cols-2 pt-4">
                        <div>
                          <p className="text-sm font-medium">{t('chains.timeout')}</p>
                          <p className="text-sm text-muted-foreground">{step.timeout_seconds}s</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium">{t('chains.retries')}</p>
                          <p className="text-sm text-muted-foreground">
                            {step.retry_count} ({step.retry_delay_seconds}s {t('chains.delay')})
                          </p>
                        </div>
                        <div>
                          <p className="text-sm font-medium">{t('chains.continueOnFailure')}</p>
                          <p className="text-sm text-muted-foreground">
                            {step.continue_on_failure ? t('common.yes') : t('common.no')}
                          </p>
                        </div>
                        {step.condition && (
                          <div>
                            <p className="text-sm font-medium">{t('chains.condition')}</p>
                            <code className="text-xs bg-muted px-1 rounded">
                              {JSON.stringify(step.condition)}
                            </code>
                          </div>
                        )}
                        {Object.keys(step.extract_variables).length > 0 && (
                          <div className="md:col-span-2">
                            <p className="text-sm font-medium">{t('chains.extractVariables')}</p>
                            <code className="text-xs bg-muted px-1 rounded block mt-1">
                              {JSON.stringify(step.extract_variables, null, 2)}
                            </code>
                          </div>
                        )}
                        {step.headers && Object.keys(step.headers).length > 0 && (
                          <div className="md:col-span-2">
                            <p className="text-sm font-medium">{t('chains.headers')}</p>
                            <code className="text-xs bg-muted px-1 rounded block mt-1 whitespace-pre">
                              {JSON.stringify(step.headers, null, 2)}
                            </code>
                          </div>
                        )}
                        {step.body && (
                          <div className="md:col-span-2">
                            <p className="text-sm font-medium">{t('chains.body')}</p>
                            <code className="text-xs bg-muted px-1 rounded block mt-1 whitespace-pre max-h-32 overflow-auto">
                              {step.body}
                            </code>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="executions">
          {executionsLoading ? (
            <TableSkeleton rows={5} columns={5} />
          ) : executions.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-8">
                <p className="text-muted-foreground">{t('chains.noExecutionsYet')}</p>
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('common.status')}</TableHead>
                    <TableHead>{t('chains.startedAt')}</TableHead>
                    <TableHead>{t('common.duration')}</TableHead>
                    <TableHead>{t('chains.stepsCompleted')}</TableHead>
                    <TableHead className="text-right">{t('common.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {executions.map((execution) => (
                    <TableRow key={execution.id}>
                      <TableCell>{getChainStatusBadge(execution.status)}</TableCell>
                      <TableCell>{formatDateTime(execution.started_at)}</TableCell>
                      <TableCell>{formatDuration(execution.duration_ms)}</TableCell>
                      <TableCell>
                        {execution.completed_steps}/{execution.total_steps}
                        {execution.failed_steps > 0 && (
                          <span className="text-destructive ml-1">
                            ({execution.failed_steps} {t('common.failed').toLowerCase()})
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleViewExecution(execution)}
                          disabled={loadingDetail}
                          title={t('chains.viewDetails')}
                        >
                          {loadingDetail ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Add Step Dialog */}
      <Dialog open={showAddStepDialog} onOpenChange={setShowAddStepDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('chains.addStep')}</DialogTitle>
            <DialogDescription>
              {t('chains.addStepDescription')}
            </DialogDescription>
          </DialogHeader>
          <ChainStepForm
            stepOrder={chain.steps.length + 1}
            onSubmit={handleAddStep}
            onCancel={() => setShowAddStepDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Step Dialog */}
      <Dialog open={!!editingStep} onOpenChange={() => setEditingStep(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('chains.editStep')}</DialogTitle>
            <DialogDescription>
              {t('chains.editStepDescription')}
            </DialogDescription>
          </DialogHeader>
          {editingStep && (
            <ChainStepForm
              step={editingStep}
              stepOrder={editingStep.step_order}
              onSubmit={(data) => handleUpdateStep(editingStep.id, data)}
              onCancel={() => setEditingStep(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Step Confirmation Dialog */}
      <Dialog open={!!deletingStep} onOpenChange={() => setDeletingStep(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('chains.deleteStep')}</DialogTitle>
            <DialogDescription>
              {t('chains.deleteStepConfirm', { name: deletingStep?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingStep(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteStep}
              disabled={actionLoading === deletingStep?.id}
            >
              {actionLoading === deletingStep?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Execution Details Dialog */}
      <Dialog open={!!selectedExecution} onOpenChange={() => setSelectedExecution(null)}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('executions.executionDetails')}</DialogTitle>
          </DialogHeader>
          {selectedExecution && (
            <div className="space-y-6">
              {/* Overview */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">{t('common.status')}</p>
                  {getChainStatusBadge(selectedExecution.status)}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('common.duration')}</p>
                  <p className="font-mono">{formatDuration(selectedExecution.duration_ms)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('executions.started')}</p>
                  <p className="text-sm">{formatDateTime(selectedExecution.started_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('executions.finished')}</p>
                  <p className="text-sm">{selectedExecution.finished_at ? formatDateTime(selectedExecution.finished_at) : '-'}</p>
                </div>
              </div>

              {/* Steps Summary */}
              <div className="grid grid-cols-4 gap-4 p-4 bg-muted rounded-lg">
                <div className="text-center">
                  <p className="text-2xl font-bold">{selectedExecution.total_steps}</p>
                  <p className="text-sm text-muted-foreground">{t('executions.totalSteps')}</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-600">{selectedExecution.completed_steps}</p>
                  <p className="text-sm text-muted-foreground">{t('executions.completedSteps')}</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-red-600">{selectedExecution.failed_steps}</p>
                  <p className="text-sm text-muted-foreground">{t('executions.failedStepsLabel')}</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-500">{selectedExecution.skipped_steps}</p>
                  <p className="text-sm text-muted-foreground">{t('executions.skippedSteps')}</p>
                </div>
              </div>

              {/* Step Executions */}
              <div className="space-y-2">
                <h3 className="font-semibold">{t('chains.stepExecutions')}</h3>
                <div className="space-y-3">
                  {selectedExecution.step_executions
                    .sort((a, b) => a.step_order - b.step_order)
                    .map((stepExec) => (
                    <Card key={stepExec.id} className={stepExec.status === 'failed' ? 'border-destructive' : ''}>
                      <CardHeader className="py-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Badge variant="outline">{stepExec.step_order}</Badge>
                            <div>
                              <CardTitle className="text-base">{stepExec.step_name}</CardTitle>
                              <CardDescription className="text-xs">
                                <Badge variant="secondary" className="mr-2">{stepExec.request_method}</Badge>
                                <span className="truncate">{stepExec.request_url}</span>
                              </CardDescription>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {getStepStatusBadge(stepExec.status)}
                            {stepExec.duration_ms !== null && (
                              <span className="text-sm text-muted-foreground font-mono">
                                {formatDuration(stepExec.duration_ms)}
                              </span>
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      {(stepExec.error_message || stepExec.response_status_code !== null || Object.keys(stepExec.extracted_variables || {}).length > 0) && (
                        <CardContent className="pt-0 border-t">
                          <div className="pt-3 space-y-3">
                            {stepExec.response_status_code !== null && (
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-muted-foreground">{t('executions.statusCode')}:</span>
                                <Badge variant={stepExec.response_status_code >= 200 && stepExec.response_status_code < 300 ? 'success' : 'destructive'}>
                                  {stepExec.response_status_code}
                                </Badge>
                              </div>
                            )}
                            {stepExec.condition_details && (
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-muted-foreground">{t('chains.conditionResult')}:</span>
                                <Badge variant={stepExec.condition_met ? 'success' : 'secondary'}>
                                  {stepExec.condition_met ? t('common.yes') : t('common.no')}
                                </Badge>
                                <span className="text-xs text-muted-foreground">{stepExec.condition_details}</span>
                              </div>
                            )}
                            {Object.keys(stepExec.extracted_variables || {}).length > 0 && (
                              <div>
                                <p className="text-sm text-muted-foreground mb-1">{t('chains.extractedVariables')}:</p>
                                <div className="bg-green-500/10 border border-green-500/20 rounded p-2 space-y-1">
                                  {Object.entries(stepExec.extracted_variables).map(([key, value]) => (
                                    <div key={key} className="flex gap-2 text-xs font-mono">
                                      <span className="text-green-600 dark:text-green-400 font-semibold">{key}:</span>
                                      <span className="text-foreground break-all">{String(value).slice(0, 200)}{String(value).length > 200 && '...'}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {stepExec.error_message && (
                              <div className="rounded-md bg-destructive/10 p-3">
                                <p className="text-sm font-medium text-destructive">{t('common.error')}</p>
                                {stepExec.error_type && (
                                  <Badge variant="destructive" className="mb-1 text-xs">{stepExec.error_type}</Badge>
                                )}
                                <p className="text-sm text-destructive">{stepExec.error_message}</p>
                              </div>
                            )}
                            {stepExec.response_body && (
                              <div>
                                <p className="text-sm text-muted-foreground mb-1">{t('executions.response')}:</p>
                                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-[200px] whitespace-pre-wrap break-all">
                                  {stepExec.response_body.slice(0, 2000)}
                                  {stepExec.response_body.length > 2000 && '...'}
                                </pre>
                              </div>
                            )}
                          </div>
                        </CardContent>
                      )}
                    </Card>
                  ))}
                </div>
              </div>

              {/* Error */}
              {selectedExecution.error_message && (
                <div className="space-y-2">
                  <h3 className="font-semibold text-destructive">{t('common.error')}</h3>
                  <div className="rounded-md bg-destructive/10 p-4">
                    <p className="text-sm text-destructive">{selectedExecution.error_message}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
