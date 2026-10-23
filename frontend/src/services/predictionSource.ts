import { parsePredictionResponse } from '../lib/predictionValidator'
import type { PredictionResult } from '../types'

const DEFAULT_API_URL = 'http://localhost:8000/api/v1'
const TIMEOUT_MS = 30_000

/** Chyba komunikace s backendem, text je určen pro uživatele. */
export class PredictionRequestError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PredictionRequestError'
  }
}

export function getApiBaseUrl(): string {
  // Prázdná hodnota (např. build bez --build-arg) spadne na výchozí adresu.
  const configured = import.meta.env.VITE_API_URL?.trim()
  return (configured || DEFAULT_API_URL).replace(/\/+$/, '')
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      return typeof detail === 'string' ? detail : null
    }
  } catch {
    // Tělo není JSON – použijeme jen stavový kód.
  }
  return null
}

/**
 * Pošle fotku na `POST {VITE_API_URL}/predict` (multipart, pole `file`)
 * a vrátí validovaný výsledek. Při jakékoli chybě vyhodí `PredictionRequestError`.
 */
export async function predictImage(file: File): Promise<PredictionResult> {
  const url = `${getApiBaseUrl()}/predict`
  const form = new FormData()
  form.append('file', file, file.name)

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(url, { method: 'POST', body: form, signal: controller.signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new PredictionRequestError(
        `Backend neodpověděl do ${TIMEOUT_MS / 1000} s. Běží na ${url}?`,
      )
    }
    throw new PredictionRequestError(
      `Nelze se spojit s backendem (${url}). Je spuštěný a povoluje CORS?`,
    )
  } finally {
    window.clearTimeout(timer)
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response)

    if (response.status === 503) {
      throw new PredictionRequestError('Model se ještě načítá, zkus to za chvilku.')
    }
    if (response.status === 415 || response.status === 400) {
      throw new PredictionRequestError(detail ?? 'Backend soubor odmítl.')
    }
    throw new PredictionRequestError(
      `Backend vrátil chybu HTTP ${response.status}${detail ? `: ${detail}` : '.'}`,
    )
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw new PredictionRequestError('Odpověď backendu není platný JSON.')
  }

  try {
    return parsePredictionResponse(payload)
  } catch (error) {
    throw new PredictionRequestError(
      error instanceof Error ? error.message : 'Neplatná odpověď backendu.',
    )
  }
}
