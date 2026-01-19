const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.cronbox.ru/v1'

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
  max_task_chains: number
  max_heartbeats: number
  max_ssl_monitors: number
  is_active: boolean
  is_public: boolean
  sort_order: number
}

export async function getPlans(): Promise<Plan[]> {
  const response = await fetch(`${API_BASE_URL}/billing/plans`, {
    next: { revalidate: 3600 }, // Revalidate every hour
  })
  if (!response.ok) {
    throw new Error('Failed to fetch plans')
  }
  return response.json()
}
