import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import {
  getSSLMonitors,
  deleteSSLMonitor,
  pauseSSLMonitor,
  resumeSSLMonitor,
  checkSSLMonitor,
} from '@/api/sslMonitors'
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
  Shield,
  Plus,
  Play,
  Pause,
  Trash2,
  Edit,
  Loader2,
  RefreshCw,
  Lock,
  CreditCard,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Info,
} from 'lucide-react'
import { SSLMonitorForm } from '@/components/ssl/SSLMonitorForm'
import { TableSkeleton } from '@/components/ui/skeleton'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { SSLMonitor, SSLMonitorStatus } from '@/types'

interface SSLMonitorsPageProps {
  onNavigate: (route: string) => void
}

export function SSLMonitorsPage({ onNavigate }: SSLMonitorsPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
  const [monitors, setMonitors] = useState<SSLMonitor[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingMonitor, setEditingMonitor] = useState<SSLMonitor | null>(null)
  const [deletingMonitor, setDeletingMonitor] = useState<SSLMonitor | null>(null)
  const [detailMonitor, setDetailMonitor] = useState<SSLMonitor | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null)

  const loadMonitors = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const response = await getSSLMonitors(currentWorkspace.id)
      setMonitors(response.monitors)
    } catch (err) {
      toast({
        title: t('ssl.errorLoading'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const loadPlan = async () => {
    try {
      const [subscription, plans] = await Promise.all([getSubscription(), getPlans()])
      const planId = subscription?.plan_id
      const plan = plans.find((p) => p.id === planId) || plans.find((p) => p.name === 'free')
      setCurrentPlan(plan || null)
    } catch (err) {
      console.error('Failed to load plan:', err)
    }
  }

  useEffect(() => {
    loadPlan()
  }, [])

  useEffect(() => {
    loadMonitors()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace])

  const handlePauseResume = async (monitor: SSLMonitor) => {
    if (!currentWorkspace) return
    setActionLoading(monitor.id)
    try {
      if (monitor.is_paused) {
        await resumeSSLMonitor(currentWorkspace.id, monitor.id)
        toast({
          title: t('ssl.resumed'),
          description: t('ssl.resumedDescription', { name: monitor.name }),
          variant: 'success',
        })
      } else {
        await pauseSSLMonitor(currentWorkspace.id, monitor.id)
        toast({
          title: t('ssl.paused'),
          description: t('ssl.pausedDescription', { name: monitor.name }),
        })
      }
      await loadMonitors()
    } catch (err) {
      toast({
        title: t('ssl.actionFailed'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCheck = async (monitor: SSLMonitor) => {
    if (!currentWorkspace) return
    setActionLoading(monitor.id)
    try {
      await checkSSLMonitor(currentWorkspace.id, monitor.id)
      toast({
        title: t('ssl.checkComplete'),
        description: t('ssl.checkCompleteDescription', { name: monitor.name }),
        variant: 'success',
      })
      await loadMonitors()
    } catch (err) {
      toast({
        title: t('ssl.checkFailed'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async () => {
    if (!currentWorkspace || !deletingMonitor) return
    const monitorName = deletingMonitor.name
    setActionLoading(deletingMonitor.id)
    try {
      await deleteSSLMonitor(currentWorkspace.id, deletingMonitor.id)
      setDeletingMonitor(null)
      toast({
        title: t('ssl.deleted'),
        description: t('ssl.deletedDescription', { name: monitorName }),
      })
      await loadMonitors()
    } catch (err) {
      toast({
        title: t('ssl.failedToDelete'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (status: SSLMonitorStatus, daysUntilExpiry: number | null) => {
    const variants: Record<SSLMonitorStatus, 'success' | 'destructive' | 'warning' | 'secondary'> = {
      valid: 'success',
      expiring: 'warning',
      expired: 'destructive',
      invalid: 'destructive',
      error: 'destructive',
      pending: 'secondary',
      paused: 'secondary',
    }

    const icons: Record<SSLMonitorStatus, React.ReactNode> = {
      valid: <CheckCircle className="h-3 w-3 mr-1" />,
      expiring: <AlertTriangle className="h-3 w-3 mr-1" />,
      expired: <XCircle className="h-3 w-3 mr-1" />,
      invalid: <XCircle className="h-3 w-3 mr-1" />,
      error: <AlertTriangle className="h-3 w-3 mr-1" />,
      pending: <Clock className="h-3 w-3 mr-1" />,
      paused: <Pause className="h-3 w-3 mr-1" />,
    }

    let label = t(`ssl.status.${status}`)

    // Add days until expiry for expiring/valid status
    if ((status === 'expiring' || status === 'valid') && daysUntilExpiry !== null) {
      label += ` (${daysUntilExpiry}${t('ssl.daysShort')})`
    }

    return (
      <Badge variant={variants[status]} className="flex items-center">
        {icons[status]}
        {label}
      </Badge>
    )
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString()
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

  // Check if SSL monitors are available for the current plan
  const isSSLAvailable = currentPlan ? currentPlan.max_ssl_monitors > 0 : true

  // Show upgrade prompt if SSL monitors are not available
  if (!isSSLAvailable && !isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('ssl.title')}</h1>
        </div>
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Lock className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('ssl.notAvailableOnPlan')}</h2>
          <p className="text-muted-foreground text-center max-w-md">{t('ssl.upgradeToUnlock')}</p>
          <Button onClick={() => onNavigate('billing')}>
            <CreditCard className="mr-2 h-4 w-4" />
            {t('ssl.viewPlans')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('ssl.title')}</h1>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 sm:mr-2" />
          <span className="hidden sm:inline">{t('ssl.create')}</span>
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={5} columns={5} />
      ) : monitors.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Shield className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('ssl.noMonitorsYet')}</h2>
          <p className="text-muted-foreground text-center max-w-md">{t('ssl.createFirstMonitor')}</p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('ssl.create')}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('ssl.domain')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead>{t('ssl.expiryDate')}</TableHead>
                <TableHead>{t('ssl.lastCheck')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {monitors.map((monitor) => (
                <TableRow key={monitor.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{monitor.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {monitor.domain}
                        {monitor.port !== 443 && `:${monitor.port}`}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(monitor.status, monitor.days_until_expiry)}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{formatDate(monitor.valid_until)}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {monitor.last_check_at
                        ? new Date(monitor.last_check_at).toLocaleString()
                        : t('ssl.neverChecked')}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCheck(monitor)}
                        disabled={actionLoading === monitor.id || monitor.is_paused}
                        title={t('ssl.checkNow')}
                      >
                        {actionLoading === monitor.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handlePauseResume(monitor)}
                        disabled={actionLoading === monitor.id}
                        title={monitor.is_paused ? t('common.resume') : t('common.pause')}
                      >
                        {monitor.is_paused ? (
                          <Play className="h-4 w-4" />
                        ) : (
                          <Pause className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDetailMonitor(monitor)}
                        title={t('ssl.viewDetails')}
                      >
                        <Info className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditingMonitor(monitor)}
                        title={t('common.edit')}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingMonitor(monitor)}
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
            <DialogTitle>{t('ssl.createMonitor')}</DialogTitle>
            <DialogDescription>{t('ssl.createDescription')}</DialogDescription>
          </DialogHeader>
          <SSLMonitorForm
            workspaceId={currentWorkspace.id}
            onSuccess={() => {
              setShowCreateDialog(false)
              loadMonitors()
            }}
            onCancel={() => setShowCreateDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingMonitor} onOpenChange={() => setEditingMonitor(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('ssl.editMonitor')}</DialogTitle>
            <DialogDescription>{t('ssl.editDescription')}</DialogDescription>
          </DialogHeader>
          {editingMonitor && (
            <SSLMonitorForm
              workspaceId={currentWorkspace.id}
              monitor={editingMonitor}
              onSuccess={() => {
                setEditingMonitor(null)
                loadMonitors()
              }}
              onCancel={() => setEditingMonitor(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingMonitor} onOpenChange={() => setDeletingMonitor(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('ssl.deleteMonitor')}</DialogTitle>
            <DialogDescription>
              {t('ssl.deleteConfirm', { name: deletingMonitor?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingMonitor(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading === deletingMonitor?.id}
            >
              {actionLoading === deletingMonitor?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Certificate Details Dialog */}
      <Dialog open={!!detailMonitor} onOpenChange={() => setDetailMonitor(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('ssl.certificateDetails')}</DialogTitle>
            <DialogDescription>
              {detailMonitor?.domain}
              {detailMonitor?.port !== 443 && `:${detailMonitor?.port}`}
            </DialogDescription>
          </DialogHeader>
          {detailMonitor && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{t('common.status')}</p>
                  <div className="mt-1">
                    {getStatusBadge(detailMonitor.status, detailMonitor.days_until_expiry)}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{t('ssl.daysUntilExpiry')}</p>
                  <p className="mt-1">
                    {detailMonitor.days_until_expiry !== null
                      ? `${detailMonitor.days_until_expiry} ${t('ssl.days')}`
                      : '-'}
                  </p>
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="font-medium mb-2">{t('ssl.certificateInfo')}</h4>
                <div className="grid gap-2 text-sm">
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.issuer')}</span>
                    <span className="col-span-2 break-all">{detailMonitor.issuer || '-'}</span>
                  </div>
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.subject')}</span>
                    <span className="col-span-2 break-all">{detailMonitor.subject || '-'}</span>
                  </div>
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.serialNumber')}</span>
                    <span className="col-span-2 font-mono text-xs break-all">
                      {detailMonitor.serial_number || '-'}
                    </span>
                  </div>
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.validFrom')}</span>
                    <span className="col-span-2">{formatDate(detailMonitor.valid_from)}</span>
                  </div>
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.validUntil')}</span>
                    <span className="col-span-2">{formatDate(detailMonitor.valid_until)}</span>
                  </div>
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="font-medium mb-2">{t('ssl.connectionInfo')}</h4>
                <div className="grid gap-2 text-sm">
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.tlsVersion')}</span>
                    <span className="col-span-2">{detailMonitor.tls_version || '-'}</span>
                  </div>
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.cipherSuite')}</span>
                    <span className="col-span-2 font-mono text-xs break-all">
                      {detailMonitor.cipher_suite || '-'}
                    </span>
                  </div>
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.chainValid')}</span>
                    <span className="col-span-2">
                      {detailMonitor.chain_valid === null
                        ? '-'
                        : detailMonitor.chain_valid
                          ? t('common.yes')
                          : t('common.no')}
                    </span>
                  </div>
                  <div className="grid grid-cols-3">
                    <span className="text-muted-foreground">{t('ssl.hostnameMatch')}</span>
                    <span className="col-span-2">
                      {detailMonitor.hostname_match === null
                        ? '-'
                        : detailMonitor.hostname_match
                          ? t('common.yes')
                          : t('common.no')}
                    </span>
                  </div>
                </div>
              </div>

              {detailMonitor.last_error && (
                <div className="border-t pt-4">
                  <h4 className="font-medium mb-2 text-destructive">{t('ssl.lastError')}</h4>
                  <p className="text-sm text-muted-foreground bg-muted p-2 rounded">
                    {detailMonitor.last_error}
                  </p>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailMonitor(null)}>
              {t('common.close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
