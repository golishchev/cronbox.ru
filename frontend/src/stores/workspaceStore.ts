import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Workspace } from '@/types'

interface WorkspaceState {
  workspaces: Workspace[]
  currentWorkspace: Workspace | null
  isLoading: boolean

  setWorkspaces: (workspaces: Workspace[]) => void
  setCurrentWorkspace: (workspace: Workspace | null) => void
  setLoading: (loading: boolean) => void
  addWorkspace: (workspace: Workspace) => void
  updateWorkspace: (workspace: Workspace) => void
  removeWorkspace: (workspaceId: string) => void
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      workspaces: [],
      currentWorkspace: null,
      isLoading: false,

      setWorkspaces: (workspaces) => set({ workspaces }),

      setCurrentWorkspace: (currentWorkspace) => set({ currentWorkspace }),

      setLoading: (isLoading) => set({ isLoading }),

      addWorkspace: (workspace) =>
        set((state) => ({ workspaces: [...state.workspaces, workspace] })),

      updateWorkspace: (workspace) =>
        set((state) => ({
          workspaces: state.workspaces.map((w) =>
            w.id === workspace.id ? workspace : w
          ),
          currentWorkspace:
            state.currentWorkspace?.id === workspace.id
              ? workspace
              : state.currentWorkspace,
        })),

      removeWorkspace: (workspaceId) =>
        set((state) => ({
          workspaces: state.workspaces.filter((w) => w.id !== workspaceId),
          currentWorkspace:
            state.currentWorkspace?.id === workspaceId
              ? null
              : state.currentWorkspace,
        })),
    }),
    {
      name: 'workspace-storage',
      partialize: (state) => ({
        currentWorkspace: state.currentWorkspace,
      }),
    }
  )
)
