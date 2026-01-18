import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { requestOTP, verifyOTP } from '@/api/auth'
import { getWorkspaces } from '@/api/workspaces'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Clock, ArrowLeft, Mail } from 'lucide-react'
import { toast } from '@/hooks/use-toast'

interface OTPLoginPageProps {
  onNavigate: (route: 'login' | 'register' | 'dashboard' | 'otp-login') => void
}

type Step = 'email' | 'code'

export function OTPLoginPage({ onNavigate }: OTPLoginPageProps) {
  const { t } = useTranslation()
  const [step, setStep] = useState<Step>('email')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [expiresIn, setExpiresIn] = useState(0)
  const [canResend, setCanResend] = useState(false)
  const { login: authLogin } = useAuthStore()
  const { setWorkspaces, setCurrentWorkspace, setLoading: setWorkspacesLoading } = useWorkspaceStore()
  const codeInputRef = useRef<HTMLInputElement>(null)

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

  // Countdown timer
  useEffect(() => {
    if (expiresIn > 0) {
      const timer = setInterval(() => {
        setExpiresIn((prev) => {
          if (prev <= 1) {
            setCanResend(true)
            return 0
          }
          return prev - 1
        })
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [expiresIn])

  // Focus code input when step changes
  useEffect(() => {
    if (step === 'code' && codeInputRef.current) {
      codeInputRef.current.focus()
    }
  }, [step])

  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await requestOTP({ email })
      setExpiresIn(response.expires_in)
      setCanResend(false)
      setStep('code')
      toast({
        title: t('auth.otp.codeSent'),
        description: t('auth.otp.checkEmail'),
        variant: 'success',
      })
    } catch (err) {
      toast({
        title: t('common.error'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await verifyOTP({ email, code })
      authLogin(response.user, response.tokens.access_token, response.tokens.refresh_token)

      // Load workspaces after successful login
      setWorkspacesLoading(true)
      const workspaces = await getWorkspaces()
      setWorkspaces(workspaces)
      if (workspaces.length > 0) {
        setCurrentWorkspace(workspaces[0])
      }
      setWorkspacesLoading(false)

      toast({
        title: t('auth.welcomeBack'),
        description: t('auth.loginSuccess'),
        variant: 'success',
      })
      onNavigate('dashboard')
    } catch (err) {
      setWorkspacesLoading(false)
      toast({
        title: t('auth.otp.invalidCode'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleResend = async () => {
    setIsLoading(true)
    setCode('')

    try {
      const response = await requestOTP({ email })
      setExpiresIn(response.expires_in)
      setCanResend(false)
      toast({
        title: t('auth.otp.codeSent'),
        description: t('auth.otp.newCodeSent'),
        variant: 'success',
      })
    } catch (err) {
      toast({
        title: t('common.error'),
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleBack = () => {
    setStep('email')
    setCode('')
    setExpiresIn(0)
    setCanResend(false)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Handle code input - only allow digits and limit to 6
  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6)
    setCode(value)
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
          <CardTitle className="text-2xl">{t('auth.otp.title')}</CardTitle>
          <CardDescription>
            {step === 'email' ? t('auth.otp.enterEmail') : t('auth.otp.enterCode')}
          </CardDescription>
        </CardHeader>

        {step === 'email' ? (
          <form onSubmit={handleRequestOTP}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">{t('common.email')}</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4">
              <Button type="submit" className="w-full" disabled={isLoading}>
                <Mail className="mr-2 h-4 w-4" />
                {isLoading ? t('auth.otp.sending') : t('auth.otp.sendCode')}
              </Button>
              <p className="text-sm text-muted-foreground">
                {t('auth.otp.orUsePassword')}{' '}
                <button
                  type="button"
                  className="text-primary underline-offset-4 hover:underline"
                  onClick={() => onNavigate('login')}
                >
                  {t('auth.signIn')}
                </button>
              </p>
            </CardFooter>
          </form>
        ) : (
          <form onSubmit={handleVerifyOTP}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="code">{t('auth.otp.code')}</Label>
                <Input
                  ref={codeInputRef}
                  id="code"
                  type="text"
                  inputMode="numeric"
                  placeholder="000000"
                  value={code}
                  onChange={handleCodeChange}
                  className="text-center text-2xl tracking-widest font-mono"
                  maxLength={6}
                  required
                />
                <p className="text-sm text-muted-foreground text-center">
                  {t('auth.otp.sentTo')} <strong>{email}</strong>
                </p>
              </div>

              {expiresIn > 0 && (
                <p className="text-sm text-muted-foreground text-center">
                  {t('auth.otp.expiresIn')} {formatTime(expiresIn)}
                </p>
              )}

              {canResend && (
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full"
                  onClick={handleResend}
                  disabled={isLoading}
                >
                  {t('auth.otp.resendCode')}
                </Button>
              )}
            </CardContent>
            <CardFooter className="flex flex-col space-y-4">
              <Button
                type="submit"
                className="w-full"
                disabled={isLoading || code.length !== 6}
              >
                {isLoading ? t('auth.signingIn') : t('auth.otp.verify')}
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={handleBack}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                {t('auth.otp.changeEmail')}
              </Button>
            </CardFooter>
          </form>
        )}
      </Card>
    </div>
  )
}
