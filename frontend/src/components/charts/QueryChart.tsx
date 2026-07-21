import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, ScatterChart, Scatter,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'

const COLORS = ['#3b82d4', '#7c5cd8', '#16a34a', '#d97706', '#dc2626', '#0891b2']

interface Props {
  results: Record<string, unknown>[]
  /** Optional hint from the backend (bar|line|pie|scatter|table); only honored when the data shape supports it. */
  suggestion?: string | null
}

export default function QueryChart({ results, suggestion }: Props) {
  if (!results.length) return <p className="text-sm text-muted py-4 text-center">No data to chart.</p>

  const keys   = Object.keys(results[0])
  const xKey   = keys[0]
  const yKeys  = keys.slice(1).filter((k) => typeof results[0][k] === 'number')
  const numericKeys = keys.filter((k) => typeof results[0][k] === 'number')

  if (!yKeys.length) {
    return <p className="text-xs text-muted py-4 text-center">No numeric columns to plot.</p>
  }

  // Scatter needs two independent numeric columns to plot against each other.
  if (suggestion === 'scatter' && numericKeys.length >= 2) {
    const [xNum, yNum] = numericKeys
    return (
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xNum} name={xNum} type="number" tick={{ fontSize: 11 }} />
          <YAxis dataKey={yNum} name={yNum} type="number" tick={{ fontSize: 11 }} />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} />
          <Legend />
          <Scatter name={`${yNum} vs ${xNum}`} data={results} fill={COLORS[0]} />
        </ScatterChart>
      </ResponsiveContainer>
    )
  }

  // Heuristic: if x-axis looks like a date/time → line chart, else bar
  const isTimeSeries = /date|month|year|time|week|day/i.test(xKey)
  const isSinglePair = keys.length === 2 && yKeys.length === 1 && results.length <= 8

  if (isSinglePair) {
    return (
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie data={results} dataKey={yKeys[0]} nameKey={xKey} cx="50%" cy="50%" outerRadius={100} label>
            {results.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  if (isTimeSeries) {
    return (
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={results}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          {yKeys.map((k, i) => (
            <Line key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={results}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        {yKeys.map((k, i) => (
          <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[3, 3, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
