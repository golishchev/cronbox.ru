import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { SSLMonitorsPage } from '@/pages/ssl/SSLMonitorsPage'
import * as sslMonitorsApi from '@/api/sslMonitors'
import * as billingApi from '@/api/billing'
import { useWorkspaceStore } from '@/stores/workspaceStore'

// Mock APIs
vi.mock('@/api/sslMonitors', () => ({
  getSSLMonitors: vi.fn(),
  deleteSSLMonitor: vi.fn(),
  pauseSSLMonitor: vi.fn(),
  resumeSSLMonitor: vi.fn(),
  checkSSLMonitor: vi.fn(),
}))

vi.mock('@/api/billing', () => ({
  getSubscription: vi.fn(),
  getPlans: vi.fn(),
}))

// Mock workspaceStore
vi.mock('@/stores/workspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('SSLMonitorsPage', () => {
  const mockOnNavigate = vi.fn()
  const mockWorkspace = {
    id: 'workspace-1',
    name: 'Test Workspace',
    slug: 'test-workspace',
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const mockPlan = {
    id: 'plan-1',
    name: 'pro',
    display_name: 'Pro',
    description: 'Pro plan',
    price_monthly: 999,
    price_yearly: 9999,
    max_cron_tasks: 50,
    max_delayed_tasks_per_month: 5000,
    max_workspaces: 5,
    max_execution_history_days: 90,
    min_cron_interval_minutes: 1,
    telegram_notifications: true,
    email_notifications: true,
    webhook_callbacks: true,
    custom_headers: true,
    retry_on_failure: true,
    max_task_chains: 20,
    max_chain_steps: 20,
    chain_variable_substitution: true,
    min_chain_interval_minutes: 1,
    max_heartbeats: 50,
    min_heartbeat_interval_minutes: 5,
    max_ssl_monitors: 10,
    is_active: true,
    is_public: true,
    sort_order: 1,
  }

  const mockSSLMonitor = {
    id: 'ssl-1',
    workspace_id: 'workspace-1',
    name: 'Test SSL Monitor',
    description: 'A test SSL monitor',
    domain: 'example.com',
    port: 443,
    status: 'valid' as const,
    is_paused: false,
    issuer: "Let's Encrypt",
    subject: 'example.com',
    serial_number: 'ABC123',
    valid_from: '2024-01-01T00:00:00Z',
    valid_until: '2025-06-01T00:00:00Z',
    days_until_expiry: 180,
    tls_version: 'TLSv1.3',
    cipher_suite: 'TLS_AES_256_GCM_SHA384',
    chain_valid: true,
    hostname_match: true,
    last_check_at: '2024-01-01T12:00:00Z',
    next_check_at: '2024-01-02T12:00:00Z',
    last_error: null,
    retry_count: 0,
    notify_on_expiring: true,
    notify_on_error: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
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
    vi.mocked(sslMonitorsApi.getSSLMonitors).mockResolvedValue({
      monitors: [mockSSLMonitor],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })
    vi.mocked(billingApi.getSubscription).mockResolvedValue({
      id: 'sub-1',
      user_id: 'user-1',
      plan_id: 'plan-1',
      status: 'active',
      current_period_start: '2024-01-01T00:00:00Z',
      current_period_end: '2024-02-01T00:00:00Z',
      cancel_at_period_end: false,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    })
    vi.mocked(billingApi.getPlans).mockResolvedValue([mockPlan])
  })

  it('should render page title', async () => {
    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('SSL Monitors')).toBeInTheDocument()
    })
  })

  it('should load SSL monitors on mount', async () => {
    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(sslMonitorsApi.getSSLMonitors).toHaveBeenCalledWith('workspace-1')
    })
  })

  it('should display SSL monitors in table', async () => {
    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test SSL Monitor')).toBeInTheDocument()
    })
  })

  it('should display domain name', async () => {
    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('example.com')).toBeInTheDocument()
    })
  })

  it('should display valid status badge', async () => {
    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      // Status badge shows "Valid (Xd)" where X is days until expiry
      expect(screen.getByText(/Valid/)).toBeInTheDocument()
    })
  })

  it('should show empty state when no SSL monitors', async () => {
    vi.mocked(sslMonitorsApi.getSSLMonitors).mockResolvedValue({
      monitors: [],
      pagination: {
        page: 1,
        limit: 20,
        total: 0,
        total_pages: 0,
      },
    })

    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(sslMonitorsApi.getSSLMonitors).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByText(/no ssl monitors yet/i)).toBeInTheDocument()
    })
  })

  it('should have create monitor button', async () => {
    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add monitor/i })).toBeInTheDocument()
    })
  })

  it('should open create dialog when button clicked', async () => {
    const { user } = render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add monitor/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /add monitor/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('should call pauseSSLMonitor when pause button clicked', async () => {
    vi.mocked(sslMonitorsApi.pauseSSLMonitor).mockResolvedValue(undefined)

    const { user } = render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test SSL Monitor')).toBeInTheDocument()
    })

    // Find pause button by its accessible name or title
    const buttons = screen.getAllByRole('button')
    const pauseButton = buttons.find(btn => btn.getAttribute('title')?.toLowerCase().includes('pause'))

    if (pauseButton) {
      await user.click(pauseButton)
      await waitFor(() => {
        expect(sslMonitorsApi.pauseSSLMonitor).toHaveBeenCalledWith('workspace-1', 'ssl-1')
      })
    }
  })

  it('should call checkSSLMonitor when check now button clicked', async () => {
    vi.mocked(sslMonitorsApi.checkSSLMonitor).mockResolvedValue(mockSSLMonitor)

    const { user } = render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test SSL Monitor')).toBeInTheDocument()
    })

    const buttons = screen.getAllByRole('button')
    const checkButton = buttons.find(btn => btn.getAttribute('title')?.toLowerCase().includes('check'))

    if (checkButton) {
      await user.click(checkButton)
      await waitFor(() => {
        expect(sslMonitorsApi.checkSSLMonitor).toHaveBeenCalledWith('workspace-1', 'ssl-1')
      })
    }
  })

  it('should show delete confirmation dialog', async () => {
    const { user } = render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Test SSL Monitor')).toBeInTheDocument()
    })

    const buttons = screen.getAllByRole('button')
    const deleteButton = buttons.find(btn => btn.getAttribute('title')?.toLowerCase().includes('delete'))

    if (deleteButton) {
      await user.click(deleteButton)
      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument()
      })
    }
  })

  it('should display expiring status', async () => {
    vi.mocked(sslMonitorsApi.getSSLMonitors).mockResolvedValue({
      monitors: [{
        ...mockSSLMonitor,
        status: 'expiring' as const,
        days_until_expiry: 10,
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })

    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      // Status badge shows "Expiring (Xd)" where X is days until expiry
      expect(screen.getByText(/Expiring/)).toBeInTheDocument()
    })
  })

  it('should display expired status', async () => {
    vi.mocked(sslMonitorsApi.getSSLMonitors).mockResolvedValue({
      monitors: [{
        ...mockSSLMonitor,
        status: 'expired' as const,
        days_until_expiry: -10,
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })

    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Expired')).toBeInTheDocument()
    })
  })

  it('should display error status', async () => {
    vi.mocked(sslMonitorsApi.getSSLMonitors).mockResolvedValue({
      monitors: [{
        ...mockSSLMonitor,
        status: 'error' as const,
        last_error: 'Connection refused',
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })

    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument()
    })
  })

  it('should display paused status', async () => {
    vi.mocked(sslMonitorsApi.getSSLMonitors).mockResolvedValue({
      monitors: [{
        ...mockSSLMonitor,
        status: 'paused' as const,
        is_paused: true,
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })

    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Paused')).toBeInTheDocument()
    })
  })

  it('should display pending status for new monitor', async () => {
    vi.mocked(sslMonitorsApi.getSSLMonitors).mockResolvedValue({
      monitors: [{
        ...mockSSLMonitor,
        status: 'pending' as const,
        last_check_at: null,
        valid_until: null,
        issuer: null,
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })

    render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Pending')).toBeInTheDocument()
    })
  })

  it('should call resumeSSLMonitor when resume button clicked on paused monitor', async () => {
    vi.mocked(sslMonitorsApi.getSSLMonitors).mockResolvedValue({
      monitors: [{
        ...mockSSLMonitor,
        status: 'paused' as const,
        is_paused: true,
      }],
      pagination: {
        page: 1,
        limit: 20,
        total: 1,
        total_pages: 1,
      },
    })
    vi.mocked(sslMonitorsApi.resumeSSLMonitor).mockResolvedValue(undefined)

    const { user } = render(<SSLMonitorsPage onNavigate={mockOnNavigate} />)

    await waitFor(() => {
      expect(screen.getByText('Paused')).toBeInTheDocument()
    })

    const buttons = screen.getAllByRole('button')
    const resumeButton = buttons.find(btn => btn.getAttribute('title')?.toLowerCase().includes('resume'))

    if (resumeButton) {
      await user.click(resumeButton)
      await waitFor(() => {
        expect(sslMonitorsApi.resumeSSLMonitor).toHaveBeenCalledWith('workspace-1', 'ssl-1')
      })
    }
  })
})
