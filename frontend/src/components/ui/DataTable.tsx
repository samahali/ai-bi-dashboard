interface DataTableProps {
  columns: string[]
  rows: Record<string, unknown>[]
  /** Shown instead of the table when `rows` is empty. */
  emptyMessage?: string
}

/**
 * Generic read-only data table: header row from `columns`, cells rendered as
 * `String(val ?? '—')`. Used for the two genuinely-generic tables (query
 * results, dataset preview) — DatasetsPage's list table has custom
 * per-column rendering (badges, action buttons) and isn't a fit for this
 * shape without a messy render-prop API, so it stays hand-rolled.
 */
export default function DataTable({ columns, rows, emptyMessage = 'No results returned.' }: DataTableProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted py-4 text-center">{emptyMessage}</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => (
              <th key={col} className="text-left text-muted pb-2 pr-4 font-medium whitespace-nowrap">{col}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-surface">
              {columns.map((col) => (
                <td key={col} className="py-2 pr-4 text-[#1f2328] whitespace-nowrap">
                  {String(row[col] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
