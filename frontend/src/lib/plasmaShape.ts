import type { EquilibriumOutputs } from '../types'

export interface ShapePoint {
  r: number
  z: number
}

const SAMPLES_PER_SEGMENT = 48

/**
 * Uzavřená Catmull-Rom křivka procházející zadanými body.
 *
 * Pro obrys plazmatu používáme krajní body jednoho snapshotu: horní,
 * vnější, dolní (X-bod) a vnitřní. Pomocný bod na vnitřní straně drží
 * spodní část obrysu více svislou. Křivka mezi nimi plynule interpoluje,
 * takže výsledek připomíná D-tvar bez potřeby dalších dat.
 */
function catmullRomClosed(points: ShapePoint[]): ShapePoint[] {
  const count = points.length
  const result: ShapePoint[] = []

  for (let index = 0; index < count; index += 1) {
    const p0 = points[(index - 1 + count) % count]
    const p1 = points[index]
    const p2 = points[(index + 1) % count]
    const p3 = points[(index + 2) % count]

    for (let step = 0; step < SAMPLES_PER_SEGMENT; step += 1) {
      const t = step / SAMPLES_PER_SEGMENT
      const t2 = t * t
      const t3 = t2 * t

      const interpolate = (a: number, b: number, c: number, d: number) =>
        0.5 *
        (2 * b +
          (-a + c) * t +
          (2 * a - 5 * b + 4 * c - d) * t2 +
          (-a + 3 * b - 3 * c + d) * t3)

      result.push({
        r: interpolate(p0.r, p1.r, p2.r, p3.r),
        z: interpolate(p0.z, p1.z, p2.z, p3.z),
      })
    }
  }

  // Uzavření cesty na první bod; SVG si tak poradí se zaobleným spojem.
  if (result.length > 0) {
    result.push(result[0])
  }

  return result
}

/**
 * Sestaví přibližný obrys plazmatu z jednoho konkrétního snapshotu.
 * Nepoužívá průměry ani hodnoty z jiných výbojů.
 */
export function buildPlasmaBoundary(
  sample: EquilibriumOutputs,
): ShapePoint[] | null {
  // Divertor má jako spodní bod X-bod; limiter použije běžný spodní bod.
  const bottomR = sample.R_x_point ?? sample.R_bottom
  const bottomZ = sample.Z_x_point ?? sample.Z_bottom

  // Vnitřní kraj je vždy R_inner/Z_inner. Bod dotyku s limiterem (R_limiter)
  // leží na vnější straně a nesmí se použít jako vnitřní kotva – jinak se
  // obrys přeloží a vznikne falešný klín. Bod dotyku se kreslí zvlášť.
  const innerR = sample.R_inner
  const innerZ = sample.Z_inner

  const required = [
    sample.R_top,
    sample.Z_top,
    sample.R_outer,
    sample.Z_outer,
    bottomR,
    bottomZ,
    innerR,
    innerZ,
  ]

  if (required.some((value) => value === null)) {
    return null
  }

  const resolvedBottomZ = bottomZ as number
  const resolvedInnerR = innerR as number
  const resolvedInnerZ = innerZ as number

  // Pojistka: obrys musí obepínat magnetickou osu. Pokud kotvy neleží
  // v očekávaném pořadí (vnitřní < osa < vnější, dolní < osa < horní),
  // obrys by se zprohýbal nebo protínal – raději ho nekreslíme.
  const axisR = sample.R_mag_axis
  const axisZ = sample.Z_mag_axis

  if (
    axisR === null ||
    axisZ === null ||
    !(resolvedInnerR < axisR && axisR < (sample.R_outer as number)) ||
    !(resolvedBottomZ < axisZ && axisZ < (sample.Z_top as number))
  ) {
    return null
  }

  const anchors: ShapePoint[] = [
    { r: sample.R_top as number, z: sample.Z_top as number },
    { r: sample.R_outer as number, z: sample.Z_outer as number },
    { r: bottomR as number, z: resolvedBottomZ },
    // Pomocný bod zpevní spodní část vnitřní strany, aby obrys nebyl oválný.
    { r: resolvedInnerR, z: (resolvedInnerZ + resolvedBottomZ) / 2 },
    { r: resolvedInnerR, z: resolvedInnerZ },
  ]

  return catmullRomClosed(anchors)
}
