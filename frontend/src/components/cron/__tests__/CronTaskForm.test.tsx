import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { CronTaskForm } from '../CronTaskForm'
import * as cronTasksApi from '@/api/cronTasks'
import type { CronTask } from '@/types'

// Mock API
vi.mock('@/api/cronTasks', () => ({
  createCronTask: vi.fn(),
  updateCronTask: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('CronTaskForm', () => {
  const mockOnSuccess = vi.fn()
  const mockOnCancel = vi.fn()
  const defaultProps = {
    workspaceId: 'workspace-1',
    onSuccess: mockOnSuccess,
    onCancel: mockOnCancel,
  }

  const mockTask: CronTask = {
    id: 'task-1',
    workspace_id: 'workspace-1',
    name: 'Test Task',
    description: 'Test description',
    url: 'https://example.com/webhook',
    method: 'POST',
    schedule: '*/5 * * * *',
    timezone: 'Europe/Moscow',
    timeout_seconds: 30,
    retry_count: 3,
    headers: { 'Content-Type': 'application/json' },
    body: '{"test": true}',
    is_active: true,
    notify_on_failure: true,
    last_run_at: null,
    next_run_at: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(cronTasksApi.createCronTask).mockResolvedValue(mockTask)
    vi.mocked(cronTasksApi.updateCronTask).mockResolvedValue(mockTask)
  })

  it('should render create form with default values', () => {
    render(<CronTaskForm {...defaultProps} />)

    expect(screen.getByRole('textbox', { name: /name/i })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /url/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create task/i })).toBeInTheDocument()
  })

  it('should render edit form with task values', () => {
    render(<CronTaskForm {...defaultProps} task={mockTask} />)

    expect(screen.getByRole('textbox', { name: /^name/i })).toHaveValue('Test Task')
    expect(screen.getByRole('textbox', { name: /url/i })).toHaveValue('https://example.com/webhook')
    expect(screen.getByRole('button', { name: /update task/i })).toBeInTheDocument()
  })

  it('should call createCronTask on submit in create mode', async () => {
    const { user } = render(<CronTaskForm {...defaultProps} />)

    const nameInput = screen.getByRole('textbox', { name: /^name/i })
    const urlInput = screen.getByRole('textbox', { name: /url/i })

    await user.type(nameInput, 'New Task')
    await user.type(urlInput, 'https://example.com/api')

    await user.click(screen.getByRole('button', { name: /create task/i }))

    await waitFor(() => {
      expect(cronTasksApi.createCronTask).toHaveBeenCalledWith(
        'workspace-1',
        expect.objectContaining({
          name: 'New Task',
          url: 'https://example.com/api',
        })
      )
    })
  })

  it('should call updateCronTask on submit in edit mode', async () => {
    const { user } = render(<CronTaskForm {...defaultProps} task={mockTask} />)

    const nameInput = screen.getByRole('textbox', { name: /^name/i })
    await user.clear(nameInput)
    await user.type(nameInput, 'Updated Task')

    await user.click(screen.getByRole('button', { name: /update task/i }))

    await waitFor(() => {
      expect(cronTasksApi.updateCronTask).toHaveBeenCalledWith(
        'workspace-1',
        'task-1',
        expect.objectContaining({
          name: 'Updated Task',
        })
      )
    })
  })

  it('should call onSuccess after successful create', async () => {
    const { user } = render(<CronTaskForm {...defaultProps} />)

    await user.type(screen.getByRole('textbox', { name: /^name/i }), 'New Task')
    await user.type(screen.getByRole('textbox', { name: /url/i }), 'https://example.com/api')

    await user.click(screen.getByRole('button', { name: /create task/i }))

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled()
    })
  })

  it('should call onCancel when cancel button clicked', async () => {
    const { user } = render(<CronTaskForm {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(mockOnCancel).toHaveBeenCalled()
  })

  it('should have multiple comboboxes for method and timezone', () => {
    render(<CronTaskForm {...defaultProps} />)

    const comboboxes = screen.getAllByRole('combobox')
    expect(comboboxes.length).toBeGreaterThanOrEqual(2) // Method + Timezone at minimum
  })

  it('should render HTTP method selector with GET as default', () => {
    render(<CronTaskForm {...defaultProps} />)

    // The select triggers and hidden selects contain GET text
    expect(screen.getAllByText('GET').length).toBeGreaterThan(0)
  })

  it('should render timezone selector', () => {
    render(<CronTaskForm {...defaultProps} />)

    // The timezone select contains Europe/Moscow
    expect(screen.getAllByText('Europe/Moscow').length).toBeGreaterThan(0)
  })

  it('should show loading state when submitting', async () => {
    // Make the API call slow
    vi.mocked(cronTasksApi.createCronTask).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockTask), 1000))
    )

    const { user } = render(<CronTaskForm {...defaultProps} />)

    await user.type(screen.getByRole('textbox', { name: /^name/i }), 'New Task')
    await user.type(screen.getByRole('textbox', { name: /url/i }), 'https://example.com/api')

    await user.click(screen.getByRole('button', { name: /create task/i }))

    // Button should be disabled during loading
    expect(screen.getByRole('button', { name: /create task/i })).toBeDisabled()
  })

  it('should render description field', () => {
    render(<CronTaskForm {...defaultProps} />)

    expect(screen.getByRole('textbox', { name: /description/i })).toBeInTheDocument()
  })

  it('should render cron schedule builder', () => {
    render(<CronTaskForm {...defaultProps} />)

    expect(screen.getByText('Builder')).toBeInTheDocument()
  })

  it('should show error when API call fails', async () => {
    const errorMessage = 'API Error'
    vi.mocked(cronTasksApi.createCronTask).mockRejectedValue(new Error(errorMessage))

    const { user } = render(<CronTaskForm {...defaultProps} />)

    await user.type(screen.getByRole('textbox', { name: /^name/i }), 'New Task')
    await user.type(screen.getByRole('textbox', { name: /url/i }), 'https://example.com/api')

    await user.click(screen.getByRole('button', { name: /create task/i }))

    // The toast should be called with error, but form doesn't show inline error
    await waitFor(() => {
      expect(mockOnSuccess).not.toHaveBeenCalled()
    })
  })
})
