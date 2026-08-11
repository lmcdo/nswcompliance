/**
 * Shared JSON-LD structured data components for SEO.
 * Each function returns a <script type="application/ld+json"> element.
 */

// Apex canibuildit — the domain this app's content actually serves on.
// plotdetect.com.au is the separate info-site project: JSON-LD URLs built on
// it 404'd, telling engines the structured data described dead pages
// (found 2026-07-23).
const BASE_URL = 'https://canibuildit.com.au';
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

/** Dataset schema for structured planning data pages. */
export function DatasetJsonLd({
  name,
  description,
  url,
  spatialCoverage,
  variableMeasured,
  license = 'https://creativecommons.org/licenses/by/4.0/',
}: {
  name: string;
  description: string;
  url: string;
  spatialCoverage: string;
  variableMeasured?: string[];
  license?: string;
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'Dataset',
          name,
          description,
          url: `${BASE_URL}${url}`,
          creator: PUBLISHER,
          license,
          spatialCoverage: {
            '@type': 'Place',
            name: spatialCoverage,
          },
          ...(variableMeasured && {
            variableMeasured: variableMeasured.map((v) => ({
              '@type': 'PropertyValue',
              name: v,
            })),
          }),
        }),
      }}
    />
  );
}

/** DefinedTerm schema for planning glossary entries. */
export function DefinedTermJsonLd({
  name,
  description,
  url,
  inDefinedTermSet,
}: {
  name: string;
  description: string;
  url: string;
  inDefinedTermSet?: string;
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'DefinedTerm',
          name,
          description,
          url: `${BASE_URL}${url}`,
          ...(inDefinedTermSet && {
            inDefinedTermSet: {
              '@type': 'DefinedTermSet',
              name: inDefinedTermSet,
              url: `${BASE_URL}/glossary`,
            },
          }),
        }),
      }}
    />
  );
}

/** HowTo schema for procedural/guide pages. */
export function HowToJsonLd({
  name,
  description,
  steps,
}: {
  name: string;
  description: string;
  steps: { name: string; text: string }[];
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'HowTo',
          name,
          description,
          step: steps.map((s, i) => ({
            '@type': 'HowToStep',
            position: i + 1,
            name: s.name,
            text: s.text,
          })),
        }),
      }}
    />
  );
}

/** DefinedTermSet schema for the glossary index page. */
export function DefinedTermSetJsonLd({
  name,
  description,
  url,
  termCount,
}: {
  name: string;
  description: string;
  url: string;
  termCount?: number;
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'DefinedTermSet',
          name,
          description,
          url: `${BASE_URL}${url}`,
          ...(termCount && { numberOfItems: termCount }),
        }),
      }}
    />
  );
}
