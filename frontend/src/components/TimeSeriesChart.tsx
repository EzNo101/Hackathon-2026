import { useMemo } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useEquilibrium } from '../state/EquilibriumContext'
import { getLimiterSpans } from '../lib/timeseries'
import type { EquilibriumOutputs, EquilibriumSample } from '../types'

const CHART_HEIGHT = 240
const GRID_COLOR = 'rgba(148, 163, 184, 0.12)'
const AXIS_COLOR = '#8492a6'
const CURRENT_COLOR = '#fbbf24'
const CURRENT_LINE_COLOR = '#22d3ee'
const LIMITER_FILL = 'rgba(148, 163, 184, 0.18)'

/**
 * Průběh plasma_current v kA v čase výboje.
 *
 * Šedé pásy označují úseky s limiterem, svislá čára aktuální čas. Klik do
 * grafu nastaví čas na nejbližší vzorek.
 */
interface TimeSeriesChartProps {
  /** Pokud nejsou předané, použije se aktivní dataset z kontextu. */
  series?: EquilibriumSample[]
  sample?: EquilibriumOutputs | null
  cursorTime?: number
  onSelectTime?: (time: number) => void
}

export function TimeSeriesChart({
  series: seriesProp,
  sample,
  cursorTime: cursorTimeProp,
  onSelectTime,
}: TimeSeriesChartProps = {}) {
  const context = useEquilibrium()
  const series = seriesProp ?? context.series
  const selectedSample = sample !== undefined ? sample : context.selectedSample
  const selectedTime = cursorTimeProp ?? context.selectedTime
  const setSelectedTime = onSelectTime ?? context.setSelectedTime

  const data = useMemo(
    () =>
      series.map((sample) => ({
        time: sample.time,
        current:
          sample.plasma_current === null ? null : sample.plasma_current / 1000,
      })),
    [series],
  )

  const limiterSpans = useMemo(() => getLimiterSpans(series), [series])

  if (series.length === 0) {
    return null
  }

  const timeStart = series[0].time
  const timeEnd = series[series.length - 1].time
  const cursorTime = cursorTimeProp ?? context.selectedSample?.time ?? selectedTime
  const currentNow =
    selectedSample?.plasma_current == null
      ? null
      : selectedSample.plasma_current / 1000

  return (
    <section className="time-chart" aria-label="Průběh proudu plazmatem">
      <div className="time-chart-body" style={{ height: CHART_HEIGHT }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 10, right: 16, bottom: 4, left: 4 }}
            onClick={(state) => {
              const index = state.activeTooltipIndex

              if (typeof index === 'number' && series[index]) {
                setSelectedTime(series[index].time)
              }
            }}
          >
            <CartesianGrid stroke={GRID_COLOR} vertical={false} />

            {limiterSpans.map((span) => (
              <ReferenceArea
                key={`${span.start}-${span.end}`}
                x1={span.start}
                x2={span.end}
                fill={LIMITER_FILL}
                stroke="none"
                ifOverflow="extendDomain"
              />
            ))}

            <XAxis
              type="number"
              dataKey="time"
              domain={[timeStart, timeEnd]}
              tickFormatter={(value: number) => value.toFixed(2)}
              stroke={AXIS_COLOR}
              tick={{ fill: AXIS_COLOR, fontSize: 11 }}
              label={{
                value: 'čas [s]',
                position: 'insideBottomRight',
                offset: -2,
                fill: AXIS_COLOR,
                fontSize: 11,
              }}
            />
            <YAxis
              type="number"
              dataKey="current"
              stroke={AXIS_COLOR}
              tick={{ fill: AXIS_COLOR, fontSize: 11 }}
              width={56}
              tickFormatter={(value: number) => value.toFixed(0)}
              label={{
                value: 'kA',
                angle: -90,
                position: 'insideLeft',
                fill: AXIS_COLOR,
                fontSize: 11,
              }}
            />

            <Tooltip
              cursor={{ stroke: CURRENT_LINE_COLOR, strokeOpacity: 0.4 }}
              contentStyle={{
                background: '#111925',
                border: '1px solid rgba(148, 163, 184, 0.3)',
                borderRadius: 10,
                fontSize: 12,
              }}
              labelFormatter={(value) => `t = ${Number(value).toFixed(4)} s`}
              formatter={(value) => [
                `${Number(value).toFixed(1)} kA`,
                'Ip',
              ]}
            />

            <ReferenceLine
              x={cursorTime}
              stroke={CURRENT_LINE_COLOR}
              strokeWidth={1.5}
              ifOverflow="extendDomain"
              label={{
                value: `t = ${cursorTime.toFixed(3)} s`,
                position: 'insideTopRight',
                fill: CURRENT_LINE_COLOR,
                fontSize: 11,
              }}
            />

            {currentNow !== null ? (
              <ReferenceDot
                x={cursorTime}
                y={currentNow}
                r={5}
                fill={CURRENT_COLOR}
                stroke="#080c12"
                strokeWidth={2}
                ifOverflow="extendDomain"
              />
            ) : null}

            <Line
              type="monotone"
              dataKey="current"
              stroke={CURRENT_COLOR}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: CURRENT_COLOR }}
              isAnimationActive={false}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
