import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import DOMPurify from 'dompurify'
import {
  getNotificationTemplates,
  updateNotificationTemplate,
  previewNotificationTemplate,
  resetNotificationTemplate,
  NotificationTemplate,
  UpdateTemplateRequest,
} from '@/api/admin'
import { getErrorMessage } from '@/api/client'
import { toast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { TableSkeleton } from '@/components/ui/skeleton'
import {
  Bell,
  ChevronLeft,
  Pencil,
  RotateCcw,
  Eye,
  Loader2,
  Mail,
  MessageSquare,
  Check,
  X,
} from 'lucide-react'

interface AdminNotificationTemplatesPageProps {
  onNavigate: (route: string) => void
}

const TEMPLATE_CODES = [
  'task_failure',
  'task_recovery',
  'task_success',
  'subscription_expiring',
  'subscription_expired',
]

const LANGUAGES = ['ru', 'en']
const CHANNELS = ['EMAIL', 'TELEGRAM']

const DEFAULT_VARIABLES: Record<string, Record<string, string>> = {
  task_failure: {
    workspace_name: 'My Workspace',
    task_name: 'Daily Backup',
    task_url: 'https://example.com/api/backup',
    error_message: 'Connection timeout',
    status_code: '500',
  },
  task_recovery: {
    workspace_name: 'My Workspace',
    task_name: 'Daily Backup',
    task_url: 'https://example.com/api/backup',
  },
  task_success: {
    workspace_name: 'My Workspace',
    task_name: 'Daily Backup',
    task_url: 'https://example.com/api/backup',
    status_code: '200',
  },
  subscription_expiring: {
    workspace_name: 'My Workspace',
    plan_name: 'Pro',
    expires_at: '2025-02-15',
    days_left: '7',
  },
  subscription_expired: {
    workspace_name: 'My Workspace',
    plan_name: 'Pro',
  },
}

export function AdminNotificationTemplatesPage({ onNavigate }: AdminNotificationTemplatesPageProps) {
  const { t } = useTranslation()
  const [templates, setTemplates] = useState<NotificationTemplate[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Filters (use 'all' instead of '' for Radix Select compatibility)
  const [filterCode, setFilterCode] = useState<string>('all')
  const [filterLanguage, setFilterLanguage] = useState<string>('all')
  const [filterChannel, setFilterChannel] = useState<string>('all')

  // Edit dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplate | null>(null)
  const [formSubject, setFormSubject] = useState<string>('')
  const [formBody, setFormBody] = useState<string>('')
  const [formIsActive, setFormIsActive] = useState(true)

  // Preview state
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewSubject, setPreviewSubject] = useState<string | null>(null)
  const [previewBody, setPreviewBody] = useState<string>('')
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)

  // Reset confirmation
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [resettingTemplate, setResettingTemplate] = useState<NotificationTemplate | null>(null)

  const loadTemplates = async () => {
    setIsLoading(true)
    try {
      const params: Record<string, string> = {}
      if (filterCode && filterCode !== 'all') params.code = filterCode
      if (filterLanguage && filterLanguage !== 'all') params.language = filterLanguage
      if (filterChannel && filterChannel !== 'all') params.channel = filterChannel

      const response = await getNotificationTemplates(
        Object.keys(params).length > 0 ? params : undefined
      )
      setTemplates(response.templates)
    } catch (err) {
      toast({
        title: t('admin.templates.errorLoading'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadTemplates()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterCode, filterLanguage, filterChannel])

  const handleOpenEdit = (template: NotificationTemplate) => {
    setEditingTemplate(template)
    setFormSubject(template.subject || '')
    setFormBody(template.body)
    setFormIsActive(template.is_active)
    setDialogOpen(true)
  }

  const handleSubmit = async () => {
    if (!editingTemplate) return
    setIsSubmitting(true)
    try {
      const data: UpdateTemplateRequest = {
        body: formBody,
        is_active: formIsActive,
      }
      if (editingTemplate.channel === 'EMAIL') {
        data.subject = formSubject || null
      }
      await updateNotificationTemplate(editingTemplate.id, data)
      toast({
        title: t('admin.templates.updated'),
        description: t('admin.templates.updatedDescription'),
      })
      setDialogOpen(false)
      loadTemplates()
    } catch (err) {
      toast({
        title: t('admin.templates.errorUpdating'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handlePreview = async () => {
    if (!editingTemplate) return
    setIsPreviewLoading(true)
    try {
      const variables = DEFAULT_VARIABLES[editingTemplate.code] || {}
      const response = await previewNotificationTemplate({
        body: formBody,
        subject: editingTemplate.channel === 'EMAIL' ? formSubject : undefined,
        variables,
      })
      setPreviewSubject(response.subject)
      setPreviewBody(response.body)
      setPreviewOpen(true)
    } catch (err) {
      toast({
        title: t('admin.templates.errorPreview'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsPreviewLoading(false)
    }
  }

  const handleReset = async () => {
    if (!resettingTemplate) return
    setIsSubmitting(true)
    try {
      await resetNotificationTemplate(resettingTemplate.id)
      toast({
        title: t('admin.templates.reset'),
        description: t('admin.templates.resetDescription'),
      })
      setResetDialogOpen(false)
      setResettingTemplate(null)
      // If editing this template, close the edit dialog too
      if (editingTemplate?.id === resettingTemplate.id) {
        setDialogOpen(false)
      }
      loadTemplates()
    } catch (err) {
      toast({
        title: t('admin.templates.errorReset'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const getCodeLabel = (code: string) => {
    return t(`admin.templates.codes.${code}`, code)
  }

  const getChannelIcon = (channel: string) => {
    return channel === 'EMAIL' ? (
      <Mail className="h-4 w-4" />
    ) : (
      <MessageSquare className="h-4 w-4" />
    )
  }

  const BooleanBadge = ({ value }: { value: boolean }) =>
    value ? (
      <Badge variant="success" className="gap-1">
        <Check className="h-3 w-3" />
      </Badge>
    ) : (
      <Badge variant="outline" className="gap-1">
        <X className="h-3 w-3" />
      </Badge>
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
          <h1 className="text-3xl font-bold tracking-tight mt-2">
            {t('admin.templates.title')}
          </h1>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="w-48">
          <Select value={filterCode} onValueChange={setFilterCode}>
            <SelectTrigger>
              <SelectValue placeholder={t('admin.templates.filterCode')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.all')}</SelectItem>
              {TEMPLATE_CODES.map((code) => (
                <SelectItem key={code} value={code}>
                  {getCodeLabel(code)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-36">
          <Select value={filterLanguage} onValueChange={setFilterLanguage}>
            <SelectTrigger>
              <SelectValue placeholder={t('admin.templates.filterLanguage')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.all')}</SelectItem>
              {LANGUAGES.map((lang) => (
                <SelectItem key={lang} value={lang}>
                  {lang.toUpperCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-40">
          <Select value={filterChannel} onValueChange={setFilterChannel}>
            <SelectTrigger>
              <SelectValue placeholder={t('admin.templates.filterChannel')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.all')}</SelectItem>
              {CHANNELS.map((channel) => (
                <SelectItem key={channel} value={channel}>
                  {channel === 'EMAIL' ? 'Email' : 'Telegram'}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center text-sm text-muted-foreground">
          {templates.length} {t('common.total')}
        </div>
      </div>

      {/* Templates Table */}
      {isLoading ? (
        <TableSkeleton rows={10} columns={6} />
      ) : templates.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-4">
          <Bell className="h-16 w-16 text-muted-foreground" />
          <h2 className="text-xl font-semibold">{t('admin.templates.noTemplates')}</h2>
          <p className="text-muted-foreground">{t('admin.templates.noTemplatesDescription')}</p>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('admin.templates.code')}</TableHead>
                <TableHead>{t('admin.templates.language')}</TableHead>
                <TableHead>{t('admin.templates.channel')}</TableHead>
                <TableHead>{t('admin.templates.subject')}</TableHead>
                <TableHead>{t('admin.templates.status')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {templates.map((template) => (
                <TableRow key={template.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{getCodeLabel(template.code)}</p>
                      <p className="text-sm text-muted-foreground font-mono">
                        {template.code}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{template.language.toUpperCase()}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {getChannelIcon(template.channel)}
                      <span>{template.channel === 'EMAIL' ? 'Email' : 'Telegram'}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {template.channel === 'EMAIL' ? (
                      <span className="text-sm truncate max-w-[200px] block">
                        {template.subject || '-'}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <BooleanBadge value={template.is_active} />
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleOpenEdit(template)}
                        title={t('common.edit')}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setResettingTemplate(template)
                          setResetDialogOpen(true)
                        }}
                        title={t('admin.templates.resetToDefault')}
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('admin.templates.edit')}</DialogTitle>
            <DialogDescription>
              {editingTemplate && (
                <span>
                  {getCodeLabel(editingTemplate.code)} &middot;{' '}
                  {editingTemplate.language.toUpperCase()} &middot;{' '}
                  {editingTemplate.channel === 'EMAIL' ? 'Email' : 'Telegram'}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Description */}
            {editingTemplate?.description && (
              <div className="p-3 bg-muted rounded-md text-sm">
                {editingTemplate.description}
              </div>
            )}

            {/* Subject (Email only) */}
            {editingTemplate?.channel === 'EMAIL' && (
              <div className="space-y-2">
                <Label htmlFor="subject">{t('admin.templates.subject')}</Label>
                <Input
                  id="subject"
                  value={formSubject}
                  onChange={(e) => setFormSubject(e.target.value)}
                  placeholder={t('admin.templates.subjectPlaceholder')}
                />
              </div>
            )}

            {/* Body */}
            <div className="space-y-2">
              <Label htmlFor="body">{t('admin.templates.body')}</Label>
              <Textarea
                id="body"
                value={formBody}
                onChange={(e) => setFormBody(e.target.value)}
                rows={10}
                className="font-mono text-sm"
              />
            </div>

            {/* Variables */}
            {editingTemplate && editingTemplate.variables.length > 0 && (
              <div className="space-y-2">
                <Label>{t('admin.templates.availableVariables')}</Label>
                <div className="flex flex-wrap gap-2">
                  {editingTemplate.variables.map((variable) => (
                    <Badge key={variable} variant="secondary" className="font-mono">
                      {`{${variable}}`}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Active Switch */}
            <div className="flex items-center justify-between py-2 px-3 rounded-md border">
              <Label htmlFor="is_active" className="text-sm font-normal">
                {t('admin.templates.isActive')}
              </Label>
              <Switch
                id="is_active"
                checked={formIsActive}
                onCheckedChange={setFormIsActive}
              />
            </div>
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={handlePreview}
              disabled={isPreviewLoading}
            >
              {isPreviewLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              {t('admin.templates.preview')}
            </Button>
            <div className="flex-1" />
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('admin.templates.previewTitle')}</DialogTitle>
            <DialogDescription>
              {t('admin.templates.previewDescription')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {previewSubject && (
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">
                  {t('admin.templates.subject')}
                </Label>
                <p className="font-medium">{previewSubject}</p>
              </div>
            )}
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">
                {t('admin.templates.body')}
              </Label>
              <div
                className="p-4 bg-muted rounded-md prose prose-sm dark:prose-invert max-w-none"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(previewBody) }}
              />
            </div>
          </div>

          <DialogFooter>
            <Button onClick={() => setPreviewOpen(false)}>{t('common.close')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Confirmation Dialog */}
      <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('admin.templates.resetConfirm')}</DialogTitle>
            <DialogDescription>
              {t('admin.templates.resetWarning')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleReset} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('admin.templates.resetToDefault')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
