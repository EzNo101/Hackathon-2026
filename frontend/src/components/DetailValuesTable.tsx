import {
  ALL_OUTPUT_COLS,
  SUPPLEMENTARY_OUTPUT_COLS,
  type EquilibriumOutputs,
} from '../types'
import {
  ValuesTable,
  numericValueRow as numericRow,
  type ValueGroup,
} from './ValuesTable'
import { MainValuesTable } from './MainValuesTable'

interface DetailValuesTableProps {
  sample: EquilibriumOutputs
}

const EXTREME_POINT_NOTE = 'Hodnota v tomto snapshotu chybí.'

/**
 * Všech výstupy snapshotu (31): hlavní parametry z `MainValuesTable` a pod nimi
 * doplňkové parametry (geometrie, extrémní body, squareness).
 */
export function DetailValuesTable({ sample }: DetailValuesTableProps) {
  const supplementaryGroups: ValueGroup[] = [
    {
      title: 'Geometrie plazmatu',
      rows: [
        numericRow('Malý poloměr a', sample.a, 'm'),
        numericRow('R geometrického středu', sample.R_geom, 'm'),
        numericRow('Z geometrického středu', sample.Z_geom, 'm'),
      ],
    },
    {
      title: 'Krajní body obrysu',
      rows: [
        numericRow('R horního bodu', sample.R_top, 'm', undefined, EXTREME_POINT_NOTE),
        numericRow('Z horního bodu', sample.Z_top, 'm', undefined, EXTREME_POINT_NOTE),
        numericRow('R dolního bodu', sample.R_bottom, 'm', undefined, EXTREME_POINT_NOTE),
        numericRow('Z dolního bodu', sample.Z_bottom, 'm', undefined, EXTREME_POINT_NOTE),
        numericRow('R vnějšího bodu', sample.R_outer, 'm', undefined, EXTREME_POINT_NOTE),
        numericRow('Z vnějšího bodu', sample.Z_outer, 'm', undefined, EXTREME_POINT_NOTE),
        numericRow('R vnitřního bodu', sample.R_inner, 'm', undefined, EXTREME_POINT_NOTE),
        numericRow('Z vnitřního bodu', sample.Z_inner, 'm', undefined, EXTREME_POINT_NOTE),
      ],
    },
    {
      title: 'Squareness (zaoblení)',
      rows: [
        numericRow('Horní vnější', sample.squareness_upper_outer, '—'),
        numericRow('Horní vnitřní', sample.squareness_upper_inner, '—'),
        numericRow('Dolní vnější', sample.squareness_lower_outer, '—'),
        numericRow('Dolní vnitřní', sample.squareness_lower_inner, '—'),
      ],
    },
  ]

  return (
    <div className="detail-values">
      <MainValuesTable sample={sample} />
      <ValuesTable
        title="Doplňkové parametry"
        meta={`${SUPPLEMENTARY_OUTPUT_COLS.length} hodnot · celkem ${ALL_OUTPUT_COLS.length}`}
        groups={supplementaryGroups}
      />
    </div>
  )
}
