import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getDelayedTasks, cancelDelayedTask, rescheduleDelayedTask, copyDelayedTask } from '@/api/delayedTasks'
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
  Pencil,
  RotateCcw,
  Copy,
  Globe,
  Radio,
  Plug,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DelayedTaskForm } from '@/components/delayed/DelayedTaskForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { DelayedTask, PaginationMeta, TaskStatus } from '@/types'

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
                      {task.status === 'pending' && (
                        <>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setEditingTask(task)}
                            disabled={actionLoading === task.id}
                            title={t('common.edit')}
                          >
                            <Pencil className="h-4 w-4" />
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
    </div>
  )
}
