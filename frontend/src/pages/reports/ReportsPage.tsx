import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Download, Trash2, Plus, Loader2, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { reportService } from '@/services/reportService'
import { datasetService } from '@/services/datasetService'
import { queryService } from '@/services/queryService'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import { formatBytes, timeAgo } from '@/utils/helpers'
import type { Dataset } from '@/types'

export default function ReportsPage() {
  const qc = useQueryClient()
  const [downloading, setDownloading] = useState<number | null>(null)
  const [pickerDataset, setPickerDataset] = useState<Dataset | null>(null)

  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: reportService.list,
    // Reports generate via a background task (see report_service.py) —
    // poll while any report is still pending/generating so completion
    // shows up on its own instead of requiring a manual page refresh.
    refetchInterval: (query) => {
      const list = query.state.data
      const stillWorking = list?.some((r) => r.status === 'pending' || r.status === 'generating')
      return stillWorking ? 2000 : false
    },
  })

  const { data: datasets } = useQuery({
    queryKey: ['datasets', 1, ''],
    queryFn: () => datasetService.list({ limit: 50 }),
  })

  const deleteMutation = useMutation({
    mutationFn: reportService.delete,
    onSuccess: () => {
      toast.success('Report deleted.')
      qc.invalidateQueries({ queryKey: ['reports'] })
    },
  })

  const handleDownload = async (reportId: number) => {
    setDownloading(reportId)
    try {
      await reportService.download(reportId)
    } catch {
      toast.error('Failed to download report.')
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Quick generate */}
      {datasets?.data.filter((d) => d.status === 'ready').length ? (
        <Card>
          <h2 className="text-sm font-semibold text-[#1f2328] mb-3">Generate Report</h2>
          <div className="flex flex-wrap gap-2">
            {datasets.data.filter((d) => d.status === 'ready').map((ds) => (
              <Button
                key={ds.id}
                variant="secondary"
                size="sm"
                onClick={() => setPickerDataset(ds)}
              >
                <Plus size={12} />
                {ds.name}
              </Button>
            ))}
          </div>
        </Card>
      ) : null}

      {pickerDataset && (
        <ReportPickerModal
          dataset={pickerDataset}
          onClose={() => setPickerDataset(null)}
          onCreated={() => {
            setPickerDataset(null)
            qc.invalidateQueries({ queryKey: ['reports'] })
          }}
        />
      )}

      {/* Reports list */}
      <Card padding="sm">
        <h2 className="text-sm font-semibold text-[#1f2328] mb-4">Reports</h2>

        {isLoading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : !reports?.length ? (
          <div className="text-center py-10">
            <FileText size={36} className="text-border mx-auto mb-3" />
            <p className="text-sm font-medium text-[#1f2328]">No reports yet</p>
            <p className="text-xs text-muted mt-1">Generate a report from a ready dataset above.</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {reports.map((r) => (
              <div key={r.id} className="flex items-center gap-4 py-3">
                <FileText size={16} className="text-muted shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#1f2328] truncate">{r.title}</p>
                  <p className="text-xs text-muted mt-0.5">
                    {r.file_size ? formatBytes(r.file_size) + ' · ' : ''}
                    {r.downloaded_count} downloads · {timeAgo(r.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {r.status === 'pending' || r.status === 'generating' ? (
                    <span className="flex items-center gap-1.5 text-xs text-muted">
                      <Loader2 size={12} className="animate-spin" /> Generating…
                    </span>
                  ) : (
                    <Badge variant={r.status === 'completed' ? 'success' : 'error'}>{r.status}</Badge>
                  )}
                  {r.status === 'completed' && (
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={downloading === r.id}
                      onClick={() => handleDownload(r.id)}
                    >
                      <Download size={12} /> Download
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="hover:text-red-500"
                    loading={deleteMutation.isPending}
                    onClick={() => { if (confirm('Delete this report?')) deleteMutation.mutate(r.id) }}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

function ReportPickerModal({
  dataset,
  onClose,
  onCreated,
}: {
  dataset: Dataset
  onClose: () => void
  onCreated: () => void
}) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [includeInsights, setIncludeInsights] = useState(true)
  const [creating, setCreating] = useState(false)

  const { data: queries, isLoading } = useQuery({
    queryKey: ['queries', dataset.id, 'success'],
    queryFn: () => queryService.list({ dataset_id: dataset.id, limit: 100 }),
  })

  const successfulQueries = (queries ?? []).filter((q) => q.status === 'success')

  const toggle = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const canGenerate = selectedIds.length > 0 || includeInsights

  const handleGenerate = async () => {
    setCreating(true)
    try {
      await reportService.create({
        dataset_id: dataset.id,
        title: `Report — ${dataset.name}`,
        query_ids: selectedIds,
        include_insights: includeInsights,
      })
      toast.success('Report generation started!')
      onCreated()
    } catch {
      toast.error('Failed to generate report.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-picker-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg max-h-[85vh] flex flex-col bg-white border border-border rounded-xl shadow-[var(--shadow-card)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-border shrink-0">
          <h2 id="report-picker-title" className="text-sm font-semibold text-[#1f2328]">
            New report — {dataset.name}
          </h2>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X size={16} />
          </Button>
        </div>

        <div className="p-4 space-y-4 overflow-y-auto">
          <label className="flex items-center gap-2 text-sm text-[#1f2328]">
            <input
              type="checkbox"
              checked={includeInsights}
              onChange={(e) => setIncludeInsights(e.target.checked)}
              className="rounded border-border"
            />
            Include AI insights for this dataset
          </label>

          <div>
            <p className="text-xs font-medium text-muted mb-2">
              Include queries ({selectedIds.length} selected)
            </p>
            {isLoading ? (
              <div className="flex justify-center py-6"><Spinner /></div>
            ) : !successfulQueries.length ? (
              <p className="text-xs text-muted py-4 text-center">
                No successful queries yet for this dataset. You can still generate a
                report with AI insights only.
              </p>
            ) : (
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {successfulQueries.map((q) => (
                  <label
                    key={q.id}
                    className="flex items-start gap-2 text-sm p-2 rounded-lg hover:bg-surface cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(q.id)}
                      onChange={() => toggle(q.id)}
                      className="mt-0.5 rounded border-border shrink-0"
                    />
                    <span className="text-[#1f2328] break-words">{q.question}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 p-4 border-t border-border shrink-0">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            loading={creating}
            disabled={!canGenerate}
            onClick={handleGenerate}
          >
            Generate Report
          </Button>
        </div>
      </div>
    </div>
  )
}
