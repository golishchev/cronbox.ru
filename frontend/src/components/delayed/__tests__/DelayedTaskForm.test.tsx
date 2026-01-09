import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { DelayedTaskForm } from '../DelayedTaskForm'
import * as delayedTasksApi from '@/api/delayedTasks'
import type { DelayedTask } from '@/types'

// Mock API
vi.mock('@/api/delayedTasks', () => ({
  createDelayedTask: vi.fn(),
  updateDelayedTask: vi.fn(),
}))

describe('DelayedTaskForm', () => {
  const mockOnSuccess = vi.fn()
  const mockOnCancel = vi.fn()
  const defaultProps = {
    workspaceId: 'workspace-1',
    onSuccess: mockOnSuccess,
    onCancel: mockOnCancel,
  }

  // Create a future date for testing
  const futureDate = new Date()
  futureDate.setHours(futureDate.getHours() + 2)

  const mockTask: DelayedTask = {
    id: 'task-1',
    workspace_id: 'workspace-1',
    name: 'Test Delayed Task',
    url: 'https://example.com/webhook',
    method: 'POST',
    execute_at: futureDate.toISOString(),
    status: 'pending',
    timeout_seconds: 30,
    retry_count: 0,
    headers: {},
    body: null,
    idempotency_key: 'key-123',
    callback_url: null,
    tags: ['tag1', 'tag2'],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    executed_at: null,
    execution_id: null,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(delayedTasksApi.createDelayedTask).mockResolvedValue(mockTask)
    vi.mocked(delayedTasksApi.updateDelayedTask).mockResolvedValue(mockTask)
  })

  it('should render create form', () => {
    render(<DelayedTaskForm {...defaultProps} />)

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^url/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /schedule/i })).toBeInTheDocument()
  })

  it('should render edit form with task values', () => {
    render(<DelayedTaskForm {...defaultProps} task={mockTask} />)

    expect(screen.getByLabelText(/name/i)).toHaveValue('Test Delayed Task')
    expect(screen.getByLabelText(/^url/i)).toHaveValue('https://example.com/webhook')
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument()
  })

  it('should show quick schedule buttons', () => {
    render(<DelayedTaskForm {...defaultProps} />)

    expect(screen.getByRole('button', { name: /in 5 minutes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /in 15 minutes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /in 30 minutes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /in 1 hour/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /in 3 hours/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /in 24 hours/i })).toBeInTheDocument()
  })

  it('should have quick schedule buttons', async () => {
    render(<DelayedTaskForm {...defaultProps} />)

    // Verify all quick schedule buttons exist
    expect(screen.getByRole('button', { name: /in 5 minutes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /in 15 minutes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /in 30 minutes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /in 1 hour/i })).toBeInTheDocument()
  })

  it('should call createDelayedTask on submit', async () => {
    const { user } = render(<DelayedTaskForm {...defaultProps} />)

    const urlInput = screen.getByLabelText(/^url/i)
    await user.clear(urlInput)
    await user.type(urlInput, 'https://example.com/api')

    // Use quick schedule to set a future time
    await user.click(screen.getByRole('button', { name: /in 1 hour/i }))

    await user.click(screen.getByRole('button', { name: /schedule/i }))

    await waitFor(() => {
      expect(delayedTasksApi.createDelayedTask).toHaveBeenCalledWith(
        'workspace-1',
        expect.objectContaining({
          url: 'https://example.com/api',
        })
      )
    })
  })

  it('should call updateDelayedTask in edit mode', async () => {
    const { user } = render(<DelayedTaskForm {...defaultProps} task={mockTask} />)

    const nameInput = screen.getByLabelText(/name/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'Updated Task')

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(delayedTasksApi.updateDelayedTask).toHaveBeenCalledWith(
        'workspace-1',
        'task-1',
        expect.objectContaining({
          url: 'https://example.com/webhook',
        })
      )
    })
  })

  it('should call onSuccess after successful create', async () => {
    const { user } = render(<DelayedTaskForm {...defaultProps} />)

    const urlInput = screen.getByLabelText(/^url/i)
    await user.clear(urlInput)
    await user.type(urlInput, 'https://example.com/api')
    await user.click(screen.getByRole('button', { name: /in 1 hour/i }))

    await user.click(screen.getByRole('button', { name: /schedule/i }))

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled()
    })
  })

  it('should call onCancel when cancel button clicked', async () => {
    const { user } = render(<DelayedTaskForm {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(mockOnCancel).toHaveBeenCalled()
  })

  it('should render HTTP method selector', () => {
    render(<DelayedTaskForm {...defaultProps} />)

    expect(screen.getByRole('combobox')).toBeInTheDocument()
    // The select trigger shows the current value "GET"
    expect(screen.getAllByText('GET').length).toBeGreaterThan(0)
  })

  it('should show advanced options section', () => {
    render(<DelayedTaskForm {...defaultProps} />)

    expect(screen.getByText('Advanced Options')).toBeInTheDocument()
  })

  it('should show idempotency key in create mode', () => {
    render(<DelayedTaskForm {...defaultProps} />)

    expect(screen.getByRole('textbox', { name: /idempotency key/i })).toBeInTheDocument()
  })

  it('should not show idempotency key in edit mode', () => {
    render(<DelayedTaskForm {...defaultProps} task={mockTask} />)

    expect(screen.queryByRole('textbox', { name: /idempotency key/i })).not.toBeInTheDocument()
  })

  it('should show tags input', () => {
    render(<DelayedTaskForm {...defaultProps} />)

    expect(screen.getByRole('textbox', { name: /tags/i })).toBeInTheDocument()
  })

  it('should show tags with existing values in edit mode', () => {
    render(<DelayedTaskForm {...defaultProps} task={mockTask} />)

    expect(screen.getByRole('textbox', { name: /tags/i })).toHaveValue('tag1, tag2')
  })

  it('should show callback URL input', () => {
    render(<DelayedTaskForm {...defaultProps} />)

    expect(screen.getByRole('textbox', { name: /callback url/i })).toBeInTheDocument()
  })

  it('should show timeout and retry count fields', () => {
    render(<DelayedTaskForm {...defaultProps} />)

    expect(screen.getByRole('spinbutton', { name: /timeout/i })).toBeInTheDocument()
    expect(screen.getByRole('spinbutton', { name: /retry count/i })).toBeInTheDocument()
  })
})
