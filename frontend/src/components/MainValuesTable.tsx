import {
  formatConfiguration,
  formatCurrentKiloAmps,
} from '../lib/format'
import { MAIN_OUTPUT_COLS, type EquilibriumOutputs } from '../types'
import {
  ValuesTable,
  numericValueRow as numericRow,
  type ValueGroup,
} from './ValuesTable'

interface MainValuesTableProps {
  sample: EquilibriumOutputs
}

const DIVERTOR_ONLY = 'Dostupné pouze v divertorové konfiguraci.'
const LIMITER_ONLY = 'Dostupné pouze v limiterové konfiguraci.'

/** Tabulka hlavních hodnot – konfigurace, globální parametry a klíčové body. */
export function MainValuesTable({ sample }: MainValuesTableProps) {
  const isLimiter = sample.is_limited

  const groups: ValueGroup[] = [
    {
      title: 'Konfigurace a proud',
      rows: [
        {
          label: 'Konfigurace',
          value: (
            <span
              className={`config-badge${
                isLimiter ? ' is-limiter' : ' is-divertor'
              }`}
            >
              {formatConfiguration(isLimiter)}
            </span>
          ),
          unit: '—',
        },
        numericRow(
          'Proud plazmatem',
          sample.plasma_current,
          'kA',
          (value) => formatCurrentKiloAmps(value, 1),
        ),
      ],
    },
    {
      title: 'Magnetická osa a tvar',
      rows: [
        numericRow('R magnetické osy', sample.R_mag_axis, 'm'),
        numericRow('Z magnetické osy', sample.Z_mag_axis, 'm'),
        numericRow('Elongace κ', sample.elongation, '—'),
        numericRow('Triangularita δ', sample.triangularity, '—'),
        numericRow('Triangularita horní δu', sample.triangularity_upper, '—'),
        numericRow('Triangularita dolní δl', sample.triangularity_lower, '—'),
      ],
    },
    {
      title: 'X-bod a strike pointy',
      rows: [
        numericRow(
          'R X-bodu',
          sample.R_x_point,
          'm',
          undefined,
          DIVERTOR_ONLY,
        ),
        numericRow(
          'Z X-bodu',
          sample.Z_x_point,
          'm',
          undefined,
          DIVERTOR_ONLY,
        ),
        numericRow(
          'R strike pointu 1',
          sample.R_strike_point_1,
          'm',
          undefined,
          DIVERTOR_ONLY,
        ),
        numericRow(
          'Z strike pointu 1',
          sample.Z_strike_point_1,
          'm',
          undefined,
          DIVERTOR_ONLY,
        ),
        numericRow(
          'R strike pointu 2',
          sample.R_strike_point_2,
          'm',
          undefined,
          DIVERTOR_ONLY,
        ),
        numericRow(
          'Z strike pointu 2',
          sample.Z_strike_point_2,
          'm',
          undefined,
          DIVERTOR_ONLY,
        ),
      ],
    },
    {
      title: 'Bod dotyku s limiterem',
      rows: [
        numericRow(
          'R limiteru',
          sample.R_limiter,
          'm',
          undefined,
          LIMITER_ONLY,
        ),
        numericRow(
          'Z limiteru',
          sample.Z_limiter,
          'm',
          undefined,
          LIMITER_ONLY,
        ),
      ],
    },
  ]

  return (
    <ValuesTable
      title="Hlavní parametry"
      meta={`${MAIN_OUTPUT_COLS.length} hodnot`}
      groups={groups}
      caption="Hodnoty X-bodu a strike pointů jsou definované pouze v divertorové konfiguraci, bod dotyku s limiterem pouze v limiterové."
    />
  )
}
