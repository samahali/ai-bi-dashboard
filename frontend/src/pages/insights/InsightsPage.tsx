import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Lightbulb, X, AlertTriangle, TrendingUp, AlertCircle } from 'lucide-react'

import { insightService } from '@/services/insightService'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import { timeAgo } from '@/utils/helpers'
import type { InsightSeverity } from '@/types'

const severityVariant: Record<InsightSeverity, 'success' | 'warning' | 'error' | 'purple'> = {
  low: 'success', medium: 'warning', high: 'error', critical: 'purple',
}

const typeIcon = { anomaly: AlertTriangle, trend: TrendingUp, outlier: AlertCircle, correlation: Lightbulb }

export default function InsightsPage() {
  const { datasetId } = useParams<{ datasetId: string }>()
  const qc = useQueryClient()

  const { data: insights, isLoading } = useQuery({
    queryKey: ['insights', datasetId],
    queryFn: () => insightService.list(Number(datasetId)),
  })

  const dismiss = useMutation({
    mutationFn: insightService.dismiss,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['insights', datasetId] }),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to={`/datasets/${datasetId}`} className="inline-flex items-center gap-1 text-xs text-muted hover:text-accent">
          <ArrowLeft size={12} /> Back
        </Link>
        <h2 className="text-base font-semibold text-[#1f2328]">AI Insights</h2>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size={28} /></div>
      ) : !insights?.length ? (
        <Card>
          <div className="text-center py-10">
            <Lightbulb size={36} className="text-border mx-auto mb-3" />
            <p className="text-sm font-medium text-[#1f2328]">No insights yet</p>
            <p className="text-xs text-muted mt-1">No anomalies, trends, or data quality issues were detected in this dataset.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {insights.map((insight) => {
            const Icon = typeIcon[insight.insight_type as keyof typeof typeIcon] ?? Lightbulb
            return (
              <Card key={insight.id} padding="sm">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-surface rounded-lg shrink-0">
                    <Icon size={16} className="text-muted" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-[#1f2328]">{insight.title}</p>
                      <Badge variant={severityVariant[insight.severity]}>{insight.severity}</Badge>
                      <Badge variant="neutral">{insight.insight_type}</Badge>
                    </div>
                    <p className="text-xs text-muted mt-1">{insight.description}</p>
                    {insight.affected_columns?.length ? (
                      <p className="text-xs text-muted mt-1">
                        Columns: <span className="font-medium">{insight.affected_columns.join(', ')}</span>
                      </p>
                    ) : null}
                    <p className="text-[10px] text-muted mt-2">{timeAgo(insight.created_at)}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="shrink-0 text-muted hover:text-red-500"
                    loading={dismiss.isPending}
                    onClick={() => dismiss.mutate(insight.id)}
                    title="Dismiss"
                  >
                    <X size={14} />
                  </Button>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
