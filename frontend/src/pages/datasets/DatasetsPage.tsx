import { useState } from 'react'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Database, Search, Trash2, MessageSquare, BarChart2, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

import { datasetService } from '@/services/datasetService'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Spinner from '@/components/ui/Spinner'
import { formatBytes, formatNumber, timeAgo, statusVariant } from '@/utils/helpers'

export default function DatasetsPage() {
  const [search, setSearch] = useState('')
  const [page, setPage]     = useState(1)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['datasets', page, search],
    queryFn: () => datasetService.list({ page, limit: 10, search: search || undefined }),
  })

  const deleteMutation = useMutation({
    mutationFn: datasetService.delete,
    onSuccess: () => {
      toast.success('Dataset deleted.')
      qc.invalidateQueries({ queryKey: ['datasets'] })
    },
  })

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative w-full sm:w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search datasets…"
            className="w-full pl-8 pr-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
          />
        </div>
        <Link to="/datasets/upload" className="shrink-0">
          <Button size="sm" className="w-full sm:w-auto">
            <Plus size={14} />
            Upload Dataset
          </Button>
        </Link>
      </div>

      {/* Table */}
      <Card padding="sm">
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : data?.data.length === 0 ? (
          <div className="text-center py-12">
            <Database size={36} className="text-border mx-auto mb-3" />
            <p className="text-sm font-medium text-[#1f2328]">No datasets found</p>
            <p className="text-xs text-muted mt-1">Upload a CSV, Excel, or JSON file to get started.</p>
            <Link to="/datasets/upload" className="mt-4 inline-block">
              <Button size="sm"><Plus size={13} /> Upload Dataset</Button>
            </Link>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-160">
              <thead>
                <tr className="border-b border-border">
                  {['Name', 'Type', 'Rows', 'Size', 'Status', 'Created', ''].map((h) => (
                    <th key={h} className="text-left text-xs font-medium text-muted pb-3 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data?.data.map((ds) => (
                  <tr key={ds.id} className="hover:bg-surface transition-colors">
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <Database size={14} className="text-muted shrink-0" />
                        <Link to={`/datasets/${ds.id}`} className="font-medium text-[#1f2328] hover:text-accent transition-colors truncate max-w-[180px]">
                          {ds.name}
                        </Link>
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant="neutral">{ds.file_type.toUpperCase()}</Badge>
                    </td>
                    <td className="py-3 pr-4 text-muted">{ds.row_count ? formatNumber(ds.row_count) : '—'}</td>
                    <td className="py-3 pr-4 text-muted">{ds.file_size ? formatBytes(ds.file_size) : '—'}</td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-1.5">
                        {ds.status === 'processing' && <RefreshCw size={11} className="animate-spin text-yellow-500" />}
                        <Badge variant={statusVariant[ds.status]}>{ds.status}</Badge>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-muted whitespace-nowrap">{timeAgo(ds.created_at)}</td>
                    <td className="py-3">
                      <div className="flex items-center gap-1">
                        {ds.status === 'ready' && (
                          <Link to={`/query/${ds.id}`}>
                            <Button variant="ghost" size="icon" title="Query">
                              <MessageSquare size={14} />
                            </Button>
                          </Link>
                        )}
                        {ds.status === 'ready' && (
                          <Link to={`/insights/${ds.id}`}>
                            <Button variant="ghost" size="icon" title="Insights">
                              <BarChart2 size={14} />
                            </Button>
                          </Link>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Delete"
                          className="hover:text-red-500"
                          loading={deleteMutation.isPending}
                          onClick={() => {
                            if (confirm(`Delete "${ds.name}"?`)) deleteMutation.mutate(ds.id)
                          }}
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>

            {/* Pagination */}
            {data && data.pagination.total_pages > 1 && (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mt-4 pt-4 border-t border-border">
                <p className="text-xs text-muted">
                  {data.pagination.total} datasets total
                </p>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                    Previous
                  </Button>
                  <Button variant="secondary" size="sm" disabled={page === data.pagination.total_pages} onClick={() => setPage(p => p + 1)}>
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  )
}
