import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getWorkers, createWorker, deleteWorker, regenerateWorkerKey } from '@/api/workers'
import { getErrorMessage } from '@/api/client'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { toast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import { TableSkeleton } from '@/components/ui/skeleton'
import {
  Key,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Copy,
  CheckCircle,
  Clock,
  Eye,
  EyeOff,
} from 'lucide-react'
import type { Worker, WorkerCreateResponse } from '@/types'

interface ApiKeysPageProps {
  onNavigate: (route: string) => void
}

export function ApiKeysPage({ onNavigate: _ }: ApiKeysPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
  const [workers, setWorkers] = useState<Worker[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showKeyDialog, setShowKeyDialog] = useState(false)
  const [deletingWorker, setDeletingWorker] = useState<Worker | null>(null)
  const [regeneratingWorker, setRegeneratingWorker] = useState<Worker | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Create form state
  const [newWorkerName, setNewWorkerName] = useState('')
  const [newWorkerDescription, setNewWorkerDescription] = useState('')
  const [createLoading, setCreateLoading] = useState(false)

  // Show key state
  const [newApiKey, setNewApiKey] = useState<WorkerCreateResponse | null>(null)
  const [showKey, setShowKey] = useState(false)
  const [copied, setCopied] = useState(false)

  const loadWorkers = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    try {
      const data = await getWorkers(currentWorkspace.id)
      setWorkers(data)
    } catch (err) {
      toast({
        title: t('apiKeys.errorLoading'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadWorkers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentWorkspace || !newWorkerName.trim()) return

    setCreateLoading(true)
    try {
      const result = await createWorker(currentWorkspace.id, {
        name: newWorkerName.trim(),
        description: newWorkerDescription.trim() || undefined,
      })

      setNewApiKey(result)
      setShowCreateDialog(false)
      setShowKeyDialog(true)
      setNewWorkerName('')
      setNewWorkerDescription('')

      toast({
        title: t('apiKeys.created'),
        description: t('apiKeys.createdCopyWarning'),
        variant: 'success',
      })

      await loadWorkers()
    } catch (err) {
      toast({
        title: t('apiKeys.failedToCreate'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setCreateLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!currentWorkspace || !deletingWorker) return

    setActionLoading(deletingWorker.id)
    try {
      await deleteWorker(currentWorkspace.id, deletingWorker.id)
      setDeletingWorker(null)
      toast({
        title: t('apiKeys.deleted'),
        description: t('apiKeys.deletedDescription', { name: deletingWorker.name }),
      })
      await loadWorkers()
    } catch (err) {
      toast({
        title: t('apiKeys.failedToDelete'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleRegenerate = async () => {
    if (!currentWorkspace || !regeneratingWorker) return

    setActionLoading(regeneratingWorker.id)
    try {
      const result = await regenerateWorkerKey(currentWorkspace.id, regeneratingWorker.id)
      setRegeneratingWorker(null)
      setNewApiKey(result)
      setShowKeyDialog(true)

      toast({
        title: t('apiKeys.regenerated'),
        description: t('apiKeys.regeneratedDescription'),
        variant: 'success',
      })

      await loadWorkers()
    } catch (err) {
      toast({
        title: t('apiKeys.failedToRegenerate'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const copyToClipboard = async () => {
    if (!newApiKey) return
    try {
      await navigator.clipboard.writeText(newApiKey.api_key)
      setCopied(true)
      toast({
        title: t('apiKeys.copied'),
        description: t('apiKeys.copiedDescription'),
        variant: 'success',
      })
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast({
        title: t('apiKeys.failedToCopy'),
        description: t('apiKeys.copyManually'),
        variant: 'destructive',
      })
    }
  }

  const getStatusBadge = (worker: Worker) => {
    if (!worker.is_active) {
      return <Badge variant="secondary">{t('common.disabled')}</Badge>
    }
    switch (worker.status) {
      case 'online':
        return (
          <Badge variant="success" className="gap-1">
            <CheckCircle className="h-3 w-3" />
            {t('apiKeys.online')}
          </Badge>
        )
      case 'busy':
        return (
          <Badge variant="default" className="gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            {t('apiKeys.busy')}
          </Badge>
        )
      case 'offline':
      default:
        return (
          <Badge variant="outline" className="gap-1">
            <Clock className="h-3 w-3" />
            {t('apiKeys.offline')}
          </Badge>
        )
    }
  }

  const formatLastSeen = (lastHeartbeat: string | null) => {
    if (!lastHeartbeat) return t('apiKeys.neverConnected')
    const date = new Date(lastHeartbeat)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return t('apiKeys.justNow')
    if (diffMins < 60) return t('apiKeys.minutesAgo', { minutes: diffMins })
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return t('apiKeys.hoursAgo', { hours: diffHours })
    return date.toLocaleDateString()
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
          <h1 className="text-3xl font-bold tracking-tight">{t('apiKeys.title')}</h1>
          <p className="text-muted-foreground">
            {t('apiKeys.subtitle')}
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t('apiKeys.createApiKey')}
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={3} columns={5} />
      ) : workers.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Key className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('apiKeys.noKeysYet')}</h2>
          <p className="text-muted-foreground text-center max-w-md">
            {t('apiKeys.noKeysDescription')}
          </p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('apiKeys.createApiKey')}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('apiKeys.name')}</TableHead>
                <TableHead>{t('apiKeys.keyPrefix')}</TableHead>
                <TableHead>{t('common.status')}</TableHead>
                <TableHead>{t('apiKeys.lastSeen')}</TableHead>
                <TableHead>{t('apiKeys.stats')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workers.map((worker) => (
                <TableRow key={worker.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{worker.name}</p>
                      {worker.description && (
                        <p className="text-sm text-muted-foreground truncate max-w-[200px]">
                          {worker.description}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <code className="text-sm bg-muted px-2 py-1 rounded">
                      {worker.api_key_prefix}...
                    </code>
                  </TableCell>
                  <TableCell>{getStatusBadge(worker)}</TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {formatLastSeen(worker.last_heartbeat)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      <span className="text-green-600">{worker.tasks_completed}</span>
                      {' / '}
                      <span className="text-red-600">{worker.tasks_failed}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setRegeneratingWorker(worker)}
                        disabled={actionLoading === worker.id}
                        title={t('apiKeys.regenerateKey')}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingWorker(worker)}
                        disabled={actionLoading === worker.id}
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('apiKeys.createTitle')}</DialogTitle>
            <DialogDescription>
              {t('apiKeys.createDescription')}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">{t('apiKeys.name')} *</Label>
              <Input
                id="name"
                value={newWorkerName}
                onChange={(e) => setNewWorkerName(e.target.value)}
                placeholder={t('apiKeys.namePlaceholder')}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">{t('common.description')}</Label>
              <Input
                id="description"
                value={newWorkerDescription}
                onChange={(e) => setNewWorkerDescription(e.target.value)}
                placeholder={t('apiKeys.descriptionPlaceholder')}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={createLoading}>
                {createLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t('common.create')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Show API Key Dialog */}
      <Dialog open={showKeyDialog} onOpenChange={(open) => {
        if (!open) {
          setShowKeyDialog(false)
          setNewApiKey(null)
          setShowKey(false)
          setCopied(false)
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('apiKeys.keyCreated')}</DialogTitle>
            <DialogDescription>
              {t('apiKeys.keyCreatedDescription')}
            </DialogDescription>
          </DialogHeader>
          {newApiKey && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>{t('apiKeys.apiKey')}</Label>
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <Input
                      value={showKey ? newApiKey.api_key : '•'.repeat(40)}
                      readOnly
                      className="font-mono pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full"
                      onClick={() => setShowKey(!showKey)}
                    >
                      {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={copyToClipboard}
                  >
                    {copied ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
              <div className="rounded-md bg-yellow-50 dark:bg-yellow-900/20 p-3 text-sm text-yellow-800 dark:text-yellow-200">
                {t('apiKeys.keyWarning')}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => {
              setShowKeyDialog(false)
              setNewApiKey(null)
              setShowKey(false)
              setCopied(false)
            }}>
              {t('apiKeys.done')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingWorker} onOpenChange={() => setDeletingWorker(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('apiKeys.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('apiKeys.deleteConfirm', { name: deletingWorker?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingWorker(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading === deletingWorker?.id}
            >
              {actionLoading === deletingWorker?.id && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Regenerate Confirmation Dialog */}
      <Dialog open={!!regeneratingWorker} onOpenChange={() => setRegeneratingWorker(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('apiKeys.regenerateTitle')}</DialogTitle>
            <DialogDescription>
              {t('apiKeys.regenerateConfirm', { name: regeneratingWorker?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRegeneratingWorker(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleRegenerate}
              disabled={actionLoading === regeneratingWorker?.id}
            >
              {actionLoading === regeneratingWorker?.id && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t('apiKeys.regenerate')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
