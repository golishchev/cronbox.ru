// User types
export interface User {
  id: string
  email: string
  name: string
  telegram_id: number | null
  telegram_username: string | null
  email_verified: boolean
  is_active: boolean
  is_superuser: boolean
  preferred_language: 'en' | 'ru'
  avatar_url: string | null
  created_at: string
  updated_at: string
}

// Auth types
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  name: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AuthResponse {
  user: User
  tokens: TokenResponse
}

// OTP types
export interface OTPRequestData {
  email: string
}

export interface OTPVerifyData {
  email: string
  code: string
}

export interface OTPResponse {
  message: string
  expires_in: number
}

// Workspace types
export interface Workspace {
  id: string
  name: string
  slug: string
  owner_id: string
  plan_id: string
  cron_tasks_count: number
  delayed_tasks_this_month: number
  default_timezone: string
  created_at: string
  updated_at: string
}

export interface WorkspaceWithStats extends Workspace {
  plan_name: string | null
  active_cron_tasks: number
  pending_delayed_tasks: number
  executions_today: number
  success_rate_7d: number
}

export interface CreateWorkspaceRequest {
  name: string
  slug: string
  default_timezone?: string
}

// HTTP Method enum
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD'

// Task status enum
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled'

// Overlap policy enum
export type OverlapPolicy = 'allow' | 'skip' | 'queue'

// Cron Task types
export interface CronTask {
  id: string
  workspace_id: string
  name: string
  description: string | null
  url: string
  method: HttpMethod
  headers: Record<string, string>
  body: string | null
  schedule: string
  timezone: string
  timeout_seconds: number
  retry_count: number
  retry_delay_seconds: number
  is_active: boolean
  is_paused: boolean
  last_run_at: string | null
  last_status: TaskStatus | null
  next_run_at: string | null
  consecutive_failures: number
  notify_on_failure: boolean
  notify_on_recovery: boolean
  // Overlap prevention
  overlap_policy: OverlapPolicy
  max_instances: number
  max_queue_size: number
  execution_timeout: number | null
  running_instances: number
  created_at: string
  updated_at: string
}

export interface CreateCronTaskRequest {
  name: string
  description?: string
  url: string
  method?: HttpMethod
  headers?: Record<string, string>
  body?: string
  schedule: string
  timezone?: string
  timeout_seconds?: number
  retry_count?: number
  retry_delay_seconds?: number
  notify_on_failure?: boolean
  notify_on_recovery?: boolean
  // Overlap prevention
  overlap_policy?: OverlapPolicy
  max_instances?: number
  max_queue_size?: number
  execution_timeout?: number
}

export interface UpdateCronTaskRequest {
  name?: string
  description?: string
  url?: string
  method?: HttpMethod
  headers?: Record<string, string>
  body?: string
  schedule?: string
  timezone?: string
  timeout_seconds?: number
  retry_count?: number
  is_active?: boolean
  notify_on_failure?: boolean
  notify_on_recovery?: boolean
  // Overlap prevention
  overlap_policy?: OverlapPolicy
  max_instances?: number
  max_queue_size?: number
  execution_timeout?: number
}

// Delayed Task types
export interface DelayedTask {
  id: string
  workspace_id: string
  idempotency_key: string | null
  name: string | null
  tags: string[]
  url: string
  method: HttpMethod
  headers: Record<string, string>
  body: string | null
  execute_at: string
  timeout_seconds: number
  retry_count: number
  retry_delay_seconds: number
  status: TaskStatus
  executed_at: string | null
  retry_attempt: number
  callback_url: string | null
  created_at: string
  updated_at: string
}

export interface CreateDelayedTaskRequest {
  url: string
  method?: HttpMethod
  headers?: Record<string, string>
  body?: string
  execute_at: string
  name?: string
  idempotency_key?: string
  tags?: string[]
  timeout_seconds?: number
  retry_count?: number
  retry_delay_seconds?: number
  callback_url?: string
}

export interface UpdateDelayedTaskRequest {
  url?: string
  method?: HttpMethod
  headers?: Record<string, string>
  body?: string
  execute_at?: string
  name?: string
  tags?: string[]
  timeout_seconds?: number
  retry_count?: number
  retry_delay_seconds?: number
  callback_url?: string
}

// Execution types
export type ExecutionTaskType = 'cron' | 'delayed' | 'chain' | 'heartbeat' | 'ssl'
export type ExecutionStatus = TaskStatus | 'partial' | 'cancelled'

export interface Execution {
  id: string
  workspace_id: string
  task_type: ExecutionTaskType
  task_id: string
  task_name: string | null
  status: ExecutionStatus
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  retry_attempt: number | null  // null for chains
  request_url: string | null    // null for chains
  request_method: HttpMethod | null  // null for chains
  response_status_code: number | null
  error_message: string | null
  error_type: string | null
  created_at: string
  // Chain-specific fields
  total_steps?: number | null
  completed_steps?: number | null
  failed_steps?: number | null
  skipped_steps?: number | null
}

export interface ExecutionDetail extends Execution {
  request_headers: Record<string, string> | null
  request_body: string | null
  response_headers: Record<string, string> | null
  response_body: string | null
  response_size_bytes: number | null
  // Chain-specific
  chain_variables?: Record<string, unknown> | null
}

export interface ExecutionStats {
  total: number
  success: number
  failed: number
  success_rate: number
  avg_duration_ms: number | null
}

// Pagination
export interface PaginationMeta {
  page: number
  limit: number
  total: number
  total_pages: number
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMeta
}

// Worker/API Key types
export type WorkerStatus = 'online' | 'offline' | 'busy'

export interface Worker {
  id: string
  workspace_id: string
  name: string
  description: string | null
  status: WorkerStatus
  is_active: boolean
  api_key_prefix: string
  last_heartbeat: string | null
  tasks_completed: number
  tasks_failed: number
  created_at: string
  updated_at: string
}

export interface WorkerCreateRequest {
  name: string
  description?: string
}

export interface WorkerUpdateRequest {
  name?: string
  description?: string
  is_active?: boolean
}

export interface WorkerCreateResponse {
  id: string
  workspace_id: string
  name: string
  description: string | null
  api_key: string
  api_key_prefix: string
  created_at: string
}

// Telegram
export interface TelegramConnectResponse {
  code: string
  expires_in: number
  bot_username: string
}

// Heartbeat types
export type HeartbeatStatus = 'waiting' | 'healthy' | 'late' | 'dead' | 'paused'

export interface Heartbeat {
  id: string
  workspace_id: string
  name: string
  description: string | null
  ping_token: string
  ping_url: string
  expected_interval: number  // seconds
  grace_period: number  // seconds
  status: HeartbeatStatus
  is_paused: boolean
  last_ping_at: string | null
  next_expected_at: string | null
  consecutive_misses: number
  alert_sent: boolean
  notify_on_late: boolean
  notify_on_recovery: boolean
  created_at: string
  updated_at: string
}

export interface CreateHeartbeatRequest {
  name: string
  description?: string
  expected_interval: string  // e.g., '1h', '30m'
  grace_period?: string  // e.g., '10m'
  notify_on_late?: boolean
  notify_on_recovery?: boolean
}

export interface UpdateHeartbeatRequest {
  name?: string
  description?: string
  expected_interval?: string
  grace_period?: string
  notify_on_late?: boolean
  notify_on_recovery?: boolean
}

export interface HeartbeatPing {
  id: string
  heartbeat_id: string
  duration_ms: number | null
  status_message: string | null
  payload: Record<string, unknown> | null
  source_ip: string | null
  created_at: string
}

// SSL Monitor types
export type SSLMonitorStatus = 'pending' | 'valid' | 'expiring' | 'expired' | 'invalid' | 'error' | 'paused'

export interface SSLMonitor {
  id: string
  workspace_id: string
  name: string
  description: string | null
  domain: string
  port: number
  status: SSLMonitorStatus
  is_paused: boolean
  // Certificate info
  issuer: string | null
  subject: string | null
  serial_number: string | null
  valid_from: string | null
  valid_until: string | null
  days_until_expiry: number | null
  // TLS info
  tls_version: string | null
  cipher_suite: string | null
  // Validation info
  chain_valid: boolean | null
  hostname_match: boolean | null
  // Check tracking
  last_check_at: string | null
  next_check_at: string | null
  last_error: string | null
  retry_count: number
  // Notifications
  notify_on_expiring: boolean
  notify_on_error: boolean
  created_at: string
  updated_at: string
}

export interface CreateSSLMonitorRequest {
  name: string
  description?: string
  domain: string
  port?: number
  notify_on_expiring?: boolean
  notify_on_error?: boolean
}

export interface UpdateSSLMonitorRequest {
  name?: string
  description?: string
  port?: number
  notify_on_expiring?: boolean
  notify_on_error?: boolean
}

// API Error
export interface ApiError {
  detail: string
}
