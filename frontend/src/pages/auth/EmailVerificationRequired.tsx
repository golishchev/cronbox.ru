import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Mail, Clock, LogOut, RefreshCw } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { sendEmailVerification } from '@/api/auth'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface EmailVerificationRequiredProps {
  onLogout: () => void
}

export function EmailVerificationRequired({ onLogout }: EmailVerificationRequiredProps) {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [cooldown, setCooldown] = useState(0)

  // Prevent search engine indexing of this page
  useEffect(() => {
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex, nofollow'
    document.head.appendChild(meta)
    return () => {
      document.head.removeChild(meta)
    }
  }, [])

  const handleResend = async () => {
    if (cooldown > 0) return

    setSending(true)
    setError('')

    try {
      await sendEmailVerification()
      setSent(true)
      // Start 60 second cooldown
      setCooldown(60)
      const interval = setInterval(() => {
        setCooldown(prev => {
          if (prev <= 1) {
            clearInterval(interval)
            setSent(false)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="flex items-center gap-2 text-2xl font-bold">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                <Clock className="h-5 w-5 text-white" />
              </div>
              <span>CronBox</span>
            </div>
          </div>
          <div className="flex justify-center mb-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/30">
              <Mail className="h-8 w-8 text-amber-600" />
            </div>
          </div>
          <CardTitle className="text-2xl">
            {t('auth.emailVerificationRequired.title')}
          </CardTitle>
          <CardDescription className="text-base">
            {t('auth.emailVerificationRequired.description')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg bg-muted p-4 text-center">
            <p className="text-sm text-muted-foreground mb-1">
              {t('auth.emailVerificationRequired.sentTo')}
            </p>
            <p className="font-medium">{user?.email}</p>
          </div>

          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}

          <div className="space-y-2">
            <Button
              className="w-full"
              onClick={handleResend}
              disabled={sending || cooldown > 0}
            >
              {sending ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  {t('auth.emailVerificationRequired.sending')}
                </>
              ) : sent || cooldown > 0 ? (
                <>
                  {t('auth.emailVerificationRequired.resendIn', { seconds: cooldown })}
                </>
              ) : (
                <>
                  <Mail className="mr-2 h-4 w-4" />
                  {t('auth.emailVerificationRequired.resend')}
                </>
              )}
            </Button>

            <Button
              variant="outline"
              className="w-full"
              onClick={onLogout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              {t('auth.emailVerificationRequired.logout')}
            </Button>
          </div>

          <p className="text-xs text-muted-foreground text-center">
            {t('auth.emailVerificationRequired.checkSpam')}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
