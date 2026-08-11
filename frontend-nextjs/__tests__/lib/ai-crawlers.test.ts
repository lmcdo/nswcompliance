import { identifyAiCrawler } from '@/lib/ai-crawlers';

describe('identifyAiCrawler', () => {
  it('identifies AI crawler user agents by name', () => {
    const cases: [string, string][] = [
      [
        'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)',
        'GPTBot',
      ],
      [
        'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot',
        'ChatGPT-User',
      ],
      [
        'Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)',
        'ClaudeBot',
      ],
      [
        'Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)',
        'PerplexityBot',
      ],
      [
        'Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)',
        'OAI-SearchBot',
      ],
      ['Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)', 'Bytespider'],
      ['CCBot/2.0 (https://commoncrawl.org/faq/)', 'CCBot'],
    ];
    for (const [ua, expected] of cases) {
      expect(identifyAiCrawler(ua)).toBe(expected);
    }
  });

  it('returns null for browsers and ordinary search bots', () => {
    const nonAi = [
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
      'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
      'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
      'curl/8.4.0',
    ];
    for (const ua of nonAi) {
      expect(identifyAiCrawler(ua)).toBeNull();
    }
  });

  it('returns null for a missing header', () => {
    expect(identifyAiCrawler(null)).toBeNull();
    expect(identifyAiCrawler('')).toBeNull();
  });
});
