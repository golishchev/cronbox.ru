import { useEffect, useState } from 'react'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getCronTasks, deleteCronTask, pauseCronTask, resumeCronTask, runCronTask } from '@/api/cronTasks'
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
} from 'lucide-react'
import { CronTaskForm } from '@/components/cron/CronTaskForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { getErrorMessage } from '@/api/client'
import type { CronTask } from '@/types'
import cronstrue from 'cronstrue'

interface CronTasksPageProps {
  onNavigate: (route: string) => void
}

export function CronTasksPage({ onNavigate: _ }: CronTasksPageProps) {
  const { currentWorkspace } = useWorkspaceStore()
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
        title: 'Error loading tasks',
        description: getErrorMessage(err),
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
          title: 'Task resumed',
          description: `"${task.name}" is now active`,
          variant: 'success',
        })
      } else {
        await pauseCronTask(currentWorkspace.id, task.id)
        toast({
          title: 'Task paused',
          description: `"${task.name}" has been paused`,
        })
      }
      await loadTasks()
    } catch (err) {
      toast({
        title: 'Action failed',
        description: getErrorMessage(err),
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
        title: 'Task triggered',
        description: `"${task.name}" has been queued for execution`,
        variant: 'success',
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: 'Failed to run task',
        description: getErrorMessage(err),
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
        title: 'Task deleted',
        description: `"${taskName}" has been deleted`,
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: 'Failed to delete task',
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (task: CronTask) => {
    if (!task.is_active) {
      return <Badge variant="secondary">Inactive</Badge>
    }
    if (task.is_paused) {
      return <Badge variant="warning">Paused</Badge>
    }
    if (task.last_status === 'failed') {
      return <Badge variant="destructive">Failed</Badge>
    }
    if (task.last_status === 'success') {
      return <Badge variant="success">Active</Badge>
    }
    return <Badge variant="secondary">Active</Badge>
  }

  const formatCronExpression = (schedule: string) => {
    try {
      return cronstrue.toString(schedule, { use24HourTimeFormat: true })
    } catch {
      return schedule
    }
  }

  const formatNextRun = (nextRunAt: string | null) => {
    if (!nextRunAt) return 'Not scheduled'
    const date = new Date(nextRunAt)
    return date.toLocaleString()
  }

  if (!currentWorkspace) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <p className="text-muted-foreground">Please select a workspace</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cron Tasks</h1>
          <p className="text-muted-foreground">
            Manage recurring HTTP requests on a schedule
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Task
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : tasks.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Clock className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">No cron tasks yet</h2>
          <p className="text-muted-foreground">Create your first scheduled task</p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Task
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Schedule</TableHead>
                <TableHead>Next Run</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
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
                        title="Edit"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingTask(task)}
                        title="Delete"
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
            <DialogTitle>Create Cron Task</DialogTitle>
            <DialogDescription>
              Create a new recurring HTTP request on a schedule
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
            <DialogTitle>Edit Cron Task</DialogTitle>
            <DialogDescription>
              Update the task configuration
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
            <DialogTitle>Delete Task</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deletingTask?.name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingTask(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading === deletingTask?.id}
            >
              {actionLoading === deletingTask?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
