import type { EquilibriumOutputs, TimelineContext, WallPoint } from '../types'
import { FullShapePlot } from './FullShapePlot'
import { MainValuesTable } from './MainValuesTable'
import { SummaryCards } from './SummaryCards'
import { TimeSeriesChart } from './TimeSeriesChart'

interface OverviewPanelProps {
  sample: EquilibriumOutputs
  wall: WallPoint[]
  /** Průběh proudu v čase – v datasetu vždy, u predikce jen pokud je fotka v datasetu. */
  showTimeline?: boolean
  timeline?: TimelineContext | null
}

/** Přehled = (graf proudu), karty, tabulka 16 hlavních hodnot a řez tvarem plazmatu. */
export function OverviewPanel({
  sample,
  wall,
  showTimeline = true,
  timeline = null,
}: OverviewPanelProps) {
  return (
    <div className="overview">
      {showTimeline ? (
        <TimeSeriesChart
          series={timeline?.series}
          sample={timeline ? sample : undefined}
          cursorTime={timeline?.cursorTime}
          onSelectTime={timeline?.onSelectTime}
        />
      ) : null}
      <SummaryCards sample={sample} />
      <div className="overview-grid">
        <MainValuesTable sample={sample} />
        <FullShapePlot sample={sample} wall={wall} />
      </div>
    </div>
  )
}
