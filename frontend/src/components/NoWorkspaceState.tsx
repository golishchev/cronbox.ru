import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Clock, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { createWorkspace } from '@/api/workspaces'
import { toast } from '@/hooks/use-toast'

export function NoWorkspaceState() {
  const { t } = useTranslation()
  const { setWorkspaces, setCurrentWorkspace } = useWorkspaceStore()
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [newWorkspace, setNewWorkspace] = useState({ name: '', slug: '' })

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newWorkspace.name || !newWorkspace.slug) {
      setCreateError(t('workspace.nameRequired'))
      return
    }

    setCreating(true)
    setCreateError(null)

    try {
      const workspace = await createWorkspace(newWorkspace)
      setWorkspaces([workspace])
      setCurrentWorkspace(workspace)
      setShowCreateDialog(false)
      setNewWorkspace({ name: '', slug: '' })
      toast({
        title: t('workspace.created'),
        description: t('workspace.createdDescription', { name: workspace.name }),
        variant: 'success',
      })
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || 'Failed to create workspace')
    } finally {
      setCreating(false)
    }
  }

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
  }

  return (
    <>
      <div className="flex h-[50vh] flex-col items-center justify-center gap-4">
        <Clock className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-2xl font-semibold">{t('dashboard.noWorkspacesYet')}</h2>
        <p className="text-muted-foreground">{t('dashboard.createFirstWorkspace')}</p>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t('workspace.create')}
        </Button>
      </div>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('workspace.createNew')}</DialogTitle>
            <DialogDescription>
              {t('workspace.createDescription')}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateWorkspace} className="space-y-4">
            {createError && (
              <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                {createError}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="name">{t('workspace.name')}</Label>
              <Input
                id="name"
                placeholder={t('workspace.namePlaceholder')}
                value={newWorkspace.name}
                onChange={(e) => {
                  const name = e.target.value
                  setNewWorkspace({
                    name,
                    slug: generateSlug(name),
                  })
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="slug">{t('workspace.slug')}</Label>
              <Input
                id="slug"
                placeholder={t('workspace.slugPlaceholder')}
                value={newWorkspace.slug}
                onChange={(e) =>
                  setNewWorkspace({ ...newWorkspace, slug: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                {t('workspace.slugDescription')}
              </p>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCreateDialog(false)}
              >
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={creating}>
                {creating ? t('common.loading') : t('workspace.create')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
