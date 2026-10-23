import type { EquilibriumOutputs, EquilibriumSample, PhotoEntry, WallPoint } from '../types'
import { DetailCharts } from './DetailCharts'
import { DetailValuesTable } from './DetailValuesTable'
import { FullShapePlot } from './FullShapePlot'

/** Časové průběhy – jen v datasetu, kde existuje časová řada výboje. */
export interface DetailTimeline {
  series: EquilibriumSample[]
  photos: PhotoEntry[] | null
  cursorTime: number
  onSelectTime: (time: number) => void
}

interface DetailPanelProps {
  sample: EquilibriumOutputs
  wall: WallPoint[]
  timeline?: DetailTimeline | null
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
