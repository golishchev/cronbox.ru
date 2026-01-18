import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  getAdminPlans,
  createAdminPlan,
  updateAdminPlan,
  deleteAdminPlan,
  AdminPlan,
  CreatePlanRequest,
  UpdatePlanRequest,
} from '@/api/admin'
import { getErrorMessage } from '@/api/client'
import { toast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
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
  CreditCard,
  ChevronLeft,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  Check,
  X,
} from 'lucide-react'

interface AdminPlansPageProps {
  onNavigate: (route: string) => void
}

const defaultPlanData: CreatePlanRequest = {
  name: '',
  display_name: '',
  description: '',
  price_monthly: 0,
  price_yearly: 0,
  max_cron_tasks: 5,
  max_delayed_tasks_per_month: 100,
  max_workspaces: 1,
  max_execution_history_days: 7,
  min_cron_interval_minutes: 5,
  telegram_notifications: false,
  email_notifications: false,
  webhook_callbacks: false,
  custom_headers: true,
  retry_on_failure: false,
  // Task Chains
  max_task_chains: 0,
  max_chain_steps: 5,
  chain_variable_substitution: false,
  min_chain_interval_minutes: 15,
  // Heartbeats
  max_heartbeats: 0,
  min_heartbeat_interval_minutes: 5,
  // Overlap prevention
  overlap_prevention_enabled: false,
  max_queue_size: 10,
  is_active: true,
  is_public: true,
  sort_order: 0,
}

export function AdminPlansPage({ onNavigate }: AdminPlansPageProps) {
  const { t } = useTranslation()
  const [plans, setPlans] = useState<AdminPlan[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Create/Edit dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingPlan, setEditingPlan] = useState<AdminPlan | null>(null)
  const [formData, setFormData] = useState<CreatePlanRequest>(defaultPlanData)

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingPlan, setDeletingPlan] = useState<AdminPlan | null>(null)

  const loadPlans = async () => {
    setIsLoading(true)
    try {
      const response = await getAdminPlans()
      setPlans(response.plans)
    } catch (err) {
      toast({
        title: t('admin.plans.errorLoading'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadPlans()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleOpenCreate = () => {
    setEditingPlan(null)
    setFormData(defaultPlanData)
    setDialogOpen(true)
  }

  const handleOpenEdit = (plan: AdminPlan) => {
    setEditingPlan(plan)
    setFormData({
      name: plan.name,
      display_name: plan.display_name,
      description: plan.description || '',
      price_monthly: plan.price_monthly,
      price_yearly: plan.price_yearly,
      max_cron_tasks: plan.max_cron_tasks,
      max_delayed_tasks_per_month: plan.max_delayed_tasks_per_month,
      max_workspaces: plan.max_workspaces,
      max_execution_history_days: plan.max_execution_history_days,
      min_cron_interval_minutes: plan.min_cron_interval_minutes,
      telegram_notifications: plan.telegram_notifications,
      email_notifications: plan.email_notifications,
      webhook_callbacks: plan.webhook_callbacks,
      custom_headers: plan.custom_headers,
      retry_on_failure: plan.retry_on_failure,
      // Task Chains
      max_task_chains: plan.max_task_chains,
      max_chain_steps: plan.max_chain_steps,
      chain_variable_substitution: plan.chain_variable_substitution,
      min_chain_interval_minutes: plan.min_chain_interval_minutes,
      // Heartbeats
      max_heartbeats: plan.max_heartbeats,
      min_heartbeat_interval_minutes: plan.min_heartbeat_interval_minutes,
      // Overlap prevention
      overlap_prevention_enabled: plan.overlap_prevention_enabled,
      max_queue_size: plan.max_queue_size,
      is_active: plan.is_active,
      is_public: plan.is_public,
      sort_order: plan.sort_order,
    })
    setDialogOpen(true)
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      if (editingPlan) {
        const { name: _, ...updateData } = formData // name cannot be updated
        await updateAdminPlan(editingPlan.id, updateData as UpdatePlanRequest)
        toast({
          title: t('admin.plans.updated'),
          description: t('admin.plans.updatedDescription'),
        })
      } else {
        await createAdminPlan(formData)
        toast({
          title: t('admin.plans.created'),
          description: t('admin.plans.createdDescription'),
        })
      }
      setDialogOpen(false)
      loadPlans()
    } catch (err) {
      toast({
        title: editingPlan ? t('admin.plans.errorUpdating') : t('admin.plans.errorCreating'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!deletingPlan) return
    setIsSubmitting(true)
    try {
      await deleteAdminPlan(deletingPlan.id)
      toast({
        title: t('admin.plans.deleted'),
        description: t('admin.plans.deletedDescription'),
      })
      setDeleteDialogOpen(false)
      setDeletingPlan(null)
      loadPlans()
    } catch (err) {
      toast({
        title: t('admin.plans.errorDeleting'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const formatPrice = (kopeks: number) => {
    if (kopeks === 0) return t('admin.plans.free')
    return `${(kopeks / 100).toLocaleString()} ${t('admin.plans.currency')}`
  }

  const BooleanBadge = ({ value }: { value: boolean }) => (
    value ? (
      <Badge variant="success" className="gap-1">
        <Check className="h-3 w-3" />
      </Badge>
    ) : (
      <Badge variant="outline" className="gap-1">
        <X className="h-3 w-3" />
      </Badge>
    )
  )

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
          <h1 className="text-3xl font-bold tracking-tight mt-2">{t('admin.plans.title')}</h1>
        </div>
        <Button onClick={handleOpenCreate}>
          <Plus className="h-4 w-4 mr-2" />
          {t('admin.plans.create')}
        </Button>
      </div>

      {/* Plans Table */}
      {isLoading ? (
        <TableSkeleton rows={5} columns={8} />
      ) : plans.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <CreditCard className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('admin.plans.noPlans')}</h2>
          <p className="text-muted-foreground text-center max-w-md">{t('admin.plans.noPlansDescription')}</p>
          <Button onClick={handleOpenCreate}>
            <Plus className="h-4 w-4 mr-2" />
            {t('admin.plans.createFirst')}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('admin.plans.name')}</TableHead>
                <TableHead>{t('admin.plans.pricing')}</TableHead>
                <TableHead>{t('admin.plans.limits')}</TableHead>
                <TableHead>{t('admin.plans.features')}</TableHead>
                <TableHead>{t('admin.plans.status')}</TableHead>
                <TableHead>{t('admin.plans.subscriptions')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {plans.map((plan) => (
                <TableRow key={plan.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{plan.display_name}</p>
                      <p className="text-sm text-muted-foreground font-mono">{plan.name}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      <p>{formatPrice(plan.price_monthly)}/{t('admin.plans.month')}</p>
                      <p className="text-muted-foreground">{formatPrice(plan.price_yearly)}/{t('admin.plans.year')}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm space-y-0.5">
                      <p>{plan.max_cron_tasks} cron</p>
                      <p>{plan.max_delayed_tasks_per_month} {t('admin.plans.delayedPerMonth')}</p>
                      {plan.max_task_chains > 0 && <p>{plan.max_task_chains} {t('admin.plans.chains')}</p>}
                      {plan.max_heartbeats > 0 && <p>{plan.max_heartbeats} {t('admin.plans.monitors')}</p>}
                      <p>{plan.min_cron_interval_minutes} {t('admin.plans.minInterval')}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      <span className="text-xs" title="Telegram">
                        <BooleanBadge value={plan.telegram_notifications} />
                      </span>
                      <span className="text-xs" title="Email">
                        <BooleanBadge value={plan.email_notifications} />
                      </span>
                      <span className="text-xs" title="Webhook">
                        <BooleanBadge value={plan.webhook_callbacks} />
                      </span>
                      <span className="text-xs" title="Retry">
                        <BooleanBadge value={plan.retry_on_failure} />
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      {plan.is_active ? (
                        <Badge variant="success">{t('admin.plans.active')}</Badge>
                      ) : (
                        <Badge variant="secondary">{t('admin.plans.inactive')}</Badge>
                      )}
                      {plan.is_public && (
                        <Badge variant="outline">{t('admin.plans.public')}</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono">{plan.subscriptions_count}</span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleOpenEdit(plan)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setDeletingPlan(plan)
                          setDeleteDialogOpen(true)
                        }}
                        disabled={plan.subscriptions_count > 0}
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

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingPlan ? t('admin.plans.edit') : t('admin.plans.create')}
            </DialogTitle>
            <DialogDescription>
              {editingPlan ? t('admin.plans.editDescription') : t('admin.plans.createDescription')}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t('admin.plans.nameField')}</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  disabled={!!editingPlan}
                  placeholder="starter"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="display_name">{t('admin.plans.displayName')}</Label>
                <Input
                  id="display_name"
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                  placeholder="Starter"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">{t('admin.plans.description')}</Label>
              <Input
                id="description"
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder={t('admin.plans.descriptionPlaceholder')}
              />
            </div>

            {/* Pricing */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="price_monthly">{t('admin.plans.priceMonthly')}</Label>
                <Input
                  id="price_monthly"
                  type="number"
                  min={0}
                  value={formData.price_monthly}
                  onChange={(e) => setFormData({ ...formData, price_monthly: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">{t('admin.plans.priceHint')}</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="price_yearly">{t('admin.plans.priceYearly')}</Label>
                <Input
                  id="price_yearly"
                  type="number"
                  min={0}
                  value={formData.price_yearly}
                  onChange={(e) => setFormData({ ...formData, price_yearly: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>

            {/* Limits */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">{t('admin.plans.limits')}</Label>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="max_cron_tasks" className="text-sm">{t('admin.plans.maxCronTasks')}</Label>
                  <Input
                    id="max_cron_tasks"
                    type="number"
                    min={0}
                    value={formData.max_cron_tasks}
                    onChange={(e) => setFormData({ ...formData, max_cron_tasks: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max_delayed" className="text-sm">{t('admin.plans.maxDelayedTasks')}</Label>
                  <Input
                    id="max_delayed"
                    type="number"
                    min={0}
                    value={formData.max_delayed_tasks_per_month}
                    onChange={(e) => setFormData({ ...formData, max_delayed_tasks_per_month: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max_workspaces" className="text-sm">{t('admin.plans.maxWorkspaces')}</Label>
                  <Input
                    id="max_workspaces"
                    type="number"
                    min={1}
                    value={formData.max_workspaces}
                    onChange={(e) => setFormData({ ...formData, max_workspaces: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="history_days" className="text-sm">{t('admin.plans.historyDays')}</Label>
                  <Input
                    id="history_days"
                    type="number"
                    min={1}
                    value={formData.max_execution_history_days}
                    onChange={(e) => setFormData({ ...formData, max_execution_history_days: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="min_interval" className="text-sm">{t('admin.plans.minCronInterval')}</Label>
                  <Input
                    id="min_interval"
                    type="number"
                    min={1}
                    value={formData.min_cron_interval_minutes}
                    onChange={(e) => setFormData({ ...formData, min_cron_interval_minutes: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sort_order" className="text-sm">{t('admin.plans.sortOrder')}</Label>
                  <Input
                    id="sort_order"
                    type="number"
                    value={formData.sort_order}
                    onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>
            </div>

            {/* Features */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">{t('admin.plans.features')}</Label>
              <div className="grid grid-cols-1 gap-3">
                <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                  <Label htmlFor="telegram" className="text-sm font-normal">{t('admin.plans.telegramNotifications')}</Label>
                  <Switch
                    id="telegram"
                    checked={formData.telegram_notifications}
                    onCheckedChange={(checked) => setFormData({ ...formData, telegram_notifications: checked })}
                  />
                </div>
                <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                  <Label htmlFor="email" className="text-sm font-normal">{t('admin.plans.emailNotifications')}</Label>
                  <Switch
                    id="email"
                    checked={formData.email_notifications}
                    onCheckedChange={(checked) => setFormData({ ...formData, email_notifications: checked })}
                  />
                </div>
                <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                  <Label htmlFor="webhook" className="text-sm font-normal">{t('admin.plans.webhookCallbacks')}</Label>
                  <Switch
                    id="webhook"
                    checked={formData.webhook_callbacks}
                    onCheckedChange={(checked) => setFormData({ ...formData, webhook_callbacks: checked })}
                  />
                </div>
                <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                  <Label htmlFor="headers" className="text-sm font-normal">{t('admin.plans.customHeaders')}</Label>
                  <Switch
                    id="headers"
                    checked={formData.custom_headers}
                    onCheckedChange={(checked) => setFormData({ ...formData, custom_headers: checked })}
                  />
                </div>
                <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                  <Label htmlFor="retry" className="text-sm font-normal">{t('admin.plans.retryOnFailure')}</Label>
                  <Switch
                    id="retry"
                    checked={formData.retry_on_failure}
                    onCheckedChange={(checked) => setFormData({ ...formData, retry_on_failure: checked })}
                  />
                </div>
              </div>
            </div>

            {/* Task Chains */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">{t('admin.plans.taskChains')}</Label>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="max_task_chains" className="text-sm">{t('admin.plans.maxTaskChains')}</Label>
                  <Input
                    id="max_task_chains"
                    type="number"
                    min={0}
                    value={formData.max_task_chains}
                    onChange={(e) => setFormData({ ...formData, max_task_chains: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max_chain_steps" className="text-sm">{t('admin.plans.maxChainSteps')}</Label>
                  <Input
                    id="max_chain_steps"
                    type="number"
                    min={1}
                    value={formData.max_chain_steps}
                    onChange={(e) => setFormData({ ...formData, max_chain_steps: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="min_chain_interval" className="text-sm">{t('admin.plans.minChainInterval')}</Label>
                  <Input
                    id="min_chain_interval"
                    type="number"
                    min={1}
                    value={formData.min_chain_interval_minutes}
                    onChange={(e) => setFormData({ ...formData, min_chain_interval_minutes: parseInt(e.target.value) || 1 })}
                  />
                </div>
              </div>
              <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                <Label htmlFor="chain_variables" className="text-sm font-normal">{t('admin.plans.chainVariableSubstitution')}</Label>
                <Switch
                  id="chain_variables"
                  checked={formData.chain_variable_substitution}
                  onCheckedChange={(checked) => setFormData({ ...formData, chain_variable_substitution: checked })}
                />
              </div>
            </div>

            {/* Heartbeats */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">{t('admin.plans.heartbeats')}</Label>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="max_heartbeats" className="text-sm">{t('admin.plans.maxHeartbeats')}</Label>
                  <Input
                    id="max_heartbeats"
                    type="number"
                    min={0}
                    value={formData.max_heartbeats}
                    onChange={(e) => setFormData({ ...formData, max_heartbeats: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="min_heartbeat_interval" className="text-sm">{t('admin.plans.minHeartbeatInterval')}</Label>
                  <Input
                    id="min_heartbeat_interval"
                    type="number"
                    min={1}
                    value={formData.min_heartbeat_interval_minutes}
                    onChange={(e) => setFormData({ ...formData, min_heartbeat_interval_minutes: parseInt(e.target.value) || 1 })}
                  />
                </div>
              </div>
            </div>

            {/* Overlap Prevention */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">{t('admin.plans.overlapPrevention')}</Label>
              <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                <Label htmlFor="overlap_enabled" className="text-sm font-normal">{t('admin.plans.overlapEnabled')}</Label>
                <Switch
                  id="overlap_enabled"
                  checked={formData.overlap_prevention_enabled}
                  onCheckedChange={(checked) => setFormData({ ...formData, overlap_prevention_enabled: checked })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max_queue_size" className="text-sm">{t('admin.plans.maxQueueSize')}</Label>
                <Input
                  id="max_queue_size"
                  type="number"
                  min={1}
                  value={formData.max_queue_size}
                  onChange={(e) => setFormData({ ...formData, max_queue_size: parseInt(e.target.value) || 10 })}
                />
              </div>
            </div>

            {/* Status */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">{t('admin.plans.status')}</Label>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                  <Label htmlFor="is_active" className="text-sm font-normal">{t('admin.plans.isActive')}</Label>
                  <Switch
                    id="is_active"
                    checked={formData.is_active}
                    onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                  />
                </div>
                <div className="flex items-center justify-between py-2 px-3 rounded-md border">
                  <Label htmlFor="is_public" className="text-sm font-normal">{t('admin.plans.isPublic')}</Label>
                  <Switch
                    id="is_public"
                    checked={formData.is_public}
                    onCheckedChange={(checked) => setFormData({ ...formData, is_public: checked })}
                  />
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {editingPlan ? t('common.save') : t('common.create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('admin.plans.deleteConfirm')}</DialogTitle>
            <DialogDescription>
              {t('admin.plans.deleteWarning', { name: deletingPlan?.display_name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
