import {
  formatConfiguration,
  formatCurrentKiloAmps,
  formatNumber,
} from '../lib/format'
import type { EquilibriumOutputs } from '../types'

interface SummaryCardsProps {
  sample: EquilibriumOutputs
}

/** Rychlý přehled nejdůležitějších čísel nad tabulkou. */
export function SummaryCards({ sample }: SummaryCardsProps) {
  const isLimiter = sample.is_limited
  const detailPoint = isLimiter
    ? `Bod dotyku: R ${formatNumber(sample.R_limiter, 3)} · Z ${formatNumber(sample.Z_limiter, 3)} m`
    : `X-bod: R ${formatNumber(sample.R_x_point, 3)} · Z ${formatNumber(sample.Z_x_point, 3)} m`

  const cards = [
    {
      label: 'Proud plazmatem',
      value: formatCurrentKiloAmps(sample.plasma_current, 1),
      unit: 'kA',
      detail: 'znaménko udává směr proudu',
    },
    {
      label: 'Magnetická osa',
      value: `R ${formatNumber(sample.R_mag_axis, 3)}`,
      unit: 'm',
      detail: `Z ${formatNumber(sample.Z_mag_axis, 3)} m`,
    },
    {
      label: 'Elongace κ',
      value: formatNumber(sample.elongation, 3),
      unit: '',
      detail: 'poměr výšky a šířky plazmatu',
    },
    {
      label: 'Triangularita δ',
      value: formatNumber(sample.triangularity, 3),
      unit: '',
      detail: `horní ${formatNumber(sample.triangularity_upper, 3)} · dolní ${formatNumber(sample.triangularity_lower, 3)}`,
    },
    {
      label: 'Konfigurace',
      value: (
        <span
          className={`config-badge${isLimiter ? ' is-limiter' : ' is-divertor'}`}
        >
          {formatConfiguration(isLimiter)}
        </span>
      ),
      unit: '',
      detail: detailPoint,
    },
  ]

  return (
    <div className="summary-cards">
      {cards.map((card) => (
        <article className="summary-card" key={card.label}>
          <span className="summary-label">{card.label}</span>
          <div className="summary-value-row">
            <strong className="summary-value">{card.value}</strong>
            {card.unit ? (
              <span className="summary-unit">{card.unit}</span>
            ) : null}
          </div>
          <span className="summary-detail">{card.detail}</span>
        </article>
      ))}
    </div>
  )
}
