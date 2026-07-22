import { useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

interface DataTableProps {
  columns: string[]
  rows: Record<string, unknown>[]
  /** Shown instead of the table when `rows` is empty. */
  emptyMessage?: string
}

const ROW_HEIGHT = 33
const MAX_VIEWPORT_HEIGHT = 480

/**
 * Generic read-only data table: header row from `columns`, cells rendered as
 * `String(val ?? '—')`. Used for the two genuinely-generic tables (query
 * results, dataset preview) — DatasetsPage's list table has custom
 * per-column rendering (badges, action buttons) and isn't a fit for this
 * shape without a messy render-prop API, so it stays hand-rolled.
 *
 * Rows are virtualized (only rows in/near the visible viewport are mounted)
 * so large result sets (hundreds of rows) don't degrade rendering — the DOM
 * node count stays roughly constant regardless of row count. Real `<table>`
 * layout can't host absolutely-positioned virtual rows, so the grid is built
 * with CSS grid instead (one grid template shared by header and body keeps
 * columns aligned across both).
 */
export default function DataTable({ columns, rows, emptyMessage = 'No results returned.' }: DataTableProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  })

  if (rows.length === 0) {
    return <p className="text-sm text-muted py-4 text-center">{emptyMessage}</p>
  }

  const gridTemplateColumns = `repeat(${columns.length}, minmax(120px, 1fr))`
  const viewportHeight = Math.min(rows.length * ROW_HEIGHT, MAX_VIEWPORT_HEIGHT)

  return (
    <div ref={scrollRef} className="overflow-auto text-xs" style={{ height: viewportHeight }}>
      <div
        className="grid sticky top-0 bg-white z-10 border-b border-border"
        style={{ gridTemplateColumns }}
      >
        {columns.map((col) => (
          <div key={col} className="text-left text-muted pb-2 pr-4 font-medium whitespace-nowrap truncate">
            {col}
          </div>
        ))}
      </div>
      <div style={{ position: 'relative', height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const row = rows[virtualRow.index]
          return (
            <div
              key={virtualRow.key}
              className="grid divide-x divide-border hover:bg-surface border-b border-border"
              style={{
                gridTemplateColumns,
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: virtualRow.size,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              {columns.map((col) => (
                <div key={col} className="py-2 pr-4 text-[#1f2328] whitespace-nowrap truncate">
                  {String(row[col] ?? '—')}
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
