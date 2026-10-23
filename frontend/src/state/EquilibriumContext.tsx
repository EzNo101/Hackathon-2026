import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { csvSource } from '../services/csvSource'
import type {
  DischargeMeta,
  EquilibriumManifest,
  EquilibriumSample,
  WallPoint,
} from '../types'

export type AppMode = 'dataset' | 'prediction'
export type DetailTab = 'overview' | 'detail'

// Výchozí výboj 92 pochází z ukázky v zadání – dobře se na něm demonstruje
// limiterová i divertorová konfigurace.
const DEFAULT_DISCHARGE = 92
// Do fáze 5 je výchozí divertorový snapshot, aby byly vidět X-bod a strike
// pointy. Limiterový snapshot má tyto hodnoty správně `null`.
const DEFAULT_TIME = 0.4613

interface EquilibriumContextValue {
  mode: AppMode
  setMode: (mode: AppMode) => void
  detailTab: DetailTab
  setDetailTab: (tab: DetailTab) => void

  manifest: EquilibriumManifest | null
  discharges: DischargeMeta[]
  selectedDischarge: number | null
  selectDischarge: (discharge: number) => void
  selectedTime: number
  setSelectedTime: (time: number) => void
  series: EquilibriumSample[]
  selectedSample: EquilibriumSample | null
  wall: WallPoint[]

  isLoading: boolean
  error: string | null
}

const EquilibriumContext = createContext<EquilibriumContextValue | null>(null)

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Nastala neznámá chyba.'
}

/**
 * Společný stav celé aplikace.
 *
 * Režim a úroveň detailu jsou čistě UI stav. Dataset se načítá lazy po
 * výbojích a `selectedSample` je vždy nejbližší řádek k `selectedTime`.
 * Predikce z backendu se do stejného stavu připojí ve fázi 7.
 */
export function EquilibriumProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<AppMode>('dataset')
  const [detailTab, setDetailTab] = useState<DetailTab>('overview')

  const [manifest, setManifest] = useState<EquilibriumManifest | null>(null)
  const [isManifestLoading, setIsManifestLoading] = useState(true)
  const [manifestError, setManifestError] = useState<string | null>(null)

  const [selectedDischarge, setSelectedDischarge] = useState<number | null>(null)
  const [selectedTime, setSelectedTime] = useState(DEFAULT_TIME)
  const [series, setSeries] = useState<EquilibriumSample[]>([])
  const [wall, setWall] = useState<WallPoint[]>([])
  const [isSeriesLoading, setIsSeriesLoading] = useState(false)
  const [seriesError, setSeriesError] = useState<string | null>(null)

  // Manifest stačí načíst jednou – obsahuje seznam výbojů i rozsahy časů.
  useEffect(() => {
    let active = true

    csvSource
      .getManifest()
      .then((loadedManifest) => {
        if (!active) {
          return
        }

        setManifest(loadedManifest)
        setSelectedDischarge((current) => {
          if (
            current !== null &&
            loadedManifest.discharges.some((item) => item.id === current)
          ) {
            return current
          }

          const hasDefault = loadedManifest.discharges.some(
            (item) => item.id === DEFAULT_DISCHARGE,
          )

          return hasDefault
            ? DEFAULT_DISCHARGE
            : (loadedManifest.discharges[0]?.id ?? null)
        })
      })
      .catch((error: unknown) => {
        if (active) {
          setManifestError(toErrorMessage(error))
        }
      })
      .finally(() => {
        if (active) {
          setIsManifestLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [])

  // Stěna komory je statická, stačí ji načíst jednou pro všechny výboje.
  useEffect(() => {
    let active = true

    csvSource
      .getWall()
      .then((loadedWall) => {
        if (active) {
          setWall(loadedWall)
        }
      })
      .catch(() => {
        // Bez stěny lze dál vykreslit alespoň obrys plazmatu.
        if (active) {
          setWall([])
        }
      })

    return () => {
      active = false
    }
  }, [])

  // Při změně výboje načteme jen jeho časovou řadu.
  useEffect(() => {
    if (selectedDischarge === null) {
      setSeries([])
      return
    }

    let active = true
    setIsSeriesLoading(true)
    setSeriesError(null)

    csvSource
      .getSeries(selectedDischarge)
      .then((loadedSeries) => {
        if (!active) {
          return
        }

        setSeries(loadedSeries)
        setSelectedTime((previous) => {
          if (loadedSeries.length === 0) {
            return DEFAULT_TIME
          }

          const start = loadedSeries[0].time
          const end = loadedSeries[loadedSeries.length - 1].time

          return Math.min(Math.max(previous, start), end)
        })
      })
      .catch((error: unknown) => {
        if (active) {
          setSeriesError(toErrorMessage(error))
          setSeries([])
        }
      })
      .finally(() => {
        if (active) {
          setIsSeriesLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [selectedDischarge])

  const selectDischarge = useCallback((discharge: number) => {
    setSelectedDischarge(discharge)
    setSelectedTime(DEFAULT_TIME)
  }, [])

  const selectTime = useCallback((time: number) => {
    setSelectedTime(time)
  }, [])

  // Vybraný čas nemusí přesně odpovídat řádku – použijeme nejbližší vzorek.
  // Vždy jde o jeden konkrétní snapshot, nikdy o kombinaci více řádků.
  const selectedSample = useMemo(() => {
    if (series.length === 0) {
      return null
    }

    let closest = series[0]
    let closestDistance = Math.abs(closest.time - selectedTime)

    for (let index = 1; index < series.length; index += 1) {
      const candidate = series[index]
      const distance = Math.abs(candidate.time - selectedTime)

      if (distance < closestDistance) {
        closest = candidate
        closestDistance = distance
      }
    }

    return closest
  }, [series, selectedTime])

  const discharges = manifest?.discharges ?? []

  const value = useMemo<EquilibriumContextValue>(
    () => ({
      mode,
      setMode,
      detailTab,
      setDetailTab,
      manifest,
      discharges,
      selectedDischarge,
      selectDischarge,
      selectedTime,
      setSelectedTime: selectTime,
      series,
      selectedSample,
      wall,
      isLoading: isManifestLoading || isSeriesLoading,
      error: manifestError ?? seriesError,
    }),
    [
      mode,
      detailTab,
      manifest,
      discharges,
      selectedDischarge,
      selectDischarge,
      selectTime,
      selectedTime,
      series,
      selectedSample,
      wall,
      isManifestLoading,
      isSeriesLoading,
      manifestError,
      seriesError,
    ],
  )

  return (
    <EquilibriumContext.Provider value={value}>
      {children}
    </EquilibriumContext.Provider>
  )
}

/** Přístup ke sdílenému stavu; mimo provider je to programátorská chyba. */
export function useEquilibrium(): EquilibriumContextValue {
  const context = useContext(EquilibriumContext)

  if (context === null) {
    throw new Error('useEquilibrium musí být použito uvnitř EquilibriumProvider.')
  }

  return context
}
