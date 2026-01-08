import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { login } from '@/api/auth'
import { getErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Clock } from 'lucide-react'
import { toast } from '@/hooks/use-toast'

interface LoginPageProps {
  onNavigate: (route: 'login' | 'register' | 'dashboard') => void
}

export function LoginPage({ onNavigate }: LoginPageProps) {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login: authLogin } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await login({ email, password })
      authLogin(response.user, response.tokens.access_token, response.tokens.refresh_token)
      toast({
        title: 'Welcome back!',
        description: 'You have successfully signed in',
        variant: 'success',
      })
      onNavigate('dashboard')
    } catch (err) {
      toast({
        title: 'Sign in failed',
        description: getErrorMessage(err),
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="flex items-center gap-2 text-2xl font-bold">
              <Clock className="h-8 w-8" />
              <span>CronBox</span>
            </div>
          </div>
          <CardTitle className="text-2xl">{t('auth.welcomeBack')}</CardTitle>
          <CardDescription>{t('auth.enterCredentials')}</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
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
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('common.password')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? t('auth.signingIn') : t('auth.signIn')}
            </Button>
            <p className="text-sm text-muted-foreground">
              {t('auth.dontHaveAccount')}{' '}
              <button
                type="button"
                className="text-primary underline-offset-4 hover:underline"
                onClick={() => onNavigate('register')}
              >
                {t('auth.signUp')}
              </button>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
