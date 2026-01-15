import { apiClient } from './client'

export interface Plan {
  id: string
  name: string
  display_name: string
  description: string | null
  price_monthly: number
  price_yearly: number
  max_cron_tasks: number
  max_delayed_tasks_per_month: number
  max_workspaces: number
  max_execution_history_days: number
  min_cron_interval_minutes: number
  telegram_notifications: boolean
  email_notifications: boolean
  webhook_callbacks: boolean
  custom_headers: boolean
  retry_on_failure: boolean
}

export interface Subscription {
  id: string
  workspace_id: string
  plan_id: string
  status: 'active' | 'past_due' | 'cancelled' | 'expired'
  current_period_start: string
  current_period_end: string
  cancel_at_period_end: boolean
  cancelled_at: string | null
  plan?: Plan
}

export interface Payment {
  id: string
  workspace_id: string
  amount: number
  currency: string
  status: 'pending' | 'waiting_for_capture' | 'succeeded' | 'cancelled' | 'refunded'
  description: string | null
  yookassa_confirmation_url: string | null
  paid_at: string | null
  created_at: string
}

export interface PricePreview {
  plan_price: number
  proration_credit: number
  final_amount: number
  remaining_days: number
  currency: string
}

export async function getPlans(): Promise<Plan[]> {
  const response = await apiClient.get('/billing/plans')
  return response.data
}

export async function getSubscription(): Promise<Subscription | null> {
  const response = await apiClient.get('/billing/subscription')
  return response.data
}

export async function createPayment(
  planId: string,
  billingPeriod: 'monthly' | 'yearly' = 'monthly',
  returnUrl?: string
): Promise<Payment> {
  const response = await apiClient.post('/billing/subscribe', {
    plan_id: planId,
    billing_period: billingPeriod,
    return_url: returnUrl,
  })
  return response.data
}

export async function cancelSubscription(
  immediately: boolean = false
): Promise<void> {
  await apiClient.post('/billing/subscription/cancel', {
    immediately,
  })
}

export async function getPaymentHistory(
  limit: number = 20,
  offset: number = 0
): Promise<Payment[]> {
  const response = await apiClient.get('/billing/payments', {
    params: { limit, offset },
  })
  return response.data
}

export async function previewPrice(
  planId: string,
  billingPeriod: 'monthly' | 'yearly' = 'monthly'
): Promise<PricePreview> {
  const response = await apiClient.post('/billing/preview-price', {
    plan_id: planId,
    billing_period: billingPeriod,
  })
  return response.data
}
