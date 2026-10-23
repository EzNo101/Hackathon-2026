import { OUTPUT_INFO } from '../lib/dictionary'
import {
  MAIN_OUTPUT_COLS,
  SUPPLEMENTARY_OUTPUT_COLS,
  type EquilibriumOutputs,
  type OutputKey,
  type PhotoTruth,
} from '../types'

interface ComparisonTableProps {
  prediction: EquilibriumOutputs
  truth: PhotoTruth | null
}

type Cell = { text: string; missing?: boolean }

function formatValue(key: OutputKey, value: boolean | number | null): Cell {
  if (key === 'is_limited') {
    return { text: value ? 'limiter' : 'divertor' }
  }
  if (value === null || typeof value !== 'number') {
    return { text: '—', missing: true }
  }

  const info = OUTPUT_INFO[key]
  const scaled = value * (info.scale ?? 1)
  return { text: scaled.toFixed(info.scale ? 1 : 3) }
}

function compare(
  key: OutputKey,
  predicted: boolean | number | null,
  actual: boolean | number | null,
): Cell {
  if (key === 'is_limited') {
    return predicted === actual
      ? { text: 'shoda' }
      : { text: 'neshoda', missing: true }
  }

  if (typeof predicted !== 'number' || typeof actual !== 'number') {
    // Obě hodnoty `null` = parametr v této konfiguraci neexistuje.
    return predicted === actual
      ? { text: '—', missing: true }
      : { text: 'neshoda', missing: true }
  }

  const info = OUTPUT_INFO[key]
  const error = Math.abs(predicted - actual) * (info.scale ?? 1)
  return { text: error.toFixed(info.scale ? 1 : 4) }
}

/**
 * Srovnání predikce modelu se skutečnou hodnotou z datasetu.
 * Chyba je absolutní, ve stejných jednotkách jako zobrazené hodnoty.
 */
export function ComparisonTable({ prediction, truth }: ComparisonTableProps) {
  if (truth === null) {
    return (
      <section className="values-panel comparison-panel" aria-label="Srovnání se skutečností">
        <div className="values-panel-head">
          <h3 className="values-title">Srovnání se skutečností</h3>
          <span className="values-meta">nedostupné</span>
        </div>
        <p className="values-caption">
          Tato fotka není v datasetu, proto nejsou k dispozici skutečné hodnoty.
          Zobrazena je jen predikce modelu.
        </p>
      </section>
    )
  }

  const truthValues = truth.sample
  const groups = [
    { title: 'Hlavní parametry', keys: MAIN_OUTPUT_COLS },
    { title: 'Doplňkové parametry', keys: SUPPLEMENTARY_OUTPUT_COLS },
  ]

  const configurationMatch = prediction.is_limited === truthValues.is_limited

  return (
    <section className="values-panel comparison-panel" aria-labelledby="comparison-title">
      <div className="values-panel-head">
        <h3 id="comparison-title" className="values-title">
          Srovnání se skutečností
        </h3>
        <span className="values-meta">
          {`výboj ${truth.discharge} · t = ${truth.time.toFixed(4)} s · ${truth.mode}`}
        </span>
      </div>

      <div className="table-scroll">
        <table className="values-table comparison-table" aria-label="Predikce a skutečnost">
          <thead>
            <tr>
              <th scope="col">Parametr</th>
              <th scope="col">Predikce</th>
              <th scope="col">Skutečnost</th>
              <th scope="col">Chyba</th>
            </tr>
          </thead>

          {groups.map((group) => (
            <tbody key={group.title}>
              <tr className="values-group">
                <th scope="colgroup" colSpan={4}>
                  {group.title}
                </th>
              </tr>
              {group.keys.map((key) => {
                const predicted = formatValue(key, prediction[key])
                const actual = formatValue(key, truthValues[key])
                const error = compare(key, prediction[key], truthValues[key])
                const info = OUTPUT_INFO[key]

                return (
                  <tr key={key}>
                    <th scope="row" className="values-param">
                      {info.label}
                      <span className="values-unit"> {info.unit}</span>
                    </th>
                    <td className={predicted.missing ? 'is-missing' : undefined}>
                      {predicted.text}
                    </td>
                    <td className={actual.missing ? 'is-missing' : undefined}>
                      {actual.text}
                    </td>
                    <td className={error.missing ? 'is-missing' : undefined}>
                      {error.text}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          ))}
        </table>
      </div>

      <p className="values-caption">
        {configurationMatch
          ? 'Konfigurace (limiter / divertor) se shoduje.'
          : 'Konfigurace (limiter / divertor) se neshoduje.'}{' '}
        Chyba je absolutní rozdíl. Skutečnost je nejbližší vzorek datasetu
        k času fotky. „—“ znamená, že hodnota v dané konfiguraci neexistuje.
      </p>
    </section>
  )
}
