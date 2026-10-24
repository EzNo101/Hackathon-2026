import { ALL_OUTPUT_COLS, type EquilibriumOutputs, type PredictionResult } from '../types'

/** Odpověď backendu neodpovídá kontraktu – data se do UI nedostanou. */
export class PredictionFormatError extends Error {
  constructor(problems: string[]) {
    super(
      `Odpověď modelu má neplatný tvar: ${problems.slice(0, 4).join('; ')}` +
        (problems.length > 4 ? ` (a dalších ${problems.length - 4})` : ''),
    )
    this.name = 'PredictionFormatError'
  }
}

type Json = Record<string, unknown>

function isObject(value: unknown): value is Json {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

/**
 * Ověří odpověď `POST /predict` a převede ji na `PredictionResult`.
 *
 * Kontroluje přesně 31 klíčů ze `columns.json`, typy (čísla nebo `null`,
 * `is_limited` boolean), konečnost čísel a shodu `is_limited` s blokem `regime`.
 * Nic z nevalidní odpovědi se nepředává dál.
 */
export function parsePredictionResponse(raw: unknown): PredictionResult {
  if (!isObject(raw)) {
    throw new PredictionFormatError(['odpověď není JSON objekt'])
  }

  const problems: string[] = []
  const values = raw.values

  if (!isObject(values)) {
    throw new PredictionFormatError(['chybí objekt "values" se 31 výstupy'])
  }

  const expected = new Set<string>(ALL_OUTPUT_COLS)
  const received = Object.keys(values)

  for (const key of ALL_OUTPUT_COLS) {
    if (!(key in values)) {
      problems.push(`chybí klíč "${key}"`)
    }
  }
  for (const key of received) {
    if (!expected.has(key)) {
      problems.push(`neznámý klíč "${key}"`)
    }
  }

  for (const key of ALL_OUTPUT_COLS) {
    if (!(key in values)) {
      continue
    }

    const value = values[key]

    if (key === 'is_limited') {
      if (typeof value !== 'boolean') {
        problems.push('"is_limited" musí být boolean')
      }
    } else if (value !== null && !isFiniteNumber(value)) {
      problems.push(`"${key}" musí být konečné číslo nebo null`)
    }
  }

  const regime = isObject(raw.regime) ? raw.regime : null

  if (regime === null || typeof regime.is_limited !== 'boolean') {
    problems.push('chybí "regime.is_limited" (boolean)')
  } else if (values.is_limited !== regime.is_limited) {
    problems.push('"values.is_limited" nesouhlasí s "regime.is_limited"')
  }

  if (regime === null || !isFiniteNumber(regime.probability_limited)) {
    problems.push('chybí "regime.probability_limited" (číslo)')
  }

  if (!isFiniteNumber(raw.latency_ms)) {
    problems.push('"latency_ms" musí být číslo')
  }

  const model = isObject(raw.model) ? raw.model : null
  if (model === null || typeof model.device !== 'string') {
    problems.push('chybí "model.device" (string)')
  }

  if (raw.filename !== null && raw.filename !== undefined && typeof raw.filename !== 'string') {
    problems.push('"filename" musí být string nebo null')
  }

  if (problems.length > 0) {
    throw new PredictionFormatError(problems)
  }

  // Po ověření jsou všechny typy správné, takže přetypování je bezpečné.
  return {
    filename: typeof raw.filename === 'string' ? raw.filename : null,
    values: values as unknown as EquilibriumOutputs,
    latencyMs: raw.latency_ms as number,
    device: (model?.device as string) ?? 'neznámé',
    probabilityLimited:
      regime !== null && isFiniteNumber(regime.probability_limited)
        ? regime.probability_limited
        : Number.NaN,
  }
}
