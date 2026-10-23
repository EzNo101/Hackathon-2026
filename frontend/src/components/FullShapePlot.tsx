import { useId, useMemo } from 'react'
import {
  formatConfiguration,
  formatNumber,
} from '../lib/format'
import {
  buildPlasmaBoundary,
  type ShapePoint,
} from '../lib/plasmaShape'
import {
  COMPASS_DOMAIN,
  PLASMA_VIEWPORT,
  createProjector,
  createTicks,
} from '../lib/plot'
import type { EquilibriumOutputs, WallPoint } from '../types'

interface FullShapePlotProps {
  sample: EquilibriumOutputs
  wall: WallPoint[]
}

interface Coordinate {
  r: number
  z: number
}

// Projekce a ticks jsou pro všechny výboje stejné, proto je počítáme jednou.
const projector = createProjector(COMPASS_DOMAIN, PLASMA_VIEWPORT)
const rTicks = createTicks(projector.domain.rMin, projector.domain.rMax, 0.1)
const zTicks = createTicks(projector.domain.zMin, projector.domain.zMax, 0.1)

const xLeft = projector.offsetX
const xRight = projector.offsetX + projector.plotWidth
const yTop = projector.offsetY
const yBottom = projector.offsetY + projector.plotHeight

function coordinateTitle(label: string, point: Coordinate): string {
  return `${label}: R = ${formatNumber(point.r, 3)} m, Z = ${formatNumber(point.z, 3)} m`
}

function toPath(points: ShapePoint[], close = true): string {
  const path = points
    .map((point, index) => {
      const position = projector.project(point.r, point.z)
      return `${index === 0 ? 'M' : 'L'} ${position.x.toFixed(2)} ${position.y.toFixed(2)}`
    })
    .join(' ')

  return close ? `${path} Z` : path
}

/**
 * Řez komorou a plazmatem v rovině R–Z.
 *
 * Všechny hodnoty pocházejí z jednoho snapshotu. Divertorový snapshot má
 * X-bod a strike pointy, limiterový má naopak bod dotyku s limiterem.
 * Obrys plazmatu je aproximace z krajních bodů, ne rekonstrukce
 * skutečné separatrix.
 */
export function FullShapePlot({ sample, wall }: FullShapePlotProps) {
  const titleId = useId()
  const descriptionId = useId()
  const clipId = `plasma-clip-${useId().replace(/:/g, '')}`
  const isLimiter = sample.is_limited

  const boundary = useMemo(() => buildPlasmaBoundary(sample), [sample])
  const wallPoints = useMemo(
    () => wall.map((point) => ({ r: point.R, z: point.Z })),
    [wall],
  )

  const axis: Coordinate | null =
    sample.R_mag_axis !== null && sample.Z_mag_axis !== null
      ? { r: sample.R_mag_axis, z: sample.Z_mag_axis }
      : null

  const xPoint: Coordinate | null =
    sample.R_x_point !== null && sample.Z_x_point !== null
      ? { r: sample.R_x_point, z: sample.Z_x_point }
      : null

  const limiterPoint: Coordinate | null =
    sample.R_limiter !== null && sample.Z_limiter !== null
      ? { r: sample.R_limiter, z: sample.Z_limiter }
      : null

  const rawStrikePoints: Array<{ r: number | null; z: number | null }> = [
    { r: sample.R_strike_point_1, z: sample.Z_strike_point_1 },
    { r: sample.R_strike_point_2, z: sample.Z_strike_point_2 },
  ]

  // Pořadí strike pointů je v datech náhodné; seřazení podle R dává
  // konzistentní označení HFS (menší R) a LFS (větší R).
  const strikePoints = rawStrikePoints
    .filter(
      (point): point is Coordinate => point.r !== null && point.z !== null,
    )
    .sort((left, right) => left.r - right.r)

  const geomX =
    sample.R_geom !== null ? projector.project(sample.R_geom, 0).x : null

  const axisPoint = axis ? projector.project(axis.r, axis.z) : null
  const xPointPosition = xPoint
    ? projector.project(xPoint.r, xPoint.z)
    : null
  const limiterPosition = limiterPoint
    ? projector.project(limiterPoint.r, limiterPoint.z)
    : null
  const axisTitle = axis ? coordinateTitle('Magnetická osa', axis) : ''
  const xTitle = xPoint ? coordinateTitle('X-bod', xPoint) : ''

  return (
    <section className="plot-panel" aria-labelledby={titleId}>
      <div className="plot-head">
        <div>
          <p className="eyebrow">R–Z řez</p>
          <h3 id={titleId}>Tvar plazmatu</h3>
        </div>
        <span
          className={`config-badge${isLimiter ? ' is-limiter' : ' is-divertor'}`}
        >
          {formatConfiguration(isLimiter)}
        </span>
      </div>

      <div className="plot-body">
        <svg
          className="plot-svg"
          viewBox={`0 0 ${PLASMA_VIEWPORT.width} ${PLASMA_VIEWPORT.height}`}
          role="img"
          aria-labelledby={`${descriptionId}-title ${descriptionId}-desc`}
        >
          <title id={`${descriptionId}-title`}>Tvar plazmatu v komoře</title>
          <desc id={`${descriptionId}-desc`}>
            Poloidální řez se souřadnicemi R a Z. Zobrazena je stěna komory,
            přibližný obrys plazmatu, magnetická osa a body dostupné pro
            zvolenou konfiguraci.
          </desc>

          <defs>
            {/* Plazma nesmí přesáhnout první stěnu, i když aproximace mírně
                překmitne. Clip je v souřadnicích SVG, stejně jako stěna. */}
            {wallPoints.length > 0 ? (
              <clipPath id={clipId} clipPathUnits="userSpaceOnUse">
                <path d={toPath(wallPoints)} />
              </clipPath>
            ) : null}
          </defs>

          <rect
            x={xLeft}
            y={yTop}
            width={projector.plotWidth}
            height={projector.plotHeight}
            className="plot-frame"
          />

          {/* Mřížka a popisky os */}
          <g className="plot-grid">
            {rTicks.map((tick) => {
              const x = projector.project(tick, 0).x

              return (
                <g key={`r-${tick}`}>
                  <line
                    x1={x}
                    x2={x}
                    y1={yTop}
                    y2={yBottom}
                    className="plot-grid-line"
                  />
                  <text
                    x={x}
                    y={yBottom + 18}
                    textAnchor="middle"
                    className="plot-tick-label"
                  >
                    {tick.toFixed(1)}
                  </text>
                </g>
              )
            })}

            {zTicks.map((tick) => {
              const y = projector.project(0, tick).y

              return (
                <g key={`z-${tick}`}>
                  <line
                    x1={xLeft}
                    x2={xRight}
                    y1={y}
                    y2={y}
                    className="plot-grid-line"
                  />
                  <text
                    x={xLeft - 10}
                    y={y + 4}
                    textAnchor="end"
                    className="plot-tick-label"
                  >
                    {tick.toFixed(1)}
                  </text>
                </g>
              )
            })}
          </g>

          <text
            x={(xLeft + xRight) / 2}
            y={PLASMA_VIEWPORT.height - 8}
            textAnchor="middle"
            className="plot-axis-title"
          >
            R [m]
          </text>
          <text
            x={14}
            y={(yTop + yBottom) / 2}
            textAnchor="middle"
            transform={`rotate(-90 14 ${(yTop + yBottom) / 2})`}
            className="plot-axis-title"
          >
            Z [m]
          </text>

          {/* Stěna komory je pod obrysem plazmatu. */}
          {wallPoints.length > 0 ? (
            <path
              d={toPath(wallPoints)}
              className="plot-wall"
              aria-label="Stěna komory"
            />
          ) : null}

          {/* Křížek procházející magnetickou osou. */}
          {axisPoint ? (
            <g className="plot-crosshair">
              <line
                x1={xLeft}
                x2={xRight}
                y1={axisPoint.y}
                y2={axisPoint.y}
              />
              <line
                x1={axisPoint.x}
                x2={axisPoint.x}
                y1={yTop}
                y2={yBottom}
              />
            </g>
          ) : null}

          {/* Svislá čára na R_geom – vůči ní se měří trojúhelníkovitost (horní a dolní vrchol). */}
          {geomX !== null ? (
            <g className="plot-geom">
              <title>{`Geometrický střed: R = ${formatNumber(sample.R_geom, 3)} m`}</title>
              <line x1={geomX} x2={geomX} y1={yTop} y2={yBottom} />
              <text x={geomX + 4} y={yTop + 12} className="plot-point-label">
                R_geom
              </text>
            </g>
          ) : null}

          {boundary ? (
            <path
              d={toPath(boundary)}
              className="plot-plasma"
              clipPath={
                wallPoints.length > 0 ? `url(#${clipId})` : undefined
              }
            >
              <title>
                Přibližný obrys plazmatu z krajních bodů tohoto snapshotu
              </title>
            </path>
          ) : null}

          {/* Divertorové nohy jako spojnice X-bodu a strike pointů. */}
          {xPointPosition
            ? strikePoints.map((point, index) => {
                const position = projector.project(point.r, point.z)

                return (
                  <line
                    key={`leg-${point.r}-${index}`}
                    x1={xPointPosition.x}
                    y1={xPointPosition.y}
                    x2={position.x}
                    y2={position.y}
                    className="plot-leg"
                  />
                )
              })
            : null}

          {axisPoint && axis ? (
            <g
              className="plot-marker plot-marker-axis"
              transform={`translate(${axisPoint.x} ${axisPoint.y})`}
            >
              <title>{axisTitle}</title>
              <circle r={9} className="plot-marker-halo" />
              <circle r={4.5} className="plot-marker-core" />
              <text x={10} y={-10} className="plot-point-label">
                Osa
              </text>
            </g>
          ) : null}

          {xPointPosition && xPoint ? (
            <g
              className="plot-marker plot-marker-x"
              transform={`translate(${xPointPosition.x} ${xPointPosition.y})`}
            >
              <title>{xTitle}</title>
              <circle r={10} className="plot-marker-halo" />
              <line x1={-5} y1={-5} x2={5} y2={5} />
              <line x1={-5} y1={5} x2={5} y2={-5} />
              <text x={-10} y={-9} textAnchor="end" className="plot-point-label">
                X-bod
              </text>
            </g>
          ) : null}

          {strikePoints.map((point, index) => {
            const position = projector.project(point.r, point.z)
            const isLeft = index === 0
            const label = `SP${index + 1}`

            return (
              <g
                key={`strike-${point.r}-${index}`}
                className="plot-marker plot-marker-strike"
                transform={`translate(${position.x} ${position.y})`}
              >
                <title>
                  {coordinateTitle(
                    index === 0 ? 'Strike point HFS' : 'Strike point LFS',
                    point,
                  )}
                </title>
                <path d="M 0 -6 L 5.5 5 L -5.5 5 Z" />
                <text
                  x={isLeft ? -9 : 9}
                  y={13}
                  textAnchor={isLeft ? 'end' : 'start'}
                  className="plot-point-label"
                >
                  {label}
                </text>
              </g>
            )
          })}

          {limiterPosition && limiterPoint ? (
            <g
              className="plot-marker plot-marker-limiter"
              transform={`translate(${limiterPosition.x} ${limiterPosition.y})`}
            >
              <title>{coordinateTitle('Bod dotyku s limiterem', limiterPoint)}</title>
              <rect x={-5} y={-5} width={10} height={10} rx={1.5} />
              <text x={10} y={-10} className="plot-point-label">
                Limiter
              </text>
            </g>
          ) : null}
        </svg>
      </div>

      <div className="plot-legend">
        {wallPoints.length > 0 ? (
          <span className="legend-item">
            <i className="legend-swatch legend-wall" aria-hidden="true" />
            Stěna komory
          </span>
        ) : null}
        {boundary ? (
          <span className="legend-item">
            <i className="legend-swatch legend-plasma" aria-hidden="true" />
            Plazma
          </span>
        ) : null}
        {axis ? (
          <span className="legend-item">
            <i className="legend-swatch legend-axis" aria-hidden="true" />
            Magnetická osa
          </span>
        ) : null}
        {geomX !== null ? (
          <span className="legend-item">
            <i className="legend-swatch legend-geom" aria-hidden="true" />
            R_geom
          </span>
        ) : null}
        {xPoint ? (
          <span className="legend-item">
            <i className="legend-swatch legend-x" aria-hidden="true">
              ×
            </i>
            X-bod
          </span>
        ) : null}
        {strikePoints.length > 0 ? (
          <span className="legend-item">
            <i className="legend-swatch legend-triangle" aria-hidden="true" />
            Strike pointy
          </span>
        ) : null}
        {limiterPoint ? (
          <span className="legend-item">
            <i className="legend-swatch legend-square" aria-hidden="true" />
            Bod dotyku
          </span>
        ) : null}
      </div>

      <p className="plot-note">
        {isLimiter
          ? 'Limiterový snapshot: zobrazen je bod dotyku, X-bod ani strike pointy v něm neexistují.'
          : 'Divertorový snapshot: zobrazen je X-bod a strike pointy, bod dotyku s limiterem v něm neexistuje.'}{' '}
        Obrys plazmatu je aproximace z krajních bodů tohoto snapshotu a je
        oříznutý stěnou komory.
      </p>
    </section>
  )
}
