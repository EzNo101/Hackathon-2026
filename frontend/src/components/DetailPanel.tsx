import type { EquilibriumOutputs, TimelineContext, WallPoint } from '../types'
import { DetailCharts } from './DetailCharts'
import { DetailValuesTable } from './DetailValuesTable'
import { FullShapePlot } from './FullShapePlot'

interface DetailPanelProps {
  sample: EquilibriumOutputs
  wall: WallPoint[]
  timeline?: TimelineContext | null
}

/**
 * Detail = všech 31 hodnot, řez plazmatem se stěnou
 * a (u datasetu) časové průběhy tvaru s pruhem režimů z fotek.
 */
export function DetailPanel({ sample, wall, timeline = null }: DetailPanelProps) {
  return (
    <div className="overview detail-panel">
      <div className="overview-grid">
        <DetailValuesTable sample={sample} />
        <FullShapePlot sample={sample} wall={wall} />
      </div>

      {timeline ? (
        <DetailCharts
          series={timeline.series}
          photos={timeline.photos}
          cursorTime={timeline.cursorTime}
          onSelectTime={timeline.onSelectTime}
        />
      ) : null}
    </div>
  )
}
