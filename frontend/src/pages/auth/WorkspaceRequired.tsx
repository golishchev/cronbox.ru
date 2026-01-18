import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Clock, LogOut, Loader2 } from 'lucide-react'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { createWorkspace } from '@/api/workspaces'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface WorkspaceRequiredProps {
  onLogout: () => void
}

export function WorkspaceRequired({ onLogout }: WorkspaceRequiredProps) {
  const { t } = useTranslation()
  const { setWorkspaces, setCurrentWorkspace } = useWorkspaceStore()
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [newWorkspace, setNewWorkspace] = useState({ name: '', slug: '' })

  // Prevent search engine indexing of this page
  useEffect(() => {
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex, nofollow'
    document.head.appendChild(meta)
    return () => {
      document.head.removeChild(meta)
    }
  }, [])

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
  }

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newWorkspace.name || !newWorkspace.slug) {
      setError(t('workspace.nameRequired'))
      return
    }

    setCreating(true)
    setError('')

    try {
      const workspace = await createWorkspace(newWorkspace)
      setWorkspaces([workspace])
      setCurrentWorkspace(workspace)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="flex items-center gap-2 text-2xl font-bold">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                <Clock className="h-5 w-5 text-white" />
              </div>
              <span>CronBox</span>
            </div>
          </div>
          <CardTitle className="text-2xl">
            {t('workspaceRequired.title')}
          </CardTitle>
          <CardDescription className="text-base">
            {t('workspaceRequired.description')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreateWorkspace} className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                {error}
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
                autoFocus
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
            <div className="space-y-2 pt-2">
              <Button
                type="submit"
                className="w-full"
                disabled={creating || !newWorkspace.name || !newWorkspace.slug}
              >
                {creating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('common.loading')}
                  </>
                ) : (
                  t('workspace.create')
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={onLogout}
              >
                <LogOut className="mr-2 h-4 w-4" />
                {t('workspaceRequired.logout')}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
