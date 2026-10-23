import type { ReactNode } from 'react'
import { formatNumber } from '../lib/format'

export interface ValueRow {
  label: string
  value: ReactNode
  unit: string
  isMissing?: boolean
  title?: string
}

export interface ValueGroup {
  title: string
  rows: ValueRow[]
}

/**
 * Řádek s číselnou hodnotou. `null` se zobrazí jako „—“ a v tooltipu
 * se vysvětlí, proč hodnota v dané konfiguraci chybí.
 */
export function numericValueRow(
  label: string,
  value: number | null,
  unit: string,
  format: (input: number | null) => string = (input) => formatNumber(input, 3),
  missingNote?: string,
): ValueRow {
  const isMissing = value === null

  return {
    label,
    value: format(value),
    unit,
    isMissing,
    title: isMissing ? missingNote : undefined,
  }
}

interface ValuesTableProps {
  title: string
  meta: string
  groups: ValueGroup[]
  caption?: string
}

/**
 * Obecná tabulka hodnot. Stejnou komponentu použijeme v Přehledu (17 hodnot)
 * i v Detailu (31 hodnot), jen jí předáme jiné skupiny řádků.
 */
export function ValuesTable({
  title,
  meta,
  groups,
  caption,
}: ValuesTableProps) {
  return (
    <section className="values-panel" aria-labelledby="values-table-title">
      <div className="values-panel-head">
        <h3 id="values-table-title" className="values-title">
          {title}
        </h3>
        <span className="values-meta">{meta}</span>
      </div>

      <div className="table-scroll">
        <table className="values-table" aria-label={title}>
          <thead>
            <tr>
              <th scope="col">Parametr</th>
              <th scope="col">Hodnota</th>
              <th scope="col">Jednotka</th>
            </tr>
          </thead>

          {groups.map((group) => (
            <tbody key={group.title}>
              <tr className="values-group">
                <th scope="colgroup" colSpan={3}>
                  {group.title}
                </th>
              </tr>
              {group.rows.map((row) => (
                <tr key={row.label}>
                  <th scope="row" className="values-param">
                    {row.label}
                  </th>
                  <td
                    className={row.isMissing ? 'is-missing' : undefined}
                    title={row.title}
                  >
                    {row.value}
                  </td>
                  <td className="values-unit">{row.unit}</td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>

      {caption ? <p className="values-caption">{caption}</p> : null}
    </section>
  )
}
