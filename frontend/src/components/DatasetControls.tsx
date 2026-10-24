import { useEquilibrium } from '../state/EquilibriumContext'

/**
 * Výběr výboje z datasetu.
 *
 * Posuvník času, krok ◀ ▶ a přehrávání jsou dočasně schované (viz komentář
 * níže). Změna výboje volá `selectDischarge`, který resetuje čas.
 */
export function DatasetControls() {
  const { discharges, selectedDischarge, selectDischarge } = useEquilibrium()

  const selectedMeta = discharges.find((item) => item.id === selectedDischarge)

  return (
    <div className="dataset-controls">
      <div className="control-group control-discharge">
        <label className="control-label" htmlFor="discharge-select">
          Výboj
        </label>
        <select
          id="discharge-select"
          className="control-select"
          value={selectedDischarge ?? ''}
          onChange={(event) => selectDischarge(Number(event.target.value))}
          disabled={discharges.length === 0}
        >
          {discharges.map((item) => (
            <option key={item.id} value={item.id}>
              {`Výboj ${item.id} · ${item.rowCount} vzorků`}
            </option>
          ))}
        </select>
        {selectedMeta ? (
          <span className="control-hint">
            {`t ${selectedMeta.timeStart.toFixed(3)} – ${selectedMeta.timeEnd.toFixed(3)} s · limiter ${selectedMeta.limiterRowCount} z ${selectedMeta.rowCount}`}
          </span>
        ) : null}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// SCHOVÁNO: posuvník času, ◀ ▶, přehrávání a rychlost 1×/2×/5×.
// Zapnutí: vrátit importy (useEffect, useRef, useState, clampIndex,
// findNearestIndex), stavy `playing`/`speed`, effect s setInterval,
// goToIndex/togglePlay a blok níže do returnu nad výběr výboje.
//
// const PLAY_INTERVAL_MS = 100
// const SPEEDS = [1, 2, 5] as const
// type Speed = (typeof SPEEDS)[number]
//
// const [playing, setPlaying] = useState(false)
// const [speed, setSpeed] = useState<Speed>(1)
// const hasSeries = series.length > 0
// const lastIndex = Math.max(series.length - 1, 0)
// const index = hasSeries ? findNearestIndex(series, selectedTime) : 0
// const atEnd = hasSeries && index >= lastIndex
//
// const latest = useRef({ series, index, setSelectedTime })
// useEffect(() => {
//   latest.current = { series, index, setSelectedTime }
// })
//
// useEffect(() => {
//   if (!playing) return
//   const timer = window.setInterval(() => {
//     const current = latest.current
//     if (current.series.length === 0) {
//       setPlaying(false)
//       return
//     }
//     const last = current.series.length - 1
//     const next = clampIndex(current.index + speed, current.series.length)
//     current.setSelectedTime(current.series[next].time)
//     if (next >= last) setPlaying(false)
//   }, PLAY_INTERVAL_MS)
//   return () => window.clearInterval(timer)
// }, [playing, speed])
//
// function goToIndex(nextIndex: number) {
//   if (!hasSeries) return
//   setSelectedTime(series[clampIndex(nextIndex, series.length)].time)
// }
//
// function togglePlay() {
//   if (!hasSeries) return
//   if (!playing && atEnd) goToIndex(0)
//   setPlaying((value) => !value)
// }
//
// JSX:
// <div className="control-group control-time">
//   <div className="control-time-head">
//     <span className="control-label">Čas</span>
//     <span className="control-time-value">
//       {hasSeries ? `${series[index].time.toFixed(3)} s` : '—'}
//     </span>
//   </div>
//   <input type="range" className="control-range" aria-label="Čas výboje"
//     min={0} max={lastIndex} step={1} value={index} disabled={!hasSeries}
//     onChange={(event) => goToIndex(Number(event.target.value))} />
//   <div className="control-buttons">
//     <button type="button" className="control-button" aria-label="Předchozí vzorek"
//       onClick={() => goToIndex(index - 1)} disabled={!hasSeries || index <= 0}>◀</button>
//     <button type="button" className="control-button control-play" onClick={togglePlay}
//       disabled={!hasSeries} aria-pressed={playing}>{playing ? 'Pauza' : 'Přehrát'}</button>
//     <button type="button" className="control-button" aria-label="Další vzorek"
//       onClick={() => goToIndex(index + 1)} disabled={!hasSeries || atEnd}>▶</button>
//     <div className="segmented control-speed" role="group" aria-label="Rychlost přehrávání">
//       {SPEEDS.map((value) => (
//         <button key={value} type="button"
//           className={`segment${speed === value ? ' is-active' : ''}`}
//           aria-pressed={speed === value} onClick={() => setSpeed(value)}>
//           {`${value}×`}
//         </button>
//       ))}
//     </div>
//   </div>
// </div>
// ---------------------------------------------------------------------------
