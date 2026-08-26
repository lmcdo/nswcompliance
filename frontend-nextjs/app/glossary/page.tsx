import type { Metadata } from 'next';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { DefinedTermSetJsonLd } from '@/lib/json-ld';
import { query } from '@/lib/database/pool-manager';
import { GlossaryClient } from './GlossaryClient';

export const revalidate = 86400; // ISR: revalidate daily

export const metadata: Metadata = {
  title: 'NSW Planning Glossary — 465+ Regulatory Definitions',
  description:
    'Definitions of NSW planning terms from LEPs, DCPs, and SEPPs. FSR, GFA, CDC, setbacks, landscaped area, site coverage, secondary dwelling, and more — with source citations.',
  openGraph: {
    title: 'NSW Planning Glossary — Regulatory Definitions',
    description:
      'Definitions of NSW planning terms from LEPs, DCPs, and SEPPs with source citations.',
    url: 'https://verify.plotdetect.com.au/glossary',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
};

interface DefinitionRow {
  id: number;
  term: string;
  definition_text: string;
  definition_summary: string | null;
  source_document: string;
  source_clause: string | null;
  legislation_type: string;
  domain_tags: string[] | null;
}

async function fetchDefinitions(): Promise<DefinitionRow[]> {
  try {
    const result = await query(
      `SELECT id, term, definition_text, definition_summary,
              source_document, source_clause, legislation_type, domain_tags
       FROM regulatory_definitions
       ORDER BY term_normalized ASC`,
      []
    );
    return result.rows as DefinitionRow[];
  } catch (error) {
    console.error('[Glossary] Failed to fetch definitions:', error);
    return [];
  }
}

export default async function GlossaryPage() {
  const definitions = await fetchDefinitions();

  // Collect unique domain tags for the filter
  const allTags = new Set<string>();
  for (const d of definitions) {
    if (d.domain_tags) {
      for (const tag of d.domain_tags) {
        allTags.add(tag);
      }
    }
  }
  const sortedTags = Array.from(allTags).sort();

  // Collect unique legislation types
  const legislationTypes = Array.from(
    new Set(definitions.map((d) => d.legislation_type))
  ).sort();

  // Collect unique first letters for alphabet nav
  const letters = Array.from(
    new Set(definitions.map((d) => d.term[0]?.toUpperCase()).filter(Boolean))
  ).sort();

  return (
    <main className="min-h-screen bg-white">
      <SiteNav />
      <DefinedTermSetJsonLd
        name="NSW Planning Glossary"
        description="Definitions of NSW planning and development terms extracted from Local Environmental Plans (LEPs), Development Control Plans (DCPs), and State Environmental Planning Policies (SEPPs)."
        url="/glossary"
        termCount={definitions.length}
      />

      <div className="max-w-4xl mx-auto px-6 py-14">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">
          NSW Planning Glossary
        </h1>
        <p className="text-base text-gray-500 mb-2 max-w-2xl">
          {definitions.length} regulatory definitions extracted from NSW LEPs,
          DCPs, and SEPPs. Each definition includes the source document and
          clause citation.
        </p>
        <p className="text-sm text-gray-400 mb-8">
          Definitions are sourced verbatim from planning instruments — not
          paraphrased or interpreted. Use the search and filters below to find
          specific terms.
        </p>

        <GlossaryClient
          definitions={definitions}
          tags={sortedTags}
          legislationTypes={legislationTypes}
          letters={letters}
        />
      </div>

      {/* DefinedTerm JSON-LD for top 50 definitions (server-rendered for crawlers) */}
      {definitions.slice(0, 50).map((d) => (
        <script
          key={`ld-${d.id}`}
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'DefinedTerm',
              name: d.term,
              description: d.definition_summary || d.definition_text,
              url: `https://verify.plotdetect.com.au/glossary#term-${d.id}`,
              inDefinedTermSet: {
                '@type': 'DefinedTermSet',
                name: 'NSW Planning Glossary',
                url: 'https://verify.plotdetect.com.au/glossary',
              },
            }),
          }}
        />
      ))}

      <SiteFooter />
    </main>
  );
}
