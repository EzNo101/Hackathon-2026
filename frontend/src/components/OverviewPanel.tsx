import type { EquilibriumOutputs, WallPoint } from '../types'
import { FullShapePlot } from './FullShapePlot'
import { MainValuesTable } from './MainValuesTable'
import { SummaryCards } from './SummaryCards'
import { TimeSeriesChart } from './TimeSeriesChart'

interface OverviewPanelProps {
  sample: EquilibriumOutputs
  wall: WallPoint[]
  /** Průběh proudu v čase – jen v datasetu, predikce nemá časovou řadu. */
  showTimeline?: boolean
}

/** Přehled = (graf proudu), karty, tabulka 16 hlavních hodnot a řez tvarem plazmatu. */
export function OverviewPanel({ sample, wall, showTimeline = true }: OverviewPanelProps) {
  return (
    <div className="overview">
      {showTimeline ? <TimeSeriesChart /> : null}
      <SummaryCards sample={sample} />
      <div className="overview-grid">
        <MainValuesTable sample={sample} />
        <FullShapePlot sample={sample} wall={wall} />
      </div>
    </div>
  )
}
