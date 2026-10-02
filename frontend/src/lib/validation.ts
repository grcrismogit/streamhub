// Validaciones del lado del cliente (la API vuelve a validar todo).
import { formatBytes } from './format'

export const MAX_VIDEO_BYTES = 100 * 1024 * 1024
export const MAX_THUMB_BYTES = 5 * 1024 * 1024

export function validateVideoFile(file: File | null): string | null {
  if (!file) return 'Selecciona un archivo de video.'
  if (!file.name.toLowerCase().endsWith('.mp4') || (file.type && file.type !== 'video/mp4'))
    return 'El video debe estar en formato MP4.'
  if (file.size > MAX_VIDEO_BYTES)
    return `El video pesa ${formatBytes(file.size)}; el máximo es ${formatBytes(MAX_VIDEO_BYTES)}.`
  return null
}

export function validateThumbnailFile(file: File | null, required = true): string | null {
  if (!file) return required ? 'Selecciona una miniatura.' : null
  if (!/\.(jpe?g|png)$/i.test(file.name)) return 'La miniatura debe ser JPG, JPEG o PNG.'
  if (file.size > MAX_THUMB_BYTES)
    return `La miniatura pesa ${formatBytes(file.size)}; el máximo es ${formatBytes(MAX_THUMB_BYTES)}.`
  return null
}

export function validateTitle(title: string): string | null {
  const t = title.trim()
  if (t.length < 3) return 'El título debe tener al menos 3 caracteres.'
  if (t.length > 120) return 'El título no puede superar 120 caracteres.'
  return null
}
