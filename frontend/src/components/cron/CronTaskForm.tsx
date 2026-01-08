import { useState } from 'react'
import { createCronTask, updateCronTask } from '@/api/cronTasks'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import type { CronTask, CreateCronTaskRequest, HttpMethod } from '@/types'

interface CronTaskFormProps {
  workspaceId: string
  task?: CronTask
  onSuccess: () => void
  onCancel: () => void
}

const HTTP_METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']

export function CronTaskForm({ workspaceId, task, onSuccess, onCancel }: CronTaskFormProps) {
  const isEditing = !!task

  const [name, setName] = useState(task?.name ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [url, setUrl] = useState(task?.url ?? '')
  const [method, setMethod] = useState<HttpMethod>(task?.method ?? 'GET')
  const [schedule, setSchedule] = useState(task?.schedule ?? '*/5 * * * *')
  const [timezone, setTimezone] = useState(task?.timezone ?? 'Europe/Moscow')
  const [timeoutSeconds, setTimeoutSeconds] = useState(task?.timeout_seconds ?? 30)
  const [retryCount, setRetryCount] = useState(task?.retry_count ?? 0)
  const [headers, setHeaders] = useState(JSON.stringify(task?.headers ?? {}, null, 2))
  const [body, setBody] = useState(task?.body ?? '')
  const [notifyOnFailure, _setNotifyOnFailure] = useState(task?.notify_on_failure ?? true)

  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    if (!url.trim()) {
      setError('URL is required')
      return
    }
    if (!schedule.trim()) {
      setError('Schedule is required')
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
      const data: CreateCronTaskRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        url: url.trim(),
        method,
        schedule: schedule.trim(),
        timezone,
        timeout_seconds: timeoutSeconds,
        retry_count: retryCount,
        headers: parsedHeaders,
        body: body.trim() || undefined,
        notify_on_failure: notifyOnFailure,
      }

      if (isEditing) {
        await updateCronTask(workspaceId, task.id, data)
        toast({
          title: 'Task updated',
          description: `"${data.name}" has been updated`,
          variant: 'success',
        })
      } else {
        await createCronTask(workspaceId, data)
        toast({
          title: 'Task created',
          description: `"${data.name}" has been created`,
          variant: 'success',
        })
      }
      onSuccess()
    } catch (err) {
      toast({
        title: isEditing ? 'Failed to update task' : 'Failed to create task',
        description: getErrorMessage(err),
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
          <Label htmlFor="name">Name *</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Health Check"
            required
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
          placeholder="https://api.example.com/health"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Input
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description"
        />
      </div>

      <CronExpressionBuilder value={schedule} onChange={setSchedule} />

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="timezone">Timezone</Label>
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
          className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
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
            className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
          />
        </div>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditing ? 'Update Task' : 'Create Task'}
        </Button>
      </div>
    </form>
  )
}
