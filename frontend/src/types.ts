import columns from './data/columns.json'

/**
 * Všech 31 cílových parametrů ekvilibria.
 *
 * Hodnoty, které v dané konfiguraci neexistují (např. X-bod v limiterové
 * konfiguraci), jsou `null` – JSON neumí reprezentovat NaN.
 */
export interface EquilibriumOutputs {
  is_limited: boolean
  plasma_current: number | null
  R_mag_axis: number | null
  Z_mag_axis: number | null
  elongation: number | null
  triangularity: number | null
  triangularity_upper: number | null
  triangularity_lower: number | null
  R_x_point: number | null
  Z_x_point: number | null
  R_strike_point_1: number | null
  Z_strike_point_1: number | null
  R_strike_point_2: number | null
  Z_strike_point_2: number | null
  R_limiter: number | null
  Z_limiter: number | null
  a: number | null
  R_geom: number | null
  Z_geom: number | null
  R_top: number | null
  Z_top: number | null
  R_bottom: number | null
  Z_bottom: number | null
  R_outer: number | null
  Z_outer: number | null
  R_inner: number | null
  Z_inner: number | null
  squareness_upper_outer: number | null
  squareness_upper_inner: number | null
  squareness_lower_outer: number | null
  squareness_lower_inner: number | null
}

export type OutputKey = keyof EquilibriumOutputs
export type NumericOutputKey = Exclude<OutputKey, 'is_limited'>

/**
 * Jeden řádek datasetu: čas, výboj a všech 31 výstupů.
 * Vstupní veličiny IPR/FL se do frontendu záměrně nenačítají.
 */
export interface EquilibriumSample extends EquilibriumOutputs {
  time: number
  discharge: number
}

/** Дані часового ряду для графіків у dataset- та prediction-режимі. */
export interface TimelineContext {
  series: EquilibriumSample[]
  photos: PhotoEntry[] | null
  cursorTime: number
  onSelectTime: (time: number) => void
}

export interface DischargeMeta {
  id: number
  rowCount: number
  timeStart: number
  timeEnd: number
  limiterRowCount: number
}

export interface EquilibriumManifest {
  version: number
  generatedAt: string
  source: string
  rowCount: number
  columns: {
    main: OutputKey[]
    supplementary: OutputKey[]
  }
  discharges: DischargeMeta[]
}

/** Režim plazmatu ve snímku (sloupec `mode` v camera_data.csv). */
export type PlasmaMode = 'L-mode' | 'H-mode' | 'ELM'

/** Jedna fotka z kamery: název souboru, čas snímku a režim plazmatu. */
export interface PhotoEntry {
  filename: string
  time: number
  mode: PlasmaMode
}

/** Statická kontura stěny komory v poloidální rovině (R, Z) v metrech. */
export interface WallPoint {
  R: number
  Z: number
}

/**
 * Výsledek predikce z backendu, po validaci. `values` je přesně 31 výstupů
 * (včetně `is_limited`), v nichž jsou hodnoty neplatné v dané konfiguraci `null`.
 */
export interface PredictionResult {
  filename: string | null
  values: EquilibriumOutputs
  latencyMs: number
  device: string
  probabilityLimited: number
}

/** Skutečná hodnota z datasetu pro fotku, nalezenou podle názvu souboru. */
export interface PhotoTruth {
  filename: string
  discharge: number
  time: number
  mode: PlasmaMode
  sample: EquilibriumSample
}

/**
 * Společné rozhraní pro zdroje dat.
 * Díky němu půjde CSV režim později nahradit backendem bez zásahu do UI.
 */
export interface EquilibriumSource {
  getDischarges(): Promise<DischargeMeta[]>
  getSeries(discharge: number): Promise<EquilibriumSample[]>
}

// Seznamy sloupců držíme na jednom místě v JSONu, aby se skript a frontend
// nemohly rozejít. Pořadí odpovídá pořadí v UI: hlavní, pak doplňkové.
export const MAIN_OUTPUT_COLS = columns.main as readonly OutputKey[]
export const SUPPLEMENTARY_OUTPUT_COLS = columns.supplementary as readonly OutputKey[]
export const ALL_OUTPUT_COLS: readonly OutputKey[] = [
  ...MAIN_OUTPUT_COLS,
  ...SUPPLEMENTARY_OUTPUT_COLS,
]

export function isMainOutput(key: OutputKey): boolean {
  return MAIN_OUTPUT_COLS.includes(key)
}
