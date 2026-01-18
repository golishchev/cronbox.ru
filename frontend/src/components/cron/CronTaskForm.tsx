import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createCronTask, updateCronTask } from '@/api/cronTasks'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { toast } from '@/hooks/use-toast'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2 } from 'lucide-react'
import { CronExpressionBuilder } from './CronExpressionBuilder'
import type { CronTask, CreateCronTaskRequest, HttpMethod, OverlapPolicy } from '@/types'

interface CronTaskFormProps {
  workspaceId: string
  task?: CronTask
  onSuccess: () => void
  onCancel: () => void
}

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']

export function CronTaskForm({ workspaceId, task, onSuccess, onCancel }: CronTaskFormProps) {
  const { t } = useTranslation()
  const isEditing = !!task

  const [name, setName] = useState(task?.name ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [url, setUrl] = useState(task?.url ?? '')
  const [method, setMethod] = useState<HttpMethod>(task?.method ?? 'GET')
  const [schedule, setSchedule] = useState(task?.schedule ?? '*/5 * * * *')
  const [timezone, setTimezone] = useState(task?.timezone ?? 'Europe/Moscow')
  const [timeoutSeconds, setTimeoutSeconds] = useState<number | ''>(task?.timeout_seconds ?? 30)
  const [retryCount, setRetryCount] = useState<number | ''>(task?.retry_count ?? 0)
  const [retryDelaySeconds, setRetryDelaySeconds] = useState<number | ''>(task?.retry_delay_seconds ?? 60)
  const [headers, setHeaders] = useState(JSON.stringify(task?.headers ?? {}, null, 2))
  const [body, setBody] = useState(task?.body ?? '')
  const [notifyOnFailure, setNotifyOnFailure] = useState(task?.notify_on_failure ?? true)
  const [notifyOnRecovery, setNotifyOnRecovery] = useState(task?.notify_on_recovery ?? true)

  // Overlap prevention settings
  const [overlapPolicy, setOverlapPolicy] = useState<OverlapPolicy>(task?.overlap_policy ?? 'allow')
  const [maxInstances, setMaxInstances] = useState<number | ''>(task?.max_instances ?? 1)
  const [maxQueueSize, setMaxQueueSize] = useState<number | ''>(task?.max_queue_size ?? 10)
  const [executionTimeout, setExecutionTimeout] = useState<number | ''>(task?.execution_timeout ?? 0)

  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate
    if (!name.trim()) {
      setError(t('taskForm.nameRequired'))
      return
    }
    if (!url.trim()) {
      setError(t('taskForm.urlRequired'))
      return
    }
    if (!schedule.trim()) {
      setError(t('taskForm.scheduleRequired'))
      return
    }

    let parsedHeaders: Record<string, string> = {}
    try {
      parsedHeaders = headers.trim() ? JSON.parse(headers) : {}
    } catch {
      setError(t('taskForm.invalidHeadersJson'))
      return
    }

    setIsLoading(true)

    try {
      const data: CreateCronTaskRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        url: url.trim(),
        method,
        schedule: schedule.trim(),
        timezone,
        timeout_seconds: timeoutSeconds || 30,
        retry_count: retryCount || 0,
        retry_delay_seconds: retryDelaySeconds || 60,
        headers: parsedHeaders,
        body: body.trim() || undefined,
        notify_on_failure: notifyOnFailure,
        notify_on_recovery: notifyOnRecovery,
        // Overlap prevention
        overlap_policy: overlapPolicy,
        max_instances: maxInstances || 1,
        max_queue_size: maxQueueSize || 10,
        execution_timeout: executionTimeout && executionTimeout > 0 ? executionTimeout : undefined,
      }

      if (isEditing) {
        await updateCronTask(workspaceId, task.id, data)
        toast({
          title: t('taskForm.taskUpdated'),
          description: t('taskForm.taskUpdatedDescription', { name: data.name }),
          variant: 'success',
        })
      } else {
        await createCronTask(workspaceId, data)
        toast({
          title: t('taskForm.taskCreated'),
          description: t('taskForm.taskCreatedDescription', { name: data.name }),
          variant: 'success',
        })
      }
      onSuccess()
    } catch (err) {
      toast({
        title: isEditing ? t('taskForm.failedToUpdate') : t('taskForm.failedToCreate'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name">{t('taskForm.name')} *</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('taskForm.namePlaceholder')}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="method">{t('taskForm.method')}</Label>
          <Select value={method} onValueChange={(v) => setMethod(v as HttpMethod)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {HTTP_METHODS.map((m) => (
                <SelectItem key={m} value={m}>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="url">{t('taskForm.url')} *</Label>
        <Input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={t('taskForm.urlPlaceholder')}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('taskForm.description')}</Label>
        <Input
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t('taskForm.descriptionPlaceholder')}
        />
      </div>

      <CronExpressionBuilder value={schedule} onChange={setSchedule} />

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="timezone">{t('taskForm.timezone')}</Label>
          <Select value={timezone} onValueChange={setTimezone}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Europe/Moscow">Europe/Moscow</SelectItem>
              <SelectItem value="UTC">UTC</SelectItem>
              <SelectItem value="America/New_York">America/New_York</SelectItem>
              <SelectItem value="America/Los_Angeles">America/Los_Angeles</SelectItem>
              <SelectItem value="Europe/London">Europe/London</SelectItem>
              <SelectItem value="Asia/Tokyo">Asia/Tokyo</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="timeout">{t('taskForm.timeoutSeconds')}</Label>
          <Input
            id="timeout"
            type="number"
            min={1}
            max={300}
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(e.target.value === '' ? '' : parseInt(e.target.value))}
            onBlur={() => {
              if (timeoutSeconds === '' || timeoutSeconds < 1) setTimeoutSeconds(30)
            }}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="retries">{t('taskForm.retryCount')}</Label>
          <Input
            id="retries"
            type="number"
            min={0}
            max={10}
            value={retryCount}
            onChange={(e) => setRetryCount(e.target.value === '' ? '' : parseInt(e.target.value))}
            onBlur={() => {
              if (retryCount === '' || retryCount < 0) setRetryCount(0)
            }}
          />
        </div>
      </div>

      {typeof retryCount === 'number' && retryCount > 0 && (
        <div className="space-y-2">
          <Label htmlFor="retryDelay">{t('taskForm.retryDelaySeconds')}</Label>
          <Input
            id="retryDelay"
            type="number"
            min={1}
            max={3600}
            value={retryDelaySeconds}
            onChange={(e) => setRetryDelaySeconds(e.target.value === '' ? '' : parseInt(e.target.value))}
            onBlur={() => {
              if (retryDelaySeconds === '' || retryDelaySeconds < 1) setRetryDelaySeconds(60)
            }}
          />
        </div>
      )}

      <div className="space-y-4 border-t pt-4">
        <p className="text-sm font-medium">{t('notifications.events')}</p>
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="notifyOnFailure"
              checked={notifyOnFailure}
              onCheckedChange={(checked) => setNotifyOnFailure(checked === true)}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="notifyOnFailure" className="cursor-pointer">
                {t('taskForm.notifyOnFailure')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('notifications.taskFailureDescription')}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="notifyOnRecovery"
              checked={notifyOnRecovery}
              onCheckedChange={(checked) => setNotifyOnRecovery(checked === true)}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="notifyOnRecovery" className="cursor-pointer">
                {t('taskForm.notifyOnRecovery')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('notifications.taskRecoveryDescription')}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Overlap Prevention Settings */}
      <div className="space-y-4 border-t pt-4">
        <p className="text-sm font-medium">{t('taskForm.overlapPrevention')}</p>
        <p className="text-xs text-muted-foreground">{t('taskForm.overlapPreventionDescription')}</p>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="overlapPolicy">{t('taskForm.overlapPolicy')}</Label>
            <Select value={overlapPolicy} onValueChange={(v) => setOverlapPolicy(v as OverlapPolicy)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="allow">{t('taskForm.overlapPolicyAllow')}</SelectItem>
                <SelectItem value="skip">{t('taskForm.overlapPolicySkip')}</SelectItem>
                <SelectItem value="queue">{t('taskForm.overlapPolicyQueue')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {overlapPolicy !== 'allow' && (
            <div className="space-y-2">
              <Label htmlFor="maxInstances">{t('taskForm.maxInstances')}</Label>
              <Input
                id="maxInstances"
                type="number"
                min={1}
                max={10}
                value={maxInstances}
                onChange={(e) => setMaxInstances(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => {
                  if (maxInstances === '' || maxInstances < 1) setMaxInstances(1)
                }}
              />
            </div>
          )}
        </div>

        {overlapPolicy === 'queue' && (
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="maxQueueSize">{t('taskForm.maxQueueSize')}</Label>
              <Input
                id="maxQueueSize"
                type="number"
                min={1}
                max={100}
                value={maxQueueSize}
                onChange={(e) => setMaxQueueSize(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => {
                  if (maxQueueSize === '' || maxQueueSize < 1) setMaxQueueSize(10)
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="executionTimeout">{t('taskForm.executionTimeout')}</Label>
              <Input
                id="executionTimeout"
                type="number"
                min={0}
                max={86400}
                value={executionTimeout}
                onChange={(e) => setExecutionTimeout(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => {
                  if (executionTimeout === '' || executionTimeout < 0) setExecutionTimeout(0)
                }}
              />
              <p className="text-xs text-muted-foreground">{t('taskForm.executionTimeoutDescription')}</p>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="headers">{t('taskForm.headers')} (JSON)</Label>
        <textarea
          id="headers"
          value={headers}
          onChange={(e) => setHeaders(e.target.value)}
          placeholder={t('taskForm.headersPlaceholder')}
          className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
        />
      </div>

      {(method === 'POST' || method === 'PUT' || method === 'PATCH') && (
        <div className="space-y-2">
          <Label htmlFor="body">{t('taskForm.body')}</Label>
          <textarea
            id="body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder='{"key": "value"}'
            className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
          />
        </div>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          {t('common.cancel')}
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditing ? t('taskForm.updateTask') : t('taskForm.createTask')}
        </Button>
      </div>
    </form>
  )
}
