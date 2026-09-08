/**
 * Client-side checks run before a file leaves the browser.
 *
 * The server validates everything here again — this is not a security boundary
 * and must never be treated as one. It exists because the school runs on phone
 * cameras and school wifi: without it a student spends thirty seconds pushing a
 * 40 MB photo up a slow link only to be told "File too large" by the server,
 * and the natural response to that is to try the same file again.
 *
 * Kept deliberately in step with `backend/utils/uploads.py`: same size cap,
 * same accepted formats. When one moves, move the other.
 */

/** Matches `MAX_SIZE_BYTES` in `backend/utils/uploads.py`. */
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

/**
 * Extensions the backend accepts for a proof or homework image.
 *
 * HEIC/HEIF are here because that is what an iPhone produces by default; the
 * backend transcodes them to WebP on arrival like every other format.
 */
export const ACCEPTED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'heic', 'heif'] as const

/**
 * The `accept` attribute for a file input.
 *
 * Extensions are listed alongside the MIME types on purpose: Safari reports an
 * empty `type` for HEIC files it has not yet decoded, so a MIME-only accept
 * list greys out exactly the photos we most want to receive.
 */
export const IMAGE_ACCEPT_ATTR =
  'image/jpeg,image/png,image/webp,image/heic,image/heif,.jpg,.jpeg,.png,.webp,.heic,.heif'

const humanSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const extensionOf = (name: string): string => {
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot + 1).toLowerCase()
}

/**
 * Returns a human-readable reason the file cannot be uploaded, or `null` when
 * it looks acceptable.
 *
 * The extension — not `file.type` — is authoritative, for the Safari reason
 * above and because the backend keys its own validation off the extension too.
 */
export const validateImageUpload = (
  file: File,
  { maxBytes = MAX_UPLOAD_BYTES }: { maxBytes?: number } = {}
): string | null => {
  if (file.size === 0) {
    return 'That file is empty. Pick the photo again — some phone galleries hand over a placeholder if the image is still syncing from the cloud.'
  }

  const ext = extensionOf(file.name)
  if (!ACCEPTED_IMAGE_EXTENSIONS.includes(ext as (typeof ACCEPTED_IMAGE_EXTENSIONS)[number])) {
    return `“${file.name}” is not an image we can accept. Use a JPG, PNG, WebP or HEIC photo.`
  }

  if (file.size > maxBytes) {
    return `That photo is ${humanSize(file.size)}; the limit is ${humanSize(maxBytes)}. Take the shot at a lower resolution, or crop it before uploading.`
  }

  return null
}
