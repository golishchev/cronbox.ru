import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getCronTasks, deleteCronTask, pauseCronTask, resumeCronTask, runCronTask, copyCronTask } from '@/api/cronTasks'
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
  Clock,
  Plus,
  Play,
  Pause,
  Trash2,
  Edit,
  Loader2,
  Copy,
  Globe,
  Radio,
  Plug,
  Rocket,
  Eye,
  CheckCircle,
  XCircle,
  RefreshCw,
} from 'lucide-react'
import { CronTaskForm } from '@/components/cron/CronTaskForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { CronTask, ExecutionDetail } from '@/types'
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
  const [selectedExecution, setSelectedExecution] = useState<ExecutionDetail | null>(null)
  const [loadingExecution, setLoadingExecution] = useState(false)

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleViewLastExecution = async (task: CronTask) => {
    if (!currentWorkspace) return
    setLoadingExecution(true)
    try {
      const execution = await getLatestExecution(currentWorkspace.id, task.id, 'cron')
      if (!execution) {
        toast({
          title: t('cronTasks.noExecutions'),
          description: t('cronTasks.noExecutionsDescription'),
          variant: 'default',
        })
        return
      }
      setSelectedExecution(execution)
    } catch (err) {
      toast({
        title: t('cronTasks.failedToLoadExecution'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setLoadingExecution(false)
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

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString()
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
          <h1 className="text-3xl font-bold tracking-tight">{t('cronTasks.title')}</h1>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 sm:mr-2" />
          <span className="hidden sm:inline">{t('cronTasks.createTask')}</span>
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : tasks.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Clock className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('cronTasks.noTasksYet')}</h2>
          <p className="text-muted-foreground text-center max-w-md">{t('cronTasks.createFirstTask')}</p>
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
                      <p className="text-sm text-muted-foreground truncate max-w-[300px] flex items-center gap-1">
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
                        onClick={() => handleViewLastExecution(task)}
                        disabled={loadingExecution}
                        title={t('cronTasks.viewLastExecution')}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
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
                          <Rocket className="h-4 w-4" />
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

      {/* Last Execution Details Dialog */}
      <Dialog open={!!selectedExecution} onOpenChange={() => setSelectedExecution(null)}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('cronTasks.lastExecutionDetails')}</DialogTitle>
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
                  <p className="font-medium">{selectedExecution.task_name}</p>
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
