import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { updateProfile, uploadAvatar, deleteAvatar, deleteAccount, sendEmailVerification } from '@/api/auth'
import { getErrorMessage } from '@/api/client'
import { getAssetUrl } from '@/lib/utils'
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
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Loader2, Save, User, Globe, CheckCircle, XCircle, Camera, Trash2, AlertTriangle, Mail } from 'lucide-react'

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

  // Avatar state
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [avatarLoading, setAvatarLoading] = useState(false)
  const [avatarKey, setAvatarKey] = useState(Date.now())

  // Email verification state
  const [emailVerificationLoading, setEmailVerificationLoading] = useState(false)
  const [emailVerificationSent, setEmailVerificationSent] = useState(false)

  // Delete account state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)
  const { logout: logoutStore } = useAuthStore()

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

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      setError(t('profile.avatarInvalidType'))
      return
    }

    // Validate file size (2 MB)
    if (file.size > 2 * 1024 * 1024) {
      setError(t('profile.avatarTooLarge'))
      return
    }

    setAvatarLoading(true)
    setError('')

    try {
      const updatedUser = await uploadAvatar(file)
      updateUser(updatedUser)
      setAvatarKey(Date.now())
      setSuccess(t('profile.avatarUploaded'))
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setAvatarLoading(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleAvatarDelete = async () => {
    setAvatarLoading(true)
    setError('')

    try {
      await deleteAvatar()
      updateUser({ avatar_url: null })
      setSuccess(t('profile.avatarDeleted'))
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setAvatarLoading(false)
    }
  }

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U'

  const handleSendEmailVerification = async () => {
    setEmailVerificationLoading(true)
    setError('')

    try {
      await sendEmailVerification()
      setEmailVerificationSent(true)
      setSuccess(t('profile.verificationEmailSent'))
      setTimeout(() => setSuccess(''), 5000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setEmailVerificationLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirmation.toLowerCase() !== 'delete') {
      return
    }

    setDeleteLoading(true)
    try {
      await deleteAccount(deleteConfirmation)
      logoutStore()
      window.location.hash = 'login'
    } catch (err) {
      setError(getErrorMessage(err))
      setDeleteDialogOpen(false)
    } finally {
      setDeleteLoading(false)
      setDeleteConfirmation('')
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('profile.title')}</h1>
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

      {/* Avatar */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            {t('profile.avatar')}
          </CardTitle>
          <CardDescription>
            {t('profile.avatarDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="relative">
              <Avatar className="h-24 w-24">
                {user?.avatar_url && (
                  <AvatarImage
                    src={`${getAssetUrl(user.avatar_url)}?t=${avatarKey}`}
                    alt={user.name}
                  />
                )}
                <AvatarFallback className="text-2xl">{initials}</AvatarFallback>
              </Avatar>
              {avatarLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full">
                  <Loader2 className="h-6 w-6 animate-spin text-white" />
                </div>
              )}
            </div>
            <div className="space-y-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                onChange={handleAvatarUpload}
                className="hidden"
              />
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={avatarLoading}
              >
                <Camera className="mr-2 h-4 w-4" />
                {t('profile.uploadAvatar')}
              </Button>
              {user?.avatar_url && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleAvatarDelete}
                  disabled={avatarLoading}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t('profile.deleteAvatar')}
                </Button>
              )}
              <p className="text-xs text-muted-foreground">
                {t('profile.avatarHint')}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

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
                  {emailVerificationSent ? (
                    <span className="text-sm text-muted-foreground">
                      ({t('profile.verificationEmailSentShort')})
                    </span>
                  ) : (
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0 text-blue-500"
                      onClick={handleSendEmailVerification}
                      disabled={emailVerificationLoading}
                    >
                      {emailVerificationLoading ? (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      ) : (
                        <Mail className="mr-1 h-3 w-3" />
                      )}
                      {t('profile.verifyEmail')}
                    </Button>
                  )}
                </>
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

      {/* Danger Zone */}
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            {t('profile.dangerZone')}
          </CardTitle>
          <CardDescription>
            {t('profile.dangerZoneDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">{t('profile.deleteAccount')}</p>
              <p className="text-sm text-muted-foreground">
                {t('profile.deleteAccountDescription')}
              </p>
            </div>
            <Button
              variant="destructive"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t('profile.deleteAccount')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Delete Account Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('profile.deleteAccountTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('profile.deleteAccountWarning')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <Label htmlFor="delete-confirmation" className="text-sm">
              {t('profile.deleteAccountConfirmLabel')}
            </Label>
            <Input
              id="delete-confirmation"
              value={deleteConfirmation}
              onChange={(e) => setDeleteConfirmation(e.target.value)}
              placeholder="delete"
              className="mt-2"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteConfirmation('')}>
              {t('common.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteAccount}
              disabled={deleteLoading || deleteConfirmation.toLowerCase() !== 'delete'}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('profile.deleteAccountConfirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
