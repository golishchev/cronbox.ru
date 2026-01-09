import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { AdminNotificationTemplatesPage } from '@/pages/admin/AdminNotificationTemplatesPage'
import * as adminApi from '@/api/admin'

// Mock APIs
vi.mock('@/api/admin', () => ({
  getNotificationTemplates: vi.fn(),
  updateNotificationTemplate: vi.fn(),
  previewNotificationTemplate: vi.fn(),
  resetNotificationTemplate: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('AdminNotificationTemplatesPage', () => {
  const mockOnNavigate = vi.fn()

  const mockTemplates = [
    {
      id: 'template-1',
      code: 'task_failure',
      language: 'en',
      channel: 'EMAIL',
      subject: 'Task Failed: {task_name}',
      body: 'Your task {task_name} has failed with error: {error_message}',
      description: 'Sent when a task fails',
      variables: ['task_name', 'error_message', 'status_code'],
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'template-2',
      code: 'task_failure',
      language: 'ru',
      channel: 'EMAIL',
      subject: 'Задача не выполнена: {task_name}',
      body: 'Ваша задача {task_name} завершилась с ошибкой: {error_message}',
      description: 'Отправляется при ошибке задачи',
      variables: ['task_name', 'error_message', 'status_code'],
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'template-3',
      code: 'task_success',
      language: 'en',
      channel: 'TELEGRAM',
      subject: null,
      body: '✅ Task {task_name} completed successfully!',
      description: 'Sent when a task succeeds',
      variables: ['task_name', 'status_code'],
      is_active: false,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminApi.getNotificationTemplates).mockResolvedValue({
      templates: mockTemplates,
    })
  })

  it('should load templates on mount', async () => {
    render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getNotificationTemplates).toHaveBeenCalled()
    })
  })

  it('should display templates in table', async () => {
    render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('task_failure').length).toBeGreaterThan(0)
    })
  })

  it('should display language badges', async () => {
    render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('EN').length).toBeGreaterThan(0)
      expect(screen.getAllByText('RU').length).toBeGreaterThan(0)
    })
  })

  it('should display channel names', async () => {
    render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('Email').length).toBeGreaterThan(0)
      expect(screen.getByText('Telegram')).toBeInTheDocument()
    })
  })

  it('should navigate back when back button clicked', async () => {
    const { user } = render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('task_failure').length).toBeGreaterThan(0)
    })

    const backButton = screen.getByRole('button', { name: /back/i })
    await user.click(backButton)

    expect(mockOnNavigate).toHaveBeenCalledWith('admin')
  })

  it('should open edit dialog when edit button clicked', async () => {
    const { user } = render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('task_failure').length).toBeGreaterThan(0)
    })

    const editButtons = screen.getAllByTitle(/edit/i)
    await user.click(editButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('should have filter dropdowns', async () => {
    render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('task_failure').length).toBeGreaterThan(0)
    })

    // Verify filter dropdowns exist
    const selects = screen.getAllByRole('combobox')
    expect(selects.length).toBe(3) // code, language, channel
  })

  it('should display empty state when no templates', async () => {
    vi.mocked(adminApi.getNotificationTemplates).mockResolvedValue({
      templates: [],
    })

    render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getNotificationTemplates).toHaveBeenCalled()
    })
  })

  it('should handle API error', async () => {
    vi.mocked(adminApi.getNotificationTemplates).mockRejectedValue(new Error('API Error'))

    render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(adminApi.getNotificationTemplates).toHaveBeenCalled()
    })
  })

  it('should update template when save clicked', async () => {
    vi.mocked(adminApi.updateNotificationTemplate).mockResolvedValue({} as any)

    const { user } = render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('task_failure').length).toBeGreaterThan(0)
    })

    const editButtons = screen.getAllByTitle(/edit/i)
    await user.click(editButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /save/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(adminApi.updateNotificationTemplate).toHaveBeenCalled()
    })
  })

  it('should open reset dialog when reset button clicked', async () => {
    const { user } = render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('task_failure').length).toBeGreaterThan(0)
    })

    const resetButtons = screen.getAllByTitle(/reset/i)
    await user.click(resetButtons[0])

    await waitFor(() => {
      expect(screen.getAllByRole('dialog').length).toBeGreaterThan(0)
    })
  })

  it('should preview template', async () => {
    vi.mocked(adminApi.previewNotificationTemplate).mockResolvedValue({
      subject: 'Previewed Subject',
      body: '<p>Previewed body content</p>',
    })

    const { user } = render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText('task_failure').length).toBeGreaterThan(0)
    })

    const editButtons = screen.getAllByTitle(/edit/i)
    await user.click(editButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    const previewButton = screen.getByRole('button', { name: /preview/i })
    await user.click(previewButton)

    await waitFor(() => {
      expect(adminApi.previewNotificationTemplate).toHaveBeenCalled()
    })
  })

  it('should display subject for email templates', async () => {
    render(<AdminNotificationTemplatesPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText(/Task Failed/i)).toBeInTheDocument()
    })
  })
})
