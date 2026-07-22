// All shared TypeScript types for the AI BI Dashboard frontend.
// Import from '@/types' anywhere in the app.

export interface User {
  id: number
  username: string
  email: string
  first_name: string | null
  last_name: string | null
  avatar_url: string | null
  is_admin: boolean
  created_at: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface AuthResponse extends AuthTokens {
  user: User
}

export type DatasetStatus = 'uploaded' | 'processing' | 'ready' | 'error'
export type FileType = 'csv' | 'excel' | 'json'

export interface ColumnMeta {
  type: string
  nullable: boolean
  sample_values: unknown[]
}

export interface Dataset {
  id: number
  user_id: number
  name: string
  description: string | null
  file_name: string
  file_type: FileType
  file_size: number | null
  row_count: number | null
  column_count: number | null
  columns_metadata: Record<string, ColumnMeta> | null
  tables_metadata?: Record<string, { original_name: string; row_count: number; column_count: number }> | null
  table_relationships?: { from_table: string; to_table: string; column: string; to_column?: string; confidence: number }[] | null
  is_public: boolean
  status: DatasetStatus
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface DatasetPreview {
  id: number
  columns: string[]
  data: unknown[][]
  row_count: number
  total_rows: number
}

export interface PaginatedDatasets {
  data: Dataset[]
  pagination: {
    page: number
    limit: number
    total: number
    total_pages: number
  }
}

export type QueryStatus = 'pending' | 'success' | 'error'

export interface Query {
  id: number
  dataset_id: number
  question: string
  generated_sql: string | null
  results: Record<string, unknown>[] | null
  execution_time_ms: number | null
  row_count: number | null
  status: QueryStatus
  error_message: string | null
  ai_model_used: string | null
  confidence_score: number | null
  visualization_suggestion: string | null
  created_at: string
  executed_at: string | null
}

export type ChartType = 'line' | 'bar' | 'pie' | 'scatter' | 'area'

export interface Visualization {
  id: number
  query_id: number
  user_id: number
  chart_type: ChartType
  title: string | null
  x_axis: string | null
  y_axis: string | null
  config: Record<string, unknown> | null
  is_saved: boolean
  created_at: string
  updated_at: string
}

export interface Report {
  id: number
  user_id: number
  dataset_id: number
  title: string
  description: string | null
  query_ids: number[] | null
  visualization_ids: number[] | null
  status: string
  pdf_path: string | null
  file_size: number | null
  downloaded_count: number
  created_at: string
  updated_at: string
}

export type InsightSeverity = 'low' | 'medium' | 'high' | 'critical'

export interface Insight {
  id: number
  dataset_id: number
  insight_type: string
  title: string
  description: string
  affected_columns: string[] | null
  severity: InsightSeverity
  confidence_score: number | null
  insight_metadata: Record<string, unknown> | null
  is_dismissed: boolean
  created_at: string
  dismissed_at: string | null
}
