import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, CreditCard, AlertCircle, Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  getPlans,
  getSubscription,
  createPayment,
  cancelSubscription,
  getPaymentHistory,
  previewPrice,
  Plan,
  Subscription,
  Payment,
  PricePreview,
} from '@/api/billing'
import { cn } from '@/lib/utils'

interface BillingPageProps {
  onNavigate: (route: string) => void
}

export function BillingPage({ onNavigate: _ }: BillingPageProps) {
  const { t } = useTranslation()
  const [plans, setPlans] = useState<Plan[]>([])
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState(true)
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly')
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false)
  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pricePreview, setPricePreview] = useState<PricePreview | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)

  useEffect(() => {
    loadBillingData()
  }, [])

  const loadBillingData = async () => {
    setLoading(true)
    try {
      const [plansData, subscriptionData, paymentsData] = await Promise.all([
        getPlans(),
        getSubscription(),
        getPaymentHistory(),
      ])
      setPlans(plansData)
      setSubscription(subscriptionData)
      setPayments(paymentsData)
    } catch (err) {
      console.error('Failed to load billing data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpgrade = async () => {
    if (!selectedPlan) return

    setProcessing(true)
    setError(null)

    try {
      const payment = await createPayment(
        selectedPlan.id,
        billingPeriod,
        window.location.href
      )

      if (payment.yookassa_confirmation_url) {
        // Redirect to YooKassa payment page
        window.location.href = payment.yookassa_confirmation_url
      } else {
        setError('Failed to get payment URL')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create payment')
    } finally {
      setProcessing(false)
      setShowUpgradeDialog(false)
    }
  }

  const handleCancel = async () => {
    setProcessing(true)
    setError(null)

    try {
      await cancelSubscription()
      await loadBillingData()
      setShowCancelDialog(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to cancel subscription')
    } finally {
      setProcessing(false)
    }
  }

  const formatPrice = (kopeks: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
    }).format(kopeks / 100)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-500">{t('billing.active')}</Badge>
      case 'past_due':
        return <Badge variant="destructive">{t('billing.pastDue')}</Badge>
      case 'cancelled':
        return <Badge variant="secondary">{t('billing.cancelled')}</Badge>
      case 'expired':
        return <Badge variant="outline">{t('billing.expired')}</Badge>
      case 'succeeded':
        return <Badge className="bg-green-500">{t('billing.paid')}</Badge>
      case 'pending':
        return <Badge variant="outline">{t('common.pending')}</Badge>
      case 'refunded':
        return <Badge variant="secondary">{t('billing.refunded')}</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const currentPlanId = subscription?.plan_id || plans.find(p => p.name === 'free')?.id
  const currentPlan = plans.find(p => p.id === currentPlanId)
  const getCurrentPlanPrice = () => {
    if (!currentPlan) return 0
    return billingPeriod === 'yearly' ? currentPlan.price_yearly : currentPlan.price_monthly
  }

  const isDowngrade = (plan: Plan) => {
    const planPrice = billingPeriod === 'yearly' ? plan.price_yearly : plan.price_monthly
    return planPrice < getCurrentPlanPrice()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t('billing.title')}</h1>
        <p className="text-muted-foreground">
          {t('billing.subtitle')}
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Current Subscription */}
      {subscription && (
        <Card>
          <CardHeader>
            <CardTitle>{t('billing.currentSubscription')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <p className="text-sm text-muted-foreground">{t('billing.plan')}</p>
                <p className="font-semibold">{subscription.plan?.display_name || 'Unknown'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('common.status')}</p>
                {getStatusBadge(subscription.status)}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('billing.currentPeriod')}</p>
                <p className="text-sm">
                  {formatDate(subscription.current_period_start)} - {formatDate(subscription.current_period_end)}
                </p>
              </div>
              <div>
                {subscription.cancel_at_period_end ? (
                  <p className="text-sm text-yellow-600">
                    {t('billing.cancelsOn', { date: formatDate(subscription.current_period_end) })}
                  </p>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowCancelDialog(true)}
                  >
                    {t('billing.cancelSubscription')}
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Billing Period Toggle */}
      <div className="flex justify-center">
        <div className="inline-flex rounded-lg bg-muted p-1">
          <button
            onClick={() => setBillingPeriod('monthly')}
            className={cn(
              'rounded-md px-4 py-2 text-sm font-medium transition-colors',
              billingPeriod === 'monthly'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {t('billing.monthly')}
          </button>
          <button
            onClick={() => setBillingPeriod('yearly')}
            className={cn(
              'rounded-md px-4 py-2 text-sm font-medium transition-colors',
              billingPeriod === 'yearly'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {t('billing.yearly')} <span className="text-green-600 ml-1">{t('billing.yearlyDiscount')}</span>
          </button>
        </div>
      </div>

      {/* Plans */}
      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => {
          const price = billingPeriod === 'yearly' ? plan.price_yearly : plan.price_monthly
          const isCurrentPlan = plan.id === currentPlanId
          const isFree = plan.price_monthly === 0

          return (
            <Card
              key={plan.id}
              className={cn(
                'relative flex flex-col',
                isCurrentPlan && 'border-primary'
              )}
            >
              {isCurrentPlan && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge>{t('billing.currentPlan')}</Badge>
                </div>
              )}
              <CardHeader>
                <CardTitle>{plan.display_name}</CardTitle>
                <CardDescription>{plan.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 flex-1">
                <div>
                  <span className="text-3xl font-bold">
                    {isFree ? t('billing.free') : formatPrice(price)}
                  </span>
                  {!isFree && (
                    <span className="text-muted-foreground">
                      /{billingPeriod === 'yearly' ? t('billing.yearly').toLowerCase() : t('billing.monthly').toLowerCase()}
                    </span>
                  )}
                </div>

                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-green-500" />
                    <span>{plan.max_cron_tasks} {t('billing.cronTasks')}</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-green-500" />
                    <span>{plan.max_delayed_tasks_per_month} {t('billing.delayedTasksMonth')}</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-green-500" />
                    <span>{plan.max_workspaces} {t('billing.workspaces', { count: plan.max_workspaces })}</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-green-500" />
                    <span>{plan.max_execution_history_days} {t('billing.daysHistory', { count: plan.max_execution_history_days })}</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-green-500" />
                    <span>{t('billing.minInterval', { minutes: plan.min_cron_interval_minutes })}</span>
                  </li>
                  {plan.telegram_notifications && (
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500" />
                      <span>{t('billing.telegramNotifications')}</span>
                    </li>
                  )}
                  {plan.email_notifications && (
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500" />
                      <span>{t('billing.emailNotifications')}</span>
                    </li>
                  )}
                  {plan.webhook_callbacks && (
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500" />
                      <span>{t('billing.webhookCallbacks')}</span>
                    </li>
                  )}
                  {plan.retry_on_failure && (
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500" />
                      <span>{t('billing.autoRetry')}</span>
                    </li>
                  )}
                </ul>
              </CardContent>
              <CardFooter>
                {isCurrentPlan ? (
                  <Button className="w-full" disabled>
                    {t('billing.currentPlan')}
                  </Button>
                ) : isFree ? (
                  <Button className="w-full" variant="outline" disabled>
                    {t('billing.free')}
                  </Button>
                ) : (
                  <Button
                    className="w-full"
                    onClick={async () => {
                      setSelectedPlan(plan)
                      setPricePreview(null)
                      setShowUpgradeDialog(true)
                      setLoadingPreview(true)
                      try {
                        const preview = await previewPrice(plan.id, billingPeriod)
                        setPricePreview(preview)
                      } catch (err) {
                        console.error('Failed to load price preview:', err)
                      } finally {
                        setLoadingPreview(false)
                      }
                    }}
                  >
                    <CreditCard className="mr-2 h-4 w-4" />
                    {isDowngrade(plan) ? t('billing.downgrade') : t('billing.upgrade')}
                  </Button>
                )}
              </CardFooter>
            </Card>
          )
        })}
      </div>

      {/* Payment History */}
      {payments.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('billing.paymentHistory')}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.date')}</TableHead>
                  <TableHead>{t('common.description')}</TableHead>
                  <TableHead>{t('billing.amount')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((payment) => (
                  <TableRow key={payment.id}>
                    <TableCell>{formatDateTime(payment.created_at)}</TableCell>
                    <TableCell>{payment.description}</TableCell>
                    <TableCell>{formatPrice(payment.amount)}</TableCell>
                    <TableCell>{getStatusBadge(payment.status)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Upgrade Dialog */}
      <Dialog open={showUpgradeDialog} onOpenChange={setShowUpgradeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedPlan && isDowngrade(selectedPlan)
                ? t('billing.downgradeTo', { plan: selectedPlan?.display_name })
                : t('billing.upgradeTo', { plan: selectedPlan?.display_name })}
            </DialogTitle>
            <DialogDescription>
              {t('billing.upgradeDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-3">
            <div className="flex justify-between items-center">
              <span>{t('billing.plan')}:</span>
              <span className="font-semibold">{selectedPlan?.display_name}</span>
            </div>
            <div className="flex justify-between items-center">
              <span>{t('billing.billingPeriod')}:</span>
              <span className="font-semibold">
                {billingPeriod === 'yearly' ? t('billing.yearly') : t('billing.monthly')}
              </span>
            </div>

            {loadingPreview ? (
              <div className="flex items-center justify-center py-2">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : pricePreview ? (
              <>
                <div className="flex justify-between items-center">
                  <span>{t('billing.planPrice')}:</span>
                  <span>{formatPrice(pricePreview.plan_price)}</span>
                </div>
                {pricePreview.proration_credit > 0 && (
                  <>
                    <div className="flex justify-between items-center text-green-600">
                      <span>{t('billing.prorationCredit')} ({pricePreview.remaining_days} {t('billing.daysRemaining')}):</span>
                      <span>-{formatPrice(pricePreview.proration_credit)}</span>
                    </div>
                    <hr className="border-border" />
                  </>
                )}
                <div className="flex justify-between items-center">
                  <span className="font-semibold">{t('billing.totalAmount')}:</span>
                  <span className="font-bold text-lg">{formatPrice(pricePreview.final_amount)}</span>
                </div>
              </>
            ) : (
              <div className="flex justify-between items-center">
                <span>{t('billing.amount')}:</span>
                <span className="font-semibold text-lg">
                  {selectedPlan && formatPrice(
                    billingPeriod === 'yearly'
                      ? selectedPlan.price_yearly
                      : selectedPlan.price_monthly
                  )}
                </span>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUpgradeDialog(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleUpgrade} disabled={processing}>
              {processing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('billing.proceedToPayment')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cancel Dialog */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('billing.cancelSubscriptionTitle')}</DialogTitle>
            <DialogDescription>
              {t('billing.cancelSubscriptionDescription')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCancelDialog(false)}>
              {t('billing.keepSubscription')}
            </Button>
            <Button variant="destructive" onClick={handleCancel} disabled={processing}>
              {processing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('billing.cancelSubscription')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
