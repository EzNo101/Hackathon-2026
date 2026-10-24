import type { EquilibriumOutputs, WallPoint } from '../types'
import { DetailValuesTable } from './DetailValuesTable'
import { FullShapePlot } from './FullShapePlot'

interface DetailPanelProps {
  sample: EquilibriumOutputs
  wall: WallPoint[]
}

/** Detail = všech 31 hodnot a řez plazmatem se stěnou. */
export function DetailPanel({ sample, wall }: DetailPanelProps) {
  return (
    <div className="overview detail-panel">
      <div className="overview-grid">
        <DetailValuesTable sample={sample} />
        <FullShapePlot sample={sample} wall={wall} />
      </div>
    </div>
  )
}
