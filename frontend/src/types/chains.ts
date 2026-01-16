import type { HttpMethod, PaginationMeta } from './index'

// Trigger type enum
export type TriggerType = 'cron' | 'delayed' | 'manual'

// Chain status enum
export type ChainStatus = 'pending' | 'running' | 'success' | 'failed' | 'partial' | 'cancelled'

// Step status enum
export type StepStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped'

// Condition for step execution
export interface StepCondition {
  operator: 'status_code_in' | 'status_code_not_in' | 'status_code_equals' | 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'regex' | 'exists' | 'not_exists'
  field?: string // JSONPath, required for value comparisons
  value: string | number | number[] | string[]
}

// Chain Step types
export interface ChainStep {
  id: string
  chain_id: string
  step_order: number
  name: string
  url: string
  method: HttpMethod
  headers: Record<string, string>
  body: string | null
  timeout_seconds: number
  retry_count: number
  retry_delay_seconds: number
  condition: StepCondition | null
  extract_variables: Record<string, string>
  continue_on_failure: boolean
  created_at: string
  updated_at: string
}

export interface CreateChainStepRequest {
  step_order: number
  name: string
  url: string
  method?: HttpMethod
  headers?: Record<string, string>
  body?: string
  timeout_seconds?: number
  retry_count?: number
  retry_delay_seconds?: number
  condition?: StepCondition | null
  extract_variables?: Record<string, string>
  continue_on_failure?: boolean
}

export interface UpdateChainStepRequest {
  name?: string
  url?: string
  method?: HttpMethod
  headers?: Record<string, string>
  body?: string
  timeout_seconds?: number
  retry_count?: number
  retry_delay_seconds?: number
  condition?: StepCondition | null
  extract_variables?: Record<string, string>
  continue_on_failure?: boolean
}

// Task Chain types
export interface TaskChain {
  id: string
  workspace_id: string
  worker_id: string | null
  name: string
  description: string | null
  tags: string[]
  trigger_type: TriggerType
  schedule: string | null
  timezone: string
  execute_at: string | null
  stop_on_failure: boolean
  timeout_seconds: number
  is_active: boolean
  is_paused: boolean
  last_run_at: string | null
  last_status: ChainStatus | null
  next_run_at: string | null
  consecutive_failures: number
  notify_on_failure: boolean
  notify_on_success: boolean
  notify_on_partial: boolean
  created_at: string
  updated_at: string
}

export interface TaskChainDetail extends TaskChain {
  steps: ChainStep[]
}

export interface CreateTaskChainRequest {
  name: string
  description?: string
  tags?: string[]
  trigger_type?: TriggerType
  schedule?: string
  timezone?: string
  execute_at?: string
  stop_on_failure?: boolean
  timeout_seconds?: number
  notify_on_failure?: boolean
  notify_on_success?: boolean
  notify_on_partial?: boolean
  worker_id?: string
  steps?: Omit<CreateChainStepRequest, 'step_order'>[]
}

export interface UpdateTaskChainRequest {
  name?: string
  description?: string
  tags?: string[]
  trigger_type?: TriggerType
  schedule?: string
  timezone?: string
  execute_at?: string
  stop_on_failure?: boolean
  timeout_seconds?: number
  is_active?: boolean
  notify_on_failure?: boolean
  notify_on_success?: boolean
  notify_on_partial?: boolean
  worker_id?: string | null
}

// Chain Execution types
export interface ChainExecution {
  id: string
  workspace_id: string
  chain_id: string
  status: ChainStatus
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  total_steps: number
  completed_steps: number
  failed_steps: number
  skipped_steps: number
  variables: Record<string, unknown>
  error_message: string | null
  created_at: string
}

export interface StepExecution {
  id: string
  chain_execution_id: string
  step_id: string | null
  step_order: number
  step_name: string
  status: StepStatus
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  retry_attempt: number
  request_url: string
  request_method: HttpMethod
  request_headers: Record<string, string> | null
  request_body: string | null
  response_status_code: number | null
  response_headers: Record<string, string> | null
  response_body: string | null
  response_size_bytes: number | null
  extracted_variables: Record<string, unknown>
  condition_met: boolean | null
  condition_details: string | null
  error_message: string | null
  error_type: string | null
  created_at: string
}

export interface ChainExecutionDetail extends ChainExecution {
  step_executions: StepExecution[]
}

// API Response types
export interface TaskChainsResponse {
  chains: TaskChain[]
  pagination: PaginationMeta
}

export interface ChainExecutionsResponse {
  executions: ChainExecution[]
  pagination: PaginationMeta
}

// Chain run request
export interface ChainRunRequest {
  initial_variables?: Record<string, string>
}

// Step reorder request
export interface StepReorderRequest {
  step_orders: Array<Record<string, number>>
}
