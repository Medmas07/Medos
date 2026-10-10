import type { ReactNode } from 'react'
import { cx } from '../cx'
import { EmptyState } from './States'

export interface TableColumn<Row> {
  key: string
  header: ReactNode
  render: (row: Row) => ReactNode
  align?: 'left' | 'right'
  /** Marks this column's cell as the row header for assistive technology. */
  rowHeader?: boolean
}

export interface TableProps<Row> {
  /** Describes the table for assistive technology. */
  caption: string
  /** Shows the caption visually; it is screen-reader-only by default. */
  showCaption?: boolean
  columns: readonly TableColumn<Row>[]
  rows: readonly Row[]
  getRowKey: (row: Row) => string
  /** Shown in place of rows when `rows` is empty. */
  empty?: ReactNode
  className?: string
}

/**
 * Data table with an explicit empty state. For loading and error states,
 * render `LoadingState` or `ErrorState` in its place.
 */
export function Table<Row>({
  caption,
  showCaption = false,
  columns,
  rows,
  getRowKey,
  empty,
  className,
}: TableProps<Row>) {
  return (
    <div className={cx('overflow-x-auto', className)}>
      <table className="w-full border-collapse text-left text-sm [&_tbody_tr:last-child>*]:border-b-0">
        <caption
          className={
            showCaption ? 'px-4 py-2 text-left text-xs font-medium text-ink-muted' : 'sr-only'
          }
        >
          {caption}
        </caption>
        <thead className="bg-surface-muted">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={cx(
                  'border-b border-line px-4 py-2.5 text-[11px] font-semibold tracking-[0.08em] whitespace-nowrap text-ink-muted uppercase',
                  column.align === 'right' && 'text-right',
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>{empty ?? <EmptyState title="No records" />}</td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={getRowKey(row)} className="transition-colors duration-150 hover:bg-brand-50/70">
                {columns.map((column) => {
                  const Cell = column.rowHeader ? 'th' : 'td'
                  return (
                    <Cell
                      key={column.key}
                      scope={column.rowHeader ? 'row' : undefined}
                      className={cx(
                        'border-b border-line px-4 py-3 align-middle text-ink-soft',
                        column.rowHeader && 'font-medium text-ink',
                        column.align === 'right' && 'tabular text-right',
                      )}
                    >
                      {column.render(row)}
                    </Cell>
                  )
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
