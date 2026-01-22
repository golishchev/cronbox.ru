import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createProcessMonitor, updateProcessMonitor } from '@/api/processMonitors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from '@/hooks/use-toast'
import { Loader2 } from 'lucide-react'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import type { ProcessMonitor, CreateProcessMonitorRequest, ScheduleType } from '@/types'

interface ProcessMonitorFormProps {
  workspaceId: string
  monitor?: ProcessMonitor
  onSuccess: (monitor?: ProcessMonitor) => void
  onCancel: () => void
}

const TIMEZONES = [
  'Europe/Moscow',
  'UTC',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Singapore',
  'Australia/Sydney',
]

function formatSecondsToInterval(seconds: number | null): string {
  if (seconds === null) return '1h'
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

export function ProcessMonitorForm({
  workspaceId,
  monitor,
  onSuccess,
  onCancel,
}: ProcessMonitorFormProps) {
  const { t } = useTranslation()
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state
  const [name, setName] = useState(monitor?.name || '')
  const [description, setDescription] = useState(monitor?.description || '')
  const [scheduleType, setScheduleType] = useState<ScheduleType>(
    monitor?.schedule_type || 'cron'
  )
  const [scheduleCron, setScheduleCron] = useState(monitor?.schedule_cron || '0 */6 * * *')
  const [scheduleInterval, setScheduleInterval] = useState(
    monitor?.schedule_interval ? formatSecondsToInterval(monitor.schedule_interval) : '6h'
  )
  const [scheduleExactTime, setScheduleExactTime] = useState(
    monitor?.schedule_exact_time || '09:00'
  )
  const [timezone, setTimezone] = useState(monitor?.timezone || 'Europe/Moscow')
  const [startGracePeriod, setStartGracePeriod] = useState(
    monitor?.start_grace_period ? formatSecondsToInterval(monitor.start_grace_period) : '5m'
  )
  const [endTimeout, setEndTimeout] = useState(
    monitor?.end_timeout ? formatSecondsToInterval(monitor.end_timeout) : '1h'
  )
  const [notifyOnMissedStart, setNotifyOnMissedStart] = useState(
    monitor?.notify_on_missed_start ?? true
  )
  const [notifyOnMissedEnd, setNotifyOnMissedEnd] = useState(
    monitor?.notify_on_missed_end ?? true
  )
  const [notifyOnRecovery, setNotifyOnRecovery] = useState(
    monitor?.notify_on_recovery ?? true
  )
  const [notifyOnSuccess, setNotifyOnSuccess] = useState(
    monitor?.notify_on_success ?? false
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      const data: CreateProcessMonitorRequest = {
        name,
        description: description || undefined,
        schedule_type: scheduleType,
        timezone,
        start_grace_period: startGracePeriod,
        end_timeout: endTimeout,
        notify_on_missed_start: notifyOnMissedStart,
        notify_on_missed_end: notifyOnMissedEnd,
        notify_on_recovery: notifyOnRecovery,
        notify_on_success: notifyOnSuccess,
      }

      // Add schedule-specific field
      if (scheduleType === 'cron') {
        data.schedule_cron = scheduleCron
      } else if (scheduleType === 'interval') {
        data.schedule_interval = scheduleInterval
      } else if (scheduleType === 'exact_time') {
        data.schedule_exact_time = scheduleExactTime
      }

      let result: ProcessMonitor
      if (monitor) {
        result = await updateProcessMonitor(workspaceId, monitor.id, data)
        toast({
          title: t('processMonitors.updated'),
          description: t('processMonitors.updatedDescription', { name: result.name }),
          variant: 'success',
        })
        onSuccess()
      } else {
        result = await createProcessMonitor(workspaceId, data)
        toast({
          title: t('processMonitors.created'),
          description: t('processMonitors.createdDescription', { name: result.name }),
          variant: 'success',
        })
        onSuccess(result)
      }
    } catch (err) {
      toast({
        title: monitor ? t('processMonitors.updateFailed') : t('processMonitors.createFailed'),
        description: translateApiError(getErrorMessage(err), t),
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">{t('common.name')} *</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('processMonitors.namePlaceholder')}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">{t('common.description')}</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t('processMonitors.descriptionPlaceholder')}
            rows={2}
          />
        </div>
      </div>

      {/* Schedule */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium">{t('processMonitors.scheduleSection')}</h3>

        <div className="space-y-2">
          <Label htmlFor="scheduleType">{t('processMonitors.scheduleType')}</Label>
          <Select value={scheduleType} onValueChange={(v) => setScheduleType(v as ScheduleType)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="cron">{t('processMonitors.scheduleTypeCron')}</SelectItem>
              <SelectItem value="interval">{t('processMonitors.scheduleTypeInterval')}</SelectItem>
              <SelectItem value="exact_time">{t('processMonitors.scheduleTypeExactTime')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {scheduleType === 'cron' && (
          <div className="space-y-2">
            <Label htmlFor="scheduleCron">{t('processMonitors.cronExpression')} *</Label>
            <Input
              id="scheduleCron"
              value={scheduleCron}
              onChange={(e) => setScheduleCron(e.target.value)}
              placeholder="0 */6 * * *"
              required
            />
            <p className="text-xs text-muted-foreground">
              {t('processMonitors.cronHelp')}
            </p>
          </div>
        )}

        {scheduleType === 'interval' && (
          <div className="space-y-2">
            <Label htmlFor="scheduleInterval">{t('processMonitors.intervalValue')} *</Label>
            <Input
              id="scheduleInterval"
              value={scheduleInterval}
              onChange={(e) => setScheduleInterval(e.target.value)}
              placeholder="6h"
              required
            />
            <p className="text-xs text-muted-foreground">
              {t('processMonitors.intervalHelp')}
            </p>
          </div>
        )}

        {scheduleType === 'exact_time' && (
          <div className="space-y-2">
            <Label htmlFor="scheduleExactTime">{t('processMonitors.exactTimeValue')} *</Label>
            <Input
              id="scheduleExactTime"
              type="time"
              value={scheduleExactTime}
              onChange={(e) => setScheduleExactTime(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground">
              {t('processMonitors.exactTimeHelp')}
            </p>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="timezone">{t('processMonitors.timezone')}</Label>
          <Select value={timezone} onValueChange={setTimezone}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEZONES.map((tz) => (
                <SelectItem key={tz} value={tz}>
                  {tz}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Timeouts */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium">{t('processMonitors.timeoutsSection')}</h3>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="startGracePeriod">{t('processMonitors.startGracePeriod')}</Label>
            <Input
              id="startGracePeriod"
              value={startGracePeriod}
              onChange={(e) => setStartGracePeriod(e.target.value)}
              placeholder="5m"
            />
            <p className="text-xs text-muted-foreground">
              {t('processMonitors.startGracePeriodHelp')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="endTimeout">{t('processMonitors.endTimeout')}</Label>
            <Input
              id="endTimeout"
              value={endTimeout}
              onChange={(e) => setEndTimeout(e.target.value)}
              placeholder="1h"
            />
            <p className="text-xs text-muted-foreground">
              {t('processMonitors.endTimeoutHelp')}
            </p>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium">{t('processMonitors.notificationsSection')}</h3>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>{t('processMonitors.notifyOnMissedStart')}</Label>
              <p className="text-xs text-muted-foreground">
                {t('processMonitors.notifyOnMissedStartHelp')}
              </p>
            </div>
            <Switch
              checked={notifyOnMissedStart}
              onCheckedChange={setNotifyOnMissedStart}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>{t('processMonitors.notifyOnMissedEnd')}</Label>
              <p className="text-xs text-muted-foreground">
                {t('processMonitors.notifyOnMissedEndHelp')}
              </p>
            </div>
            <Switch
              checked={notifyOnMissedEnd}
              onCheckedChange={setNotifyOnMissedEnd}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>{t('processMonitors.notifyOnRecovery')}</Label>
              <p className="text-xs text-muted-foreground">
                {t('processMonitors.notifyOnRecoveryHelp')}
              </p>
            </div>
            <Switch
              checked={notifyOnRecovery}
              onCheckedChange={setNotifyOnRecovery}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>{t('processMonitors.notifyOnSuccess')}</Label>
              <p className="text-xs text-muted-foreground">
                {t('processMonitors.notifyOnSuccessHelp')}
              </p>
            </div>
            <Switch
              checked={notifyOnSuccess}
              onCheckedChange={setNotifyOnSuccess}
            />
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          {t('common.cancel')}
        </Button>
        <Button type="submit" disabled={isSubmitting || !name}>
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('common.saving')}
            </>
          ) : monitor ? (
            t('common.save')
          ) : (
            t('processMonitors.create')
          )}
        </Button>
      </div>
    </form>
  )
}
