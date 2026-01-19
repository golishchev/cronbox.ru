import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createSSLMonitor, updateSSLMonitor } from '@/api/sslMonitors'
import { getErrorMessage } from '@/api/client'
import { translateApiError } from '@/lib/translateApiError'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import { toast } from '@/hooks/use-toast'
import { Loader2 } from 'lucide-react'
import type { SSLMonitor, CreateSSLMonitorRequest } from '@/types'

interface SSLMonitorFormProps {
  workspaceId: string
  monitor?: SSLMonitor
  onSuccess: (monitor?: SSLMonitor) => void
  onCancel: () => void
}

export function SSLMonitorForm({ workspaceId, monitor, onSuccess, onCancel }: SSLMonitorFormProps) {
  const { t } = useTranslation()
  const isEditing = !!monitor

  const [name, setName] = useState(monitor?.name ?? '')
  const [domain, setDomain] = useState(monitor?.domain ?? '')
  const [port, setPort] = useState(monitor?.port?.toString() ?? '443')
  const [description, setDescription] = useState(monitor?.description ?? '')
  const [notifyOnExpiring, setNotifyOnExpiring] = useState(monitor?.notify_on_expiring ?? true)
  const [notifyOnError, setNotifyOnError] = useState(monitor?.notify_on_error ?? true)

  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!name.trim()) {
      setError(t('ssl.nameRequired'))
      return
    }

    if (!isEditing && !domain.trim()) {
      setError(t('ssl.domainRequired'))
      return
    }

    const portNum = parseInt(port, 10)
    if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
      setError(t('ssl.invalidPort'))
      return
    }

    setIsLoading(true)

    try {
      const data: CreateSSLMonitorRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        domain: domain.trim(),
        port: portNum,
        notify_on_expiring: notifyOnExpiring,
        notify_on_error: notifyOnError,
      }

      if (isEditing) {
        const { domain: _, ...updateData } = data
        await updateSSLMonitor(workspaceId, monitor.id, updateData)
        toast({
          title: t('ssl.updated'),
          description: t('ssl.updatedDescription', { name: data.name }),
          variant: 'success',
        })
        onSuccess()
      } else {
        const createdMonitor = await createSSLMonitor(workspaceId, data)
        toast({
          title: t('ssl.created'),
          description: t('ssl.createdDescription', { name: data.name }),
          variant: 'success',
        })
        onSuccess(createdMonitor)
      }
    } catch (err) {
      toast({
        title: isEditing ? t('ssl.failedToUpdate') : t('ssl.failedToCreate'),
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
        <Label htmlFor="name">{t('ssl.name')} *</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('ssl.namePlaceholder')}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="domain">{t('ssl.domain')} *</Label>
          <Input
            id="domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder={t('ssl.domainPlaceholder')}
            disabled={isEditing}
          />
          <p className="text-xs text-muted-foreground">
            {isEditing ? t('ssl.domainCannotChange') : t('ssl.domainHelp')}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="port">{t('ssl.port')}</Label>
          <Input
            id="port"
            type="number"
            value={port}
            onChange={(e) => setPort(e.target.value)}
            placeholder="443"
            min={1}
            max={65535}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('ssl.description')}</Label>
        <Textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t('ssl.descriptionPlaceholder')}
          rows={2}
        />
      </div>

      <div className="space-y-4 border-t pt-4">
        <p className="text-sm font-medium">{t('notifications.events')}</p>
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="notifyOnExpiring"
              checked={notifyOnExpiring}
              onCheckedChange={(checked) => setNotifyOnExpiring(checked === true)}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="notifyOnExpiring" className="cursor-pointer">
                {t('ssl.notifyOnExpiring')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('ssl.notifyOnExpiringHelp')}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="notifyOnError"
              checked={notifyOnError}
              onCheckedChange={(checked) => setNotifyOnError(checked === true)}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="notifyOnError" className="cursor-pointer">
                {t('ssl.notifyOnError')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('ssl.notifyOnErrorHelp')}
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
          {isEditing ? t('ssl.update') : t('ssl.create')}
        </Button>
      </div>
    </form>
  )
}
