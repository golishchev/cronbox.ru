import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { HeartbeatForm } from '@/components/heartbeats/HeartbeatForm'
import * as heartbeatsApi from '@/api/heartbeats'

// Mock APIs
vi.mock('@/api/heartbeats', () => ({
  createHeartbeat: vi.fn(),
  updateHeartbeat: vi.fn(),
}))

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  toast: vi.fn(),
}))

describe('HeartbeatForm', () => {
  const mockOnSuccess = vi.fn()
  const mockOnCancel = vi.fn()
  const mockWorkspaceId = 'workspace-1'

  const mockHeartbeat = {
    id: 'heartbeat-1',
    workspace_id: 'workspace-1',
    name: 'Test Heartbeat',
    description: 'A test heartbeat',
    ping_token: 'abc123',
    ping_url: 'https://cronbox.ru/ping/abc123',
    expected_interval: 3600,
    grace_period: 600,
    status: 'healthy' as const,
    is_paused: false,
    last_ping_at: null,
    next_expected_at: null,
    consecutive_misses: 0,
    alert_sent: false,
    notify_on_late: true,
    notify_on_recovery: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(heartbeatsApi.createHeartbeat).mockResolvedValue(mockHeartbeat)
    vi.mocked(heartbeatsApi.updateHeartbeat).mockResolvedValue(mockHeartbeat)
  })

  describe('Create mode', () => {
    it('should render form fields', () => {
      render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
    })

    it('should have create button', () => {
      render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('button', { name: /create heartbeat/i })).toBeInTheDocument()
    })

    it('should have cancel button', () => {
      render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })

    it('should call onCancel when cancel clicked', async () => {
      const { user } = render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(mockOnCancel).toHaveBeenCalled()
    })

    it('should show error when name is empty', async () => {
      const { user } = render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      await user.click(screen.getByRole('button', { name: /create heartbeat/i }))

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument()
      })
    })

    it('should call createHeartbeat with form data', async () => {
      const { user } = render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      await user.type(screen.getByLabelText(/name/i), 'My Heartbeat')

      await user.click(screen.getByRole('button', { name: /create heartbeat/i }))

      await waitFor(() => {
        expect(heartbeatsApi.createHeartbeat).toHaveBeenCalledWith(
          mockWorkspaceId,
          expect.objectContaining({
            name: 'My Heartbeat',
            expected_interval: '1h',
            grace_period: '10m',
          })
        )
      })
    })

    it('should call onSuccess after successful creation', async () => {
      const { user } = render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      await user.type(screen.getByLabelText(/name/i), 'My Heartbeat')
      await user.click(screen.getByRole('button', { name: /create heartbeat/i }))

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled()
      })
    })

    it('should have notification checkboxes', () => {
      render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByLabelText(/notify when late/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/notify on recovery/i)).toBeInTheDocument()
    })
  })

  describe('Edit mode', () => {
    it('should populate fields with existing data', () => {
      render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          heartbeat={mockHeartbeat}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByDisplayValue('Test Heartbeat')).toBeInTheDocument()
      expect(screen.getByDisplayValue('A test heartbeat')).toBeInTheDocument()
    })

    it('should have update button', () => {
      render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          heartbeat={mockHeartbeat}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('button', { name: /update heartbeat/i })).toBeInTheDocument()
    })

    it('should call updateHeartbeat with form data', async () => {
      const { user } = render(
        <HeartbeatForm
          workspaceId={mockWorkspaceId}
          heartbeat={mockHeartbeat}
          onSuccess={mockOnSuccess}
          onCancel={mockOnCancel}
        />
      )

      const nameInput = screen.getByDisplayValue('Test Heartbeat')
      await user.clear(nameInput)
      await user.type(nameInput, 'Updated Heartbeat')

      await user.click(screen.getByRole('button', { name: /update heartbeat/i }))

      await waitFor(() => {
        expect(heartbeatsApi.updateHeartbeat).toHaveBeenCalledWith(
          mockWorkspaceId,
          mockHeartbeat.id,
          expect.objectContaining({
            name: 'Updated Heartbeat',
          })
        )
      })
    })
  })
})
