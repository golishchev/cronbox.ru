import { describe, it, expect, beforeEach } from 'vitest'
import { act } from '@testing-library/react'
import { useWorkspaceStore } from '../workspaceStore'
import { createMockWorkspace } from '@/test/mocks/data'

describe('workspaceStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useWorkspaceStore.setState({
      workspaces: [],
      currentWorkspace: null,
      isLoading: false,
    })
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useWorkspaceStore.getState()

      expect(state.workspaces).toEqual([])
      expect(state.currentWorkspace).toBeNull()
      expect(state.isLoading).toBe(false)
    })
  })

  describe('setWorkspaces', () => {
    it('should set workspaces array', () => {
      const workspaces = [
        createMockWorkspace({ id: 'ws-1', name: 'Workspace 1' }),
        createMockWorkspace({ id: 'ws-2', name: 'Workspace 2' }),
      ]

      act(() => {
        useWorkspaceStore.getState().setWorkspaces(workspaces)
      })

      expect(useWorkspaceStore.getState().workspaces).toEqual(workspaces)
    })

    it('should replace existing workspaces', () => {
      const oldWorkspaces = [createMockWorkspace({ id: 'old-ws' })]
      useWorkspaceStore.setState({ workspaces: oldWorkspaces })

      const newWorkspaces = [createMockWorkspace({ id: 'new-ws' })]
      act(() => {
        useWorkspaceStore.getState().setWorkspaces(newWorkspaces)
      })

      expect(useWorkspaceStore.getState().workspaces).toEqual(newWorkspaces)
    })
  })

  describe('setCurrentWorkspace', () => {
    it('should set current workspace', () => {
      const workspace = createMockWorkspace()

      act(() => {
        useWorkspaceStore.getState().setCurrentWorkspace(workspace)
      })

      expect(useWorkspaceStore.getState().currentWorkspace).toEqual(workspace)
    })

    it('should allow setting to null', () => {
      useWorkspaceStore.setState({ currentWorkspace: createMockWorkspace() })

      act(() => {
        useWorkspaceStore.getState().setCurrentWorkspace(null)
      })

      expect(useWorkspaceStore.getState().currentWorkspace).toBeNull()
    })
  })

  describe('setLoading', () => {
    it('should set loading state', () => {
      act(() => {
        useWorkspaceStore.getState().setLoading(true)
      })

      expect(useWorkspaceStore.getState().isLoading).toBe(true)

      act(() => {
        useWorkspaceStore.getState().setLoading(false)
      })

      expect(useWorkspaceStore.getState().isLoading).toBe(false)
    })
  })

  describe('addWorkspace', () => {
    it('should add workspace to the list', () => {
      const existingWorkspace = createMockWorkspace({ id: 'ws-1' })
      useWorkspaceStore.setState({ workspaces: [existingWorkspace] })

      const newWorkspace = createMockWorkspace({ id: 'ws-2', name: 'New Workspace' })
      act(() => {
        useWorkspaceStore.getState().addWorkspace(newWorkspace)
      })

      const state = useWorkspaceStore.getState()
      expect(state.workspaces).toHaveLength(2)
      expect(state.workspaces[1]).toEqual(newWorkspace)
    })

    it('should add to empty list', () => {
      const workspace = createMockWorkspace()

      act(() => {
        useWorkspaceStore.getState().addWorkspace(workspace)
      })

      expect(useWorkspaceStore.getState().workspaces).toEqual([workspace])
    })
  })

  describe('updateWorkspace', () => {
    it('should update workspace in the list', () => {
      const workspace = createMockWorkspace({ id: 'ws-1', name: 'Old Name' })
      useWorkspaceStore.setState({ workspaces: [workspace] })

      const updatedWorkspace = { ...workspace, name: 'New Name' }
      act(() => {
        useWorkspaceStore.getState().updateWorkspace(updatedWorkspace)
      })

      expect(useWorkspaceStore.getState().workspaces[0].name).toBe('New Name')
    })

    it('should update currentWorkspace if it matches', () => {
      const workspace = createMockWorkspace({ id: 'ws-1', name: 'Old Name' })
      useWorkspaceStore.setState({
        workspaces: [workspace],
        currentWorkspace: workspace,
      })

      const updatedWorkspace = { ...workspace, name: 'New Name' }
      act(() => {
        useWorkspaceStore.getState().updateWorkspace(updatedWorkspace)
      })

      expect(useWorkspaceStore.getState().currentWorkspace?.name).toBe('New Name')
    })

    it('should not update currentWorkspace if it does not match', () => {
      const workspace1 = createMockWorkspace({ id: 'ws-1', name: 'Workspace 1' })
      const workspace2 = createMockWorkspace({ id: 'ws-2', name: 'Workspace 2' })
      useWorkspaceStore.setState({
        workspaces: [workspace1, workspace2],
        currentWorkspace: workspace1,
      })

      const updatedWorkspace2 = { ...workspace2, name: 'Updated Workspace 2' }
      act(() => {
        useWorkspaceStore.getState().updateWorkspace(updatedWorkspace2)
      })

      expect(useWorkspaceStore.getState().currentWorkspace?.name).toBe('Workspace 1')
    })

    it('should not modify other workspaces', () => {
      const workspace1 = createMockWorkspace({ id: 'ws-1', name: 'Workspace 1' })
      const workspace2 = createMockWorkspace({ id: 'ws-2', name: 'Workspace 2' })
      useWorkspaceStore.setState({ workspaces: [workspace1, workspace2] })

      const updatedWorkspace1 = { ...workspace1, name: 'Updated Workspace 1' }
      act(() => {
        useWorkspaceStore.getState().updateWorkspace(updatedWorkspace1)
      })

      const state = useWorkspaceStore.getState()
      expect(state.workspaces[0].name).toBe('Updated Workspace 1')
      expect(state.workspaces[1].name).toBe('Workspace 2')
    })
  })

  describe('removeWorkspace', () => {
    it('should remove workspace from the list', () => {
      const workspace1 = createMockWorkspace({ id: 'ws-1' })
      const workspace2 = createMockWorkspace({ id: 'ws-2' })
      useWorkspaceStore.setState({ workspaces: [workspace1, workspace2] })

      act(() => {
        useWorkspaceStore.getState().removeWorkspace('ws-1')
      })

      const state = useWorkspaceStore.getState()
      expect(state.workspaces).toHaveLength(1)
      expect(state.workspaces[0].id).toBe('ws-2')
    })

    it('should set currentWorkspace to null if removed', () => {
      const workspace = createMockWorkspace({ id: 'ws-1' })
      useWorkspaceStore.setState({
        workspaces: [workspace],
        currentWorkspace: workspace,
      })

      act(() => {
        useWorkspaceStore.getState().removeWorkspace('ws-1')
      })

      expect(useWorkspaceStore.getState().currentWorkspace).toBeNull()
    })

    it('should not affect currentWorkspace if different workspace removed', () => {
      const workspace1 = createMockWorkspace({ id: 'ws-1' })
      const workspace2 = createMockWorkspace({ id: 'ws-2' })
      useWorkspaceStore.setState({
        workspaces: [workspace1, workspace2],
        currentWorkspace: workspace1,
      })

      act(() => {
        useWorkspaceStore.getState().removeWorkspace('ws-2')
      })

      expect(useWorkspaceStore.getState().currentWorkspace?.id).toBe('ws-1')
    })

    it('should do nothing if workspace not found', () => {
      const workspace = createMockWorkspace({ id: 'ws-1' })
      useWorkspaceStore.setState({ workspaces: [workspace] })

      act(() => {
        useWorkspaceStore.getState().removeWorkspace('non-existent')
      })

      expect(useWorkspaceStore.getState().workspaces).toHaveLength(1)
    })
  })
})
