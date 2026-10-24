export interface PlotDomain {
  rMin: number
  rMax: number
  zMin: number
  zMax: number
}

export interface PlotPadding {
  top: number
  right: number
  bottom: number
  left: number
}

export interface PlotViewport {
  width: number
  height: number
  padding: PlotPadding
}

export interface PlottedPoint {
  x: number
  y: number
}

export interface Projector {
  domain: PlotDomain
  viewport: PlotViewport
  scale: number
  plotWidth: number
  plotHeight: number
  offsetX: number
  offsetY: number
  project: (r: number, z: number) => PlottedPoint
}

// Rozsah vychází ze skutečné kontury komory COMPASS (R 0,327–0,772,
// Z −0,358–0,367) s malým okrajem. Díky pevnému rozsahu jsou jednotlivé
// časy výboje vizuálně porovnatelné.
export const COMPASS_DOMAIN: PlotDomain = {
  rMin: 0.3,
  rMax: 0.82,
  zMin: -0.42,
  zMax: 0.42,
}

export const PLASMA_VIEWPORT: PlotViewport = {
  width: 420,
  height: 580,
  padding: { top: 24, right: 20, bottom: 48, left: 56 },
}

/**
 * Vytvoří převod z fyzikálních souřadnic (R, Z) do SVG pixelů.
 * Měřítko je pro obě osy stejné, aby byl řez geometricky věrný.
 */
export function createProjector(
  domain: PlotDomain,
  viewport: PlotViewport,
): Projector {
  const { width, height, padding } = viewport
  const innerWidth = width - padding.left - padding.right
  const innerHeight = height - padding.top - padding.bottom

  if (innerWidth <= 0 || innerHeight <= 0) {
    throw new Error('Neplatné rozměry nebo padding SVG viewportu.')
  }

  const rSpan = domain.rMax - domain.rMin
  const zSpan = domain.zMax - domain.zMin

  if (rSpan <= 0 || zSpan <= 0) {
    throw new Error('Neplatný rozsah R–Z domény.')
  }

  const scale = Math.min(innerWidth / rSpan, innerHeight / zSpan)
  const plotWidth = rSpan * scale
  const plotHeight = zSpan * scale
  const offsetX = padding.left + (innerWidth - plotWidth) / 2
  const offsetY = padding.top + (innerHeight - plotHeight) / 2

  return {
    domain,
    viewport,
    scale,
    plotWidth,
    plotHeight,
    offsetX,
    offsetY,
    project: (r, z) => ({
      x: offsetX + (r - domain.rMin) * scale,
      y: offsetY + (domain.zMax - z) * scale,
    }),
  }
}

/** Ticks po zvoleném kroku; zaokrouhlení brání chybám typu 0.30000000004. */
export function createTicks(min: number, max: number, step: number): number[] {
  if (step <= 0 || max < min) {
    return []
  }

  const start = Math.ceil((min - 1e-9) / step) * step
  const end = Math.floor((max + 1e-9) / step) * step
  const count = Math.round((end - start) / step) + 1

  return Array.from({ length: Math.max(0, count) }, (_, index) =>
    Number((start + index * step).toFixed(6)),
  )
}
