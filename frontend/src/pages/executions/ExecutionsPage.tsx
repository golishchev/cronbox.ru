import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
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
  AlertCircle,
  Link2,
  HeartPulse,
  ShieldCheck,
  Radio,
  Plug,
} from 'lucide-react'
import { getErrorMessage } from '@/api/client'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { translateApiError } from '@/lib/translateApiError'
import type { Execution, ExecutionDetail, ExecutionStatus, ExecutionTaskType, PaginationMeta } from '@/types'

interface ExecutionsPageProps {
  onNavigate: (route: string) => void
}

export function ExecutionsPage({ onNavigate: _ }: ExecutionsPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
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
        task_type: typeFilter !== 'all' ? typeFilter as ExecutionTaskType : undefined,
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace, statusFilter, typeFilter, page])

  const handleViewDetails = async (execution: Execution) => {
    if (!currentWorkspace) return
    setLoadingDetail(true)
    try {
      const detail = await getExecution(
        currentWorkspace.id,
        execution.id,
        execution.task_type === 'chain' ? 'chain' : undefined
      )
      setSelectedExecution(detail)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoadingDetail(false)
    }
  }

  const getStatusBadge = (status: ExecutionStatus) => {
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
      case 'partial':
        return (
          <Badge variant="warning" className="gap-1">
            <AlertCircle className="h-3 w-3" />
            {t('executions.partial')}
          </Badge>
        )
      case 'cancelled':
        return (
          <Badge variant="secondary" className="gap-1">
            <XCircle className="h-3 w-3" />
            {t('executions.cancelled')}
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
          <h1 className="text-3xl font-bold tracking-tight">{t('executions.title')}</h1>
        </div>
        <Button variant="outline" onClick={loadExecutions} disabled={isLoading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{t('common.status')}:</span>
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
            <SelectTrigger className="w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.all')}</SelectItem>
              <SelectItem value="success">{t('common.success')}</SelectItem>
              <SelectItem value="failed">{t('common.failed')}</SelectItem>
              <SelectItem value="running">{t('common.running')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{t('common.type')}:</span>
          <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1) }}>
            <SelectTrigger className="w-[150px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.all')}</SelectItem>
              <SelectItem value="cron">Cron</SelectItem>
              <SelectItem value="delayed">{t('executions.delayed')}</SelectItem>
              <SelectItem value="chain">{t('executions.chain')}</SelectItem>
              <SelectItem value="heartbeat">{t('executions.heartbeat')}</SelectItem>
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
          <h2 className="text-xl font-semibold">{t('executions.noExecutionsYet')}</h2>
          <p className="text-muted-foreground text-center max-w-md">
            {t('executions.executionsWillAppear')}
          </p>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('executions.task')}</TableHead>
                <TableHead>{t('common.type')}</TableHead>
                <TableHead>{t('executions.started')}</TableHead>
                <TableHead>{t('common.duration')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead>{t('executions.response')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {executions.map((execution) => (
                <TableRow key={execution.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">
                        {execution.task_name || t('executions.unnamedTask')}
                      </p>
                      {execution.task_type === 'chain' ? (
                        <p className="text-sm text-muted-foreground">
                          {t('executions.stepsInfo', {
                            completed: execution.completed_steps ?? 0,
                            total: execution.total_steps ?? 0,
                          })}
                        </p>
                      ) : execution.task_type === 'heartbeat' ? (
                        <p className="text-sm text-muted-foreground">
                          {t('executions.pingReceived')}
                        </p>
                      ) : execution.protocol_type === 'icmp' ? (
                        <p className="text-sm text-muted-foreground truncate max-w-[250px]">
                          <Radio className="h-3 w-3 inline mr-1" />
                          {execution.target_host}
                        </p>
                      ) : execution.protocol_type === 'tcp' ? (
                        <p className="text-sm text-muted-foreground truncate max-w-[250px]">
                          <Plug className="h-3 w-3 inline mr-1" />
                          {execution.target_host}:{execution.target_port}
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground truncate max-w-[250px]">
                          {execution.request_url}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="gap-1">
                      {execution.task_type === 'chain' && <Link2 className="h-3 w-3" />}
                      {execution.task_type === 'heartbeat' && <HeartPulse className="h-3 w-3" />}
                      {execution.task_type === 'ssl' && <ShieldCheck className="h-3 w-3" />}
                      {execution.task_type === 'chain'
                        ? t('executions.chain')
                        : execution.task_type === 'heartbeat'
                          ? t('executions.heartbeat')
                          : execution.task_type === 'ssl'
                            ? t('executions.ssl')
                            : execution.task_type}
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
                      {execution.task_type === 'chain' ? (
                        execution.failed_steps && execution.failed_steps > 0 ? (
                          <span className="text-xs text-destructive">
                            {t('executions.failedSteps', { count: execution.failed_steps })}
                          </span>
                        ) : null
                      ) : execution.protocol_type === 'icmp' ? (
                        <>
                          {execution.icmp_packet_loss !== null && (
                            <Badge variant={execution.icmp_packet_loss === 0 ? 'success' : execution.icmp_packet_loss < 50 ? 'warning' : 'destructive'}>
                              {execution.icmp_packet_loss === 0 ? '0%' : `${execution.icmp_packet_loss.toFixed(0)}%`} loss
                            </Badge>
                          )}
                          {execution.icmp_avg_rtt !== null && (
                            <span className="text-xs text-muted-foreground">
                              {execution.icmp_avg_rtt.toFixed(1)}ms avg
                            </span>
                          )}
                          {execution.error_message && (
                            <span className="text-xs text-destructive truncate max-w-[150px]" title={translateApiError(execution.error_message, t)}>
                              {translateApiError(execution.error_message, t)}
                            </span>
                          )}
                        </>
                      ) : execution.protocol_type === 'tcp' ? (
                        <>
                          {execution.tcp_connection_time !== null && (
                            <Badge variant="success">
                              {execution.tcp_connection_time.toFixed(0)}ms
                            </Badge>
                          )}
                          {execution.error_message && (
                            <span className="text-xs text-destructive truncate max-w-[150px]" title={translateApiError(execution.error_message, t)}>
                              {translateApiError(execution.error_message, t)}
                            </span>
                          )}
                        </>
                      ) : (
                        <>
                          {getStatusCodeBadge(execution.response_status_code)}
                          {execution.error_message && (
                            <span className="text-xs text-destructive truncate max-w-[150px]" title={translateApiError(execution.error_message, t)}>
                              {translateApiError(execution.error_message, t)}
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleViewDetails(execution)}
                      title={t('executions.viewDetails')}
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
            {t('executions.showing', { count: executions.length, total: pagination.total })}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="h-4 w-4" />
              {t('common.previous')}
            </Button>
            <span className="text-sm">
              {t('executions.page', { current: pagination.page, total: pagination.total_pages })}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(pagination.total_pages, p + 1))}
              disabled={page === pagination.total_pages}
            >
              {t('common.next')}
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Execution Details Dialog */}
      <Dialog open={!!selectedExecution} onOpenChange={() => setSelectedExecution(null)}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('executions.executionDetails')}</DialogTitle>
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
                  <p className="text-sm text-muted-foreground">{t('executions.task')}</p>
                  <p className="font-medium">{selectedExecution.task_name || t('executions.unnamedTask')}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('common.type')}</p>
                  <Badge variant="outline">{selectedExecution.task_type}</Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t('common.status')}</p>
                  {getStatusBadge(selectedExecution.status)}
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

              {/* Chain-specific: Steps summary */}
              {selectedExecution.task_type === 'chain' && (
                <div className="space-y-2">
                  <h3 className="font-semibold">{t('executions.chainSteps')}</h3>
                  <div className="rounded-md bg-muted p-4 space-y-4">
                    <div className="grid grid-cols-4 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executions.totalSteps')}</p>
                        <p className="text-lg font-semibold">{selectedExecution.total_steps ?? 0}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executions.completedSteps')}</p>
                        <p className="text-lg font-semibold text-green-600">{selectedExecution.completed_steps ?? 0}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executions.failedStepsLabel')}</p>
                        <p className="text-lg font-semibold text-red-600">{selectedExecution.failed_steps ?? 0}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{t('executions.skippedSteps')}</p>
                        <p className="text-lg font-semibold text-gray-500">{selectedExecution.skipped_steps ?? 0}</p>
                      </div>
                    </div>
                    {selectedExecution.chain_variables && Object.keys(selectedExecution.chain_variables).length > 0 && (
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">{t('executions.chainVariables')}:</p>
                        <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-[200px] whitespace-pre-wrap break-all">
                          {JSON.stringify(selectedExecution.chain_variables, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Request/Target (for non-chain executions) */}
              {selectedExecution.task_type !== 'chain' && (
                <div className="space-y-2">
                  <h3 className="font-semibold">
                    {selectedExecution.protocol_type === 'http' || !selectedExecution.protocol_type
                      ? t('executions.request')
                      : t('executionResults.target')}
                  </h3>
                  <div className="rounded-md bg-muted p-4 space-y-2">
                    {/* HTTP request */}
                    {(selectedExecution.protocol_type === 'http' || !selectedExecution.protocol_type) && selectedExecution.request_url && (
                      <>
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
                      </>
                    )}
                    {/* ICMP target */}
                    {selectedExecution.protocol_type === 'icmp' && (
                      <div className="flex gap-2 items-center">
                        <Radio className="h-4 w-4 text-muted-foreground" />
                        <Badge variant="outline">ICMP</Badge>
                        <code className="text-sm">{selectedExecution.target_host}</code>
                      </div>
                    )}
                    {/* TCP target */}
                    {selectedExecution.protocol_type === 'tcp' && (
                      <div className="flex gap-2 items-center">
                        <Plug className="h-4 w-4 text-muted-foreground" />
                        <Badge variant="outline">TCP</Badge>
                        <code className="text-sm">{selectedExecution.target_host}:{selectedExecution.target_port}</code>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Response/Results (for non-chain executions) */}
              {selectedExecution.task_type !== 'chain' && (
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
              )}

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
