import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getAdminWorkspaces, AdminWorkspace } from '@/api/admin'
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
import { TableSkeleton } from '@/components/ui/skeleton'
import {
  Building2,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

interface AdminWorkspacesPageProps {
  onNavigate: (route: string) => void
}

export function AdminWorkspacesPage({ onNavigate }: AdminWorkspacesPageProps) {
  const { t } = useTranslation()
  const [workspaces, setWorkspaces] = useState<AdminWorkspace[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  const loadWorkspaces = async () => {
    setIsLoading(true)
    try {
      const response = await getAdminWorkspaces({
        page,
        page_size: pageSize,
        search: search || undefined,
      })
      setWorkspaces(response.workspaces)
      setTotal(response.total)
    } catch (err) {
      toast({
        title: t('admin.errorLoadingWorkspaces'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadWorkspaces()
  }, [page, search])

  const getPlanBadge = (plan: string) => {
    switch (plan) {
      case 'enterprise':
        return <Badge variant="default">Enterprise</Badge>
      case 'pro':
        return <Badge variant="success">Pro</Badge>
      default:
        return <Badge variant="outline">Free</Badge>
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
          <h1 className="text-3xl font-bold tracking-tight mt-2">{t('admin.workspaces')}</h1>
          <p className="text-muted-foreground">
            {t('admin.workspacesSubtitle')}
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('admin.searchWorkspacesPlaceholder')}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            className="pl-10"
          />
        </div>
        <span className="text-sm text-muted-foreground">
          {t('admin.workspacesTotal', { count: total })}
        </span>
      </div>

      {/* Workspaces Table */}
      {isLoading ? (
        <TableSkeleton rows={10} columns={7} />
      ) : workspaces.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Building2 className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('admin.noWorkspacesFound')}</h2>
          <p className="text-muted-foreground">
            {search ? t('admin.tryDifferentSearch') : t('admin.noWorkspacesYet')}
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('admin.workspaces')}</TableHead>
                  <TableHead>{t('admin.owner')}</TableHead>
                  <TableHead>{t('admin.plan')}</TableHead>
                  <TableHead>{t('admin.cronTasks')}</TableHead>
                  <TableHead>{t('admin.delayedTasks')}</TableHead>
                  <TableHead>{t('nav.executions')}</TableHead>
                  <TableHead>{t('admin.created')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {workspaces.map((ws) => (
                  <TableRow key={ws.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{ws.name}</p>
                        <p className="text-sm text-muted-foreground">/{ws.slug}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">{ws.owner_name}</p>
                        <p className="text-sm text-muted-foreground">{ws.owner_email}</p>
                      </div>
                    </TableCell>
                    <TableCell>{getPlanBadge(ws.plan_name)}</TableCell>
                    <TableCell>{ws.cron_tasks_count}</TableCell>
                    <TableCell>{ws.delayed_tasks_count}</TableCell>
                    <TableCell>{ws.executions_count}</TableCell>
                    <TableCell>
                      {new Date(ws.created_at).toLocaleDateString()}
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
    </div>
  )
}
