import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Database, MessageSquare, BarChart2, ArrowLeft, RefreshCw } from 'lucide-react'
import { datasetService } from '@/services/datasetService'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import { formatBytes, formatNumber, timeAgo } from '@/utils/helpers'
import type { DatasetStatus } from '@/types'

const statusVariant: Record<DatasetStatus, 'success' | 'warning' | 'error' | 'neutral'> = {
  ready: 'success', processing: 'warning', uploaded: 'neutral', error: 'error',
}

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>()
  const datasetId = Number(id)

  const { data: ds, isLoading } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => datasetService.get(datasetId),
  })

  const { data: preview } = useQuery({
    queryKey: ['dataset-preview', datasetId],
    queryFn: () => datasetService.preview(datasetId, 10),
    enabled: ds?.status === 'ready',
  })

  if (isLoading) return <div className="flex justify-center py-20"><Spinner size={28} /></div>
  if (!ds) return <p className="text-sm text-muted">Dataset not found.</p>

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link to="/datasets" className="inline-flex items-center gap-1 text-xs text-muted hover:text-accent mb-2">
            <ArrowLeft size={12} /> Back to Datasets
          </Link>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-[#1f2328]">{ds.name}</h2>
            {ds.status === 'processing' && <RefreshCw size={14} className="animate-spin text-yellow-500" />}
            <Badge variant={statusVariant[ds.status]}>{ds.status}</Badge>
          </div>
          {ds.description && <p className="text-sm text-muted mt-1">{ds.description}</p>}
        </div>
        {ds.status === 'ready' && (
          <div className="flex gap-2 shrink-0">
            <Link to={`/query/${ds.id}`}>
              <Button size="sm"><MessageSquare size={13} /> Query</Button>
            </Link>
            <Link to={`/insights/${ds.id}`}>
              <Button size="sm" variant="secondary"><BarChart2 size={13} /> Insights</Button>
            </Link>
          </div>
        )}
      </div>

      {/* Meta cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Rows',    value: ds.row_count    ? formatNumber(ds.row_count)    : '—' },
          { label: 'Columns', value: ds.column_count ? formatNumber(ds.column_count) : '—' },
          { label: 'Size',    value: ds.file_size    ? formatBytes(ds.file_size)     : '—' },
          { label: 'Uploaded',value: timeAgo(ds.created_at) },
        ].map(({ label, value }) => (
          <Card key={label} padding="sm">
            <p className="text-xs text-muted">{label}</p>
            <p className="text-lg font-semibold text-[#1f2328] mt-0.5">{value}</p>
          </Card>
        ))}
      </div>

      {/* Column schema */}
      {ds.columns_metadata && (
        <Card>
          <h3 className="text-sm font-semibold text-[#1f2328] mb-3 flex items-center gap-2">
            <Database size={14} className="text-muted" /> Schema
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {Object.entries(ds.columns_metadata).map(([col, meta]) => (
              <div key={col} className="flex items-center justify-between px-3 py-2 bg-surface rounded-lg text-xs">
                <span className="font-medium text-[#1f2328] truncate">{col}</span>
                <Badge variant="neutral">{meta.type}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Data preview */}
      {preview && (
        <Card>
          <h3 className="text-sm font-semibold text-[#1f2328] mb-3">
            Preview <span className="text-muted font-normal text-xs">(first {preview.row_count} of {formatNumber(preview.total_rows)} rows)</span>
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  {preview.columns.map((col) => (
                    <th key={col} className="text-left text-muted pb-2 pr-4 font-medium whitespace-nowrap">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {preview.data.map((row, i) => (
                  <tr key={i} className="hover:bg-surface">
                    {row.map((cell, j) => (
                      <td key={j} className="py-2 pr-4 text-[#1f2328] whitespace-nowrap">
                        {String(cell ?? '—')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
