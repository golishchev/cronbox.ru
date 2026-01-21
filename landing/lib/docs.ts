import {
  Book,
  Key,
  Clock,
  Timer,
  Activity,
  Bell,
  CreditCard,
  Layers,
  Link,
  HeartPulse,
  ShieldCheck,
  Radio,
  type LucideIcon,
} from 'lucide-react'

export interface DocSection {
  id: string
  name: string
  icon: LucideIcon
}

export const sections: DocSection[] = [
  { id: 'getting-started', name: 'Начало работы', icon: Book },
  { id: 'authentication', name: 'Аутентификация', icon: Key },
  { id: 'cron-tasks', name: 'Cron-задачи', icon: Clock },
  { id: 'delayed-tasks', name: 'Отложенные задачи', icon: Timer },
  { id: 'task-chains', name: 'Цепочки задач', icon: Link },
  { id: 'heartbeats', name: 'Heartbeat-мониторы', icon: HeartPulse },
  { id: 'ssl-monitors', name: 'SSL-мониторинг', icon: ShieldCheck },
  { id: 'icmp-tcp', name: 'ICMP/TCP мониторинг', icon: Radio },
  { id: 'overlap-prevention', name: 'Политика запуска', icon: Layers },
  { id: 'executions', name: 'Выполнения', icon: Activity },
  { id: 'notifications', name: 'Уведомления', icon: Bell },
  { id: 'billing', name: 'Биллинг', icon: CreditCard },
]

export function getSectionById(id: string): DocSection | undefined {
  return sections.find((s) => s.id === id)
}
