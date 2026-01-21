import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { createDelayedTask, updateDelayedTask } from '@/api/delayedTasks'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2, Globe, Radio, Plug } from 'lucide-react'
import type { CreateDelayedTaskRequest, UpdateDelayedTaskRequest, DelayedTask, HttpMethod, ProtocolType } from '@/types'

interface DelayedTaskFormProps {
  workspaceId: string
  task?: DelayedTask
  onSuccess: () => void
  onCancel: () => void
}

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']

// Format date as local datetime string for datetime-local input
function formatDateTimeLocal(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

// Helper to get default datetime (now + 1 hour)
function getDefaultDateTime(): string {
  const date = new Date()
  date.setHours(date.getHours() + 1)
  date.setMinutes(0)
  date.setSeconds(0)
  date.setMilliseconds(0)
  return formatDateTimeLocal(date)
}

// Quick schedule options
const QUICK_SCHEDULES = [
  { key: 'in5minutes', minutes: 5 },
  { key: 'in15minutes', minutes: 15 },
  { key: 'in30minutes', minutes: 30 },
  { key: 'in1hour', minutes: 60 },
  { key: 'in3hours', minutes: 180 },
  { key: 'in24hours', minutes: 1440 },
]

export function DelayedTaskForm({ workspaceId, task, onSuccess, onCancel }: DelayedTaskFormProps) {
  const { t } = useTranslation()
  const isEditMode = !!task

  // Protocol type
  const [protocolType, setProtocolType] = useState<ProtocolType>('http')

  const [name, setName] = useState('')
  // HTTP fields
  const [url, setUrl] = useState('')
  const [method, setMethod] = useState<HttpMethod>('GET')
  const [headers, setHeaders] = useState('{}')
  const [body, setBody] = useState('')
  // ICMP/TCP fields
  const [host, setHost] = useState('')
  const [port, setPort] = useState<number | ''>(443)
  const [icmpCount, setIcmpCount] = useState<number | ''>(3)
  // Schedule
  const [executeAt, setExecuteAt] = useState(getDefaultDateTime())
  const [timeoutSeconds, setTimeoutSeconds] = useState<number | ''>(30)
  const [retryCount, setRetryCount] = useState<number | ''>(0)
  const [retryDelaySeconds, setRetryDelaySeconds] = useState<number | ''>(60)
  const [idempotencyKey, setIdempotencyKey] = useState('')
  const [callbackUrl, setCallbackUrl] = useState('')
  const [tags, setTags] = useState('')

  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Initialize form with task data in edit mode
  useEffect(() => {
    if (task) {
      setProtocolType(task.protocol_type)
      setName(task.name || '')
      // HTTP fields
      setUrl(task.url || '')
      setMethod(task.method)
      setHeaders(JSON.stringify(task.headers, null, 2))
      setBody(task.body || '')
      // ICMP/TCP fields
      setHost(task.host || '')
      setPort(task.port ?? 443)
      setIcmpCount(task.icmp_count ?? 3)
      // Schedule
      setExecuteAt(formatDateTimeLocal(new Date(task.execute_at)))
      setTimeoutSeconds(task.timeout_seconds)
      setRetryCount(task.retry_count)
      setRetryDelaySeconds(task.retry_delay_seconds)
      setIdempotencyKey(task.idempotency_key || '')
      setCallbackUrl(task.callback_url || '')
      setTags(task.tags.join(', '))
    }
  }, [task])

  const handleQuickSchedule = (minutes: number) => {
    const date = new Date()
    date.setMinutes(date.getMinutes() + minutes)
    setExecuteAt(formatDateTimeLocal(date))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate
    if (!executeAt) {
      setError(t('taskForm.executeAtRequired'))
      return
    }

    // Validate execute_at is in the future
    const executeAtDate = new Date(executeAt)
    if (executeAtDate <= new Date()) {
      setError(t('taskForm.executeAtFuture'))
      return
    }

    // Protocol-specific validation
    if (protocolType === 'http') {
      if (!url.trim()) {
        setError(t('taskForm.urlRequired'))
        return
      }
    } else {
      // ICMP or TCP
      if (!host.trim()) {
        setError(t('taskForm.hostRequired'))
        return
      }
      if (protocolType === 'tcp' && (port === '' || port < 1 || port > 65535)) {
        setError(t('taskForm.portRequired'))
        return
      }
    }

    let parsedHeaders: Record<string, string> = {}
    if (protocolType === 'http') {
      try {
        parsedHeaders = headers.trim() ? JSON.parse(headers) : {}
      } catch {
        setError(t('taskForm.invalidHeadersJson'))
        return
      }
    }

    setIsLoading(true)

    try {
      if (isEditMode && task) {
        const data: UpdateDelayedTaskRequest = {
          protocol_type: protocolType,
          // HTTP fields (only for http protocol)
          ...(protocolType === 'http' ? {
            url: url.trim(),
            method,
            headers: parsedHeaders,
            body: body.trim() || undefined,
          } : {}),
          // ICMP/TCP fields
          ...(protocolType !== 'http' ? {
            host: host.trim(),
            ...(protocolType === 'tcp' ? { port: port || 443 } : {}),
            ...(protocolType === 'icmp' ? { icmp_count: icmpCount || 3 } : {}),
          } : {}),
          execute_at: new Date(executeAt).toISOString(),
          name: name.trim() || undefined,
          timeout_seconds: timeoutSeconds || 30,
          retry_count: retryCount || 0,
          retry_delay_seconds: retryDelaySeconds || 60,
          callback_url: callbackUrl.trim() || undefined,
          tags: tags.trim() ? tags.split(',').map(tag => tag.trim()).filter(Boolean) : [],
        }
        await updateDelayedTask(workspaceId, task.id, data)
      } else {
        const data: CreateDelayedTaskRequest = {
          protocol_type: protocolType,
          // HTTP fields (only for http protocol)
          ...(protocolType === 'http' ? {
            url: url.trim(),
            method,
            headers: parsedHeaders,
            body: body.trim() || undefined,
          } : {}),
          // ICMP/TCP fields
          ...(protocolType !== 'http' ? {
            host: host.trim(),
            ...(protocolType === 'tcp' ? { port: port || 443 } : {}),
            ...(protocolType === 'icmp' ? { icmp_count: icmpCount || 3 } : {}),
          } : {}),
          execute_at: new Date(executeAt).toISOString(),
          name: name.trim() || undefined,
          timeout_seconds: timeoutSeconds || 30,
          retry_count: retryCount || 0,
          retry_delay_seconds: retryDelaySeconds || 60,
          idempotency_key: idempotencyKey.trim() || undefined,
          callback_url: callbackUrl.trim() || undefined,
          tags: tags.trim() ? tags.split(',').map(tag => tag.trim()).filter(Boolean) : undefined,
        }
        await createDelayedTask(workspaceId, data)
      }
      onSuccess()
    } catch (err) {
      setError(getErrorMessage(err))
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

      {/* Protocol Type Selector */}
      <div className="space-y-2">
        <Label>{t('taskForm.protocolType')}</Label>
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => setProtocolType('http')}
            className={`flex items-center justify-center gap-2 rounded-lg border-2 p-3 transition-colors ${
              protocolType === 'http'
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border hover:border-primary/50'
            }`}
          >
            <Globe className="h-5 w-5" />
            <span className="font-medium">{t('taskForm.protocolHttp')}</span>
          </button>
          <button
            type="button"
            onClick={() => setProtocolType('icmp')}
            className={`flex items-center justify-center gap-2 rounded-lg border-2 p-3 transition-colors ${
              protocolType === 'icmp'
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border hover:border-primary/50'
            }`}
          >
            <Radio className="h-5 w-5" />
            <span className="font-medium">{t('taskForm.protocolIcmp')}</span>
          </button>
          <button
            type="button"
            onClick={() => setProtocolType('tcp')}
            className={`flex items-center justify-center gap-2 rounded-lg border-2 p-3 transition-colors ${
              protocolType === 'tcp'
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border hover:border-primary/50'
            }`}
          >
            <Plug className="h-5 w-5" />
            <span className="font-medium">{t('taskForm.protocolTcp')}</span>
          </button>
        </div>
        <p className="text-xs text-muted-foreground">
          {protocolType === 'http' && t('taskForm.protocolHttpDescription')}
          {protocolType === 'icmp' && t('taskForm.protocolIcmpDescription')}
          {protocolType === 'tcp' && t('taskForm.protocolTcpDescription')}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name">{t('taskForm.nameOptional')}</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('taskForm.namePlaceholder')}
          />
        </div>

        {protocolType === 'http' && (
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
        )}
      </div>

      {/* HTTP-specific: URL */}
      {protocolType === 'http' && (
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
      )}

      {/* ICMP/TCP: Host and Port */}
      {protocolType !== 'http' && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="host">{t('taskForm.host')} *</Label>
            <Input
              id="host"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder={t('taskForm.hostPlaceholder')}
              required
            />
          </div>

          {protocolType === 'tcp' && (
            <div className="space-y-2">
              <Label htmlFor="port">{t('taskForm.port')} *</Label>
              <Input
                id="port"
                type="number"
                min={1}
                max={65535}
                value={port}
                onChange={(e) => setPort(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => {
                  if (port === '' || port < 1) setPort(443)
                }}
                placeholder="443"
              />
            </div>
          )}

          {protocolType === 'icmp' && (
            <div className="space-y-2">
              <Label htmlFor="icmpCount">{t('taskForm.icmpCount')}</Label>
              <Input
                id="icmpCount"
                type="number"
                min={1}
                max={10}
                value={icmpCount}
                onChange={(e) => setIcmpCount(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => {
                  if (icmpCount === '' || icmpCount < 1) setIcmpCount(3)
                }}
              />
              <p className="text-xs text-muted-foreground">{t('taskForm.icmpCountDescription')}</p>
            </div>
          )}
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="executeAt">{t('taskForm.executeAt')} *</Label>
        <div className="flex gap-2">
          <Input
            id="executeAt"
            type="datetime-local"
            value={executeAt}
            onChange={(e) => setExecuteAt(e.target.value)}
            required
            className="flex-1"
          />
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {QUICK_SCHEDULES.map((s) => (
            <Button
              key={s.minutes}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleQuickSchedule(s.minutes)}
            >
              {t(`taskForm.${s.key}`)}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
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

      {/* HTTP-specific: Headers and Body */}
      {protocolType === 'http' && (
        <>
          <div className="space-y-2">
            <Label htmlFor="headers">{t('taskForm.headers')} (JSON)</Label>
            <textarea
              id="headers"
              value={headers}
              onChange={(e) => setHeaders(e.target.value)}
              placeholder={t('taskForm.headersPlaceholder')}
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
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
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
              />
            </div>
          )}
        </>
      )}

      <div className="space-y-4 border-t pt-4">
        <p className="text-sm text-muted-foreground">{t('taskForm.advancedOptions')}</p>

        <div className={`grid gap-4 ${isEditMode ? '' : 'md:grid-cols-2'}`}>
          {!isEditMode && (
            <div className="space-y-2">
              <Label htmlFor="idempotencyKey">{t('taskForm.idempotencyKey')}</Label>
              <Input
                id="idempotencyKey"
                value={idempotencyKey}
                onChange={(e) => setIdempotencyKey(e.target.value)}
                placeholder="unique-task-id-123"
              />
              <p className="text-xs text-muted-foreground">
                {t('taskForm.idempotencyKeyHint')}
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="tags">{t('taskForm.tags')}</Label>
            <Input
              id="tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder={t('taskForm.tagsPlaceholder')}
            />
            <p className="text-xs text-muted-foreground">
              {t('taskForm.tagsHint')}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="callbackUrl">{t('taskForm.callbackUrl')}</Label>
          <Input
            id="callbackUrl"
            type="url"
            value={callbackUrl}
            onChange={(e) => setCallbackUrl(e.target.value)}
            placeholder="https://api.example.com/task-completed"
          />
          <p className="text-xs text-muted-foreground">
            {t('taskForm.callbackUrlHint')}
          </p>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          {t('common.cancel')}
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditMode ? t('common.saveChanges') : t('taskForm.scheduleTask')}
        </Button>
      </div>
    </form>
  )
}
