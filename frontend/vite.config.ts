import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// Fotky z kamery jsou v původní složce (přes 1 GB), proto je nekopírujeme
// do public/. Lze přepsat proměnnou PHOTO_DIR.
const photoDir = process.env.PHOTO_DIR
  ? path.resolve(process.env.PHOTO_DIR)
  : fileURLToPath(new URL('../../uloha_1-photron/jpeg', import.meta.url))

const PHOTO_NAME = /^[\w.-]+\.jpe?g$/i

/**
 * Vývojový endpoint `/photos/<soubor>`.
 * Jméno souboru se ořízne na basename a ověří regulárním výrazem, takže
 * nelze číst mimo složku s fotkami. Při buildu plugin neběží.
 */
function servePhotos(): Plugin {
  return {
    name: 'serve-photos',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/photos', async (req, res) => {
        const rawPath = (req.url ?? '/').split('?')[0]
        const name = path.basename(decodeURIComponent(rawPath))

        if (!PHOTO_NAME.test(name)) {
          res.statusCode = 404
          res.end()
          return
        }

        const filePath = path.join(photoDir, name)

        try {
          const info = await stat(filePath)

          if (!info.isFile()) {
            res.statusCode = 404
            res.end()
            return
          }

          res.setHeader('Content-Type', 'image/jpeg')
          res.setHeader('Content-Length', info.size)
          res.setHeader('Cache-Control', 'max-age=3600')
          createReadStream(filePath).pipe(res)
        } catch {
          res.statusCode = 404
          res.end()
        }
      })
    },
  }
}

// Základní konfigurace Vite. Backend (FastAPI) se připojí až ve fázi 7,
// proto zde zatím není žádný proxy.
export default defineConfig({
  plugins: [react(), servePhotos()],
  server: {
    port: 5173,
    strictPort: true,
  },
})
