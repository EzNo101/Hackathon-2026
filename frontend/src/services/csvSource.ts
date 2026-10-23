import { findNearestIndex } from '../lib/timeseries'
import type {
  DischargeMeta,
  EquilibriumManifest,
  EquilibriumSample,
  EquilibriumSource,
  PhotoEntry,
  PhotoTruth,
  WallPoint,
} from '../types'

// Vite servíruje obsah public/ z kořene. BASE_URL drží správnou cestu
// i v případě, že by aplikace později běžela v podadresáři.
const DATA_ROOT = `${import.meta.env.BASE_URL}data`

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(
      `Nepodařilo se načíst ${url} (HTTP ${response.status}). ` +
        'Spustil jsi přípravu dat přes `npm run prepare-data`?',
    )
  }

  return (await response.json()) as T
}

interface PhotoLocation {
  discharge: number
  time: number
  mode: PhotoEntry['mode']
}

/**
 * Zdroj dat pro dataset a srovnání predikce se skutečností.
 *
 * Manifest se načte jednou, série jednotlivých výbojů lazy podle potřeby.
 * Celý 41MB CSV se tak do prohlížeče nikdy nedostane.
 */
export class CsvSource implements EquilibriumSource {
  private manifestPromise: Promise<EquilibriumManifest> | null = null
  private readonly seriesCache = new Map<number, Promise<EquilibriumSample[]>>()
  private readonly photoCache = new Map<number, Promise<PhotoEntry[]>>()
  private photoLookupPromise: Promise<Map<string, PhotoLocation>> | null = null
  private wallPromise: Promise<WallPoint[]> | null = null

  getManifest(): Promise<EquilibriumManifest> {
    this.manifestPromise ??= fetchJson<EquilibriumManifest>(
      `${DATA_ROOT}/manifest.json`,
    )

    return this.manifestPromise
  }

  async getDischarges(): Promise<DischargeMeta[]> {
    const manifest = await this.getManifest()
    return manifest.discharges
  }

  getSeries(discharge: number): Promise<EquilibriumSample[]> {
    const cached = this.seriesCache.get(discharge)

    if (cached) {
      return cached
    }

    const request = fetchJson<EquilibriumSample[]>(
      `${DATA_ROOT}/discharges/${discharge}.json`,
    )
    this.seriesCache.set(discharge, request)

    return request
  }

  /**
   * Index fotek výboje. Výboj bez fotek nemá soubor – server vrátí 404
   * nebo (ve vývojovém serveru) HTML, obojí znamená prázdné pole.
   */
  getPhotos(discharge: number): Promise<PhotoEntry[]> {
    const cached = this.photoCache.get(discharge)

    if (cached) {
      return cached
    }

    const request = fetch(`${DATA_ROOT}/photos/${discharge}.json`).then(
      async (response) => {
        if (response.status === 404) {
          return []
        }

        if (!response.ok) {
          throw new Error(
            `Nepodařilo se načíst index fotek výboje ${discharge} (HTTP ${response.status}).`,
          )
        }

        // Vite pro neexistující cestu vrací index.html se stavem 200, proto
        // kontrolujeme typ obsahu.
        const contentType = response.headers.get('content-type') ?? ''

        if (!contentType.includes('application/json')) {
          return []
        }

        return (await response.json()) as PhotoEntry[]
      },
    )
    this.photoCache.set(discharge, request)

    return request
  }

  /** Mapa název fotky → výboj, čas a režim. Sestaví se jednou ze všech indexů. */
  private getPhotoLookup(): Promise<Map<string, PhotoLocation>> {
    this.photoLookupPromise ??= this.getManifest()
      .then(async (manifest) => {
        const lists = await Promise.all(
          manifest.discharges.map(async (item) => ({
            discharge: item.id,
            photos: await this.getPhotos(item.id),
          })),
        )

        const lookup = new Map<string, PhotoLocation>()
        for (const { discharge, photos } of lists) {
          for (const photo of photos) {
            lookup.set(photo.filename, {
              discharge,
              time: photo.time,
              mode: photo.mode,
            })
          }
        }

        return lookup
      })
      .catch((error: unknown) => {
        // Chybu nezapamatujeme, další pokus proběhne znovu.
        this.photoLookupPromise = null
        throw error
      })

    return this.photoLookupPromise
  }

  /**
   * Skutečná hodnota pro fotku z datasetu: nejbližší vzorek dat k času fotky.
   * Vrací `null`, pokud fotka v datasetu není.
   */
  async findPhotoTruth(filename: string): Promise<PhotoTruth | null> {
    const lookup = await this.getPhotoLookup()
    const location = lookup.get(filename)

    if (!location) {
      return null
    }

    const series = await this.getSeries(location.discharge)

    if (series.length === 0) {
      return null
    }

    const sample = series[findNearestIndex(series, location.time)]

    return {
      filename,
      discharge: location.discharge,
      time: location.time,
      mode: location.mode,
      sample,
    }
  }

  /** Statická stěna komory; pokud chybí, skript zapíše prázdné pole. */
  getWall(): Promise<WallPoint[]> {
    this.wallPromise ??= fetchJson<WallPoint[]>(`${DATA_ROOT}/wall.json`)
    return this.wallPromise
  }
}

export const csvSource = new CsvSource()
