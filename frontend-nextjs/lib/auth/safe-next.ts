// prior-art-checked: grep for safeNext / isSafeRedirect / safe-redirect in lib and app found nothing;
// the callback used `next` unchecked.
/**
 * Where to send someone after sign-in: a path on THIS site only.
 *
 * `next` arrives from the address bar, so it is untrusted. "//evil.example" and "https://..." are
 * refused (they leave the site); anything that is not a plain "/path" falls back to /reports.
 */
export function safeNext(next: string | null | undefined): string {
  if (typeof next !== 'string') return '/reports';
  if (!next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) return '/reports';
  return next;
}
