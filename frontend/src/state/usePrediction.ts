import { useCallback, useEffect, useRef, useState } from 'react'
import { csvSource } from '../services/csvSource'
import { predictImage } from '../services/predictionSource'
import type { PhotoTruth, PredictionResult } from '../types'

export type PredictionStatus = 'idle' | 'loading' | 'success' | 'error'

export interface PredictionState {
  status: PredictionStatus
  file: File | null
  previewUrl: string | null
  result: PredictionResult | null
  /** Skutečná hodnota, pokud je fotka v datasetu; jinak null. */
  truth: PhotoTruth | null
  error: string | null
}

const EMPTY: PredictionState = {
  status: 'idle',
  file: null,
  previewUrl: null,
  result: null,
  truth: null,
  error: null,
}

/**
 * Stav režimu Predikce: nahraná fotka, výsledek modelu a (pokud existuje)
 * skutečná hodnota z datasetu pro srovnání.
 *
 * Starší odpovědi se ignorují, takže rychlé opakované nahrání nepřepíše
 * novější výsledek. Náhled se uvolňuje při změně souboru i při odchodu.
 */
export function usePrediction() {
  const [state, setState] = useState<PredictionState>(EMPTY)
  const requestId = useRef(0)
  const previewRef = useRef<string | null>(null)

  const replacePreview = useCallback((file: File | null): string | null => {
    if (previewRef.current) {
      URL.revokeObjectURL(previewRef.current)
    }
    const next = file ? URL.createObjectURL(file) : null
    previewRef.current = next
    return next
  }, [])

  useEffect(
    () => () => {
      if (previewRef.current) {
        URL.revokeObjectURL(previewRef.current)
      }
    },
    [],
  )

  const submit = useCallback(
    (file: File) => {
      const id = ++requestId.current
      const previewUrl = replacePreview(file)

      setState({ ...EMPTY, status: 'loading', file, previewUrl })

      const truthPromise = csvSource
        .findPhotoTruth(file.name)
        .catch(() => null) // srovnání je volitelné, chyba ho nesmí shodit

      predictImage(file)
        .then(async (result) => {
          const truth = await truthPromise

          if (id === requestId.current) {
            setState({
              status: 'success',
              file,
              previewUrl,
              result,
              truth,
              error: null,
            })
          }
        })
        .catch((error: unknown) => {
          if (id === requestId.current) {
            setState({
              ...EMPTY,
              status: 'error',
              file,
              previewUrl,
              error: error instanceof Error ? error.message : 'Neznámá chyba.',
            })
          }
        })
    },
    [replacePreview],
  )

  const reset = useCallback(() => {
    requestId.current += 1
    replacePreview(null)
    setState(EMPTY)
  }, [replacePreview])

  return { state, submit, reset }
}
