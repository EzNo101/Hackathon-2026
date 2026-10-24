import { createReadStream, existsSync } from 'node:fs'
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { createInterface } from 'node:readline'
import { fileURLToPath } from 'node:url'

// ---------------------------------------------------------------------------
// Cesty
// Skript leží ve frontend/scripts, projektový kořen je tedy o úroveň výš.
// Vstupy lze přepsat proměnnými prostředí DATA_CSV a WALL_CSV.
// ---------------------------------------------------------------------------
const projectRoot = fileURLToPath(new URL('..', import.meta.url))
const inputCsvPath = process.env.DATA_CSV
  ? path.resolve(process.env.DATA_CSV)
  : path.resolve(projectRoot, '../../uloha_1-magneticka_data/equil_data.csv')
const wallCsvPath = process.env.WALL_CSV
  ? path.resolve(process.env.WALL_CSV)
  : path.resolve(projectRoot, 'COMPASS/COMPASS_stena.csv')
const photoCsvPath = process.env.PHOTO_CSV
  ? path.resolve(process.env.PHOTO_CSV)
  : path.resolve(projectRoot, '../../uloha_1-photron/camera_data.csv')
const columnsPath = path.resolve(projectRoot, 'src/data/columns.json')
const outputRoot = path.resolve(projectRoot, 'public/data')
const dischargeOutputDir = path.resolve(outputRoot, 'discharges')
const photoOutputDir = path.resolve(outputRoot, 'photos')
// Režim plazmatu z camera_data.csv (L-mode, H-mode, ELM).
const PHOTO_MODES = ['L-mode', 'H-mode', 'ELM']

// ---------------------------------------------------------------------------
// Pomocné funkce pro CSV
// Data neobsahují uvozovky, ale jednoduchý parser je zvládne také – kdyby
// někdo později exportoval CSV jiným nástrojem, skript nespadne.
// ---------------------------------------------------------------------------
function stripBom(value) {
  return value.replace(/^\uFEFF/, '')
}

function parseCsvLine(line) {
  const cells = []
  let cell = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i]

    if (inQuotes) {
      if (char === '"') {
        if (line[i + 1] === '"') {
          cell += '"'
          i += 1
        } else {
          inQuotes = false
        }
      } else {
        cell += char
      }
      continue
    }

    if (char === '"') {
      inQuotes = true
    } else if (char === ',') {
      cells.push(cell)
      cell = ''
    } else {
      cell += char
    }
  }

  cells.push(cell)
  return cells
}

function parseNumber(raw, column, lineNumber) {
  if (raw === '') {
    return null
  }

  const value = Number(raw)

  if (!Number.isFinite(value)) {
    throw new Error(
      `Řádek ${lineNumber}: sloupec "${column}" obsahuje nečíselnou hodnotu "${raw}".`,
    )
  }

  return value
}

function parseBoolean(raw, column, lineNumber) {
  if (raw === 'True' || raw === 'true' || raw === '1') {
    return true
  }

  if (raw === 'False' || raw === 'false' || raw === '0') {
    return false
  }

  throw new Error(
    `Řádek ${lineNumber}: sloupec "${column}" obsahuje neplatnou logickou hodnotu "${raw}".`,
  )
}

function parseDischarge(raw, lineNumber) {
  const value = Number.parseInt(raw, 10)

  if (!Number.isInteger(value) || value < 0) {
    throw new Error(
      `Řádek ${lineNumber}: neplatné číslo výboje "${raw}".`,
    )
  }

  return value
}

// ---------------------------------------------------------------------------
// Načtení seznamu sloupců
// ---------------------------------------------------------------------------
async function loadColumns() {
  const raw = await readFile(columnsPath, 'utf8')
  const parsed = JSON.parse(raw)

  if (!Array.isArray(parsed.main) || !Array.isArray(parsed.supplementary)) {
    throw new Error('columns.json musí obsahovat pole "main" a "supplementary".')
  }

  const main = parsed.main
  const supplementary = parsed.supplementary
  const all = [...main, ...supplementary]

  if (new Set(all).size !== all.length) {
    throw new Error('columns.json obsahuje duplicitní název sloupce.')
  }

  return { main, supplementary, all }
}

// ---------------------------------------------------------------------------
// Zpracování equil_data.csv
// ---------------------------------------------------------------------------
async function prepareEquilibriumData(columns) {
  if (!existsSync(inputCsvPath)) {
    throw new Error(
      `Vstupní CSV nebylo nalezeno: ${inputCsvPath}\n` +
        'Cestu lze předat proměnnou prostředí DATA_CSV.',
    )
  }

  const outputColumns = columns.all
  const requiredColumns = ['time', 'discharge', ...outputColumns]
  const rowsByDischarge = new Map()
  let header = null
  let columnIndex = null
  let lineNumber = 0

  const lineReader = createInterface({
    input: createReadStream(inputCsvPath, 'utf8'),
    crlfDelay: Infinity,
  })

  for await (const rawLine of lineReader) {
    lineNumber += 1
    const line = stripBom(rawLine)

    if (lineNumber === 1) {
      header = parseCsvLine(line).map((name) => name.trim())
      columnIndex = new Map(header.map((name, index) => [name, index]))

      const missing = requiredColumns.filter((name) => !columnIndex.has(name))

      if (missing.length > 0) {
        throw new Error(
          `V CSV chybí povinné sloupce: ${missing.join(', ')}`,
        )
      }

      continue
    }

    if (line.trim() === '') {
      continue
    }

    const cells = parseCsvLine(line)
    const cell = (name) => cells[columnIndex.get(name)] ?? ''

    const time = parseNumber(cell('time'), 'time', lineNumber)
    const discharge = parseDischarge(cell('discharge'), lineNumber)

    if (time === null) {
      throw new Error(`Řádek ${lineNumber}: chybí čas (time).`)
    }

    const row = { time, discharge }

    for (const column of outputColumns) {
      row[column] =
        column === 'is_limited'
          ? parseBoolean(cell(column), column, lineNumber)
          : parseNumber(cell(column), column, lineNumber)
    }

    const dischargeRows = rowsByDischarge.get(discharge)

    if (dischargeRows) {
      dischargeRows.push(row)
    } else {
      rowsByDischarge.set(discharge, [row])
    }
  }

  if (header === null) {
    throw new Error('Vstupní CSV je prázdné.')
  }

  // Stálé pořadí výbojů i časových řad – usnadní testování a diffy.
  const discharges = [...rowsByDischarge.entries()]
    .sort(([left], [right]) => left - right)
    .map(([id, rows]) => {
      rows.sort((left, right) => left.time - right.time)

      const timeStart = Math.min(...rows.map((row) => row.time))
      const timeEnd = Math.max(...rows.map((row) => row.time))
      const limiterRowCount = rows.filter((row) => row.is_limited).length

      return { id, rows, timeStart, timeEnd, limiterRowCount }
    })

  await rm(dischargeOutputDir, { recursive: true, force: true })
  await mkdir(dischargeOutputDir, { recursive: true })

  await Promise.all(
    discharges.map(({ id, rows }) =>
      writeFile(
        path.resolve(dischargeOutputDir, `${id}.json`),
        JSON.stringify(rows),
        'utf8',
      ),
    ),
  )

  const manifest = {
    version: 1,
    generatedAt: new Date().toISOString(),
    source: path.basename(inputCsvPath),
    rowCount: discharges.reduce((sum, item) => sum + item.rows.length, 0),
    columns: {
      main: columns.main,
      supplementary: columns.supplementary,
    },
    discharges: discharges.map(({ id, rows, timeStart, timeEnd, limiterRowCount }) => ({
      id,
      rowCount: rows.length,
      timeStart,
      timeEnd,
      limiterRowCount,
    })),
  }

  await mkdir(outputRoot, { recursive: true })
  await writeFile(
    path.resolve(outputRoot, 'manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
    'utf8',
  )

  return manifest
}

// ---------------------------------------------------------------------------
// Index fotek z kamery
// Samotné JPEG se nekopírují (složka má přes 1 GB) – frontend je čte
// z původní složky přes vývojový server. Zde vzniká jen malý index
// { filename, time } na výboj, seřazený podle času.
// ---------------------------------------------------------------------------
async function preparePhotos() {
  if (!existsSync(photoCsvPath)) {
    console.warn(
      `Upozornění: index fotek nebyl nalezen (${photoCsvPath}). ` +
        'Fotky nebudou dostupné.',
    )
    await rm(photoOutputDir, { recursive: true, force: true })
    return 0
  }

  const photosByDischarge = new Map()
  let columnIndex = null
  let lineNumber = 0
  let photoCount = 0

  const lineReader = createInterface({
    input: createReadStream(photoCsvPath, 'utf8'),
    crlfDelay: Infinity,
  })

  for await (const rawLine of lineReader) {
    lineNumber += 1
    const line = stripBom(rawLine)

    if (lineNumber === 1) {
      const header = parseCsvLine(line).map((name) => name.trim())
      columnIndex = new Map(header.map((name, index) => [name, index]))

      const missing = ['filename', 'time', 'discharge', 'mode'].filter(
        (name) => !columnIndex.has(name),
      )

      if (missing.length > 0) {
        throw new Error(
          `V camera_data.csv chybí povinné sloupce: ${missing.join(', ')}`,
        )
      }

      continue
    }

    if (line.trim() === '') {
      continue
    }

    const cells = parseCsvLine(line)
    const cell = (name) => cells[columnIndex.get(name)] ?? ''

    const filename = cell('filename').trim()
    const time = parseNumber(cell('time'), 'time', lineNumber)
    const discharge = parseDischarge(cell('discharge'), lineNumber)
    const mode = cell('mode').trim()

    if (filename === '' || time === null) {
      throw new Error(`Řádek ${lineNumber}: chybí název fotky nebo čas.`)
    }

    if (!PHOTO_MODES.includes(mode)) {
      throw new Error(
        `Řádek ${lineNumber}: neznámý režim "${mode}" (očekává se ${PHOTO_MODES.join(', ')}).`,
      )
    }

    const entry = { filename, time, mode }
    const list = photosByDischarge.get(discharge)

    if (list) {
      list.push(entry)
    } else {
      photosByDischarge.set(discharge, [entry])
    }

    photoCount += 1
  }

  await rm(photoOutputDir, { recursive: true, force: true })
  await mkdir(photoOutputDir, { recursive: true })

  await Promise.all(
    [...photosByDischarge.entries()].map(([id, photos]) => {
      photos.sort((left, right) => left.time - right.time)

      return writeFile(
        path.resolve(photoOutputDir, `${id}.json`),
        JSON.stringify(photos),
        'utf8',
      )
    }),
  )

  return photoCount
}

// ---------------------------------------------------------------------------
// Kontura stěny komory
// ---------------------------------------------------------------------------
async function prepareWall() {
  const emptyWall = []

  if (!existsSync(wallCsvPath)) {
    console.warn(
      `Upozornění: stěna komory nebyla nalezena (${wallCsvPath}). ` +
        'Zapisuji prázdné pole.',
    )
    await writeFile(
      path.resolve(outputRoot, 'wall.json'),
      `${JSON.stringify(emptyWall)}\n`,
      'utf8',
    )
    return emptyWall
  }

  const content = await readFile(wallCsvPath, 'utf8')
  const lines = content.split(/\r?\n/).filter((line) => line.trim() !== '')

  if (lines.length < 2) {
    throw new Error(`Soubor se stěnou je prázdný: ${wallCsvPath}`)
  }

  const header = parseCsvLine(stripBom(lines[0])).map((name) => name.trim())
  const rIndex = header.indexOf('R')
  const zIndex = header.indexOf('Z')

  if (rIndex === -1 || zIndex === -1) {
    throw new Error('Soubor se stěnou musí mít sloupce R a Z.')
  }

  const points = lines.slice(1).map((line, index) => {
    const cells = parseCsvLine(line)
    const lineNumber = index + 2
    const R = parseNumber(cells[rIndex] ?? '', 'R', lineNumber)
    const Z = parseNumber(cells[zIndex] ?? '', 'Z', lineNumber)

    if (R === null || Z === null) {
      throw new Error(`Řádek ${lineNumber}: stěna obsahuje prázdnou souřadnici.`)
    }

    return { R, Z }
  })

  await writeFile(
    path.resolve(outputRoot, 'wall.json'),
    `${JSON.stringify(points)}\n`,
    'utf8',
  )

  return points
}

// ---------------------------------------------------------------------------
// Spuštění
// ---------------------------------------------------------------------------
async function main() {
  const columns = await loadColumns()
  const manifest = await prepareEquilibriumData(columns)
  const wall = await prepareWall()
  const photoCount = await preparePhotos()

  console.log('Příprava dat hotová.')
  console.log(`  výbojů:  ${manifest.discharges.length}`)
  console.log(`  řádků:   ${manifest.rowCount}`)
  console.log(`  stěna:   ${wall.length} bodů`)
  console.log(`  fotek:   ${photoCount}`)
  console.log(`  výstup:  ${outputRoot}`)
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})
