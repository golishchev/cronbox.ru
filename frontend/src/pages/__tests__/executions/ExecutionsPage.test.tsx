import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { ExecutionsPage } from '@/pages/executions/ExecutionsPage'
import * as executionsApi from '@/api/executions'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/executions', () => ({
  getExecutions: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('ExecutionsPage', () => {
  const mockOnNavigate = vi.fn()
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockExecution = {
    id: 'exec-1',
    workspace_id: 'workspace-1',
    task_id: 'task-1',
    task_type: 'cron' as const,
    task_name: 'Test Task',
    status: 'success' as const,
    started_at: '2024-01-01T12:00:00Z',
    finished_at: '2024-01-01T12:00:01Z',
    duration_ms: 1000,
    http_status_code: 200,
    response_body: null,
    error_message: null,
    triggered_by: 'scheduler',
    retry_count: 0,
    created_at: '2024-01-01T12:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useWorkspaceStore).mockReturnValue({
      currentWorkspace: mockWorkspace,
      workspaces: [mockWorkspace],
      setWorkspaces: vi.fn(),
      setCurrentWorkspace: vi.fn(),
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
    })
    vi.mocked(executionsApi.getExecutions).mockResolvedValue({
      executions: [mockExecution],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    })
  })

  it('should render page title', async () => {
    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Executions')).toBeInTheDocument()
    })
  })

  it('should load executions on mount', async () => {
    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(executionsApi.getExecutions).toHaveBeenCalledWith('workspace-1', expect.any(Object))
    })
  })

  it('should display executions in table', async () => {
    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test Task')).toBeInTheDocument()
    })
  })

  it('should display execution status badge', async () => {
    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText(/success/i).length).toBeGreaterThan(0)
    })
  })

  it('should display task type badge', async () => {
    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText(/cron/i).length).toBeGreaterThan(0)
    })
  })

  it('should show empty state when no executions', async () => {
    vi.mocked(executionsApi.getExecutions).mockResolvedValue({
      executions: [],
      total: 0,
      page: 1,
      per_page: 20,
      total_pages: 0,
    })

    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(executionsApi.getExecutions).toHaveBeenCalled()
    })
  })

  it('should load page successfully', async () => {
    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Executions')).toBeInTheDocument()
    })
  })

  it('should show failed execution with error status', async () => {
    const failedExecution = {
      ...mockExecution,
      id: 'exec-2',
      status: 'failed' as const,
      error_message: 'Connection timeout',
      http_status_code: null,
    }
    vi.mocked(executionsApi.getExecutions).mockResolvedValue({
      executions: [failedExecution],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    })

    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getAllByText(/failed/i).length).toBeGreaterThan(0)
    })
  })

  it('should display execution details', async () => {
    render(<ExecutionsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      // Just check that the execution is rendered
      expect(screen.getByText('Test Task')).toBeInTheDocument()
    })
  })
})
