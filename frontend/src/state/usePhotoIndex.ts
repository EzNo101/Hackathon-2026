import { useEffect, useState } from 'react'
import { csvSource } from '../services/csvSource'
import type { PhotoEntry } from '../types'

interface PhotoIndexState {
  discharge: number
  photos: PhotoEntry[]
}

/**
 * Index fotek vybraného výboje.
 * Vrací `null`, dokud se index nenačte (nebo když není vybraný výboj).
 * Výboj bez fotek i chyba načtení vrací prázdné pole.
 */
export function usePhotoIndex(discharge: number | null): PhotoEntry[] | null {
  const [state, setState] = useState<PhotoIndexState | null>(null)

  useEffect(() => {
    if (discharge === null) {
      return
    }

    let active = true

    csvSource
      .getPhotos(discharge)
      .then((photos) => {
        if (active) {
          setState({ discharge, photos })
        }
      })
      .catch(() => {
        if (active) {
          setState({ discharge, photos: [] })
        }
      })

    return () => {
      active = false
    }
  }, [discharge])

  // Index platí jen pro výboj, pro který byl načten.
  if (discharge === null || state === null || state.discharge !== discharge) {
    return null
  }

  return state.photos
}
