import { twMerge } from 'tailwind-merge'
import { clsx, type ClassValue } from 'clsx'

import type { DatasetStatus } from '@/types'

/** Merge Tailwind classes safely — resolves conflicts (e.g. bg-red overrides bg-blue) */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Shared Badge variant mapping for dataset status — used by DatasetsPage and DatasetDetailPage. */
export const statusVariant: Record<DatasetStatus, 'success' | 'warning' | 'error' | 'neutral'> = {
  ready:      'success',
  processing: 'warning',
  uploaded:   'neutral',
  error:      'error',
}

/** Format bytes to human-readable string */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Format a number with commas */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat().format(n)
}

/** Truncate a string with ellipsis */
export function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max) + '…' : str
}

/** Relative time (e.g. "2 hours ago") */
export function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export type ChartTypeResolved = 'bar' | 'line' | 'pie' | 'scatter'

/**
 * Resolve the chart type to render for a set of query results. The backend's
 * `visualization_suggestion` is the sole source of truth when present and
 * the data shape supports it; otherwise falls back to a local heuristic
 * (date/time-looking x-axis → line, single label/value pair with few rows →
 * pie, else bar). Shared by QueryChart (what to render) and QueryPage's
 * "Save chart" action (what type to persist) so the logic isn't duplicated.
 */
export function resolveChartType(
  results: Record<string, unknown>[],
  suggestion?: string | null
): ChartTypeResolved {
  if (!results.length) return 'bar'
  const keys = Object.keys(results[0])
  const xKey = keys[0]
  const yKeys = keys.slice(1).filter((k) => typeof results[0][k] === 'number')
  const numericKeys = keys.filter((k) => typeof results[0][k] === 'number')
  const canRenderScatter = numericKeys.length >= 2
  const canRenderPie     = keys.length === 2 && yKeys.length === 1 && results.length <= 8

  const resolvedType =
    suggestion === 'scatter' && canRenderScatter ? 'scatter' :
    suggestion === 'pie'     && canRenderPie     ? 'pie' :
    suggestion === 'line'                        ? 'line' :
    suggestion === 'bar'                         ? 'bar' :
    null
  if (resolvedType) return resolvedType

  const isTimeSeries = /date|month|year|time|week|day/i.test(xKey)
  if (canRenderPie) return 'pie'
  if (isTimeSeries) return 'line'
  return 'bar'
}
