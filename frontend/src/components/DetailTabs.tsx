import { useEquilibrium, type DetailTab } from '../state/EquilibriumContext'
import { ALL_OUTPUT_COLS, MAIN_OUTPUT_COLS } from '../types'

interface DetailDefinition {
  id: DetailTab
  label: string
  count: number
}

// Počty bereme z seznamů sloupců, aby se UI nerozešlo s daty.
const details: DetailDefinition[] = [
  { id: 'overview', label: 'Přehled', count: MAIN_OUTPUT_COLS.length },
  { id: 'detail', label: 'Detail', count: ALL_OUTPUT_COLS.length },
]

/** Přepínač úrovně detailu – hlavní hodnoty vs. všech 31 výstupů. */
export function DetailTabs() {
  const { detailTab, setDetailTab } = useEquilibrium()

  return (
    <div className="segmented" role="tablist" aria-label="Úroveň detailu">
      {details.map((item) => {
        const isActive = detailTab === item.id

        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls="workspace-content"
            className={`segment${isActive ? ' is-active' : ''}`}
            onClick={() => setDetailTab(item.id)}
          >
            {item.label}
            <span className="segment-count">{item.count}</span>
          </button>
        )
      })}
    </div>
  )
}
