import type { ReactNode } from 'react'
import { ComparisonTable } from './components/ComparisonTable'
import { DatasetControls } from './components/DatasetControls'
import { DetailPanel } from './components/DetailPanel'
import { DetailTabs } from './components/DetailTabs'
import { ModeTabs } from './components/ModeTabs'
import { OverviewPanel } from './components/OverviewPanel'
import { PhotoPanel } from './components/PhotoPanel'
import { UploadPanel } from './components/UploadPanel'
import { useEquilibrium } from './state/EquilibriumContext'
import { usePhotoIndex } from './state/usePhotoIndex'
import { usePrediction } from './state/usePrediction'

function App() {
  const {
    mode,
    detailTab,
    manifest,
    discharges,
    selectedDischarge,
    selectedSample,
    series,
    setSelectedTime,
    wall,
    isLoading,
    error,
  } = useEquilibrium()
  const photos = usePhotoIndex(selectedDischarge)
  const prediction = usePrediction()

  const isPrediction = mode === 'prediction'
  const predictionResult = prediction.state.result
  const selectedMeta = discharges.find(
    (item) => item.id === selectedDischarge,
  )
  const configuration = selectedSample
    ? selectedSample.is_limited
      ? 'Limiter'
      : 'Divertor'
    : '—'

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <span className="brand-mark-core" />
          </div>
          <div>
            <p className="eyebrow">COMPASS · tokamak</p>
            <h1>Equilibrium dashboard</h1>
          </div>
        </div>

        <ModeTabs />

        <div className="header-status" role="status">
          <span className="status-dot" aria-hidden="true" />
          <span>Fáze 7 / 8</span>
        </div>
      </header>

      <main className="app-main">
        <section className="workspace-panel" aria-labelledby="workspace-title">
          <div className="panel-head">
            <div className="panel-heading">
              <p className="eyebrow">
                {isPrediction ? 'Model · jeden snímek' : 'Dataset · CSV'}
              </p>
              <h2 id="workspace-title">
                {isPrediction
                  ? 'Predikce z fotky plazmatu'
                  : selectedDischarge !== null
                    ? `Výboj ${selectedDischarge}`
                    : 'Načítání datasetu'}
              </h2>
              <p className="panel-description">
                {isPrediction
                  ? 'Nahraj fotku z kamery. Backend vrátí 31 parametrů tvaru plazmatu a jsou zobrazeny stejně jako v datasetu. Je-li fotka v datasetu, zobrazí se i skutečné hodnoty pro srovnání.'
                  : 'Procházení naměřených dat: časový průběh výboje a parametry tvaru plazmatu pro zvolený okamžik.'}
              </p>
            </div>

            <div className="panel-actions">
              <DetailTabs />
            </div>
          </div>

          {/* Rychlý přehled stavu. */}
          <div className="context-bar">
            {isPrediction ? (
              <>
                <Metric
                  label="Soubor"
                  value={prediction.state.file?.name ?? '—'}
                  mono
                />
                <Metric
                  label="Výstup"
                  value={predictionResult ? '31 hodnot' : '—'}
                  mono
                />
                <Metric
                  label="P(limiter)"
                  value={
                    predictionResult
                      ? `${(predictionResult.probabilityLimited * 100).toFixed(1)} %`
                      : '—'
                  }
                  mono
                />
                <Metric
                  label="Latence"
                  value={
                    predictionResult
                      ? `${predictionResult.latencyMs.toFixed(1)} ms`
                      : '—'
                  }
                  mono
                />
                <Metric
                  label="Konfigurace"
                  value={
                    predictionResult ? (
                      <span
                        className={`config-badge${
                          predictionResult.values.is_limited
                            ? ' is-limiter'
                            : ' is-divertor'
                        }`}
                      >
                        {predictionResult.values.is_limited ? 'Limiter' : 'Divertor'}
                      </span>
                    ) : (
                      '—'
                    )
                  }
                />
              </>
            ) : (
              <>
                <Metric label="Dataset" value={manifest?.source ?? '—'} />
                <Metric label="Výboje" value={discharges.length || '—'} mono />
                <Metric
                  label="Řádky"
                  value={
                    manifest ? manifest.rowCount.toLocaleString('cs-CZ') : '—'
                  }
                  mono
                />
                <Metric
                  label="Vybraný čas"
                  value={
                    selectedSample
                      ? selectedSample.time.toFixed(3)
                      : selectedMeta
                        ? selectedMeta.timeStart.toFixed(3)
                        : '—'
                  }
                  mono
                />
                <Metric
                  label="Konfigurace"
                  value={
                    <span
                      className={`config-badge${
                        selectedSample
                          ? selectedSample.is_limited
                            ? ' is-limiter'
                            : ' is-divertor'
                          : ''
                      }`}
                    >
                      {configuration}
                    </span>
                  }
                />
              </>
            )}
          </div>

          {isPrediction ? (
            <UploadPanel
              state={prediction.state}
              onFile={prediction.submit}
              onReset={prediction.reset}
            />
          ) : (
            <>
              <DatasetControls />
              <PhotoPanel />
            </>
          )}

          <div
            id="workspace-content"
            className="workspace-content"
            role="tabpanel"
            aria-live="polite"
          >
            {isPrediction ? (
              predictionResult ? (
                <>
                  {detailTab === 'overview' ? (
                    <OverviewPanel
                      sample={predictionResult.values}
                      wall={wall}
                      showTimeline={false}
                    />
                  ) : (
                    <DetailPanel sample={predictionResult.values} wall={wall} />
                  )}
                  <ComparisonTable
                    prediction={predictionResult.values}
                    truth={prediction.state.truth}
                  />
                </>
              ) : (
                <PredictionIntro
                  status={prediction.state.status}
                  hasError={prediction.state.status === 'error'}
                />
              )
            ) : error ? (
              <ErrorState message={error} />
            ) : isLoading ? (
              <LoadingState />
            ) : selectedSample === null ? (
              <EmptyState />
            ) : detailTab === 'overview' ? (
              <OverviewPanel sample={selectedSample} wall={wall} />
            ) : (
              <DetailPanel
                sample={selectedSample}
                wall={wall}
                timeline={{
                  series,
                  photos,
                  cursorTime: selectedSample.time,
                  onSelectTime: setSelectedTime,
                }}
              />
            )}
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <span>COMPASS · Ústav fyziky plazmatu AV ČR</span>
        <span>
          {isPrediction
            ? 'Režim Predikce · backend FastAPI'
            : 'Režim Dataset · dočasný zdroj CSV'}
        </span>
      </footer>
    </div>
  )
}

interface MetricProps {
  label: string
  value: ReactNode
  mono?: boolean
}

function Metric({ label, value, mono = false }: MetricProps) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className={`metric-value${mono ? ' is-mono' : ''}`}>{value}</span>
    </div>
  )
}

function PredictionIntro({
  status,
  hasError,
}: {
  status: string
  hasError: boolean
}) {
  if (status === 'loading') {
    return (
      <div className="state-box" role="status">
        <span className="spinner" aria-hidden="true" />
        <div>
          <h3>Počítám predikci</h3>
          <p>Fotka je odeslána na backend, výsledek se zobrazí za chvíli.</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`state-box${hasError ? ' state-box-error' : ''}`} role="status">
      <div>
        <h3>{hasError ? 'Zkus jinou fotku' : 'Nahraj fotku'}</h3>
        <p>
          {hasError
            ? 'Predikce neproběhla. Chybu najdeš výše, po opravě můžeš fotku nahrát znovu.'
            : 'Po nahrání se zobrazí 31 parametrů tvaru plazmatu, přehled, detail a srovnání, pokud je fotka v datasetu.'}
        </p>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="state-box" role="status">
      <span className="spinner" aria-hidden="true" />
      <div>
        <h3>Načítám data</h3>
        <p>Manifest a časová řada se načítají postupně po výbojích.</p>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="state-box" role="status">
      <div>
        <h3>Žádná data</h3>
        <p>Pro vybraný výboj nejsou v datasetu žádné časové vzorky.</p>
      </div>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="state-box state-box-error" role="alert">
      <div>
        <h3>Data se nepodařilo načíst</h3>
        <p>{message}</p>
        <code className="state-code">npm run prepare-data</code>
      </div>
    </div>
  )
}

export default App
