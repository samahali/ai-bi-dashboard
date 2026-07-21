import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Database, MessageSquare, FileText, TrendingUp, Upload, ArrowRight } from 'lucide-react'
import { datasetService } from '@/services/datasetService'
import { reportService } from '@/services/reportService'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Spinner from '@/components/ui/Spinner'
import { formatNumber, timeAgo } from '@/utils/helpers'

export default function DashboardPage() {
  const { data: datasets, isLoading: loadingDs } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => datasetService.list({ limit: 5 }),
  })
  const { data: reports } = useQuery({
    queryKey: ['reports'],
    queryFn: () => reportService.list(),
  })

  const stats = [
    {
      label: 'Datasets',
      value: datasets?.pagination.total ?? 0,
      icon: Database,
      to: '/datasets',
      color: 'text-accent',
      bg: 'bg-accent/10',
    },
    {
      label: 'Reports',
      value: reports?.length ?? 0,
      icon: FileText,
      to: '/reports',
      color: 'text-purple-600',
      bg: 'bg-purple-100',
    },
    {
      label: 'Total Rows Analyzed',
      value: formatNumber(datasets?.data.reduce((s, d) => s + (d.row_count ?? 0), 0) ?? 0),
      icon: TrendingUp,
      to: '/datasets',
      color: 'text-green-600',
      bg: 'bg-green-100',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {stats.map(({ label, value, icon: Icon, to, color, bg }) => (
          <Link key={label} to={to}>
            <Card className="hover:border-accent/40 transition-colors cursor-pointer">
              <div className="flex items-center gap-4">
                <div className={`p-2.5 rounded-lg ${bg}`}>
                  <Icon size={20} className={color} />
                </div>
                <div>
                  <p className="text-2xl font-semibold text-[#1f2328]">{value}</p>
                  <p className="text-xs text-muted mt-0.5">{label}</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick actions */}
      <Card>
        <h2 className="text-sm font-semibold text-[#1f2328] mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Link
            to="/datasets/upload"
            className="flex items-center gap-3 p-3 rounded-lg border border-border hover:border-accent/50 hover:bg-accent/5 transition-colors"
          >
            <Upload size={16} className="text-accent" />
            <span className="text-sm font-medium text-[#1f2328]">Upload Dataset</span>
            <ArrowRight size={14} className="text-muted ml-auto" />
          </Link>
          <Link
            to="/datasets"
            className="flex items-center gap-3 p-3 rounded-lg border border-border hover:border-accent/50 hover:bg-accent/5 transition-colors"
          >
            <MessageSquare size={16} className="text-accent" />
            <span className="text-sm font-medium text-[#1f2328]">Query Data</span>
            <ArrowRight size={14} className="text-muted ml-auto" />
          </Link>
          <Link
            to="/reports"
            className="flex items-center gap-3 p-3 rounded-lg border border-border hover:border-accent/50 hover:bg-accent/5 transition-colors"
          >
            <FileText size={16} className="text-accent" />
            <span className="text-sm font-medium text-[#1f2328]">Generate Report</span>
            <ArrowRight size={14} className="text-muted ml-auto" />
          </Link>
        </div>
      </Card>

      {/* Recent datasets */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-[#1f2328]">Recent Datasets</h2>
          <Link to="/datasets" className="text-xs text-accent hover:underline flex items-center gap-1">
            View all <ArrowRight size={11} />
          </Link>
        </div>

        {loadingDs ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : datasets?.data.length === 0 ? (
          <div className="text-center py-8">
            <Database size={32} className="text-border mx-auto mb-2" />
            <p className="text-sm text-muted">No datasets yet.</p>
            <Link to="/datasets/upload" className="text-xs text-accent hover:underline mt-1 block">
              Upload your first dataset →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {datasets?.data.map((ds) => (
              <div key={ds.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3 min-w-0">
                  <Database size={15} className="text-muted shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[#1f2328] truncate">{ds.name}</p>
                    <p className="text-xs text-muted">
                      {ds.row_count ? formatNumber(ds.row_count) + ' rows' : '—'} · {timeAgo(ds.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4 shrink-0">
                  <Badge variant={ds.status === 'ready' ? 'success' : ds.status === 'error' ? 'error' : 'warning'}>
                    {ds.status}
                  </Badge>
                  {ds.status === 'ready' && (
                    <Link to={`/query/${ds.id}`} className="text-xs text-accent hover:underline">
                      Query →
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
