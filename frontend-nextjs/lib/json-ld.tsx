/**
 * Shared JSON-LD structured data components for SEO.
 * Each function returns a <script type="application/ld+json"> element.
 */

const BASE_URL = 'https://plotdetect.com.au';
const PUBLISHER = {
  '@type': 'Organization',
  name: 'PlotDetect',
  url: BASE_URL,
  logo: { '@type': 'ImageObject', url: `${BASE_URL}/plotdetect-logo.png` },
};

/** BlogPosting schema for individual blog articles. */
export function BlogPostingJsonLd({
  title,
  description,
  slug,
  date,
}: {
  title: string;
  description: string;
  slug: string;
  date: string;
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'BlogPosting',
          headline: title,
          description,
          url: `${BASE_URL}/blog/${slug}`,
          datePublished: date,
          dateModified: date,
          author: PUBLISHER,
          publisher: PUBLISHER,
          mainEntityOfPage: { '@type': 'WebPage', '@id': `${BASE_URL}/blog/${slug}` },
        }),
      }}
    />
  );
}

/** BreadcrumbList schema from an array of {name, href} items. */
export function BreadcrumbJsonLd({
  items,
}: {
  items: { name: string; href: string }[];
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'BreadcrumbList',
          itemListElement: items.map((item, i) => ({
            '@type': 'ListItem',
            position: i + 1,
            name: item.name,
            item: `${BASE_URL}${item.href}`,
          })),
        }),
      }}
    />
  );
}

/** Product schema for paid report pages. */
export function ProductJsonLd({
  name,
  description,
  url,
  price,
  priceCurrency = 'AUD',
}: {
  name: string;
  description: string;
  url: string;
  price: string;
  priceCurrency?: string;
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'Product',
          name,
          description,
          url: `${BASE_URL}${url}`,
          brand: PUBLISHER,
          offers: {
            '@type': 'Offer',
            price,
            priceCurrency,
            availability: 'https://schema.org/InStock',
            url: `${BASE_URL}${url}`,
          },
        }),
      }}
    />
  );
}

/** SoftwareApplication schema for free tool pages. */
export function SoftwareAppJsonLd({
  name,
  description,
  url,
}: {
  name: string;
  description: string;
  url: string;
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'SoftwareApplication',
          name,
          description,
          url: `${BASE_URL}${url}`,
          applicationCategory: 'UtilitiesApplication',
          operatingSystem: 'Web',
          offers: { '@type': 'Offer', price: '0', priceCurrency: 'AUD' },
          provider: PUBLISHER,
        }),
      }}
    />
  );
}
