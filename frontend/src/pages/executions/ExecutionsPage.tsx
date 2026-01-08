import { useEffect, useState } from 'react'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getExecutions, getExecution } from '@/api/executions'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
  History,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
} from 'lucide-react'
import { getErrorMessage } from '@/api/client'
import { TableSkeleton } from '@/components/ui/skeleton'
import type { Execution, ExecutionDetail, PaginationMeta, TaskStatus } from '@/types'

interface ExecutionsPageProps {
  onNavigate: (route: string) => void
}

export function ExecutionsPage({ onNavigate: _ }: ExecutionsPageProps) {
  const { currentWorkspace } = useWorkspaceStore()
  const [executions, setExecutions] = useState<Execution[]>([])
  const [pagination, setPagination] = useState<PaginationMeta | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedExecution, setSelectedExecution] = useState<ExecutionDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [page, setPage] = useState(1)

  const loadExecutions = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const response = await getExecutions(currentWorkspace.id, {
        page,
        limit: 20,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        task_type: typeFilter !== 'all' ? typeFilter as 'cron' | 'delayed' : undefined,
      })
      setExecutions(response.executions)
      setPagination(response.pagination)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadExecutions()
  }, [currentWorkspace, statusFilter, typeFilter, page])

  const handleViewDetails = async (execution: Execution) => {
    if (!currentWorkspace) return
    setLoadingDetail(true)
    try {
      const detail = await getExecution(currentWorkspace.id, execution.id)
      setSelectedExecution(detail)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoadingDetail(false)
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
            <RefreshCw className="h-3 w-3 animate-spin" />
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
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
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
          <h1 className="text-3xl font-bold tracking-tight">Executions</h1>
          <p className="text-muted-foreground">
            View the history of all task executions
          </p>
        </div>
        <Button variant="outline" onClick={loadExecutions} disabled={isLoading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
            <SelectTrigger className="w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="running">Running</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Type:</span>
          <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1) }}>
            <SelectTrigger className="w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="cron">Cron</SelectItem>
              <SelectItem value="delayed">Delayed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-4 text-destructive">
          {error}
        </div>
      )}

      {isLoading ? (
        <TableSkeleton rows={5} columns={6} />
      ) : executions.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <History className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">No executions yet</h2>
          <p className="text-muted-foreground">
            Task executions will appear here once tasks run
          </p>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Task</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Response</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {executions.map((execution) => (
                <TableRow key={execution.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">
                        {execution.task_name || 'Unnamed task'}
                      </p>
                      <p className="text-sm text-muted-foreground truncate max-w-[250px]">
                        {execution.request_url}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {execution.task_type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {formatDateTime(execution.started_at)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono">
                      {formatDuration(execution.duration_ms)}
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(execution.status)}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {getStatusCodeBadge(execution.response_status_code)}
                      {execution.error_message && (
                        <span className="text-xs text-destructive truncate max-w-[150px]" title={execution.error_message}>
                          {execution.error_message}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleViewDetails(execution)}
                      title="View details"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Showing {executions.length} of {pagination.total} executions
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm">
              Page {pagination.page} of {pagination.total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(pagination.total_pages, p + 1))}
              disabled={page === pagination.total_pages}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Execution Details Dialog */}
      <Dialog open={!!selectedExecution} onOpenChange={() => setSelectedExecution(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Execution Details</DialogTitle>
          </DialogHeader>
          {loadingDetail ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : selectedExecution && (
            <div className="space-y-6">
              {/* Overview */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Task</p>
                  <p className="font-medium">{selectedExecution.task_name || 'Unnamed'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Type</p>
                  <Badge variant="outline">{selectedExecution.task_type}</Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  {getStatusBadge(selectedExecution.status)}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Duration</p>
                  <p className="font-mono">{formatDuration(selectedExecution.duration_ms)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Started</p>
                  <p>{formatDateTime(selectedExecution.started_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Finished</p>
                  <p>{selectedExecution.finished_at ? formatDateTime(selectedExecution.finished_at) : '-'}</p>
                </div>
              </div>

              {/* Request */}
              <div className="space-y-2">
                <h3 className="font-semibold">Request</h3>
                <div className="rounded-md bg-muted p-4 space-y-2">
                  <div className="flex gap-2">
                    <Badge variant="outline">{selectedExecution.request_method}</Badge>
                    <code className="text-sm break-all">{selectedExecution.request_url}</code>
                  </div>
                  {selectedExecution.request_headers && Object.keys(selectedExecution.request_headers).length > 0 && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">Headers:</p>
                      <pre className="text-xs bg-background p-2 rounded overflow-x-auto">
                        {JSON.stringify(selectedExecution.request_headers, null, 2)}
                      </pre>
                    </div>
                  )}
                  {selectedExecution.request_body && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">Body:</p>
                      <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-[200px]">
                        {selectedExecution.request_body}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              {/* Response */}
              <div className="space-y-2">
                <h3 className="font-semibold">Response</h3>
                <div className="rounded-md bg-muted p-4 space-y-2">
                  <div className="flex gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Status Code</p>
                      {getStatusCodeBadge(selectedExecution.response_status_code)}
                    </div>
                    {selectedExecution.response_size_bytes && (
                      <div>
                        <p className="text-sm text-muted-foreground">Size</p>
                        <p className="text-sm">{(selectedExecution.response_size_bytes / 1024).toFixed(2)} KB</p>
                      </div>
                    )}
                  </div>
                  {selectedExecution.response_headers && Object.keys(selectedExecution.response_headers).length > 0 && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">Headers:</p>
                      <pre className="text-xs bg-background p-2 rounded overflow-x-auto">
                        {JSON.stringify(selectedExecution.response_headers, null, 2)}
                      </pre>
                    </div>
                  )}
                  {selectedExecution.response_body && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">Body:</p>
                      <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-[300px]">
                        {selectedExecution.response_body}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              {/* Error */}
              {selectedExecution.error_message && (
                <div className="space-y-2">
                  <h3 className="font-semibold text-destructive">Error</h3>
                  <div className="rounded-md bg-destructive/10 p-4">
                    {selectedExecution.error_type && (
                      <Badge variant="destructive" className="mb-2">
                        {selectedExecution.error_type}
                      </Badge>
                    )}
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
