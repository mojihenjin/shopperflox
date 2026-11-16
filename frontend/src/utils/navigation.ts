/**
 * Sanitizes return-to / redirect URL to prevent Open Redirect vulnerabilities.
 * Must start strictly with a single '/' and not with '//', '/\\', or any scheme like 'http:', 'javascript:'.
 */
export function sanitizeReturnTo(target: string | null | undefined, fallback = '/'): string {
  if (!target || typeof target !== 'string') {
    return fallback;
  }

  const trimmed = target.trim();

  // Must begin with single '/'
  if (!trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.startsWith('/\\')) {
    return fallback;
  }

  // Prevent protocol tricks like '/http:', '/javascript:', etc.
  if (/^\/[a-zA-Z0-9+.-]+:/.test(trimmed)) {
    return fallback;
  }

  return trimmed;
}

/**
 * Extracts and sanitizes the target return-to URL from React Router location state or query parameter '?redirect=...'.
 */
export function getReturnTo(
  locationState: unknown,
  searchParams: URLSearchParams,
  fallback = '/'
): string {
  // Check location state
  const stateFrom = (locationState as { from?: { pathname?: string; search?: string } | string })?.from;

  if (typeof stateFrom === 'string') {
    return sanitizeReturnTo(stateFrom, fallback);
  }

  if (stateFrom && typeof stateFrom === 'object' && stateFrom.pathname) {
    const combined = `${stateFrom.pathname}${stateFrom.search || ''}`;
    return sanitizeReturnTo(combined, fallback);
  }

  // Check ?redirect= query param
  const redirectParam = searchParams.get('redirect');
  if (redirectParam) {
    return sanitizeReturnTo(redirectParam, fallback);
  }

  return fallback;
}
