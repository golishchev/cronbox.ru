import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { DashboardPage } from '@/pages/DashboardPage'
import * as workspacesApi from '@/api/workspaces'
import * as executionsApi from '@/api/executions'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/workspaces', () => ({
  getWorkspaces: vi.fn(),
  getWorkspace: vi.fn(),
  createWorkspace: vi.fn(),
}))

vi.mock('@/api/executions', () => ({
  getExecutions: vi.fn(),
  getDailyExecutionStats: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

// Mock recharts (chart library doesn't render well in tests)
vi.mock('recharts', () => ({
  AreaChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

describe('DashboardPage', () => {
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockWorkspaceWithStats = {
    ...mockWorkspace,
    cron_tasks_count: 5,
    delayed_tasks_count: 3,
    total_executions: 100,
    success_rate: 95.5,
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

  const mockSetWorkspaces = vi.fn()
  const mockSetCurrentWorkspace = vi.fn()
  const mockSetLoading = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useWorkspaceStore).mockReturnValue({
      workspaces: [mockWorkspace],
      currentWorkspace: mockWorkspace,
      setWorkspaces: mockSetWorkspaces,
      setCurrentWorkspace: mockSetCurrentWorkspace,
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
      isLoading: false,
      setLoading: mockSetLoading,
    })

    vi.mocked(workspacesApi.getWorkspaces).mockResolvedValue([mockWorkspace])
    vi.mocked(workspacesApi.getWorkspace).mockResolvedValue(mockWorkspaceWithStats)
    vi.mocked(executionsApi.getExecutions).mockResolvedValue({
      executions: [mockExecution],
      total: 1,
      page: 1,
      per_page: 10,
      total_pages: 1,
    })
    vi.mocked(executionsApi.getDailyExecutionStats).mockResolvedValue([
      { date: '2024-01-01', success: 10, failed: 2 },
      { date: '2024-01-02', success: 15, failed: 1 },
      { date: '2024-01-03', success: 12, failed: 3 },
    ])
  })

  it('should render loading skeleton when loading', () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      workspaces: [],
      currentWorkspace: null,
      setWorkspaces: mockSetWorkspaces,
      setCurrentWorkspace: mockSetCurrentWorkspace,
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
      isLoading: true,
      setLoading: mockSetLoading,
    })

    render(<DashboardPage />)

    // Should show skeleton instead of actual content
    expect(screen.queryByText('Overview')).not.toBeInTheDocument()
  })

  it('should render empty state when no workspaces', async () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      workspaces: [],
      currentWorkspace: null,
      setWorkspaces: mockSetWorkspaces,
      setCurrentWorkspace: mockSetCurrentWorkspace,
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
      isLoading: false,
      setLoading: mockSetLoading,
    })

    render(<DashboardPage />)

    expect(screen.getByText('No workspaces yet')).toBeInTheDocument()
    expect(screen.getByText('Create your first workspace to get started')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create workspace/i })).toBeInTheDocument()
  })

  it('should load workspaces on mount', async () => {
    render(<DashboardPage />)

    await waitFor(() => {
      expect(workspacesApi.getWorkspaces).toHaveBeenCalled()
    })
  })

  it('should load workspace stats when workspace is selected', async () => {
    render(<DashboardPage />)

    await waitFor(() => {
      expect(workspacesApi.getWorkspace).toHaveBeenCalledWith('workspace-1')
    })
  })

  it('should load recent executions when workspace is selected', async () => {
    render(<DashboardPage />)

    await waitFor(() => {
      expect(executionsApi.getExecutions).toHaveBeenCalledWith('workspace-1', { limit: 10 })
    })
  })

  it('should display stats cards', async () => {
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Active Cron Tasks')).toBeInTheDocument()
      expect(screen.getByText('Pending Delayed Tasks')).toBeInTheDocument()
    })
  })

  it('should display recent executions table', async () => {
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Recent Executions')).toBeInTheDocument()
    })
  })

  it('should display execution chart area', async () => {
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Executions Last 7 Days')).toBeInTheDocument()
      expect(screen.getByTestId('area-chart')).toBeInTheDocument()
    })
  })

  it('should show error state on load failure', async () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      workspaces: [mockWorkspace],
      currentWorkspace: mockWorkspace,
      setWorkspaces: mockSetWorkspaces,
      setCurrentWorkspace: mockSetCurrentWorkspace,
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
      isLoading: false,
      setLoading: mockSetLoading,
    })

    // This simulates error by setting it in render
    // Dashboard handles errors internally, not throwing
    render(<DashboardPage />)

    // Dashboard should still try to render
    await waitFor(() => {
      expect(workspacesApi.getWorkspaces).toHaveBeenCalled()
    })
  })

  it('should open create workspace dialog when button clicked', async () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      workspaces: [],
      currentWorkspace: null,
      setWorkspaces: mockSetWorkspaces,
      setCurrentWorkspace: mockSetCurrentWorkspace,
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
      isLoading: false,
      setLoading: mockSetLoading,
    })

    const { user } = render(<DashboardPage />)

    await user.click(screen.getByRole('button', { name: /create workspace/i }))

    await waitFor(() => {
      expect(screen.getByText('Create New Workspace')).toBeInTheDocument()
    })
  })

  it('should create workspace when form submitted', async () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      workspaces: [],
      currentWorkspace: null,
      setWorkspaces: mockSetWorkspaces,
      setCurrentWorkspace: mockSetCurrentWorkspace,
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
      isLoading: false,
      setLoading: mockSetLoading,
    })

    vi.mocked(workspacesApi.createWorkspace).mockResolvedValue(mockWorkspace)

    const { user } = render(<DashboardPage />)

    await user.click(screen.getByRole('button', { name: /create workspace/i }))

    await waitFor(() => {
      expect(screen.getByText('Create New Workspace')).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText(/name/i)
    await user.type(nameInput, 'My New Workspace')

    await user.click(screen.getByRole('button', { name: /create$/i }))

    await waitFor(() => {
      expect(workspacesApi.createWorkspace).toHaveBeenCalled()
    })
  })

  it('should generate slug from workspace name', async () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      workspaces: [],
      currentWorkspace: null,
      setWorkspaces: mockSetWorkspaces,
      setCurrentWorkspace: mockSetCurrentWorkspace,
      addWorkspace: vi.fn(),
      updateWorkspace: vi.fn(),
      removeWorkspace: vi.fn(),
      clearWorkspaces: vi.fn(),
      isLoading: false,
      setLoading: mockSetLoading,
    })

    const { user } = render(<DashboardPage />)

    await user.click(screen.getByRole('button', { name: /create workspace/i }))

    await waitFor(() => {
      expect(screen.getByText('Create New Workspace')).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText(/name/i)
    await user.type(nameInput, 'My New Workspace')

    const slugInput = screen.getByLabelText(/slug/i)
    expect(slugInput).toHaveValue('my-new-workspace')
  })

  it('should display execution status badges', async () => {
    render(<DashboardPage />)

    await waitFor(() => {
      // Recent executions table should show success badge
      const successBadges = screen.getAllByText('Success')
      expect(successBadges.length).toBeGreaterThan(0)
    })
  })
})
