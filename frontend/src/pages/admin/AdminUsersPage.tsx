import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getAdminUsers, updateAdminUser, AdminUser } from '@/api/admin'
import { getErrorMessage } from '@/api/client'
import { toast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
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
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Users,
  Search,
  ChevronLeft,
  ChevronRight,
  Shield,
  Mail,
  Loader2,
} from 'lucide-react'

interface AdminUsersPageProps {
  onNavigate: (route: string) => void
}

export function AdminUsersPage({ onNavigate }: AdminUsersPageProps) {
  const { t } = useTranslation()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)
  const [updateLoading, setUpdateLoading] = useState(false)

  // Edit form state
  const [editIsActive, setEditIsActive] = useState(true)
  const [editIsSuperuser, setEditIsSuperuser] = useState(false)
  const [editEmailVerified, setEditEmailVerified] = useState(false)

  const loadUsers = async () => {
    setIsLoading(true)
    try {
      const response = await getAdminUsers({
        page,
        page_size: pageSize,
        search: search || undefined,
      })
      setUsers(response.users)
      setTotal(response.total)
    } catch (err) {
      toast({
        title: t('admin.errorLoadingUsers'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [page, search])

  const handleEdit = (user: AdminUser) => {
    setEditingUser(user)
    setEditIsActive(user.is_active)
    setEditIsSuperuser(user.is_superuser)
    setEditEmailVerified(user.email_verified)
  }

  const handleSave = async () => {
    if (!editingUser) return

    setUpdateLoading(true)
    try {
      await updateAdminUser(editingUser.id, {
        is_active: editIsActive,
        is_superuser: editIsSuperuser,
        email_verified: editEmailVerified,
      })
      toast({
        title: t('admin.userUpdated'),
        description: t('admin.userUpdatedDescription', { email: editingUser.email }),
        variant: 'success',
      })
      setEditingUser(null)
      loadUsers()
    } catch (err) {
      toast({
        title: t('admin.errorUpdatingUser'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setUpdateLoading(false)
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => onNavigate('admin')}>
              <ChevronLeft className="h-4 w-4 mr-1" />
              {t('admin.back')}
            </Button>
          </div>
          <h1 className="text-3xl font-bold tracking-tight mt-2">{t('admin.users')}</h1>
          <p className="text-muted-foreground">
            {t('admin.usersSubtitle')}
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('admin.searchUsersPlaceholder')}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            className="pl-10"
          />
        </div>
        <span className="text-sm text-muted-foreground">
          {t('admin.usersTotal', { count: total })}
        </span>
      </div>

      {/* Users Table */}
      {isLoading ? (
        <TableSkeleton rows={10} columns={6} />
      ) : users.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Users className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('admin.noUsersFound')}</h2>
          <p className="text-muted-foreground">
            {search ? t('admin.tryDifferentSearch') : t('admin.noUsersYet')}
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('admin.user')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('admin.role')}</TableHead>
                  <TableHead>{t('admin.workspaces')}</TableHead>
                  <TableHead>{t('admin.tasks')}</TableHead>
                  <TableHead>{t('admin.created')}</TableHead>
                  <TableHead className="text-right">{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{user.name}</p>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                        {user.telegram_username && (
                          <p className="text-xs text-muted-foreground">
                            @{user.telegram_username}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        {user.is_active ? (
                          <Badge variant="success">{t('admin.active')}</Badge>
                        ) : (
                          <Badge variant="secondary">{t('admin.inactive')}</Badge>
                        )}
                        {user.email_verified && (
                          <Badge variant="outline" className="gap-1">
                            <Mail className="h-3 w-3" />
                            {t('admin.verified')}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {user.is_superuser ? (
                        <Badge variant="default" className="gap-1">
                          <Shield className="h-3 w-3" />
                          {t('admin.admin')}
                        </Badge>
                      ) : (
                        <Badge variant="outline">{t('admin.user')}</Badge>
                      )}
                    </TableCell>
                    <TableCell>{user.workspaces_count}</TableCell>
                    <TableCell>{user.tasks_count}</TableCell>
                    <TableCell>
                      {new Date(user.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(user)}
                      >
                        {t('common.edit')}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {t('admin.pageOf', { current: page, total: totalPages })}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  {t('common.previous')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  {t('common.next')}
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Edit User Dialog */}
      <Dialog open={!!editingUser} onOpenChange={() => setEditingUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('admin.editUser')}</DialogTitle>
            <DialogDescription>
              {editingUser?.email}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="is_active">{t('admin.active')}</Label>
              <Switch
                id="is_active"
                checked={editIsActive}
                onCheckedChange={setEditIsActive}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="email_verified">{t('admin.emailVerified')}</Label>
              <Switch
                id="email_verified"
                checked={editEmailVerified}
                onCheckedChange={setEditEmailVerified}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="is_superuser">{t('admin.admin')}</Label>
              <Switch
                id="is_superuser"
                checked={editIsSuperuser}
                onCheckedChange={setEditIsSuperuser}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingUser(null)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleSave} disabled={updateLoading}>
              {updateLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
