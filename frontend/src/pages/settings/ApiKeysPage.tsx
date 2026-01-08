import { useEffect, useState } from 'react'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { getWorkers, createWorker, deleteWorker, regenerateWorkerKey } from '@/api/workers'
import { getErrorMessage } from '@/api/client'
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
  const { currentWorkspace } = useWorkspaceStore()
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
  const [newWorkerRegion, setNewWorkerRegion] = useState('')
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
        title: 'Error loading API keys',
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadWorkers()
  }, [currentWorkspace])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentWorkspace || !newWorkerName.trim()) return

    setCreateLoading(true)
    try {
      const result = await createWorker(currentWorkspace.id, {
        name: newWorkerName.trim(),
        description: newWorkerDescription.trim() || undefined,
        region: newWorkerRegion.trim() || undefined,
      })

      setNewApiKey(result)
      setShowCreateDialog(false)
      setShowKeyDialog(true)
      setNewWorkerName('')
      setNewWorkerDescription('')
      setNewWorkerRegion('')

      toast({
        title: 'API key created',
        description: 'Make sure to copy the key - it will not be shown again!',
        variant: 'success',
      })

      await loadWorkers()
    } catch (err) {
      toast({
        title: 'Failed to create API key',
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
        title: 'API key deleted',
        description: `"${deletingWorker.name}" has been deleted`,
      })
      await loadWorkers()
    } catch (err) {
      toast({
        title: 'Failed to delete API key',
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
        title: 'API key regenerated',
        description: 'The old key has been invalidated. Copy the new key!',
        variant: 'success',
      })

      await loadWorkers()
    } catch (err) {
      toast({
        title: 'Failed to regenerate API key',
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
        title: 'Copied!',
        description: 'API key copied to clipboard',
        variant: 'success',
      })
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast({
        title: 'Failed to copy',
        description: 'Please copy the key manually',
        variant: 'destructive',
      })
    }
  }

  const getStatusBadge = (worker: Worker) => {
    if (!worker.is_active) {
      return <Badge variant="secondary">Disabled</Badge>
    }
    switch (worker.status) {
      case 'online':
        return (
          <Badge variant="success" className="gap-1">
            <CheckCircle className="h-3 w-3" />
            Online
          </Badge>
        )
      case 'busy':
        return (
          <Badge variant="default" className="gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Busy
          </Badge>
        )
      case 'offline':
      default:
        return (
          <Badge variant="outline" className="gap-1">
            <Clock className="h-3 w-3" />
            Offline
          </Badge>
        )
    }
  }

  const formatLastSeen = (lastHeartbeat: string | null) => {
    if (!lastHeartbeat) return 'Never connected'
    const date = new Date(lastHeartbeat)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    return date.toLocaleDateString()
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
          <h1 className="text-3xl font-bold tracking-tight">API Keys</h1>
          <p className="text-muted-foreground">
            Manage API keys for external workers and integrations
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create API Key
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={3} columns={5} />
      ) : workers.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Key className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">No API keys yet</h2>
          <p className="text-muted-foreground text-center max-w-md">
            Create an API key to connect external workers or integrate with your applications
          </p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create API Key
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key Prefix</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Seen</TableHead>
                <TableHead>Stats</TableHead>
                <TableHead className="text-right">Actions</TableHead>
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
                      {worker.region && (
                        <Badge variant="outline" className="mt-1 text-xs">
                          {worker.region}
                        </Badge>
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
                        title="Regenerate key"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeletingWorker(worker)}
                        disabled={actionLoading === worker.id}
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              Create a new API key for workers or external integrations
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={newWorkerName}
                onChange={(e) => setNewWorkerName(e.target.value)}
                placeholder="Production Worker"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={newWorkerDescription}
                onChange={(e) => setNewWorkerDescription(e.target.value)}
                placeholder="Main production worker for HTTP requests"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="region">Region</Label>
              <Input
                id="region"
                value={newWorkerRegion}
                onChange={(e) => setNewWorkerRegion(e.target.value)}
                placeholder="eu-west-1"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createLoading}>
                {createLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create
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
            <DialogTitle>API Key Created</DialogTitle>
            <DialogDescription>
              Make sure to copy the API key now. You will not be able to see it again!
            </DialogDescription>
          </DialogHeader>
          {newApiKey && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>API Key</Label>
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
                This key will only be shown once. Make sure to copy it now!
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
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingWorker} onOpenChange={() => setDeletingWorker(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete API Key</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deletingWorker?.name}"?
              This will immediately invalidate the key and any workers using it will stop working.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingWorker(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={actionLoading === deletingWorker?.id}
            >
              {actionLoading === deletingWorker?.id && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Regenerate Confirmation Dialog */}
      <Dialog open={!!regeneratingWorker} onOpenChange={() => setRegeneratingWorker(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Regenerate API Key</DialogTitle>
            <DialogDescription>
              Are you sure you want to regenerate the API key for "{regeneratingWorker?.name}"?
              The old key will be immediately invalidated.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRegeneratingWorker(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleRegenerate}
              disabled={actionLoading === regeneratingWorker?.id}
            >
              {actionLoading === regeneratingWorker?.id && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Regenerate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
