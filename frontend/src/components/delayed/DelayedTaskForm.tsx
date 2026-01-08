import { useState } from 'react'
import { createDelayedTask } from '@/api/delayedTasks'
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
import { Loader2 } from 'lucide-react'
import type { CreateDelayedTaskRequest, HttpMethod } from '@/types'

interface DelayedTaskFormProps {
  workspaceId: string
  onSuccess: () => void
  onCancel: () => void
}

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']

// Helper to get default datetime (now + 1 hour)
function getDefaultDateTime(): string {
  const date = new Date()
  date.setHours(date.getHours() + 1)
  date.setMinutes(0)
  date.setSeconds(0)
  date.setMilliseconds(0)
  return date.toISOString().slice(0, 16) // Format: YYYY-MM-DDTHH:mm
}

// Quick schedule options
const QUICK_SCHEDULES = [
  { label: 'In 5 minutes', minutes: 5 },
  { label: 'In 15 minutes', minutes: 15 },
  { label: 'In 30 minutes', minutes: 30 },
  { label: 'In 1 hour', minutes: 60 },
  { label: 'In 3 hours', minutes: 180 },
  { label: 'In 24 hours', minutes: 1440 },
]

export function DelayedTaskForm({ workspaceId, onSuccess, onCancel }: DelayedTaskFormProps) {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [method, setMethod] = useState<HttpMethod>('GET')
  const [executeAt, setExecuteAt] = useState(getDefaultDateTime())
  const [timeoutSeconds, setTimeoutSeconds] = useState(30)
  const [retryCount, setRetryCount] = useState(0)
  const [headers, setHeaders] = useState('{}')
  const [body, setBody] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState('')
  const [callbackUrl, setCallbackUrl] = useState('')
  const [tags, setTags] = useState('')

  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleQuickSchedule = (minutes: number) => {
    const date = new Date()
    date.setMinutes(date.getMinutes() + minutes)
    setExecuteAt(date.toISOString().slice(0, 16))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate
    if (!url.trim()) {
      setError('URL is required')
      return
    }
    if (!executeAt) {
      setError('Execution time is required')
      return
    }

    // Validate execute_at is in the future
    const executeAtDate = new Date(executeAt)
    if (executeAtDate <= new Date()) {
      setError('Execution time must be in the future')
      return
    }

    let parsedHeaders: Record<string, string> = {}
    try {
      parsedHeaders = headers.trim() ? JSON.parse(headers) : {}
    } catch {
      setError('Invalid JSON in headers')
      return
    }

    setIsLoading(true)

    try {
      const data: CreateDelayedTaskRequest = {
        url: url.trim(),
        method,
        execute_at: new Date(executeAt).toISOString(),
        name: name.trim() || undefined,
        timeout_seconds: timeoutSeconds,
        retry_count: retryCount,
        headers: parsedHeaders,
        body: body.trim() || undefined,
        idempotency_key: idempotencyKey.trim() || undefined,
        callback_url: callbackUrl.trim() || undefined,
        tags: tags.trim() ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
      }

      await createDelayedTask(workspaceId, data)
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

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name">Name (optional)</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Send welcome email"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="method">HTTP Method</Label>
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
        <Label htmlFor="url">URL *</Label>
        <Input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://api.example.com/webhook"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="executeAt">Execute At *</Label>
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
              {s.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="timeout">Timeout (seconds)</Label>
          <Input
            id="timeout"
            type="number"
            min={1}
            max={300}
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(parseInt(e.target.value) || 30)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="retries">Retry Count</Label>
          <Input
            id="retries"
            type="number"
            min={0}
            max={10}
            value={retryCount}
            onChange={(e) => setRetryCount(parseInt(e.target.value) || 0)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="headers">Headers (JSON)</Label>
        <textarea
          id="headers"
          value={headers}
          onChange={(e) => setHeaders(e.target.value)}
          placeholder='{"Content-Type": "application/json"}'
          className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
        />
      </div>

      {(method === 'POST' || method === 'PUT' || method === 'PATCH') && (
        <div className="space-y-2">
          <Label htmlFor="body">Request Body</Label>
          <textarea
            id="body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder='{"key": "value"}'
            className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
          />
        </div>
      )}

      <div className="space-y-4 border-t pt-4">
        <p className="text-sm text-muted-foreground">Advanced Options</p>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="idempotencyKey">Idempotency Key</Label>
            <Input
              id="idempotencyKey"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
              placeholder="unique-task-id-123"
            />
            <p className="text-xs text-muted-foreground">
              Prevents duplicate tasks with the same key
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <Input
              id="tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="email, welcome, user-123"
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated list of tags
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="callbackUrl">Callback URL</Label>
          <Input
            id="callbackUrl"
            type="url"
            value={callbackUrl}
            onChange={(e) => setCallbackUrl(e.target.value)}
            placeholder="https://api.example.com/task-completed"
          />
          <p className="text-xs text-muted-foreground">
            URL to call after task execution (success or failure)
          </p>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Schedule Task
        </Button>
      </div>
    </form>
  )
}
