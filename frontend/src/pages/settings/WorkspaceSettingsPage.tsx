import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation, Trans } from 'react-i18next'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { updateWorkspace } from '@/api/workspaces'
import {
  getNotificationSettings,
  updateNotificationSettings,
  sendTestNotification,
  NotificationSettings,
} from '@/api/notifications'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { toast } from '@/hooks/use-toast'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Loader2,
  Building2,
  Clock,
  Bell,
  Mail,
  MessageSquare,
  MessageCircle,
  Webhook,
  Send,
  Plus,
  X,
  Check,
} from 'lucide-react'

// Common timezones
const TIMEZONES = [
  { value: 'Europe/Moscow', label: 'Москва (UTC+3)' },
  { value: 'Europe/Kaliningrad', label: 'Калининград (UTC+2)' },
  { value: 'Europe/Samara', label: 'Самара (UTC+4)' },
  { value: 'Asia/Yekaterinburg', label: 'Екатеринбург (UTC+5)' },
  { value: 'Asia/Omsk', label: 'Омск (UTC+6)' },
  { value: 'Asia/Krasnoyarsk', label: 'Красноярск (UTC+7)' },
  { value: 'Asia/Irkutsk', label: 'Иркутск (UTC+8)' },
  { value: 'Asia/Yakutsk', label: 'Якутск (UTC+9)' },
  { value: 'Asia/Vladivostok', label: 'Владивосток (UTC+10)' },
  { value: 'Asia/Magadan', label: 'Магадан (UTC+11)' },
  { value: 'Asia/Kamchatka', label: 'Камчатка (UTC+12)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'Лондон (UTC+0)' },
  { value: 'Europe/Paris', label: 'Париж (UTC+1)' },
  { value: 'Europe/Berlin', label: 'Берлин (UTC+1)' },
  { value: 'Europe/Kiev', label: 'Киев (UTC+2)' },
  { value: 'America/New_York', label: 'Нью-Йорк (UTC-5)' },
  { value: 'America/Chicago', label: 'Чикаго (UTC-6)' },
  { value: 'America/Denver', label: 'Денвер (UTC-7)' },
  { value: 'America/Los_Angeles', label: 'Лос-Анджелес (UTC-8)' },
  { value: 'Asia/Tokyo', label: 'Токио (UTC+9)' },
  { value: 'Asia/Shanghai', label: 'Шанхай (UTC+8)' },
  { value: 'Asia/Singapore', label: 'Сингапур (UTC+8)' },
  { value: 'Australia/Sydney', label: 'Сидней (UTC+11)' },
]

interface WorkspaceSettingsPageProps {
  onNavigate: (route: string) => void
}

export function WorkspaceSettingsPage({ onNavigate: _ }: WorkspaceSettingsPageProps) {
  const { t } = useTranslation()
  const { currentWorkspace, updateWorkspace: updateWorkspaceStore } = useWorkspaceStore()

  // General settings state
  const [name, setName] = useState(currentWorkspace?.name || '')
  const [timezone, setTimezone] = useState(currentWorkspace?.default_timezone || 'Europe/Moscow')
  const [generalSaveStatus, setGeneralSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [error, setError] = useState('')

  // Track if initial load is complete to avoid saving on mount
  const isGeneralInitialized = useRef(false)
  const generalSaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Notification settings state
  const [_settings, setSettings] = useState<NotificationSettings | null>(null)
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(true)
  const [_isSavingNotifications, setIsSavingNotifications] = useState(false)
  const [notificationSaveStatus, setNotificationSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [testingChannel, setTestingChannel] = useState<string | null>(null)
  const [notificationError, setNotificationError] = useState('')

  // Track if initial load is complete to avoid saving on mount
  const isNotificationsInitialized = useRef(false)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Notification form state
  const [telegramEnabled, setTelegramEnabled] = useState(false)
  const [telegramChatIds, setTelegramChatIds] = useState<string[]>([])
  const [newTelegramChatId, setNewTelegramChatId] = useState('')

  const [emailEnabled, setEmailEnabled] = useState(false)
  const [emailAddresses, setEmailAddresses] = useState<string[]>([])
  const [newEmailAddress, setNewEmailAddress] = useState('')

  const [maxEnabled, setMaxEnabled] = useState(false)
  const [maxChatIds, setMaxChatIds] = useState<string[]>([])
  const [newMaxChatId, setNewMaxChatId] = useState('')

  const [webhookEnabled, setWebhookEnabled] = useState(false)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')

  const [notifyOnFailure, setNotifyOnFailure] = useState(true)
  const [notifyOnRecovery, setNotifyOnRecovery] = useState(true)
  const [notifyOnSuccess, setNotifyOnSuccess] = useState(false)

  // Load general settings when workspace changes
  useEffect(() => {
    if (currentWorkspace) {
      isGeneralInitialized.current = false
      setName(currentWorkspace.name)
      setTimezone(currentWorkspace.default_timezone || 'Europe/Moscow')
      // Mark as initialized after a short delay
      setTimeout(() => {
        isGeneralInitialized.current = true
      }, 100)
    }
  }, [currentWorkspace])

  // Load notification settings
  const loadNotificationSettings = useCallback(async () => {
    if (!currentWorkspace) return
    setIsLoadingNotifications(true)
    isNotificationsInitialized.current = false
    try {
      const data = await getNotificationSettings(currentWorkspace.id)
      setSettings(data)
      setTelegramEnabled(data.telegram_enabled)
      setTelegramChatIds(data.telegram_chat_ids || [])
      setMaxEnabled(data.max_enabled)
      setMaxChatIds(data.max_chat_ids || [])
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
        isNotificationsInitialized.current = true
      }, 100)
    } catch (err) {
      setNotificationError(getErrorMessage(err))
    } finally {
      setIsLoadingNotifications(false)
    }
  }, [currentWorkspace])

  useEffect(() => {
    loadNotificationSettings()
  }, [loadNotificationSettings])

  // Save notification settings
  const saveNotificationSettings = useCallback(async () => {
    if (!currentWorkspace || !isNotificationsInitialized.current) return

    setIsSavingNotifications(true)
    setNotificationSaveStatus('saving')
    setNotificationError('')

    try {
      await updateNotificationSettings(currentWorkspace.id, {
        telegram_enabled: telegramEnabled,
        telegram_chat_ids: telegramChatIds,
        max_enabled: maxEnabled,
        max_chat_ids: maxChatIds,
        email_enabled: emailEnabled,
        email_addresses: emailAddresses,
        webhook_enabled: webhookEnabled,
        webhook_url: webhookUrl || undefined,
        webhook_secret: webhookSecret || undefined,
        notify_on_failure: notifyOnFailure,
        notify_on_recovery: notifyOnRecovery,
        notify_on_success: notifyOnSuccess,
      })
      setNotificationSaveStatus('saved')
      setTimeout(() => setNotificationSaveStatus('idle'), 2000)
    } catch (err) {
      setNotificationError(getErrorMessage(err))
      setNotificationSaveStatus('error')
    } finally {
      setIsSavingNotifications(false)
    }
  }, [
    currentWorkspace,
    telegramEnabled,
    telegramChatIds,
    maxEnabled,
    maxChatIds,
    emailEnabled,
    emailAddresses,
    webhookEnabled,
    webhookUrl,
    webhookSecret,
    notifyOnFailure,
    notifyOnRecovery,
    notifyOnSuccess,
  ])

  // Auto-save notifications with debounce when settings change
  useEffect(() => {
    if (!isNotificationsInitialized.current || isLoadingNotifications) return

    // Clear previous timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }

    // Debounce save by 500ms
    saveTimeoutRef.current = setTimeout(() => {
      saveNotificationSettings()
    }, 500)

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [
    telegramEnabled,
    telegramChatIds,
    maxEnabled,
    maxChatIds,
    emailEnabled,
    emailAddresses,
    webhookEnabled,
    webhookUrl,
    webhookSecret,
    notifyOnFailure,
    notifyOnRecovery,
    notifyOnSuccess,
    saveNotificationSettings,
    isLoadingNotifications,
  ])

  // Save general settings
  const saveGeneralSettings = useCallback(async () => {
    if (!currentWorkspace || !isGeneralInitialized.current) return

    const updates: { name?: string; default_timezone?: string } = {}

    if (name !== currentWorkspace.name && name.trim()) {
      updates.name = name.trim()
    }
    if (timezone !== currentWorkspace.default_timezone) {
      updates.default_timezone = timezone
    }

    if (Object.keys(updates).length === 0) return

    setGeneralSaveStatus('saving')
    setError('')

    try {
      const updatedWorkspace = await updateWorkspace(currentWorkspace.id, updates)
      updateWorkspaceStore(updatedWorkspace)
      setGeneralSaveStatus('saved')
      setTimeout(() => setGeneralSaveStatus('idle'), 2000)
    } catch (err) {
      setError(getErrorMessage(err))
      setGeneralSaveStatus('error')
    }
  }, [currentWorkspace, name, timezone, updateWorkspaceStore])

  // Auto-save general settings with debounce
  useEffect(() => {
    if (!isGeneralInitialized.current) return

    if (generalSaveTimeoutRef.current) {
      clearTimeout(generalSaveTimeoutRef.current)
    }

    generalSaveTimeoutRef.current = setTimeout(() => {
      saveGeneralSettings()
    }, 500)

    return () => {
      if (generalSaveTimeoutRef.current) {
        clearTimeout(generalSaveTimeoutRef.current)
      }
    }
  }, [name, timezone, saveGeneralSettings])

  // Notification helper functions
  const handleTestNotification = async (channel: 'telegram' | 'max' | 'email' | 'webhook') => {
    if (!currentWorkspace) return
    setTestingChannel(channel)
    setNotificationError('')

    try {
      await sendTestNotification(currentWorkspace.id, channel)
      toast({
        title: t('notifications.testSent'),
        description: t('notifications.testSentDescription', { channel }),
        variant: 'success',
      })
    } catch (err) {
      setNotificationError(getErrorMessage(err))
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

  const addMaxChatId = () => {
    if (newMaxChatId && !maxChatIds.includes(newMaxChatId)) {
      setMaxChatIds([...maxChatIds, newMaxChatId])
      setNewMaxChatId('')
    }
  }

  const removeMaxChatId = (chatId: string) => {
    setMaxChatIds(maxChatIds.filter(id => id !== chatId))
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

  if (!currentWorkspace) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">{t('workspaceSettings.noWorkspace')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('workspaceSettings.title')}</h1>
        <p className="text-muted-foreground mt-2">{t('workspaceSettings.description')}</p>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-4 text-destructive">
          {error}
        </div>
      )}

      {/* Workspace Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              {t('workspaceSettings.generalInfo')}
            </CardTitle>
            {generalSaveStatus === 'saving' && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('profile.saving')}
              </div>
            )}
            {generalSaveStatus === 'saved' && (
              <div className="flex items-center gap-2 text-sm text-green-600">
                <Check className="h-4 w-4" />
                {t('notifications.settingsSaved')}
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">{t('workspaceSettings.name')}</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('workspaceSettings.namePlaceholder')}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="slug">{t('workspaceSettings.slug')}</Label>
            <Input
              id="slug"
              value={currentWorkspace.slug}
              disabled
              className="bg-muted"
            />
            <p className="text-xs text-muted-foreground">
              {t('workspaceSettings.slugDescription')}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Timezone Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            {t('workspaceSettings.timezone')}
          </CardTitle>
          <CardDescription>
            {t('workspaceSettings.timezoneDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={timezone} onValueChange={setTimezone}>
            <SelectTrigger className="w-full sm:w-[300px]">
              <SelectValue placeholder={t('workspaceSettings.selectTimezone')} />
            </SelectTrigger>
            <SelectContent>
              {TIMEZONES.map((tz) => (
                <SelectItem key={tz.value} value={tz.value}>
                  {tz.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Notifications Section */}
      <div className="pt-4 border-t">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold">{t('workspaceSettings.tabNotifications')}</h2>
            <p className="text-sm text-muted-foreground">{t('notifications.eventsDescription')}</p>
          </div>
          {notificationSaveStatus === 'saving' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('profile.saving')}
            </div>
          )}
          {notificationSaveStatus === 'saved' && (
            <div className="flex items-center gap-2 text-sm text-green-600">
              <Check className="h-4 w-4" />
              {t('notifications.settingsSaved')}
            </div>
          )}
        </div>

        {isLoadingNotifications ? (
          <div className="flex h-[20vh] items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-6">
            {notificationError && (
              <div className="rounded-md bg-destructive/15 p-4 text-destructive">
                {notificationError}
              </div>
            )}

            {/* Notification Events */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  {t('notifications.events')}
                </CardTitle>
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
                    <Trans i18nKey="notifications.chatIdHint">
                      Начните чат с <a href="https://t.me/cronbox_bot" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">@cronbox_bot</a> и отправьте /start для получения вашего Chat ID
                    </Trans>
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

            {/* MAX */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <MessageCircle className="h-5 w-5" />
                    <CardTitle>{t('notifications.max')}</CardTitle>
                  </div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={maxEnabled}
                      onChange={(e) => setMaxEnabled(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <span className="text-sm">{t('common.enabled')}</span>
                  </label>
                </div>
                <CardDescription>
                  {t('notifications.maxDescription')}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>{t('notifications.maxChatIds')}</Label>
                  <div className="flex flex-wrap gap-2">
                    {maxChatIds.map((chatId) => (
                      <Badge key={chatId} variant="secondary" className="gap-1">
                        {chatId}
                        <button onClick={() => removeMaxChatId(chatId)}>
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      placeholder={t('notifications.maxChatIdPlaceholder')}
                      value={newMaxChatId}
                      onChange={(e) => setNewMaxChatId(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && addMaxChatId()}
                    />
                    <Button type="button" variant="outline" onClick={addMaxChatId}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    <Trans i18nKey="notifications.maxChatIdHint">
                      Начните чат с <a href="https://max.ru/id263107925047_bot" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">ботом в MAX</a> и отправьте /start для получения вашего Chat ID
                    </Trans>
                  </p>
                </div>

                {maxEnabled && maxChatIds.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleTestNotification('max')}
                    disabled={testingChannel === 'max'}
                  >
                    {testingChannel === 'max' ? (
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
        )}
      </div>
    </div>
  )
}
