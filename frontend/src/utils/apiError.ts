/**
 * Turn an axios rejection into a sentence worth showing a user.
 *
 * Three things the raw `err.response.data.detail` read misses:
 *
 *  - FastAPI validation errors (422) put an ARRAY of `{loc, msg, type}` in
 *    `detail`, not a string. Dropping that straight into a toast renders
 *    "[object Object]".
 *  - Responses with no `detail` at all (rate limiter, proxy errors, gateway
 *    timeouts) fall through to axios's own `err.message`, which reads
 *    "Request failed with status code 429".
 *  - A dropped connection has no `response` at all.
 */
export const apiError = (err: unknown, fallback = 'Something went wrong'): string => {
  const e = err as {
    response?: { status?: number; data?: { detail?: unknown } }
    message?: string
    code?: string
  }

  // No response: DNS failure, CORS block, server down, request aborted.
  if (!e?.response) {
    if (e?.code === 'ECONNABORTED') return 'The server took too long to respond.'
    return 'Could not reach the server. Check your connection and try again.'
  }

  const detail = e.response.data?.detail

  if (typeof detail === 'string' && detail.trim()) return detail

  // FastAPI/Pydantic validation payload.
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d: { msg?: string }) => (typeof d?.msg === 'string' ? d.msg : null))
      .filter((m): m is string => !!m)
    if (messages.length) return messages.join('. ')
  }

  // Statuses that commonly arrive with no usable body.
  switch (e.response.status) {
    case 401: return 'Your credentials were not accepted.'
    case 403: return 'You do not have permission to do that.'
    case 404: return 'That item no longer exists.'
    case 413: return 'That file is too large to upload.'
    case 423: return 'Account temporarily locked due to too many failed login attempts.'
    case 429: return 'Too many attempts. Wait a minute and try again.'
    case 503: return 'The server is undergoing maintenance. Try again shortly.'
  }

  return fallback
}
