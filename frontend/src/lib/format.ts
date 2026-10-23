export const MISSING_VALUE = '—'

/** Číslo s pevným počtem desetinných míst; null z datasetu zobrazíme jako „—“ */
export function formatNumber(value: number | null, digits = 3): string {
  if (value === null || !Number.isFinite(value)) {
    return MISSING_VALUE
  }

  return value.toFixed(digits)
}

/** Proud převádíme z ampérů na kiloampéry – v tabulce i kartách je čitelnější. */
export function formatCurrentKiloAmps(
  value: number | null,
  digits = 1,
): string {
  if (value === null || !Number.isFinite(value)) {
    return MISSING_VALUE
  }

  return (value / 1000).toFixed(digits)
}

export function formatConfiguration(isLimited: boolean): string {
  return isLimited ? 'Limiter' : 'Divertor'
}
