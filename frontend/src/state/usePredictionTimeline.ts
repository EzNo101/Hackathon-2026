import { useEffect, useState } from 'react'
import { csvSource } from '../services/csvSource'
import type { EquilibriumSample, PhotoEntry, PhotoTruth } from '../types'

interface LoadedTimeline {
  discharge: number
  series: EquilibriumSample[]
  photos: PhotoEntry[]
}

/**
 * Časová řada výboje pro nahranou fotku, pokud je fotka v datasetu.
 * V prediction režimu tak lze zobrazit stejné grafy jako v datasetu.
 */
export function usePredictionTimeline(truth: PhotoTruth | null) {
  const [state, setState] = useState<LoadedTimeline | null>(null)

  useEffect(() => {
    if (truth === null) {
      setState(null)
      return
    }

    let active = true

    Promise.all([
      csvSource.getSeries(truth.discharge),
      csvSource.getPhotos(truth.discharge).catch(() => [] as PhotoEntry[]),
    ])
      .then(([series, photos]) => {
        if (active) {
          setState({ discharge: truth.discharge, series, photos })
        }
      })
      .catch(() => {
        if (active) {
          setState(null)
        }
      })

    return () => {
      active = false
    }
  }, [truth])

  if (truth === null || state === null || state.discharge !== truth.discharge) {
    return null
  }

  return { series: state.series, photos: state.photos }
}
