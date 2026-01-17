import {
  Book,
  Key,
  Clock,
  Timer,
  Activity,
  Bell,
  CreditCard,
  Layers,
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
  { id: 'overlap-prevention', name: 'Предотвращение перекрытия', icon: Layers },
  { id: 'executions', name: 'Выполнения', icon: Activity },
  { id: 'notifications', name: 'Уведомления', icon: Bell },
  { id: 'billing', name: 'Биллинг', icon: CreditCard },
]

export function getSectionById(id: string): DocSection | undefined {
  return sections.find((s) => s.id === id)
}
