import { useState } from 'react'
import { LogOut, User, Menu, Settings, Globe, ChevronDown, Plus, Check, Trash2, BookOpen } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { useUIStore } from '@/stores/uiStore'
import { updateProfile } from '@/api/auth'
import { createWorkspace, deleteWorkspace } from '@/api/workspaces'
import { getErrorMessage } from '@/api/client'
import { getAssetUrl } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from '@/hooks/use-toast'
import { Loader2 } from 'lucide-react'
import type { Workspace } from '@/types'

interface HeaderProps {
  onNavigate: (route: string) => void
  onLogout: () => void
}

export function Header({ onNavigate, onLogout }: HeaderProps) {
  const { t, i18n } = useTranslation()
  const { user, updateUser } = useAuthStore()
  const { workspaces, currentWorkspace, setCurrentWorkspace, addWorkspace, removeWorkspace } = useWorkspaceStore()
  const { toggleSidebar } = useUIStore()

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [workspaceToDelete, setWorkspaceToDelete] = useState<Workspace | null>(null)
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [newWorkspaceSlug, setNewWorkspaceSlug] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const handleCreateWorkspace = async () => {
    if (!newWorkspaceName.trim() || !newWorkspaceSlug.trim()) return

    setIsCreating(true)
    try {
      const workspace = await createWorkspace({
        name: newWorkspaceName.trim(),
        slug: newWorkspaceSlug.trim(),
      })
      addWorkspace(workspace)
      setCurrentWorkspace(workspace)
      setIsCreateDialogOpen(false)
      setNewWorkspaceName('')
      setNewWorkspaceSlug('')
      toast({
        title: t('workspace.created'),
        description: t('workspace.createdDescription', { name: workspace.name }),
        variant: 'success',
      })
    } catch (error) {
      toast({
        title: t('common.error'),
        description: getErrorMessage(error),
        variant: 'destructive',
      })
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteWorkspace = async () => {
    if (!workspaceToDelete) return

    setIsDeleting(true)
    try {
      await deleteWorkspace(workspaceToDelete.id)
      removeWorkspace(workspaceToDelete.id)

      // If we deleted the current workspace, switch to the first available one
      if (currentWorkspace?.id === workspaceToDelete.id) {
        const remainingWorkspaces = workspaces.filter(w => w.id !== workspaceToDelete.id)
        setCurrentWorkspace(remainingWorkspaces[0] || null)
      }

      setIsDeleteDialogOpen(false)
      setWorkspaceToDelete(null)
      toast({
        title: t('common.success'),
        description: t('workspace.deleted', { name: workspaceToDelete.name }),
        variant: 'success',
      })
    } catch {
      toast({
        title: t('common.error'),
        description: t('workspace.deleteFailed'),
        variant: 'destructive',
      })
    } finally {
      setIsDeleting(false)
    }
  }

  const handleNameChange = (name: string) => {
    setNewWorkspaceName(name)
    // Auto-generate slug from name
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .trim()
    setNewWorkspaceSlug(slug)
  }

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U'

  const currentLanguage = i18n.language as 'en' | 'ru'

  const handleLanguageChange = async (lang: 'en' | 'ru') => {
    try {
      await updateProfile({ preferred_language: lang })
      updateUser({ preferred_language: lang })
    } catch {
      // Still update locally even if API fails
      i18n.changeLanguage(lang)
    }
  }

  return (
    <header className="sticky top-0 z-30 h-16 bg-background border-b px-6 flex items-center justify-between">
      {/* Left side */}
      <div className="flex items-center gap-4">
        {/* Mobile menu button */}
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={toggleSidebar}
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Workspace selector */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 max-w-[200px]">
              <span className="font-medium truncate hidden sm:block">
                {currentWorkspace?.name || t('common.selectWorkspace')}
              </span>
              <ChevronDown className="h-4 w-4 shrink-0" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuLabel>{t('admin.workspaces')}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {workspaces.map((workspace) => (
              <DropdownMenuItem
                key={workspace.id}
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setCurrentWorkspace(workspace)}
              >
                <span className="truncate">{workspace.name}</span>
                <div className="flex items-center gap-1">
                  {workspace.id === currentWorkspace?.id && (
                    <Check className="h-4 w-4 text-primary" />
                  )}
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-muted-foreground hover:text-destructive"
                            disabled={workspaces.length <= 1}
                            onClick={(e) => {
                              e.stopPropagation()
                              setWorkspaceToDelete(workspace)
                              setIsDeleteDialogOpen(true)
                            }}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </span>
                      </TooltipTrigger>
                      {workspaces.length <= 1 && (
                        <TooltipContent>
                          <p>{t('workspace.cannotDeleteLast')}</p>
                        </TooltipContent>
                      )}
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="cursor-pointer"
              onClick={() => setIsCreateDialogOpen(true)}
            >
              <Plus className="mr-2 h-4 w-4" />
              {t('workspace.createNew')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        {/* Documentation link */}
        <Button
          variant="ghost"
          size="sm"
          className="hidden sm:flex items-center gap-2"
          onClick={() => window.open('https://cronbox.ru/docs', '_blank')}
        >
          <BookOpen className="h-4 w-4" />
          <span>{t('header.documentation')}</span>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="sm:hidden"
          onClick={() => window.open('https://cronbox.ru/docs', '_blank')}
          title={t('header.documentation')}
        >
          <BookOpen className="h-5 w-5" />
        </Button>

        {/* Language switcher */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" title={t('header.language')}>
              <Globe className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() => handleLanguageChange('ru')}
              className="cursor-pointer"
            >
              Русский {currentLanguage === 'ru' && '✓'}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => handleLanguageChange('en')}
              className="cursor-pointer"
            >
              English {currentLanguage === 'en' && '✓'}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2">
              <Avatar className="h-8 w-8">
                {user?.avatar_url && (
                  <AvatarImage src={getAssetUrl(user.avatar_url)} alt={user.name} />
                )}
                <AvatarFallback className="text-sm">{initials}</AvatarFallback>
              </Avatar>
              <span className="hidden md:block text-sm">
                {user?.name}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span>{user?.name}</span>
                <span className="text-sm font-normal text-muted-foreground">
                  {user?.email}
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => onNavigate('profile')}
              className="cursor-pointer"
            >
              <User className="mr-2 h-4 w-4" />
              {t('header.profile')}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onNavigate('api-keys')}
              className="cursor-pointer"
            >
              <Settings className="mr-2 h-4 w-4" />
              {t('nav.apiKeys')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={onLogout}
              className="text-destructive cursor-pointer"
            >
              <LogOut className="mr-2 h-4 w-4" />
              {t('header.logout')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Create Workspace Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('workspace.createNew')}</DialogTitle>
            <DialogDescription>{t('workspace.createDescription')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="workspace-name">{t('workspace.name')}</Label>
              <Input
                id="workspace-name"
                value={newWorkspaceName}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder={t('workspace.namePlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="workspace-slug">{t('workspace.slug')}</Label>
              <Input
                id="workspace-slug"
                value={newWorkspaceSlug}
                onChange={(e) => setNewWorkspaceSlug(e.target.value)}
                placeholder={t('workspace.slugPlaceholder')}
              />
              <p className="text-xs text-muted-foreground">
                {t('workspace.slugDescription')}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleCreateWorkspace}
              disabled={isCreating || !newWorkspaceName.trim() || !newWorkspaceSlug.trim()}
            >
              {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('common.create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Workspace Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('workspace.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('workspace.deleteConfirm', { name: workspaceToDelete?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteWorkspace}
              disabled={isDeleting}
            >
              {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </header>
  )
}
