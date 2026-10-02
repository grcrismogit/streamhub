import { useRef, useState, type FormEvent } from 'react'
import { api, ApiError, type Video } from '../api'
import { formatBytes } from '../lib/format'
import { useObjectUrl } from '../lib/hooks'
import { validateThumbnailFile, validateTitle, validateVideoFile } from '../lib/validation'
import { Alert, ProgressBar } from './ui'

export function VideoUploadForm({ onUploaded }: { onUploaded: (video: Video) => void }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [thumbFile, setThumbFile] = useState<File | null>(null)
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const formRef = useRef<HTMLFormElement>(null)

  const thumbPreview = useObjectUrl(thumbFile) // vista previa local de la miniatura

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    const problem = validateTitle(title) ?? validateVideoFile(videoFile) ?? validateThumbnailFile(thumbFile)
    if (problem) return setError(problem)

    const form = new FormData()
    form.append('title', title.trim())
    form.append('description', description.trim())
    form.append('video', videoFile!)
    form.append('thumbnail', thumbFile!)

    setProgress(0)
    try {
      const created = await api.createVideo(form, setProgress)
      onUploaded(created)
      setSuccess(`“${created.title}” se publicó correctamente.`)
      setTitle('')
      setDescription('')
      setVideoFile(null)
      setThumbFile(null)
      formRef.current?.reset()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo publicar el video')
    } finally {
      setProgress(null)
    }
  }

  const uploading = progress !== null

  return (
    <form ref={formRef} className="form upload-form" onSubmit={onSubmit}>
      {/* <fieldset> agrupa campos relacionados; en escritorio se ven en 2 columnas. */}
      <fieldset className="stack" disabled={uploading}>
        <legend className="sr-only">Información del video</legend>
        <label className="field">
          <span>Título *</span>
          <input
            type="text"
            required
            minLength={3}
            maxLength={120}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Descripción</span>
          <textarea rows={4} maxLength={5000} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
      </fieldset>

      <fieldset className="stack" disabled={uploading}>
        <legend className="sr-only">Archivos</legend>
        <label className="field file-field">
          <span>Video (MP4, máx. 100 MB) *</span>
          <input
            type="file"
            accept="video/mp4,.mp4"
            required
            onChange={(e) => setVideoFile(e.target.files?.[0] ?? null)}
          />
          {videoFile && (
            <small className="muted">
              {videoFile.name} · {formatBytes(videoFile.size)}
            </small>
          )}
        </label>
        <label className="field file-field">
          <span>Miniatura (JPG/PNG, máx. 5 MB) *</span>
          <input
            type="file"
            accept="image/jpeg,image/png,.jpg,.jpeg,.png"
            required
            onChange={(e) => setThumbFile(e.target.files?.[0] ?? null)}
          />
        </label>
        {thumbPreview && <img src={thumbPreview} alt="Vista previa de la miniatura" className="thumb-preview" />}
      </fieldset>

      {uploading && <ProgressBar value={progress} />}
      {error && <Alert>{error}</Alert>}
      {success && <Alert tone="success">{success}</Alert>}

      <footer className="row-end">
        <button type="submit" className="btn btn-primary" disabled={uploading}>
          {uploading ? (progress === 100 ? 'Procesando…' : 'Subiendo…') : 'Publicar video'}
        </button>
      </footer>
    </form>
  )
}
