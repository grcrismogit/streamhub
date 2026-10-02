import { useState, type FormEvent } from 'react'
import { api, ApiError, type Video } from '../api'
import { useObjectUrl } from '../lib/hooks'
import { validateThumbnailFile, validateTitle } from '../lib/validation'
import { Alert, ProgressBar } from './ui'

export function EditVideoForm({
  video,
  onSaved,
  onCancel,
}: {
  video: Video
  onSaved: (video: Video) => void
  onCancel: () => void
}) {
  const [title, setTitle] = useState(video.title)
  const [description, setDescription] = useState(video.description)
  const [thumbFile, setThumbFile] = useState<File | null>(null)
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const preview = useObjectUrl(thumbFile) // vista previa local de la miniatura

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const problem = validateTitle(title) ?? validateThumbnailFile(thumbFile, false)
    if (problem) return setError(problem)

    const form = new FormData()
    form.append('title', title.trim())
    form.append('description', description.trim())
    if (thumbFile) form.append('thumbnail', thumbFile)

    setError(null)
    setProgress(0)
    try {
      onSaved(await api.updateVideo(video.id, form, setProgress))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo actualizar el video')
    } finally {
      setProgress(null)
    }
  }

  const saving = progress !== null

  return (
    <form className="form" onSubmit={onSubmit}>
      <label className="field">
        <span>Título</span>
        <input
          type="text"
          required
          minLength={3}
          maxLength={120}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          autoFocus
        />
      </label>
      <label className="field">
        <span>Descripción</span>
        <textarea rows={4} maxLength={5000} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <fieldset className="edit-thumb">
        <legend className="sr-only">Miniatura</legend>
        <img src={preview ?? video.thumbnail_url} alt={preview ? 'Nueva miniatura' : 'Miniatura actual'} />
        <label className="field file-field">
          <span>Reemplazar miniatura (opcional)</span>
          <input
            type="file"
            accept="image/jpeg,image/png,.jpg,.jpeg,.png"
            onChange={(e) => setThumbFile(e.target.files?.[0] ?? null)}
          />
        </label>
      </fieldset>

      {saving && <ProgressBar value={progress} />}
      {error && <Alert>{error}</Alert>}

      <footer className="row-end">
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={saving}>
          Cancelar
        </button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </footer>
    </form>
  )
}
