import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { verifyEmail } from '@/api/auth'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'

interface VerifyEmailPageProps {
  token: string
  onNavigate: (route: string) => void
}

export function VerifyEmailPage({ token, onNavigate }: VerifyEmailPageProps) {
  const { t } = useTranslation()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState('')
  const { user, updateUser } = useAuthStore()

  useEffect(() => {
    const verify = async () => {
      // If user is already logged in and email is verified, show success immediately
      if (user?.email_verified) {
        setStatus('success')
        return
      }

      if (!token) {
        setStatus('error')
        setError(t('auth.verifyEmailNoToken'))
        return
      }

      try {
        const verifiedUser = await verifyEmail(token)
        updateUser(verifiedUser)
        setStatus('success')
      } catch (err) {
        setStatus('error')
        setError(getErrorMessage(err))
      }
    }

    verify()
  }, [token, user?.email_verified, updateUser, t])

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
          <CardTitle className="text-2xl">{t('auth.verifyEmailTitle')}</CardTitle>
          <CardDescription>
            {status === 'loading' && t('auth.verifyEmailProcessing')}
            {status === 'success' && t('auth.verifyEmailSuccess')}
            {status === 'error' && t('auth.verifyEmailError')}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center py-6">
          {status === 'loading' && (
            <Loader2 className="h-16 w-16 text-muted-foreground animate-spin" />
          )}
          {status === 'success' && (
            <CheckCircle className="h-16 w-16 text-green-500" />
          )}
          {status === 'error' && (
            <>
              <XCircle className="h-16 w-16 text-destructive" />
              <p className="mt-4 text-sm text-muted-foreground text-center">
                {error}
              </p>
            </>
          )}
        </CardContent>
        <CardFooter className="flex justify-center">
          {status !== 'loading' && (
            <Button onClick={() => onNavigate('dashboard')}>
              {t('auth.goToDashboard')}
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  )
}
