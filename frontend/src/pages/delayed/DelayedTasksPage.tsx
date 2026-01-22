import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getDelayedTasks, cancelDelayedTask, rescheduleDelayedTask, copyDelayedTask } from '@/api/delayedTasks'
import { getLatestExecution } from '@/api/executions'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Calendar,
  Plus,
  Trash2,
  Loader2,
  XCircle,
  CheckCircle,
  Clock,
  AlertCircle,
  Edit,
  RotateCcw,
  Copy,
  Globe,
  Radio,
  Plug,
  Eye,
  RefreshCw,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DelayedTaskForm } from '@/components/delayed/DelayedTaskForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { DelayedTask, PaginationMeta, TaskStatus, ExecutionDetail } from '@/types'

interface DelayedTasksPageProps {
  onNavigate: (route: string) => void
}

export function DelayedTasksPage({ onNavigate: _ }: DelayedTasksPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
  const [tasks, setTasks] = useState<DelayedTask[]>([])
  const [pagination, setPagination] = useState<PaginationMeta | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingTask, setEditingTask] = useState<DelayedTask | null>(null)
  const [cancelingTask, setCancelingTask] = useState<DelayedTask | null>(null)
  const [reschedulingTask, setReschedulingTask] = useState<DelayedTask | null>(null)
  const [rescheduleDateTime, setRescheduleDateTime] = useState('')
  const [copyingTask, setCopyingTask] = useState<DelayedTask | null>(null)
  const [copyDateTime, setCopyDateTime] = useState('')
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('pending')
  const [selectedExecution, setSelectedExecution] = useState<ExecutionDetail | null>(null)
  const [loadingExecution, setLoadingExecution] = useState(false)

  const loadTasks = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const response = await getDelayedTasks(currentWorkspace.id, {
        status: statusFilter !== 'all' ? statusFilter : undefined,
      })
      setTasks(response.tasks)
      setPagination(response.pagination)
    } catch (err) {
      toast({
        title: t('delayedTasks.errorLoading'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace, statusFilter])

  const handleCancel = async () => {
    if (!currentWorkspace || !cancelingTask) return
    const taskName = cancelingTask.name || t('executions.unnamedTask')
    setActionLoading(cancelingTask.id)
    try {
      await cancelDelayedTask(currentWorkspace.id, cancelingTask.id)
      setCancelingTask(null)
      toast({
        title: t('delayedTasks.taskCancelled'),
        description: t('delayedTasks.taskCancelledDescription', { name: taskName }),
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: t('delayedTasks.failedToCancelTask'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleReschedule = async () => {
    if (!currentWorkspace || !reschedulingTask || !rescheduleDateTime) return
    const taskName = reschedulingTask.name || t('executions.unnamedTask')
    setActionLoading(reschedulingTask.id)
    try {
      await rescheduleDelayedTask(currentWorkspace.id, reschedulingTask.id, {
        execute_at: new Date(rescheduleDateTime).toISOString(),
      })
      setReschedulingTask(null)
      setRescheduleDateTime('')
      toast({
        title: t('delayedTasks.taskRescheduled'),
        description: t('delayedTasks.taskRescheduledDescription', { name: taskName }),
        variant: 'success',
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: t('delayedTasks.failedToRescheduleTask'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const openRescheduleDialog = (task: DelayedTask) => {
    // Set default datetime to 1 hour from now
    const defaultTime = new Date()
    defaultTime.setHours(defaultTime.getHours() + 1)
    defaultTime.setMinutes(0, 0, 0)
    setRescheduleDateTime(defaultTime.toISOString().slice(0, 16))
    setReschedulingTask(task)
  }

  const handleCopy = async () => {
    if (!currentWorkspace || !copyingTask || !copyDateTime) return
    const taskName = copyingTask.name || t('executions.unnamedTask')
    setActionLoading(copyingTask.id)
    try {
      const newTask = await copyDelayedTask(currentWorkspace.id, copyingTask.id, {
        execute_at: new Date(copyDateTime).toISOString(),
      })
      setCopyingTask(null)
      setCopyDateTime('')
      toast({
        title: t('delayedTasks.taskCopied'),
        description: t('delayedTasks.taskCopiedDescription', { name: newTask.name || taskName }),
        variant: 'success',
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: t('delayedTasks.failedToCopyTask'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const openCopyDialog = (task: DelayedTask) => {
    // Set default datetime to 1 hour from now
    const defaultTime = new Date()
    defaultTime.setHours(defaultTime.getHours() + 1)
    defaultTime.setMinutes(0, 0, 0)
    setCopyDateTime(defaultTime.toISOString().slice(0, 16))
    setCopyingTask(task)
  }

  const getStatusBadge = (status: TaskStatus) => {
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

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  const formatTimeUntil = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = date.getTime() - now.getTime()

    if (diffMs <= 0) return t('delayedTasks.now')

    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 0) return t('delayedTasks.inDaysHours', { days: diffDays, hours: diffHours % 24 })
    if (diffHours > 0) return t('delayedTasks.inHoursMinutes', { hours: diffHours, minutes: diffMins % 60 })
    return t('delayedTasks.inMinutes', { minutes: diffMins })
  }

  const handleViewLastExecution = async (task: DelayedTask) => {
    if (!currentWorkspace) return
    setLoadingExecution(true)
    try {
      const execution = await getLatestExecution(currentWorkspace.id, task.id, 'delayed')
      if (!execution) {
        toast({
          title: t('delayedTasks.noExecutions'),
          description: t('delayedTasks.noExecutionsDescription'),
          variant: 'default',
        })
        return
      }
      setSelectedExecution(execution)
    } catch (err) {
      toast({
        title: t('delayedTasks.failedToLoadExecution'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setLoadingExecution(false)
    }
  }

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const getStatusCodeBadge = (code: number | null) => {
    if (code === null) return <span className="text-muted-foreground">-</span>
    if (code >= 200 && code < 300) {
      return <Badge variant="success">{code}</Badge>
    }
    if (code >= 400 && code < 500) {
      return <Badge variant="warning">{code}</Badge>
    }
    if (code >= 500) {
      return <Badge variant="destructive">{code}</Badge>
    }
    return <Badge variant="secondary">{code}</Badge>
  }

  const getExecutionStatusBadge = (status: string) => {
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
            <RefreshCw className="h-3 w-3 animate-spin" />
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
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('delayedTasks.title')}</h1>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 sm:mr-2" />
          <span className="hidden sm:inline">{t('delayedTasks.scheduleTask')}</span>
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{t('common.status')}:</span>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pending">{t('common.pending')}</SelectItem>
              <SelectItem value="running">{t('common.running')}</SelectItem>
              <SelectItem value="success">{t('common.success')}</SelectItem>
              <SelectItem value="failed">{t('common.failed')}</SelectItem>
              <SelectItem value="cancelled">{t('common.cancelled')}</SelectItem>
              <SelectItem value="all">{t('common.all')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : tasks.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Calendar className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('delayedTasks.noTasksYet')}</h2>
          <p className="text-muted-foreground text-center max-w-md">
            {statusFilter !== 'all'
              ? t('delayedTasks.noTasksFound', { status: t(`common.${statusFilter}`) })
              : t('delayedTasks.scheduleFirstTask')}
          </p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('delayedTasks.scheduleTask')}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('delayedTasks.nameUrl')}</TableHead>
                <TableHead>{t('delayedTasks.executeAt')}</TableHead>
                <TableHead>{t('delayedTasks.method')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell>
                    <div>
                      {task.name && (
                        <p className="font-medium">{task.name}</p>
                      )}
                      <p className={`text-sm truncate max-w-[300px] flex items-center gap-1 ${task.name ? 'text-muted-foreground' : 'font-medium'}`}>
                        {task.protocol_type === 'http' && (
                          <>
                            <Globe className="h-3 w-3 flex-shrink-0" />
                            {task.url}
                          </>
                        )}
                        {task.protocol_type === 'icmp' && (
                          <>
                            <Radio className="h-3 w-3 flex-shrink-0" />
                            {task.host}
                          </>
                        )}
                        {task.protocol_type === 'tcp' && (
                          <>
                            <Plug className="h-3 w-3 flex-shrink-0" />
                            {task.host}:{task.port}
                          </>
                        )}
                      </p>
                      {task.tags.length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {task.tags.slice(0, 3).map((tag) => (
                            <Badge key={tag} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {task.tags.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{task.tags.length - 3}
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="text-sm">{formatDateTime(task.execute_at)}</p>
                      {task.status === 'pending' && (
                        <p className="text-xs text-muted-foreground">
                          {formatTimeUntil(task.execute_at)}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <code className="text-sm bg-muted px-1 rounded">
                      {task.protocol_type === 'http' ? task.method : task.protocol_type.toUpperCase()}
                    </code>
                  </TableCell>
                  <TableCell>{getStatusBadge(task.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {['success', 'failed', 'cancelled'].includes(task.status) && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleViewLastExecution(task)}
                          disabled={loadingExecution}
                          title={t('delayedTasks.viewExecution')}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      )}
                      {task.status === 'pending' && (
                        <>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setEditingTask(task)}
                            disabled={actionLoading === task.id}
                            title={t('common.edit')}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setCancelingTask(task)}
                            disabled={actionLoading === task.id}
                            title={t('common.cancel')}
                          >
                            {actionLoading === task.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </>
                      )}
                      {['success', 'failed', 'cancelled'].includes(task.status) && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openRescheduleDialog(task)}
                          disabled={actionLoading === task.id}
                          title={t('delayedTasks.reschedule')}
                        >
                          {actionLoading === task.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <RotateCcw className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openCopyDialog(task)}
                        disabled={actionLoading === task.id}
                        title={t('delayedTasks.copyTask')}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {pagination && pagination.total_pages > 1 && (
        <div className="flex justify-center gap-2">
          <span className="text-sm text-muted-foreground">
            {t('executions.page', { current: pagination.page, total: pagination.total_pages })} ({pagination.total} {t('common.total')})
          </span>
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('delayedTasks.createDelayedTask')}</DialogTitle>
            <DialogDescription>
              {t('delayedTasks.createDescription')}
            </DialogDescription>
          </DialogHeader>
          <DelayedTaskForm
            workspaceId={currentWorkspace.id}
            onSuccess={() => {
              setShowCreateDialog(false)
              loadTasks()
            }}
            onCancel={() => setShowCreateDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingTask} onOpenChange={(open) => !open && setEditingTask(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('delayedTasks.editDelayedTask')}</DialogTitle>
            <DialogDescription>
              {t('delayedTasks.editDescription')}
            </DialogDescription>
          </DialogHeader>
          {editingTask && (
            <DelayedTaskForm
              workspaceId={currentWorkspace.id}
              task={editingTask}
              onSuccess={() => {
                setEditingTask(null)
                loadTasks()
              }}
              onCancel={() => setEditingTask(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Cancel Confirmation Dialog */}
      <Dialog open={!!cancelingTask} onOpenChange={() => setCancelingTask(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('delayedTasks.cancelTask')}</DialogTitle>
            <DialogDescription>
              {t('delayedTasks.cancelConfirm')}
              {cancelingTask?.name && (
                <span className="block mt-2 font-medium">
                  "{cancelingTask.name}"
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelingTask(null)}>
              {t('delayedTasks.keepTask')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleCancel}
              disabled={actionLoading === cancelingTask?.id}
            >
              {actionLoading === cancelingTask?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {t('delayedTasks.cancelTask')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reschedule Dialog */}
      <Dialog open={!!reschedulingTask} onOpenChange={(open) => {
        if (!open) {
          setReschedulingTask(null)
          setRescheduleDateTime('')
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('delayedTasks.rescheduleTask')}</DialogTitle>
            <DialogDescription>
              {t('delayedTasks.rescheduleDescription')}
              {reschedulingTask?.name && (
                <span className="block mt-2 font-medium">
                  "{reschedulingTask.name}"
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="reschedule-datetime">{t('delayedTasks.newExecuteAt')}</Label>
              <Input
                id="reschedule-datetime"
                type="datetime-local"
                value={rescheduleDateTime}
                onChange={(e) => setRescheduleDateTime(e.target.value)}
                min={new Date().toISOString().slice(0, 16)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setReschedulingTask(null)
              setRescheduleDateTime('')
            }}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleReschedule}
              disabled={actionLoading === reschedulingTask?.id || !rescheduleDateTime}
            >
              {actionLoading === reschedulingTask?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {t('delayedTasks.reschedule')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Copy Dialog */}
      <Dialog open={!!copyingTask} onOpenChange={(open) => {
        if (!open) {
          setCopyingTask(null)
          setCopyDateTime('')
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('delayedTasks.copyTask')}</DialogTitle>
            <DialogDescription>
              {t('delayedTasks.copyDescription')}
              {copyingTask?.name && (
                <span className="block mt-2 font-medium">
                  "{copyingTask.name}"
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="copy-datetime">{t('delayedTasks.newExecuteAt')}</Label>
              <Input
                id="copy-datetime"
                type="datetime-local"
                value={copyDateTime}
                onChange={(e) => setCopyDateTime(e.target.value)}
                min={new Date().toISOString().slice(0, 16)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setCopyingTask(null)
              setCopyDateTime('')
            }}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleCopy}
              disabled={actionLoading === copyingTask?.id || !copyDateTime}
            >
              {actionLoading === copyingTask?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {t('delayedTasks.copy')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Last Execution Details Dialog */}
      <Dialog open={!!selectedExecution} onOpenChange={() => setSelectedExecution(null)}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('delayedTasks.executionDetails')}</DialogTitle>
          </DialogHeader>
          {loadingExecution ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : selectedExecution && (
            <div className="space-y-6">
              {/* Overview */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">{t('executions.task')}</p>
                  <p className="font-medium">{selectedExecution.task_name || t('executions.unnamedTask')}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('common.status')}</p>
                  {getExecutionStatusBadge(selectedExecution.status)}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('common.duration')}</p>
                  <p className="font-mono">{formatDuration(selectedExecution.duration_ms)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('executions.started')}</p>
                  <p>{formatDateTime(selectedExecution.started_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('executions.finished')}</p>
                  <p>{selectedExecution.finished_at ? formatDateTime(selectedExecution.finished_at) : '-'}</p>
                </div>
              </div>

              {/* Request */}
              {(selectedExecution.protocol_type === 'http' || !selectedExecution.protocol_type) && selectedExecution.request_url && (
                <div className="space-y-2">
                  <h3 className="font-semibold">{t('executions.request')}</h3>
                  <div className="rounded-md bg-muted p-4 space-y-2">
                    <div className="flex gap-2">
                      <Badge variant="outline">{selectedExecution.request_method}</Badge>
                      <code className="text-sm break-all">{selectedExecution.request_url}</code>
                    </div>
                    {selectedExecution.request_headers && Object.keys(selectedExecution.request_headers).length > 0 && (
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">{t('executions.headers')}:</p>
                        <pre className="text-xs bg-background p-2 rounded overflow-x-auto whitespace-pre-wrap break-all">
                          {JSON.stringify(selectedExecution.request_headers, null, 2)}
                        </pre>
                      </div>
                    )}
                    {selectedExecution.request_body && (
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">{t('executions.body')}:</p>
                        <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-[200px] whitespace-pre-wrap break-all">
                          {selectedExecution.request_body}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ICMP target */}
              {selectedExecution.protocol_type === 'icmp' && (
                <div className="space-y-2">
                  <h3 className="font-semibold">{t('executionResults.target')}</h3>
                  <div className="rounded-md bg-muted p-4">
                    <div className="flex gap-2 items-center">
                      <Radio className="h-4 w-4 text-muted-foreground" />
                      <Badge variant="outline">ICMP</Badge>
                      <code className="text-sm">{selectedExecution.target_host}</code>
                    </div>
                  </div>
                </div>
              )}

              {/* TCP target */}
              {selectedExecution.protocol_type === 'tcp' && (
                <div className="space-y-2">
                  <h3 className="font-semibold">{t('executionResults.target')}</h3>
                  <div className="rounded-md bg-muted p-4">
                    <div className="flex gap-2 items-center">
                      <Plug className="h-4 w-4 text-muted-foreground" />
                      <Badge variant="outline">TCP</Badge>
                      <code className="text-sm">{selectedExecution.target_host}:{selectedExecution.target_port}</code>
                    </div>
                  </div>
                </div>
              )}

              {/* Response/Results */}
              <div className="space-y-2">
                <h3 className="font-semibold">
                  {selectedExecution.protocol_type === 'http' || !selectedExecution.protocol_type
                    ? t('executions.response')
                    : t('executionResults.results')}
                </h3>
                <div className="rounded-md bg-muted p-4 space-y-2">
                  {/* HTTP Response */}
                  {(selectedExecution.protocol_type === 'http' || !selectedExecution.protocol_type) && (
                    <>
                      <div className="flex gap-4">
                        <div>
                          <p className="text-sm text-muted-foreground">{t('executions.statusCode')}</p>
                          {getStatusCodeBadge(selectedExecution.response_status_code)}
                        </div>
                        {selectedExecution.response_size_bytes && (
                          <div>
                            <p className="text-sm text-muted-foreground">{t('executions.size')}</p>
                            <p className="text-sm">{(selectedExecution.response_size_bytes / 1024).toFixed(2)} KB</p>
                          </div>
                        )}
                      </div>
                      {selectedExecution.response_headers && Object.keys(selectedExecution.response_headers).length > 0 && (
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">{t('executions.headers')}:</p>
                          <pre className="text-xs bg-background p-2 rounded overflow-x-auto whitespace-pre-wrap break-all">
                            {JSON.stringify(selectedExecution.response_headers, null, 2)}
                          </pre>
                        </div>
                      )}
                      {selectedExecution.response_body && (
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">{t('executions.body')}:</p>
                          <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-[300px] whitespace-pre-wrap break-all">
                            {selectedExecution.response_body}
                          </pre>
                        </div>
                      )}
                    </>
                  )}
                  {/* ICMP Results */}
                  {selectedExecution.protocol_type === 'icmp' && (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executionResults.packetsSent')}</p>
                        <p className="text-lg font-semibold">{selectedExecution.icmp_packets_sent ?? '-'}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executionResults.packetsReceived')}</p>
                        <p className="text-lg font-semibold">{selectedExecution.icmp_packets_received ?? '-'}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executionResults.packetLoss')}</p>
                        <p className={`text-lg font-semibold ${
                          selectedExecution.icmp_packet_loss === 0 ? 'text-green-600' :
                          selectedExecution.icmp_packet_loss !== null && selectedExecution.icmp_packet_loss < 50 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {selectedExecution.icmp_packet_loss !== null ? `${selectedExecution.icmp_packet_loss.toFixed(1)}%` : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executionResults.minRtt')}</p>
                        <p className="text-lg font-semibold">{selectedExecution.icmp_min_rtt !== null ? `${selectedExecution.icmp_min_rtt.toFixed(2)}ms` : '-'}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executionResults.avgRtt')}</p>
                        <p className="text-lg font-semibold">{selectedExecution.icmp_avg_rtt !== null ? `${selectedExecution.icmp_avg_rtt.toFixed(2)}ms` : '-'}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executionResults.maxRtt')}</p>
                        <p className="text-lg font-semibold">{selectedExecution.icmp_max_rtt !== null ? `${selectedExecution.icmp_max_rtt.toFixed(2)}ms` : '-'}</p>
                      </div>
                    </div>
                  )}
                  {/* TCP Results */}
                  {selectedExecution.protocol_type === 'tcp' && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executionResults.connectionTime')}</p>
                        <p className="text-lg font-semibold text-green-600">
                          {selectedExecution.tcp_connection_time !== null ? `${selectedExecution.tcp_connection_time.toFixed(2)}ms` : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executionResults.portStatus')}</p>
                        <Badge variant={selectedExecution.status === 'success' ? 'success' : 'destructive'}>
                          {selectedExecution.status === 'success' ? t('executionResults.portOpen') : t('executionResults.portClosed')}
                        </Badge>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Error */}
              {selectedExecution.error_message && (
                <div className="space-y-2">
                  <h3 className="font-semibold text-destructive">{t('common.error')}</h3>
                  <div className="rounded-md bg-destructive/10 p-4">
                    {selectedExecution.error_type && (
                      <Badge variant="destructive" className="mb-2">
                        {selectedExecution.error_type}
                      </Badge>
                    )}
                    <p className="text-sm text-destructive">{translateApiError(selectedExecution.error_message, t)}</p>
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
