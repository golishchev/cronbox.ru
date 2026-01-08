import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { updateProfile } from '@/api/auth'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2, Save, User, Globe, MessageSquare, CheckCircle, XCircle } from 'lucide-react'

interface ProfilePageProps {
  onNavigate: (route: string) => void
}

export function ProfilePage({ onNavigate: _ }: ProfilePageProps) {
  const { t } = useTranslation()
  const { user, updateUser } = useAuthStore()
  const [name, setName] = useState(user?.name || '')
  const [language, setLanguage] = useState<'en' | 'ru'>(user?.preferred_language || 'ru')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleSave = async () => {
    setIsSaving(true)
    setError('')
    setSuccess('')

    try {
      const updatedUser = await updateProfile({
        name: name !== user?.name ? name : undefined,
        preferred_language: language !== user?.preferred_language ? language : undefined,
      })
      updateUser(updatedUser)
      setSuccess(t('notifications.settingsSaved'))
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsSaving(false)
    }
  }

  const hasChanges = name !== user?.name || language !== user?.preferred_language

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('profile.title')}</h1>
        <p className="text-muted-foreground">
          {t('profile.subtitle')}
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-4 text-destructive">
          {error}
        </div>
      )}

      {success && (
        <div className="rounded-md bg-green-500/15 p-4 text-green-600">
          {success}
        </div>
      )}

      {/* Personal Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            {t('profile.personalInfo')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">{t('common.name')}</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('common.name')}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">{t('common.email')}</Label>
            <Input
              id="email"
              value={user?.email || ''}
              disabled
              className="bg-muted"
            />
          </div>
        </CardContent>
      </Card>

      {/* Language Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            {t('profile.language')}
          </CardTitle>
          <CardDescription>
            {t('profile.languageDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={language} onValueChange={(v) => setLanguage(v as 'en' | 'ru')}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ru">{t('profile.russian')}</SelectItem>
              <SelectItem value="en">{t('profile.english')}</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Account Info */}
      <Card>
        <CardHeader>
          <CardTitle>{t('profile.accountInfo')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">{t('profile.memberSince')}</span>
            <span>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">{t('common.email')}</span>
            <div className="flex items-center gap-2">
              {user?.email_verified ? (
                <>
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-green-600">{t('profile.emailVerified')}</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-yellow-500" />
                  <span className="text-yellow-600">{t('profile.emailNotVerified')}</span>
                </>
              )}
            </div>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Telegram</span>
            <div className="flex items-center gap-2">
              {user?.telegram_id ? (
                <>
                  <MessageSquare className="h-4 w-4 text-blue-500" />
                  <span className="text-blue-600">@{user.telegram_username || user.telegram_id}</span>
                </>
              ) : (
                <span className="text-muted-foreground">{t('profile.telegramNotConnected')}</span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isSaving || !hasChanges}>
          {isSaving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          {isSaving ? t('profile.saving') : t('profile.saveChanges')}
        </Button>
      </div>
    </div>
  )
}
