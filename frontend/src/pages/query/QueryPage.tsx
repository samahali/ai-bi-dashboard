import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { Send, ArrowLeft, BrainCircuit, Code2, Table2, BarChart2, Save } from 'lucide-react'
import toast from 'react-hot-toast'
import { datasetService } from '@/services/datasetService'
import { queryService } from '@/services/queryService'
import { visualizationService } from '@/services/visualizationService'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Spinner from '@/components/ui/Spinner'
import Button from '@/components/ui/Button'
import QueryChart from '@/components/charts/QueryChart'
import DataTable from '@/components/ui/DataTable'
import { cn, resolveChartType } from '@/utils/helpers'
import type { Query } from '@/types'

type ResultView = 'table' | 'chart' | 'sql'

export default function QueryPage() {
  const { datasetId } = useParams<{ datasetId: string }>()
  const qc = useQueryClient()
  const [question, setQuestion]       = useState('')
  const [isAsking, setIsAsking]       = useState(false)
  const [activeQuery, setActiveQuery] = useState<Query | null>(null)
  const [view, setView]               = useState<ResultView>('table')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { data: dataset } = useQuery({
    queryKey: ['dataset', Number(datasetId)],
    queryFn: () => datasetService.get(Number(datasetId)),
  })

  // Persisted query history — survives navigating away and back, unlike local state.
  const { data: history = [] } = useQuery({
    queryKey: ['queries', Number(datasetId)],
    queryFn: () => queryService.list({ dataset_id: Number(datasetId), limit: 20 }),
  })

  // Default to the most recent query once history loads, if nothing is active yet.
  useEffect(() => {
    if (!activeQuery && history.length > 0) {
      setActiveQuery(history[0])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [history])

  const askQuestion = async () => {
    if (!question.trim() || isAsking) return
    setIsAsking(true)
    try {
      const { id } = await queryService.create({
        dataset_id: Number(datasetId),
        question: question.trim(),
      })
      const result = await queryService.pollUntilDone(id)
      setActiveQuery(result)
      setView('table')
      setQuestion('')
      qc.invalidateQueries({ queryKey: ['queries', Number(datasetId)] })
    } catch {
      toast.error('Query failed. Please try again.')
    } finally {
      setIsAsking(false)
    }
  }

  const saveChartMutation = useMutation({
    mutationFn: visualizationService.create,
    onSuccess: () => toast.success('Chart saved.'),
    onError: () => toast.error('Failed to save chart.'),
  })

  const handleSaveChart = () => {
    if (!activeQuery?.results?.length) return
    const keys = Object.keys(activeQuery.results[0])
    const chartType = resolveChartType(activeQuery.results, activeQuery.visualization_suggestion)
    const xKey = keys[0]
    const numericKeys = keys.filter((k) => typeof activeQuery.results![0][k] === 'number')
    const yKey = chartType === 'scatter' ? numericKeys[1] : numericKeys[0]

    saveChartMutation.mutate({
      query_id: activeQuery.id,
      chart_type: chartType,
      title: activeQuery.question,
      x_axis: chartType === 'scatter' ? numericKeys[0] : xKey,
      y_axis: yKey,
    })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); askQuestion() }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to={`/datasets/${datasetId}`} className="inline-flex items-center gap-1 text-xs text-muted hover:text-accent">
          <ArrowLeft size={12} /> Back
        </Link>
        <h2 className="text-base font-semibold text-[#1f2328]">
          Query: <span className="text-accent">{dataset?.name}</span>
        </h2>
        <Badge variant="info">{dataset?.row_count?.toLocaleString()} rows</Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: input + results */}
        <div className="lg:col-span-2 space-y-4">
          {/* Question input */}
          <Card padding="sm">
            <div className="flex items-start gap-3">
              <BrainCircuit size={18} className="text-accent mt-2 shrink-0" />
              <textarea
                ref={textareaRef}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything about your data… e.g. 'What are the top 5 products by sales?'"
                rows={3}
                className="flex-1 resize-none text-sm outline-none placeholder:text-muted text-[#1f2328] bg-transparent"
              />
              <Button
                onClick={askQuestion}
                loading={isAsking}
                disabled={!question.trim()}
                size="icon"
                className="shrink-0 mt-1"
              >
                <Send size={15} />
              </Button>
            </div>
            <p className="text-xs text-muted mt-2 ml-9">Press Enter to send · Shift+Enter for new line</p>
          </Card>

          {/* Results */}
          {isAsking && (
            <Card>
              <div className="flex items-center gap-3 py-4">
                <Spinner size={18} />
                <p className="text-sm text-muted">AI is analyzing your question…</p>
              </div>
            </Card>
          )}

          {activeQuery && !isAsking && (
            <Card padding="sm">
              {/* View toggle */}
              <div className="flex items-center gap-1 mb-4 border-b border-border pb-3">
                {([['table', Table2, 'Table'], ['chart', BarChart2, 'Chart'], ['sql', Code2, 'SQL']] as const).map(
                  ([v, Icon, label]) => (
                    <button
                      key={v}
                      onClick={() => setView(v)}
                      className={cn(
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                        view === v ? 'bg-accent text-white' : 'text-muted hover:bg-surface'
                      )}
                    >
                      <Icon size={12} /> {label}
                    </button>
                  )
                )}
                <div className="ml-auto flex items-center gap-2">
                  <Badge variant={activeQuery.status === 'success' ? 'success' : 'error'}>
                    {activeQuery.status}
                  </Badge>
                  {activeQuery.execution_time_ms && (
                    <span className="text-xs text-muted">{activeQuery.execution_time_ms}ms</span>
                  )}
                </div>
              </div>

              {/* Table view */}
              {view === 'table' && activeQuery.results && (
                <div>
                  <DataTable
                    columns={activeQuery.results.length ? Object.keys(activeQuery.results[0]) : []}
                    rows={activeQuery.results}
                  />
                  <p className="text-xs text-muted mt-3">{activeQuery.row_count} rows returned</p>
                </div>
              )}

              {/* Chart view */}
              {view === 'chart' && activeQuery.results && (
                <div>
                  <QueryChart results={activeQuery.results} suggestion={activeQuery.visualization_suggestion} />
                  {activeQuery.results.length > 0 && (
                    <div className="flex justify-end mt-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        loading={saveChartMutation.isPending}
                        onClick={handleSaveChart}
                      >
                        <Save size={12} /> Save chart
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* SQL view */}
              {view === 'sql' && (
                <pre className="bg-surface rounded-lg p-4 text-xs font-mono text-[#1f2328] overflow-x-auto whitespace-pre-wrap">
                  {activeQuery.generated_sql ?? 'No SQL generated.'}
                </pre>
              )}

              {activeQuery.error_message && (
                <p className="mt-3 text-xs text-red-500">{activeQuery.error_message}</p>
              )}
            </Card>
          )}
        </div>

        {/* Right: query history */}
        <div>
          <Card padding="sm">
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">History</h3>
            {history.length === 0 ? (
              <p className="text-xs text-muted">Your queries will appear here.</p>
            ) : (
              <ul className="space-y-1">
                {history.map((q) => (
                  <li key={q.id}>
                    <button
                      onClick={() => { setActiveQuery(q); setView('table') }}
                      className={cn(
                        'w-full text-left px-2 py-2 rounded-lg text-xs transition-colors',
                        activeQuery?.id === q.id ? 'bg-accent/10 text-accent' : 'text-muted hover:bg-surface'
                      )}
                    >
                      <p className="truncate font-medium">{q.question}</p>
                      <p className="text-[10px] mt-0.5 opacity-70">{q.row_count} rows · {q.execution_time_ms}ms</p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
