import type { PlasmaMode } from '../types'

/** Pořadí režimů v legendách a počítadlech. */
export const MODE_ORDER: readonly PlasmaMode[] = ['L-mode', 'H-mode', 'ELM']

/**
 * Barvy režimů pro SVG i HTML. Stejné přiřazení používají všechny grafy,
 * aby se L-mode, H-mode a ELM nezaměnily.
 */
export const MODE_COLORS: Record<PlasmaMode, string> = {
  'L-mode': '#22d3ee',
  'H-mode': '#34d399',
  ELM: '#f87171',
}
