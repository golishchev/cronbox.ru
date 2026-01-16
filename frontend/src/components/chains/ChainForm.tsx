import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createTaskChain, updateTaskChain } from '@/api/taskChains'
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
import { CronExpressionBuilder } from '@/components/cron/CronExpressionBuilder'
import type { TaskChain, CreateTaskChainRequest, TriggerType } from '@/types/chains'

interface ChainFormProps {
  workspaceId: string
  chain?: TaskChain
  onSuccess: () => void
  onCancel: () => void
}

const TRIGGER_TYPES: TriggerType[] = ['cron', 'delayed', 'manual']

export function ChainForm({ workspaceId, chain, onSuccess, onCancel }: ChainFormProps) {
  const { t } = useTranslation()
  const isEditing = !!chain

  const [name, setName] = useState(chain?.name ?? '')
  const [description, setDescription] = useState(chain?.description ?? '')
  const [triggerType, setTriggerType] = useState<TriggerType>(chain?.trigger_type ?? 'manual')
  const [schedule, setSchedule] = useState(chain?.schedule ?? '*/5 * * * *')
  const [timezone, setTimezone] = useState(chain?.timezone ?? 'Europe/Moscow')
  const [executeAt, setExecuteAt] = useState(chain?.execute_at ? chain.execute_at.slice(0, 16) : '')
  const [timeoutSeconds, setTimeoutSeconds] = useState(chain?.timeout_seconds ?? 300)
  const [stopOnFailure, setStopOnFailure] = useState(chain?.stop_on_failure ?? true)
  const [notifyOnFailure, setNotifyOnFailure] = useState(chain?.notify_on_failure ?? true)
  const [notifyOnSuccess, setNotifyOnSuccess] = useState(chain?.notify_on_success ?? false)
  const [notifyOnPartial, setNotifyOnPartial] = useState(chain?.notify_on_partial ?? true)

  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate
    if (!name.trim()) {
      setError(t('chains.nameRequired'))
      return
    }

    if (triggerType === 'cron' && !schedule.trim()) {
      setError(t('chains.scheduleRequired'))
      return
    }

    if (triggerType === 'delayed' && !executeAt) {
      setError(t('chains.executeAtRequired'))
      return
    }

    setIsLoading(true)

    try {
      const data: CreateTaskChainRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        trigger_type: triggerType,
        timezone,
        timeout_seconds: timeoutSeconds,
        stop_on_failure: stopOnFailure,
        notify_on_failure: notifyOnFailure,
        notify_on_success: notifyOnSuccess,
        notify_on_partial: notifyOnPartial,
      }

      if (triggerType === 'cron') {
        data.schedule = schedule.trim()
      } else if (triggerType === 'delayed') {
        data.execute_at = new Date(executeAt).toISOString()
      }

      if (isEditing) {
        await updateTaskChain(workspaceId, chain.id, data)
        toast({
          title: t('chains.chainUpdated'),
          description: t('chains.chainUpdatedDescription', { name: data.name }),
          variant: 'success',
        })
      } else {
        await createTaskChain(workspaceId, data)
        toast({
          title: t('chains.chainCreated'),
          description: t('chains.chainCreatedDescription', { name: data.name }),
          variant: 'success',
        })
      }
      onSuccess()
    } catch (err) {
      toast({
        title: isEditing ? t('chains.failedToUpdate') : t('chains.failedToCreate'),
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

      <div className="space-y-2">
        <Label htmlFor="name">{t('chains.chainName')} *</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('chains.chainNamePlaceholder')}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('common.description')}</Label>
        <Input
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t('chains.descriptionPlaceholder')}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="triggerType">{t('chains.triggerType')}</Label>
        <Select value={triggerType} onValueChange={(v) => setTriggerType(v as TriggerType)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TRIGGER_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {t(`chains.trigger${type.charAt(0).toUpperCase() + type.slice(1)}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          {triggerType === 'cron' && t('chains.cronDescription')}
          {triggerType === 'delayed' && t('chains.delayedDescription')}
          {triggerType === 'manual' && t('chains.manualDescription')}
        </p>
      </div>

      {triggerType === 'cron' && (
        <>
          <CronExpressionBuilder value={schedule} onChange={setSchedule} />

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
        </>
      )}

      {triggerType === 'delayed' && (
        <div className="space-y-2">
          <Label htmlFor="executeAt">{t('chains.executeAt')}</Label>
          <Input
            id="executeAt"
            type="datetime-local"
            value={executeAt}
            onChange={(e) => setExecuteAt(e.target.value)}
            min={new Date().toISOString().slice(0, 16)}
          />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="timeout">{t('chains.chainTimeout')}</Label>
          <Input
            id="timeout"
            type="number"
            min={1}
            max={3600}
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(parseInt(e.target.value) || 300)}
          />
          <p className="text-xs text-muted-foreground">{t('chains.chainTimeoutHelp')}</p>
        </div>
      </div>

      <div className="space-y-4 border-t pt-4">
        <p className="text-sm font-medium">{t('chains.executionSettings')}</p>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="stopOnFailure"
            checked={stopOnFailure}
            onCheckedChange={(checked) => setStopOnFailure(checked === true)}
          />
          <div className="grid gap-1.5 leading-none">
            <Label htmlFor="stopOnFailure" className="cursor-pointer">
              {t('chains.stopOnFailure')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('chains.stopOnFailureHelp')}
            </p>
          </div>
        </div>
      </div>

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
                {t('chains.notifyOnFailure')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('chains.notifyOnFailureHelp')}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="notifyOnPartial"
              checked={notifyOnPartial}
              onCheckedChange={(checked) => setNotifyOnPartial(checked === true)}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="notifyOnPartial" className="cursor-pointer">
                {t('chains.notifyOnPartial')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('chains.notifyOnPartialHelp')}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="notifyOnSuccess"
              checked={notifyOnSuccess}
              onCheckedChange={(checked) => setNotifyOnSuccess(checked === true)}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="notifyOnSuccess" className="cursor-pointer">
                {t('chains.notifyOnSuccess')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('chains.notifyOnSuccessHelp')}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          {t('common.cancel')}
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditing ? t('chains.updateChain') : t('chains.createChain')}
        </Button>
      </div>
    </form>
  )
}
