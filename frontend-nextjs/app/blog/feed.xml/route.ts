import { ARTICLES } from '@/lib/blog-articles';

const BASE_URL = 'https://plotdetect.com.au';

export async function GET() {
  const sorted = [...ARTICLES].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );

  const items = sorted
    .map(
      (article) => `    <item>
      <title><![CDATA[${article.title}]]></title>
      <link>${BASE_URL}/blog/${article.slug}</link>
      <guid isPermaLink="true">${BASE_URL}/blog/${article.slug}</guid>
      <description><![CDATA[${article.description}]]></description>
      <category>${article.category}</category>
      <pubDate>${new Date(article.date).toUTCString()}</pubDate>
    </item>`
    )
    .join('\n');

  const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>PlotDetect Insights</title>
    <link>${BASE_URL}/blog</link>
    <description>Property intelligence, climate risk, and planning compliance research for NSW professionals.</description>
    <language>en-AU</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${BASE_URL}/blog/feed.xml" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>`;

  return new Response(rss, {
    headers: {
      'Content-Type': 'application/rss+xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600, s-maxage=3600',
    },
  });
}
