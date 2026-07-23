/**
 * AI crawler identification from the User-Agent header.
 *
 * Why this exists: PostHog's browser SDK never sees AI crawlers — GPTBot,
 * ClaudeBot and PerplexityBot do not execute JavaScript, so client-side
 * analytics silently under-reports them to zero. The GEO plan's citation
 * measurement therefore needs a server-side signal: middleware matches the
 * User-Agent and fires an `ai_crawler_hit` event to PostHog over HTTP.
 *
 * The list mirrors the crawlers allowlisted in app/robots.ts, plus the
 * user-triggered fetcher agents the same vendors use for live retrieval
 * (those are the hits that indicate a page is being read to answer a user's
 * question — the signal the GEO plan measures).
 */

const AI_CRAWLER_PATTERNS: { name: string; pattern: RegExp }[] = [
  { name: 'GPTBot', pattern: /GPTBot/i },
  { name: 'OAI-SearchBot', pattern: /OAI-SearchBot/i },
  { name: 'ChatGPT-User', pattern: /ChatGPT-User/i },
  { name: 'ClaudeBot', pattern: /ClaudeBot/i },
  { name: 'Claude-User', pattern: /Claude-User/i },
  { name: 'Claude-SearchBot', pattern: /Claude-SearchBot/i },
  { name: 'PerplexityBot', pattern: /PerplexityBot/i },
  { name: 'Perplexity-User', pattern: /Perplexity-User/i },
  { name: 'Google-Extended', pattern: /Google-Extended/i },
  { name: 'GeminiBot', pattern: /Gemini-Deep-Research|GoogleAgent/i },
  { name: 'Bytespider', pattern: /Bytespider/i },
  { name: 'CCBot', pattern: /CCBot/i },
  { name: 'Meta-ExternalAgent', pattern: /meta-externalagent/i },
];

/**
 * Returns the crawler name for an AI crawler User-Agent, or null for
 * browsers, ordinary search bots, and missing headers.
 */
export function identifyAiCrawler(userAgent: string | null): string | null {
  if (!userAgent) return null;
  for (const { name, pattern } of AI_CRAWLER_PATTERNS) {
    if (pattern.test(userAgent)) return name;
  }
  return null;
}
