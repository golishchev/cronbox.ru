import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getCronTasks, deleteCronTask, pauseCronTask, resumeCronTask, runCronTask, copyCronTask } from '@/api/cronTasks'
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
  Clock,
  Plus,
  Play,
  Pause,
  Trash2,
  Edit,
  Loader2,
  Copy,
} from 'lucide-react'
import { CronTaskForm } from '@/components/cron/CronTaskForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { CronTask } from '@/types'
import cronstrue from 'cronstrue/i18n'
import i18n from 'i18next'

interface CronTasksPageProps {
  onNavigate: (route: string) => void
}

export function CronTasksPage({ onNavigate: _ }: CronTasksPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
  const [tasks, setTasks] = useState<CronTask[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingTask, setEditingTask] = useState<CronTask | null>(null)
  const [deletingTask, setDeletingTask] = useState<CronTask | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const loadTasks = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const response = await getCronTasks(currentWorkspace.id)
      setTasks(response.tasks)
    } catch (err) {
      toast({
        title: t('cronTasks.errorLoading'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
  }, [currentWorkspace])

  const handlePauseResume = async (task: CronTask) => {
    if (!currentWorkspace) return
    setActionLoading(task.id)
    try {
      if (task.is_paused) {
        await resumeCronTask(currentWorkspace.id, task.id)
        toast({
          title: t('cronTasks.taskResumed'),
          description: t('cronTasks.taskResumedDescription', { name: task.name }),
          variant: 'success',
        })
      } else {
        await pauseCronTask(currentWorkspace.id, task.id)
        toast({
          title: t('cronTasks.taskPaused'),
          description: t('cronTasks.taskPausedDescription', { name: task.name }),
        })
      }
      await loadTasks()
    } catch (err) {
      toast({
        title: t('cronTasks.actionFailed'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleRun = async (task: CronTask) => {
    if (!currentWorkspace) return
    setActionLoading(task.id)
    try {
      await runCronTask(currentWorkspace.id, task.id)
      toast({
        title: t('cronTasks.taskTriggered'),
        description: t('cronTasks.taskTriggeredDescription', { name: task.name }),
        variant: 'success',
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: t('cronTasks.failedToRunTask'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async () => {
    if (!currentWorkspace || !deletingTask) return
    const taskName = deletingTask.name
    setActionLoading(deletingTask.id)
    try {
      await deleteCronTask(currentWorkspace.id, deletingTask.id)
      setDeletingTask(null)
      toast({
        title: t('cronTasks.taskDeleted'),
        description: t('cronTasks.taskDeletedDescription', { name: taskName }),
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: t('cronTasks.failedToDeleteTask'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCopy = async (task: CronTask) => {
    if (!currentWorkspace) return
    setActionLoading(task.id)
    try {
      const newTask = await copyCronTask(currentWorkspace.id, task.id)
      toast({
        title: t('cronTasks.taskCopied'),
        description: t('cronTasks.taskCopiedDescription', { name: newTask.name }),
        variant: 'success',
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: t('cronTasks.failedToCopyTask'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (task: CronTask) => {
    if (!task.is_active) {
      return <Badge variant="secondary">{t('common.inactive')}</Badge>
    }
    if (task.is_paused) {
      return <Badge variant="warning">{t('cronTasks.paused')}</Badge>
    }
    if (task.last_status === 'failed') {
      return <Badge variant="destructive">{t('common.failed')}</Badge>
    }
    if (task.last_status === 'success') {
      return <Badge variant="success">{t('common.active')}</Badge>
    }
    return <Badge variant="secondary">{t('common.active')}</Badge>
  }

  const formatCronExpression = (schedule: string) => {
    try {
      const locale = i18n.language === 'ru' ? 'ru' : 'en'
      return cronstrue.toString(schedule, { use24HourTimeFormat: true, locale })
    } catch {
      return schedule
    }
  }

  const formatNextRun = (nextRunAt: string | null) => {
    if (!nextRunAt) return t('cronTasks.notScheduled')
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('cronTasks.title')}</h1>
          <p className="text-muted-foreground">
            {t('cronTasks.subtitle')}
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t('cronTasks.createTask')}
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : tasks.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Clock className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('cronTasks.noTasksYet')}</h2>
          <p className="text-muted-foreground">{t('cronTasks.createFirstTask')}</p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('cronTasks.createTask')}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('common.name')}</TableHead>
                <TableHead>{t('cronTasks.schedule')}</TableHead>
                <TableHead>{t('cronTasks.nextRun')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{task.name}</p>
                      <p className="text-sm text-muted-foreground truncate max-w-[300px]">
                        {task.url}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <code className="text-sm bg-muted px-1 rounded">{task.schedule}</code>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatCronExpression(task.schedule)}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {formatNextRun(task.next_run_at)}
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(task)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRun(task)}
                        disabled={actionLoading === task.id || !task.is_active}
                        title="Run now"
                      >
                        {actionLoading === task.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handlePauseResume(task)}
                        disabled={actionLoading === task.id || !task.is_active}
                        title={task.is_paused ? 'Resume' : 'Pause'}
                      >
                        {task.is_paused ? (
                          <Play className="h-4 w-4" />
                        ) : (
                          <Pause className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditingTask(task)}
                        title={t('common.edit')}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCopy(task)}
                        disabled={actionLoading === task.id}
                        title={t('cronTasks.copyTask')}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingTask(task)}
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
            <DialogTitle>{t('cronTasks.createCronTask')}</DialogTitle>
            <DialogDescription>
              {t('cronTasks.createDescription')}
            </DialogDescription>
          </DialogHeader>
          <CronTaskForm
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
      <Dialog open={!!editingTask} onOpenChange={() => setEditingTask(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('cronTasks.editCronTask')}</DialogTitle>
            <DialogDescription>
              {t('cronTasks.editDescription')}
            </DialogDescription>
          </DialogHeader>
          {editingTask && (
            <CronTaskForm
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingTask} onOpenChange={() => setDeletingTask(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('cronTasks.deleteTask')}</DialogTitle>
            <DialogDescription>
              {t('cronTasks.deleteConfirm', { name: deletingTask?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingTask(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading === deletingTask?.id}
            >
              {actionLoading === deletingTask?.id ? (
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
