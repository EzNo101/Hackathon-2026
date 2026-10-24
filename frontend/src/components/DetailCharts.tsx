import { useMemo } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { MODE_COLORS, MODE_ORDER } from '../lib/plasmaMode'
import { getLimiterSpans } from '../lib/timeseries'
import type { EquilibriumSample, PhotoEntry, PlasmaMode } from '../types'

const AXIS_COLOR = '#8492a6'
const GRID_COLOR = 'rgba(148, 163, 184, 0.12)'
const CURSOR_COLOR = '#22d3ee'
const LIMITER_FILL = 'rgba(148, 163, 184, 0.18)'
const CHART_HEIGHT = 150

/** Řádek grafu: čas a odvozené hodnoty (null tam, kde chybí vstup). */
type ChartRow = { time: number } & Record<string, number | null>

interface ChartLine {
  key: string
  label: string
  color: string
}

interface ChartDefinition {
  id: string
  title: string
  unit: string
  lines: ChartLine[]
  zeroLine?: boolean
}

const CHARTS: ChartDefinition[] = [
  {
    id: 'elongation',
    title: 'Elongace κ',
    unit: '—',
    lines: [{ key: 'elongation', label: 'κ', color: '#22d3ee' }],
  },
  {
    id: 'triangularity',
    title: 'Trojúhelníkovitost δ',
    unit: '—',
    lines: [
      { key: 'triangularity_upper', label: 'horní δu', color: '#f59e0b' },
      { key: 'triangularity_lower', label: 'dolní δl', color: '#34d399' },
      { key: 'triangularity', label: 'průměr δ', color: '#e8eef7' },
    ],
    zeroLine: true,
  },
  {
    id: 'minor-radius',
    title: 'Malý poloměr a',
    unit: 'm',
    lines: [{ key: 'a', label: 'a', color: '#a78bfa' }],
  },
  {
    id: 'axis-shift',
    title: 'Posun magnetické osy',
    unit: 'm',
    lines: [
      { key: 'shift_r', label: 'R_osy − R_geom', color: '#f59e0b' },
      { key: 'shift_z', label: 'Z_osy − Z_geom', color: '#22d3ee' },
    ],
    zeroLine: true,
  },
  {
    id: 'squareness',
    title: 'Squareness okraje',
    unit: '—',
    lines: [
      { key: 'squareness_upper_outer', label: 'horní vnější', color: '#f59e0b' },
      { key: 'squareness_upper_inner', label: 'horní vnitřní', color: '#fb7185' },
      { key: 'squareness_lower_outer', label: 'dolní vnější', color: '#a78bfa' },
      { key: 'squareness_lower_inner', label: 'dolní vnitřní', color: '#34d399' },
    ],
    zeroLine: true,
  },
]

function difference(a: number | null, b: number | null): number | null {
  return a === null || b === null ? null : a - b
}

function toChartRow(sample: EquilibriumSample): ChartRow {
  return {
    time: sample.time,
    elongation: sample.elongation,
    triangularity: sample.triangularity,
    triangularity_upper: sample.triangularity_upper,
    triangularity_lower: sample.triangularity_lower,
    a: sample.a,
    shift_r: difference(sample.R_mag_axis, sample.R_geom),
    shift_z: difference(sample.Z_mag_axis, sample.Z_geom),
    squareness_upper_outer: sample.squareness_upper_outer,
    squareness_upper_inner: sample.squareness_upper_inner,
    squareness_lower_outer: sample.squareness_lower_outer,
    squareness_lower_inner: sample.squareness_lower_inner,
  }
}

interface DetailChartsProps {
  series: EquilibriumSample[]
  photos: PhotoEntry[] | null
  cursorTime: number
  onSelectTime: (time: number) => void
}

/**
 * Časové průběhy tvaru plazmatu pro celý výboj a pruh režimů z fotek.
 * Svislá čára ukazuje vybraný okamžik, šedé pásy limiter a klik nastaví čas.
 */
export function DetailCharts({
  series,
  photos,
  cursorTime,
  onSelectTime,
}: DetailChartsProps) {
  const rows = useMemo(() => series.map(toChartRow), [series])
  const limiterSpans = useMemo(() => getLimiterSpans(series), [series])

  if (series.length === 0) {
    return null
  }

  const timeStart = series[0].time
  const timeEnd = series[series.length - 1].time

  return (
    <section className="detail-charts" aria-label="Časové průběhy tvaru plazmatu">
      <ModeStrip
        photos={photos}
        timeStart={timeStart}
        timeEnd={timeEnd}
        cursorTime={cursorTime}
      />

      <div className="chart-grid">
        {CHARTS.map((definition) => (
          <ShapeChart
            key={definition.id}
            definition={definition}
            rows={rows}
            timeStart={timeStart}
            timeEnd={timeEnd}
            cursorTime={cursorTime}
            limiterSpans={limiterSpans}
            onSelectTime={onSelectTime}
          />
        ))}
      </div>
    </section>
  )
}

interface ShapeChartProps {
  definition: ChartDefinition
  rows: ChartRow[]
  timeStart: number
  timeEnd: number
  cursorTime: number
  limiterSpans: { start: number; end: number }[]
  onSelectTime: (time: number) => void
}

function ShapeChart({
  definition,
  rows,
  timeStart,
  timeEnd,
  cursorTime,
  limiterSpans,
  onSelectTime,
}: ShapeChartProps) {
  const labelFor = (key: string) =>
    definition.lines.find((line) => line.key === key)?.label ?? key

  return (
    <article className="chart-card">
      <div className="chart-card-head">
        <span className="control-label">{definition.title}</span>
        <span className="control-hint">{definition.unit}</span>
      </div>

      <div className="chart-legend">
        {definition.lines.map((line) => (
          <span className="legend-chip" key={line.key}>
            <i style={{ background: line.color }} aria-hidden="true" />
            {line.label}
          </span>
        ))}
      </div>

      <div style={{ height: CHART_HEIGHT }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={rows}
            margin={{ top: 6, right: 10, bottom: 0, left: 0 }}
            onClick={(state) => {
              const index = state.activeTooltipIndex

              if (typeof index === 'number' && rows[index]) {
                onSelectTime(rows[index].time)
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
              tick={{ fill: AXIS_COLOR, fontSize: 10 }}
            />
            <YAxis
              type="number"
              stroke={AXIS_COLOR}
              tick={{ fill: AXIS_COLOR, fontSize: 10 }}
              width={48}
              domain={['auto', 'auto']}
              tickFormatter={(value: number) => value.toFixed(3)}
            />

            <Tooltip
              contentStyle={{
                background: '#111925',
                border: '1px solid rgba(148, 163, 184, 0.3)',
                borderRadius: 10,
                fontSize: 12,
              }}
              labelFormatter={(value) => `t = ${Number(value).toFixed(4)} s`}
              formatter={(value, name) => [
                Number(value).toFixed(4),
                labelFor(String(name)),
              ]}
            />

            {definition.zeroLine ? (
              <ReferenceLine y={0} stroke="rgba(148, 163, 184, 0.35)" />
            ) : null}

            <ReferenceLine
              x={cursorTime}
              stroke={CURSOR_COLOR}
              strokeWidth={1.2}
              ifOverflow="extendDomain"
            />

            {definition.lines.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                stroke={line.color}
                strokeWidth={1.6}
                dot={false}
                isAnimationActive={false}
                connectNulls={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}

interface ModeStripProps {
  photos: PhotoEntry[] | null
  timeStart: number
  timeEnd: number
  cursorTime: number
}

interface ModeSegment {
  mode: PlasmaMode
  start: number
  end: number
}

/**
 * Režim plazmatu z fotek jako barevný pruh v čase výboje.
 * Každá fotka platí od svého času do času další fotky.
 */
function ModeStrip({ photos, timeStart, timeEnd, cursorTime }: ModeStripProps) {
  const span = timeEnd - timeStart
  const toPercent = (time: number) =>
    span > 0 ? Math.min(Math.max((time - timeStart) / span, 0), 1) * 100 : 0

  const { segments, counts } = useMemo(() => {
    const result: ModeSegment[] = []
    const modeCounts: Record<PlasmaMode, number> = {
      'L-mode': 0,
      'H-mode': 0,
      ELM: 0,
    }

    ;(photos ?? []).forEach((photo, index, all) => {
      modeCounts[photo.mode] += 1

      const end = index + 1 < all.length ? all[index + 1].time : timeEnd
      const last = result[result.length - 1]

      if (last && last.mode === photo.mode) {
        last.end = end
      } else {
        result.push({ mode: photo.mode, start: photo.time, end })
      }
    })

    return { segments: result, counts: modeCounts }
  }, [photos, timeEnd])

  return (
    <article className="chart-card mode-strip">
      <div className="chart-card-head">
        <span className="control-label">Režim plazmatu (fotky)</span>
        <span className="control-hint">
          {photos ? `${photos.length} fotek` : ''}
        </span>
      </div>

      {photos === null ? (
        <span className="control-hint">Načítám režimy…</span>
      ) : photos.length === 0 ? (
        <span className="control-hint">
          Pro tento výboj nejsou fotky, režim plazmatu nelze zobrazit.
        </span>
      ) : (
        <>
          <svg
            className="mode-strip-svg"
            viewBox="0 0 1000 28"
            preserveAspectRatio="none"
            role="img"
            aria-label="Režim plazmatu v čase výboje"
          >
            {segments.map((segment) => {
              const x = toPercent(segment.start) * 10
              const width = Math.max(
                (toPercent(segment.end) - toPercent(segment.start)) * 10,
                0.5,
              )

              return (
                <rect
                  key={`${segment.start}-${segment.mode}`}
                  x={x}
                  y={0}
                  width={width}
                  height={28}
                  fill={MODE_COLORS[segment.mode]}
                >
                  <title>{`${segment.mode}: t ${segment.start.toFixed(4)} – ${segment.end.toFixed(4)} s`}</title>
                </rect>
              )
            })}
            <line
              x1={toPercent(cursorTime) * 10}
              x2={toPercent(cursorTime) * 10}
              y1={0}
              y2={28}
              stroke="#e8eef7"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
            />
          </svg>

          <div className="chart-legend">
            {MODE_ORDER.map((mode) => (
              <span className="legend-chip" key={mode}>
                <i style={{ background: MODE_COLORS[mode] }} aria-hidden="true" />
                {`${mode} · ${counts[mode]}`}
              </span>
            ))}
          </div>
        </>
      )}
    </article>
  )
}
