import { useEffect, useMemo, useState } from 'react'
import { csvSource } from '../services/csvSource'
import { useEquilibrium } from '../state/EquilibriumContext'
import { findNearestIndex } from '../lib/timeseries'
import type { PhotoEntry, PlasmaMode } from '../types'

// Barvy režimů: L-mode (cyan), H-mode (zelená), ELM (červená). Stejné
// přiřazení použijí i budoucí grafy, aby se režimy nezaměnily.
const MODE_LABEL: Record<PlasmaMode, string> = {
  'L-mode': 'L-mode',
  'H-mode': 'H-mode',
  ELM: 'ELM',
}

const MODE_CLASS: Record<PlasmaMode, string> = {
  'L-mode': 'is-mode-l',
  'H-mode': 'is-mode-h',
  ELM: 'is-mode-elm',
}

interface LoadedPhotos {
  discharge: number
  photos: PhotoEntry[]
  error: string | null
}

/**
 * Fotka z kamery pro vybraný výboj: nejbližší snímek k času aktuálních dat.
 * Index se načte jednou pro výboj, obrázek se čte z `/photos/<filename>`.
 */
export function PhotoPanel() {
  const { selectedDischarge, selectedSample } = useEquilibrium()
  const [loaded, setLoaded] = useState<LoadedPhotos | null>(null)
  const [failedSrc, setFailedSrc] = useState<string | null>(null)

  useEffect(() => {
    if (selectedDischarge === null) {
      return
    }

    let active = true

    csvSource
      .getPhotos(selectedDischarge)
      .then((photos) => {
        if (active) {
          setLoaded({ discharge: selectedDischarge, photos, error: null })
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setLoaded({
            discharge: selectedDischarge,
            photos: [],
            error: error instanceof Error ? error.message : 'Neznámá chyba.',
          })
        }
      })

    return () => {
      active = false
    }
  }, [selectedDischarge])

  // Stav patří jen k výboji, pro který byl načten – jinak by se na chvíli
  // ukázala fotka z předchozího výboje.
  const current =
    loaded !== null && loaded.discharge === selectedDischarge ? loaded : null
  const isLoading = selectedDischarge !== null && current === null

  const photo = useMemo(() => {
    if (!current || current.photos.length === 0 || !selectedSample) {
      return null
    }

    return current.photos[findNearestIndex(current.photos, selectedSample.time)]
  }, [current, selectedSample])

  if (isLoading) {
    return (
      <section className="photo-panel" aria-label="Fotka z kamery">
        <span className="control-hint">Načítám seznam fotek…</span>
      </section>
    )
  }

  if (current?.error) {
    return (
      <section className="photo-panel" aria-label="Fotka z kamery">
        <span className="control-hint">Fotky nejsou k dispozici: {current.error}</span>
      </section>
    )
  }

  if (!photo || !selectedSample) {
    return (
      <section className="photo-panel" aria-label="Fotka z kamery">
        j   <span className="control-hint">Pro tento výboj nejsou k dispozici žádné fotky.</span>
      </section>
    )
  }

  const src = `${import.meta.env.BASE_URL}photos/${photo.filename}`
  const deltaMs = (photo.time - selectedSample.time) * 1000
  const imageFailed = failedSrc === src

  return (
    <section className="photo-panel" aria-label="Fotka z kamery">
      <div className="photo-frame">
        {imageFailed ? (
          <span className="control-hint">
            Obrázek se nenačetl. Fotky jsou dostupné jen ve vývojovém serveru.
          </span>
        ) : (
          <img
            key={src}
            src={src}
            alt={`Fotka ${photo.filename}`}
            onError={() => setFailedSrc(src)}
          />
        )}
      </div>

      <div className="photo-meta">
        <span className="control-label">Fotka z kamery</span>
        <span className="photo-filename">{photo.filename}</span>
        <span className={`mode-badge ${MODE_CLASS[photo.mode]}`}>
          {MODE_LABEL[photo.mode]}
        </span>
        <span className="control-hint">
          {`t fotky ${photo.time.toFixed(4)} s · t dat ${selectedSample.time.toFixed(4)} s · Δt ${deltaMs >= 0 ? '+' : ''}${deltaMs.toFixed(1)} ms`}
        </span>
      </div>
    </section>
  )
}
