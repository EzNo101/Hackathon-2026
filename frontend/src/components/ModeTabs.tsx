import { useEquilibrium, type AppMode } from '../state/EquilibriumContext'

interface ModeDefinition {
  id: AppMode
  label: string
  hint: string
}

const modes: ModeDefinition[] = [
  {
    id: 'dataset',
    label: 'Dataset',
    hint: 'výboj + čas',
  },
  {
    id: 'prediction',
    label: 'Predikce',
    hint: 'fotka → model',
  },
]

/** Přepínač hlavního režimu: ukázková data, nebo predikce z fotky. */
export function ModeTabs() {
  const { mode, setMode } = useEquilibrium()

  return (
    <div className="mode-tabs" role="tablist" aria-label="Režim aplikace">
      {modes.map((item) => {
        const isActive = mode === item.id

        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls="workspace-content"
            className={`mode-tab${isActive ? ' is-active' : ''}`}
            onClick={() => setMode(item.id)}
          >
            <span className="mode-label">{item.label}</span>
            <span className="mode-hint">{item.hint}</span>
          </button>
        )
      })}
    </div>
  )
}
