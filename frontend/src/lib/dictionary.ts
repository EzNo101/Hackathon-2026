import type { OutputKey } from '../types'

export interface OutputInfo {
  /** Český popisek parametru. */
  label: string
  /** Jednotka zobrazená v UI. */
  unit: string
  /** Násobitel z uložené hodnoty do zobrazené jednotky (proud: A → kA). */
  scale?: number
}

/** Slovník všech 31 výstupů. Klíče odpovídají `columns.json`. */
export const OUTPUT_INFO: Record<OutputKey, OutputInfo> = {
  is_limited: { label: 'Limiterová konfigurace', unit: 'bool' },
  plasma_current: { label: 'Proud plazmatem', unit: 'kA', scale: 1e-3 },
  R_mag_axis: { label: 'R magnetické osy', unit: 'm' },
  Z_mag_axis: { label: 'Z magnetické osy', unit: 'm' },
  elongation: { label: 'Elongace κ', unit: '—' },
  triangularity: { label: 'Triangularita δ', unit: '—' },
  triangularity_upper: { label: 'Triangularita horní δu', unit: '—' },
  triangularity_lower: { label: 'Triangularita dolní δl', unit: '—' },
  R_x_point: { label: 'R X-bodu', unit: 'm' },
  Z_x_point: { label: 'Z X-bodu', unit: 'm' },
  R_strike_point_1: { label: 'R strike pointu 1', unit: 'm' },
  Z_strike_point_1: { label: 'Z strike pointu 1', unit: 'm' },
  R_strike_point_2: { label: 'R strike pointu 2', unit: 'm' },
  Z_strike_point_2: { label: 'Z strike pointu 2', unit: 'm' },
  R_limiter: { label: 'R bodu dotyku s limiterem', unit: 'm' },
  Z_limiter: { label: 'Z bodu dotyku s limiterem', unit: 'm' },
  a: { label: 'Malý poloměr a', unit: 'm' },
  R_geom: { label: 'R geometrického středu', unit: 'm' },
  Z_geom: { label: 'Z geometrického středu', unit: 'm' },
  R_top: { label: 'R horního bodu', unit: 'm' },
  Z_top: { label: 'Z horního bodu', unit: 'm' },
  R_bottom: { label: 'R dolního bodu', unit: 'm' },
  Z_bottom: { label: 'Z dolního bodu', unit: 'm' },
  R_outer: { label: 'R vnějšího bodu', unit: 'm' },
  Z_outer: { label: 'Z vnějšího bodu', unit: 'm' },
  R_inner: { label: 'R vnitřního bodu', unit: 'm' },
  Z_inner: { label: 'Z vnitřního bodu', unit: 'm' },
  squareness_upper_outer: { label: 'Squareness horní vnější', unit: '—' },
  squareness_upper_inner: { label: 'Squareness horní vnitřní', unit: '—' },
  squareness_lower_outer: { label: 'Squareness dolní vnější', unit: '—' },
  squareness_lower_inner: { label: 'Squareness dolní vnitřní', unit: '—' },
}
