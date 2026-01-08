import { useEffect, useState } from 'react'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getDelayedTasks, cancelDelayedTask } from '@/api/delayedTasks'
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
} from 'lucide-react'
import { DelayedTaskForm } from '@/components/delayed/DelayedTaskForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { getErrorMessage } from '@/api/client'
import type { DelayedTask, PaginationMeta, TaskStatus } from '@/types'

interface DelayedTasksPageProps {
  onNavigate: (route: string) => void
}

export function DelayedTasksPage({ onNavigate: _ }: DelayedTasksPageProps) {
  const { currentWorkspace } = useWorkspaceStore()
  const [tasks, setTasks] = useState<DelayedTask[]>([])
  const [pagination, setPagination] = useState<PaginationMeta | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [cancelingTask, setCancelingTask] = useState<DelayedTask | null>(null)
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
  }, [currentWorkspace, statusFilter])

  const handleCancel = async () => {
    if (!currentWorkspace || !cancelingTask) return
    const taskName = cancelingTask.name || 'Task'
    setActionLoading(cancelingTask.id)
    try {
      await cancelDelayedTask(currentWorkspace.id, cancelingTask.id)
      setCancelingTask(null)
      toast({
        title: 'Task cancelled',
        description: `"${taskName}" has been cancelled`,
      })
      await loadTasks()
    } catch (err) {
      toast({
        title: 'Failed to cancel task',
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (status: TaskStatus) => {
    switch (status) {
      case 'pending':
        return (
          <Badge variant="secondary" className="gap-1">
            <Clock className="h-3 w-3" />
            Pending
          </Badge>
        )
      case 'running':
        return (
          <Badge variant="default" className="gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Running
          </Badge>
        )
      case 'success':
        return (
          <Badge variant="success" className="gap-1">
            <CheckCircle className="h-3 w-3" />
            Success
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        )
      case 'cancelled':
        return (
          <Badge variant="outline" className="gap-1">
            <AlertCircle className="h-3 w-3" />
            Cancelled
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

    if (diffMs <= 0) return 'Now'

    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 0) return `in ${diffDays}d ${diffHours % 24}h`
    if (diffHours > 0) return `in ${diffHours}h ${diffMins % 60}m`
    return `in ${diffMins}m`
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
          <h1 className="text-3xl font-bold tracking-tight">Delayed Tasks</h1>
          <p className="text-muted-foreground">
            Schedule one-time HTTP requests for future execution
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Schedule Task
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
              <SelectItem value="all">All</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : tasks.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Calendar className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">No delayed tasks</h2>
          <p className="text-muted-foreground">
            {statusFilter !== 'all'
              ? `No ${statusFilter} tasks found`
              : 'Schedule your first delayed task'}
          </p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Schedule Task
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name / URL</TableHead>
                <TableHead>Execute At</TableHead>
                <TableHead>Method</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
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
                      <p className={`text-sm truncate max-w-[300px] ${task.name ? 'text-muted-foreground' : 'font-medium'}`}>
                        {task.url}
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
                      {task.method}
                    </code>
                  </TableCell>
                  <TableCell>{getStatusBadge(task.status)}</TableCell>
                  <TableCell className="text-right">
                    {task.status === 'pending' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setCancelingTask(task)}
                        disabled={actionLoading === task.id}
                        title="Cancel"
                      >
                        {actionLoading === task.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    )}
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
            Page {pagination.page} of {pagination.total_pages} ({pagination.total} total)
          </span>
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Schedule Delayed Task</DialogTitle>
            <DialogDescription>
              Create a one-time HTTP request to be executed at a specific time
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

      {/* Cancel Confirmation Dialog */}
      <Dialog open={!!cancelingTask} onOpenChange={() => setCancelingTask(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Task</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel this task? It will not be executed.
              {cancelingTask?.name && (
                <span className="block mt-2 font-medium">
                  "{cancelingTask.name}"
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelingTask(null)}>
              Keep Task
            </Button>
            <Button
              variant="destructive"
              onClick={handleCancel}
              disabled={actionLoading === cancelingTask?.id}
            >
              {actionLoading === cancelingTask?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Cancel Task
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
