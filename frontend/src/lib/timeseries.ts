import type { EquilibriumSample } from '../types'

export interface LimiterSpan {
  start: number
  end: number
}

/** Cokoli, co má čas – vzorek ze série i fotka. */
interface Timed {
  time: number
}

/** Ohraničí index do platného rozsahu řady; prázdná řada vrací 0. */
export function clampIndex(index: number, length: number): number {
  if (length <= 0) {
    return 0
  }

  return Math.min(Math.max(index, 0), length - 1)
}

/**
 * Index vzorku, jehož čas je nejblíže `time`.
 * Řady jsou seřazené podle času, ale funkce nespoléhá na lineární hledání
 * s předpokladem – prochází celou řadu a vybírá minimum.
 */
export function findNearestIndex(
  series: readonly Timed[],
  time: number,
): number {
  if (series.length === 0) {
    return 0
  }

  let bestIndex = 0
  let bestDistance = Math.abs(series[0].time - time)

  for (let index = 1; index < series.length; index += 1) {
    const distance = Math.abs(series[index].time - time)

    if (distance < bestDistance) {
      bestIndex = index
      bestDistance = distance
    }
  }

  return bestIndex
}

/** Souvislé úseky, ve kterých je plazma omezeno limiterem (`is_limited`). */
export function getLimiterSpans(
  series: readonly EquilibriumSample[],
): LimiterSpan[] {
  const spans: LimiterSpan[] = []
  let current: LimiterSpan | null = null

  for (const sample of series) {
    if (sample.is_limited) {
      if (current === null) {
        current = { start: sample.time, end: sample.time }
      } else {
        current.end = sample.time
      }
    } else if (current !== null) {
      spans.push(current)
      current = null
    }
  }

  if (current !== null) {
    spans.push(current)
  }

  return spans
}
