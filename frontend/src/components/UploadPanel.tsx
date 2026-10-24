import { useRef, useState, type DragEvent } from 'react'
import type { PredictionState } from '../state/usePrediction'

const ACCEPTED_TYPES = ['image/jpeg', 'image/png']

interface UploadPanelProps {
  state: PredictionState
  onFile: (file: File) => void
  onReset: () => void
}

/** Nahrání jedné fotky: drag & drop nebo výběr souboru, náhled a stav. */
export function UploadPanel({ state, onFile, onReset }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  function handleFile(file: File | undefined) {
    if (!file) {
      return
    }

    if (!ACCEPTED_TYPES.includes(file.type)) {
      setLocalError('Nahrej soubor ve formátu JPEG nebo PNG.')
      return
    }

    setLocalError(null)
    onFile(file)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    handleFile(event.dataTransfer.files[0])
  }

  const isLoading = state.status === 'loading'
  const errorText = localError ?? (state.status === 'error' ? state.error : null)

  return (
    <section className="upload-panel" aria-label="Nahrání fotky">
      <div
        className={`dropzone${isDragging ? ' is-dragging' : ''}${isLoading ? ' is-busy' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(',')}
          className="dropzone-input"
          aria-label="Vybrat fotku z kamery"
          disabled={isLoading}
          onChange={(event) => {
            handleFile(event.target.files?.[0])
            // Stejný soubor je možné vybrat znovu.
            event.target.value = ''
          }}
        />
        <p className="dropzone-title">Přetáhni sem fotku z kamery</p>
        <p className="dropzone-hint">JPEG nebo PNG, jeden snímek</p>
        <div className="dropzone-actions">
          <button
            type="button"
            className="control-button"
            onClick={() => inputRef.current?.click()}
            disabled={isLoading}
          >
            Vybrat soubor
          </button>
          {state.file ? (
            <button type="button" className="control-button" onClick={onReset} disabled={isLoading}>
              Zrušit
            </button>
          ) : null}
        </div>
      </div>

      {state.previewUrl ? (
        <div className="upload-preview">
          <div className="photo-frame">
            <img src={state.previewUrl} alt={`Náhled ${state.file?.name ?? 'fotky'}`} />
          </div>
          <div className="photo-meta">
            <span className="control-label">Nahraná fotka</span>
            <span className="photo-filename">{state.file?.name}</span>
            {isLoading ? (
              <span className="upload-status" role="status">
                <span className="spinner" aria-hidden="true" /> Model počítá predikci…
              </span>
            ) : null}
            {state.status === 'success' && state.result ? (
              <span className="upload-status is-success" role="status">
                Predikce hotova · {state.result.latencyMs.toFixed(1)} ms · {state.result.device}
              </span>
            ) : null}
          </div>
        </div>
      ) : null}

      {errorText ? (
        <div className="state-box state-box-error upload-error" role="alert">
          <div>
            <h3>Predikce se nepodařila</h3>
            <p>{errorText}</p>
            {state.file && state.status === 'error' ? (
              <button
                type="button"
                className="control-button"
                onClick={() => onFile(state.file as File)}
              >
                Zkusit znovu
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  )
}
