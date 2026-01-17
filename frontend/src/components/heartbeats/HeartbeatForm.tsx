import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createHeartbeat, updateHeartbeat } from '@/api/heartbeats'
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
import type { Heartbeat, CreateHeartbeatRequest } from '@/types'

interface HeartbeatFormProps {
  workspaceId: string
  heartbeat?: Heartbeat
  onSuccess: () => void
  onCancel: () => void
}

// Convert seconds to human-readable interval string
function secondsToInterval(seconds: number): string {
  if (seconds >= 86400 && seconds % 86400 === 0) {
    return `${seconds / 86400}d`
  }
  if (seconds >= 3600 && seconds % 3600 === 0) {
    return `${seconds / 3600}h`
  }
  if (seconds >= 60 && seconds % 60 === 0) {
    return `${seconds / 60}m`
  }
  return `${seconds}s`
}

const INTERVAL_VALUES = ['5m', '10m', '15m', '30m', '1h', '2h', '6h', '12h', '1d'] as const
const GRACE_VALUES = ['5m', '10m', '15m', '30m', '1h'] as const

export function HeartbeatForm({ workspaceId, heartbeat, onSuccess, onCancel }: HeartbeatFormProps) {
  const { t } = useTranslation()
  const isEditing = !!heartbeat

  const [name, setName] = useState(heartbeat?.name ?? '')
  const [description, setDescription] = useState(heartbeat?.description ?? '')
  const [expectedInterval, setExpectedInterval] = useState(
    heartbeat ? secondsToInterval(heartbeat.expected_interval) : '1h'
  )
  const [customInterval, setCustomInterval] = useState('')
  const [gracePeriod, setGracePeriod] = useState(
    heartbeat ? secondsToInterval(heartbeat.grace_period) : '10m'
  )
  const [customGrace, setCustomGrace] = useState('')
  const [notifyOnLate, setNotifyOnLate] = useState(heartbeat?.notify_on_late ?? true)
  const [notifyOnRecovery, setNotifyOnRecovery] = useState(heartbeat?.notify_on_recovery ?? true)

  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!name.trim()) {
      setError(t('heartbeats.nameRequired'))
      return
    }

    const finalInterval = expectedInterval === 'custom' ? customInterval : expectedInterval
    const finalGrace = gracePeriod === 'custom' ? customGrace : gracePeriod

    if (!finalInterval) {
      setError(t('heartbeats.intervalRequired'))
      return
    }

    setIsLoading(true)

    try {
      const data: CreateHeartbeatRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        expected_interval: finalInterval,
        grace_period: finalGrace,
        notify_on_late: notifyOnLate,
        notify_on_recovery: notifyOnRecovery,
      }

      if (isEditing) {
        await updateHeartbeat(workspaceId, heartbeat.id, data)
        toast({
          title: t('heartbeats.updated'),
          description: t('heartbeats.updatedDescription', { name: data.name }),
          variant: 'success',
        })
      } else {
        await createHeartbeat(workspaceId, data)
        toast({
          title: t('heartbeats.created'),
          description: t('heartbeats.createdDescription', { name: data.name }),
          variant: 'success',
        })
      }
      onSuccess()
    } catch (err) {
      toast({
        title: isEditing ? t('heartbeats.failedToUpdate') : t('heartbeats.failedToCreate'),
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
        <Label htmlFor="name">{t('heartbeats.name')} *</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('heartbeats.namePlaceholder')}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('heartbeats.description')}</Label>
        <Input
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t('heartbeats.descriptionPlaceholder')}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="expectedInterval">{t('heartbeats.expectedInterval')} *</Label>
          <Select value={expectedInterval} onValueChange={setExpectedInterval}>
            <SelectTrigger>
              <SelectValue placeholder={t('heartbeats.selectInterval')} />
            </SelectTrigger>
            <SelectContent>
              {INTERVAL_VALUES.map((value) => (
                <SelectItem key={value} value={value}>
                  {t(`heartbeats.intervals.${value}`)}
                </SelectItem>
              ))}
              <SelectItem value="custom">{t('common.custom')}</SelectItem>
            </SelectContent>
          </Select>
          {expectedInterval === 'custom' && (
            <Input
              value={customInterval}
              onChange={(e) => setCustomInterval(e.target.value)}
              placeholder={t('heartbeats.customIntervalPlaceholder')}
              className="mt-2"
            />
          )}
          <p className="text-xs text-muted-foreground">
            {t('heartbeats.expectedIntervalHelp')}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="gracePeriod">{t('heartbeats.gracePeriod')}</Label>
          <Select value={gracePeriod} onValueChange={setGracePeriod}>
            <SelectTrigger>
              <SelectValue placeholder={t('heartbeats.selectGracePeriod')} />
            </SelectTrigger>
            <SelectContent>
              {GRACE_VALUES.map((value) => (
                <SelectItem key={value} value={value}>
                  {t(`heartbeats.intervals.${value}`)}
                </SelectItem>
              ))}
              <SelectItem value="custom">{t('common.custom')}</SelectItem>
            </SelectContent>
          </Select>
          {gracePeriod === 'custom' && (
            <Input
              value={customGrace}
              onChange={(e) => setCustomGrace(e.target.value)}
              placeholder={t('heartbeats.customGracePlaceholder')}
              className="mt-2"
            />
          )}
          <p className="text-xs text-muted-foreground">
            {t('heartbeats.gracePeriodHelp')}
          </p>
        </div>
      </div>

      <div className="space-y-4 border-t pt-4">
        <p className="text-sm font-medium">{t('notifications.events')}</p>
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="notifyOnLate"
              checked={notifyOnLate}
              onCheckedChange={(checked) => setNotifyOnLate(checked === true)}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="notifyOnLate" className="cursor-pointer">
                {t('heartbeats.notifyOnLate')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('heartbeats.notifyOnLateHelp')}
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
                {t('heartbeats.notifyOnRecovery')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('heartbeats.notifyOnRecoveryHelp')}
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
          {isEditing ? t('heartbeats.update') : t('heartbeats.create')}
        </Button>
      </div>
    </form>
  )
}
