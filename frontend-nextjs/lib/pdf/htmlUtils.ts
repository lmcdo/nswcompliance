/**
 * Parse an HTML string that may contain an anchor tag or HTML entities.
 * Used to extract clean display text and optional URL from planning portal
 * layer values stored in the DB (which may contain raw HTML or entity-encoded HTML).
 */
export function parseHtmlLink(value: string): { text: string; url?: string } {
  const decoded = value
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
  const urlMatch = decoded.match(/href="([^"]+)"/);
  const textMatch = decoded.match(/>([^<]+)</);
  const text = textMatch?.[1]?.trim() || decoded.replace(/<[^>]*>/g, '').trim() || decoded;
  return { text, url: urlMatch?.[1] };
}

export function containsHtml(value: string): boolean {
  return value.includes('<') || value.includes('&lt;');
}
