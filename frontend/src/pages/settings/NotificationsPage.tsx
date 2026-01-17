import { useEffect, useState, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import {
  getNotificationSettings,
  updateNotificationSettings,
  sendTestNotification,
  NotificationSettings,
} from '@/api/notifications'
import { getErrorMessage } from '@/api/client'
import { NoWorkspaceState } from '@/components/NoWorkspaceState'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { toast } from '@/hooks/use-toast'
import {
  Loader2,
  Bell,
  Mail,
  MessageSquare,
  Webhook,
  Send,
  Plus,
  X,
  Check,
} from 'lucide-react'

interface NotificationsPageProps {
  onNavigate: (route: string) => void
}

export function NotificationsPage({ onNavigate: _ }: NotificationsPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, workspaces } = useWorkspaceStore()
  const [_settings, setSettings] = useState<NotificationSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [_isSaving, setIsSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [testingChannel, setTestingChannel] = useState<string | null>(null)
  const [error, setError] = useState('')

  // Track if initial load is complete to avoid saving on mount
  const isInitialized = useRef(false)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Form state
  const [telegramEnabled, setTelegramEnabled] = useState(false)
  const [telegramChatIds, setTelegramChatIds] = useState<string[]>([])
  const [newTelegramChatId, setNewTelegramChatId] = useState('')

  const [emailEnabled, setEmailEnabled] = useState(false)
  const [emailAddresses, setEmailAddresses] = useState<string[]>([])
  const [newEmailAddress, setNewEmailAddress] = useState('')

  const [webhookEnabled, setWebhookEnabled] = useState(false)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')

  const [notifyOnFailure, setNotifyOnFailure] = useState(true)
  const [notifyOnRecovery, setNotifyOnRecovery] = useState(true)
  const [notifyOnSuccess, setNotifyOnSuccess] = useState(false)

  const loadSettings = async () => {
    if (!currentWorkspace) return
    setIsLoading(true)
    isInitialized.current = false
    try {
      const data = await getNotificationSettings(currentWorkspace.id)
      setSettings(data)
      setTelegramEnabled(data.telegram_enabled)
      setTelegramChatIds(data.telegram_chat_ids || [])
      setEmailEnabled(data.email_enabled)
      setEmailAddresses(data.email_addresses || [])
      setWebhookEnabled(data.webhook_enabled)
      setWebhookUrl(data.webhook_url || '')
      setWebhookSecret(data.webhook_secret || '')
      setNotifyOnFailure(data.notify_on_failure)
      setNotifyOnRecovery(data.notify_on_recovery)
      setNotifyOnSuccess(data.notify_on_success)
      // Mark as initialized after a short delay to allow state to settle
      setTimeout(() => {
        isInitialized.current = true
      }, 100)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadSettings()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace])

  const saveSettings = useCallback(async () => {
    if (!currentWorkspace || !isInitialized.current) return

    setIsSaving(true)
    setSaveStatus('saving')
    setError('')

    try {
      await updateNotificationSettings(currentWorkspace.id, {
        telegram_enabled: telegramEnabled,
        telegram_chat_ids: telegramChatIds,
        email_enabled: emailEnabled,
        email_addresses: emailAddresses,
        webhook_enabled: webhookEnabled,
        webhook_url: webhookUrl || undefined,
        webhook_secret: webhookSecret || undefined,
        notify_on_failure: notifyOnFailure,
        notify_on_recovery: notifyOnRecovery,
        notify_on_success: notifyOnSuccess,
      })
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err) {
      setError(getErrorMessage(err))
      setSaveStatus('error')
    } finally {
      setIsSaving(false)
    }
  }, [
    currentWorkspace,
    telegramEnabled,
    telegramChatIds,
    emailEnabled,
    emailAddresses,
    webhookEnabled,
    webhookUrl,
    webhookSecret,
    notifyOnFailure,
    notifyOnRecovery,
    notifyOnSuccess,
  ])

  // Auto-save with debounce when settings change
  useEffect(() => {
    if (!isInitialized.current || isLoading) return

    // Clear previous timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }

    // Debounce save by 500ms
    saveTimeoutRef.current = setTimeout(() => {
      saveSettings()
    }, 500)

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [
    telegramEnabled,
    telegramChatIds,
    emailEnabled,
    emailAddresses,
    webhookEnabled,
    webhookUrl,
    webhookSecret,
    notifyOnFailure,
    notifyOnRecovery,
    notifyOnSuccess,
    saveSettings,
    isLoading,
  ])

  const handleTestNotification = async (channel: 'telegram' | 'email' | 'webhook') => {
    if (!currentWorkspace) return
    setTestingChannel(channel)
    setError('')

    try {
      await sendTestNotification(currentWorkspace.id, channel)
      toast({
        title: t('notifications.testSent'),
        description: t('notifications.testSentDescription', { channel }),
        variant: 'success',
      })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setTestingChannel(null)
    }
  }

  const addTelegramChatId = () => {
    if (newTelegramChatId && !telegramChatIds.includes(newTelegramChatId)) {
      setTelegramChatIds([...telegramChatIds, newTelegramChatId])
      setNewTelegramChatId('')
    }
  }

  const removeTelegramChatId = (chatId: string) => {
    setTelegramChatIds(telegramChatIds.filter(id => id !== chatId))
  }

  const addEmailAddress = () => {
    if (newEmailAddress && !emailAddresses.includes(newEmailAddress)) {
      setEmailAddresses([...emailAddresses, newEmailAddress])
      setNewEmailAddress('')
    }
  }

  const removeEmailAddress = (email: string) => {
    setEmailAddresses(emailAddresses.filter(e => e !== email))
  }

  if (workspaces.length === 0) {
    return <NoWorkspaceState />
  }

  if (!currentWorkspace) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <p className="text-muted-foreground">{t('common.selectWorkspace')}</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{t('notifications.title')}</h1>
          {saveStatus === 'saving' && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
          {saveStatus === 'saved' && (
            <Check className="h-4 w-4 text-green-600" />
          )}
        </div>
        <p className="text-muted-foreground">
          {t('notifications.subtitle')}
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-4 text-destructive">
          {error}
        </div>
      )}

      {/* Notification Events */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            {t('notifications.events')}
          </CardTitle>
          <CardDescription>
            {t('notifications.eventsDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={notifyOnFailure}
              onChange={(e) => setNotifyOnFailure(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <div>
              <p className="font-medium">{t('notifications.taskFailure')}</p>
              <p className="text-sm text-muted-foreground">
                {t('notifications.taskFailureDescription')}
              </p>
            </div>
          </label>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={notifyOnRecovery}
              onChange={(e) => setNotifyOnRecovery(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <div>
              <p className="font-medium">{t('notifications.taskRecovery')}</p>
              <p className="text-sm text-muted-foreground">
                {t('notifications.taskRecoveryDescription')}
              </p>
            </div>
          </label>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={notifyOnSuccess}
              onChange={(e) => setNotifyOnSuccess(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <div>
              <p className="font-medium">{t('notifications.taskSuccess')}</p>
              <p className="text-sm text-muted-foreground">
                {t('notifications.taskSuccessDescription')}
              </p>
            </div>
          </label>
        </CardContent>
      </Card>

      {/* Telegram */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              <CardTitle>{t('notifications.telegram')}</CardTitle>
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={telegramEnabled}
                onChange={(e) => setTelegramEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm">{t('common.enabled')}</span>
            </label>
          </div>
          <CardDescription>
            {t('notifications.telegramDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>{t('notifications.chatIds')}</Label>
            <div className="flex flex-wrap gap-2">
              {telegramChatIds.map((chatId) => (
                <Badge key={chatId} variant="secondary" className="gap-1">
                  {chatId}
                  <button onClick={() => removeTelegramChatId(chatId)}>
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                placeholder={t('notifications.chatIdPlaceholder')}
                value={newTelegramChatId}
                onChange={(e) => setNewTelegramChatId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addTelegramChatId()}
              />
              <Button type="button" variant="outline" onClick={addTelegramChatId}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('notifications.chatIdHint')}
            </p>
          </div>

          {telegramEnabled && telegramChatIds.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleTestNotification('telegram')}
              disabled={testingChannel === 'telegram'}
            >
              {testingChannel === 'telegram' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-2 h-4 w-4" />
              )}
              {t('notifications.sendTest')}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Email */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              <CardTitle>{t('notifications.emailNotifications')}</CardTitle>
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={emailEnabled}
                onChange={(e) => setEmailEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm">{t('common.enabled')}</span>
            </label>
          </div>
          <CardDescription>
            {t('notifications.emailDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>{t('notifications.emailAddresses')}</Label>
            <div className="flex flex-wrap gap-2">
              {emailAddresses.map((email) => (
                <Badge key={email} variant="secondary" className="gap-1">
                  {email}
                  <button onClick={() => removeEmailAddress(email)}>
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                type="email"
                placeholder={t('notifications.emailPlaceholder')}
                value={newEmailAddress}
                onChange={(e) => setNewEmailAddress(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addEmailAddress()}
              />
              <Button type="button" variant="outline" onClick={addEmailAddress}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {emailEnabled && emailAddresses.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleTestNotification('email')}
              disabled={testingChannel === 'email'}
            >
              {testingChannel === 'email' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-2 h-4 w-4" />
              )}
              {t('notifications.sendTest')}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Webhook */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Webhook className="h-5 w-5" />
              <CardTitle>{t('notifications.webhook')}</CardTitle>
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={webhookEnabled}
                onChange={(e) => setWebhookEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm">{t('common.enabled')}</span>
            </label>
          </div>
          <CardDescription>
            {t('notifications.webhookDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="webhookUrl">{t('notifications.webhookUrl')}</Label>
            <Input
              id="webhookUrl"
              type="url"
              placeholder="https://example.com/webhook"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="webhookSecret">{t('notifications.webhookSecret')}</Label>
            <Input
              id="webhookSecret"
              type="password"
              placeholder={t('notifications.webhookSecretPlaceholder')}
              value={webhookSecret}
              onChange={(e) => setWebhookSecret(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              {t('notifications.webhookSecretHint')}
            </p>
          </div>

          {webhookEnabled && webhookUrl && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleTestNotification('webhook')}
              disabled={testingChannel === 'webhook'}
            >
              {testingChannel === 'webhook' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-2 h-4 w-4" />
              )}
              {t('notifications.sendTest')}
            </Button>
          )}
        </CardContent>
      </Card>

    </div>
  )
}
