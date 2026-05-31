'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';

interface Definition {
  id: number;
  term: string;
  definition_text: string;
  definition_summary: string | null;
  source_document: string;
  source_clause: string | null;
  legislation_type: string;
  domain_tags: string[] | null;
}

/** Map domain tags to relevant tool CTAs */
const TAG_TOOL_MAP: Record<string, { label: string; href: string }> = {
  flood: { label: 'Check flood risk', href: '/flood-risk' },
  heritage: { label: 'Check planning controls', href: '/assessment' },
  setback: { label: 'Check planning controls', href: '/assessment' },
  parking: { label: 'Check planning controls', href: '/assessment' },
  landscaping: { label: 'Check planning controls', href: '/assessment' },
  tree: { label: 'Check planning controls', href: '/assessment' },
  bushfire: { label: 'Check bushfire status', href: '/bushfire' },
  stormwater: { label: 'Check planning controls', href: '/assessment' },
};

/** Legislation type display labels */
const TYPE_LABELS: Record<string, string> = {
  DCP: 'Development Control Plan',
  SEPP: 'State Environmental Planning Policy',
  SI_LEP: 'Standard Instrument LEP',
};

export function GlossaryClient({
  definitions,
  tags,
  legislationTypes,
  letters,
}: {
  definitions: Definition[];
  tags: string[];
  legislationTypes: string[];
  letters: string[];
}) {
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedTag, setSelectedTag] = useState<string>('');
  const [selectedLetter, setSelectedLetter] = useState<string>('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const filtered = useMemo(() => {
    let result = definitions;

    if (search) {
      const lower = search.toLowerCase();
      result = result.filter(
        (d) =>
          d.term.toLowerCase().includes(lower) ||
          d.definition_text.toLowerCase().includes(lower)
      );
    }

    if (selectedType) {
      result = result.filter((d) => d.legislation_type === selectedType);
    }

    if (selectedTag) {
      result = result.filter((d) => d.domain_tags?.includes(selectedTag));
    }

    if (selectedLetter) {
      result = result.filter(
        (d) => d.term[0]?.toUpperCase() === selectedLetter
      );
    }

    return result;
  }, [definitions, search, selectedType, selectedTag, selectedLetter]);

  const clearFilters = () => {
    setSearch('');
    setSelectedType('');
    setSelectedTag('');
    setSelectedLetter('');
  };

  const hasFilters = search || selectedType || selectedTag || selectedLetter;

  return (
    <>
      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search terms and definitions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-4 py-3 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
        />
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="">All instrument types</option>
          {legislationTypes.map((t) => (
            <option key={t} value={t}>
              {TYPE_LABELS[t] || t}
            </option>
          ))}
        </select>

        <select
          value={selectedTag}
          onChange={(e) => setSelectedTag(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="">All categories</option>
          {tags.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        {hasFilters && (
          <button
            onClick={clearFilters}
            className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Alphabet navigation */}
      <div className="flex flex-wrap gap-1 mb-6">
        {letters.map((letter) => (
          <button
            key={letter}
            onClick={() =>
              setSelectedLetter(selectedLetter === letter ? '' : letter)
            }
            className={`w-8 h-8 text-xs font-medium rounded transition-colors ${
              selectedLetter === letter
                ? 'bg-teal-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {letter}
          </button>
        ))}
      </div>

      {/* Results count */}
      <p className="text-sm text-gray-400 mb-6">
        {filtered.length === definitions.length
          ? `${definitions.length} definitions`
          : `${filtered.length} of ${definitions.length} definitions`}
      </p>

      {/* Definition list */}
      <div className="space-y-0 divide-y divide-gray-100">
        {filtered.map((d) => {
          const isExpanded = expandedId === d.id;
          const toolCta = d.domain_tags?.find((t) => TAG_TOOL_MAP[t]);

          return (
            <div key={d.id} className="py-4" id={`term-${d.id}`}>
              <button
                onClick={() => setExpandedId(isExpanded ? null : d.id)}
                className="w-full text-left group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h2 className="text-sm font-semibold text-gray-900 group-hover:text-teal-700 transition-colors">
                      {d.term}
                    </h2>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                      {d.definition_summary || d.definition_text}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                      {d.legislation_type}
                    </span>
                    <span className="text-gray-300 text-xs">
                      {isExpanded ? '−' : '+'}
                    </span>
                  </div>
                </div>
              </button>

              {isExpanded && (
                <div className="mt-3 pl-0">
                  {/* Full definition */}
                  <div className="bg-gray-50 rounded-lg p-4 mb-3">
                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                      {d.definition_text}
                    </p>
                  </div>

                  {/* Source citation */}
                  <div className="flex flex-wrap gap-4 text-xs text-gray-400 mb-3">
                    <span>
                      <span className="font-medium text-gray-500">Source:</span>{' '}
                      {d.source_document}
                    </span>
                    {d.source_clause && (
                      <span>
                        <span className="font-medium text-gray-500">
                          Clause:
                        </span>{' '}
                        {d.source_clause}
                      </span>
                    )}
                    <span>
                      <span className="font-medium text-gray-500">Type:</span>{' '}
                      {TYPE_LABELS[d.legislation_type] || d.legislation_type}
                    </span>
                  </div>

                  {/* Domain tags */}
                  {d.domain_tags && d.domain_tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {d.domain_tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-xs px-2 py-0.5 rounded-full bg-teal-50 text-teal-700"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Tool CTA */}
                  {toolCta && TAG_TOOL_MAP[toolCta] && (
                    <Link
                      href={TAG_TOOL_MAP[toolCta].href}
                      className="inline-block text-xs px-3 py-1.5 bg-teal-600 text-white rounded-md hover:bg-teal-700 transition-colors"
                    >
                      {TAG_TOOL_MAP[toolCta].label} for your address
                    </Link>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-sm text-gray-400">
              No definitions match your search.
            </p>
            <button
              onClick={clearFilters}
              className="mt-2 text-sm text-teal-600 hover:text-teal-700 transition-colors"
            >
              Clear all filters
            </button>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <p className="mt-12 text-xs text-gray-400 text-center px-4 pb-8">
        Definitions are extracted verbatim from NSW planning instruments
        (LEPs, DCPs, SEPPs). Where the same term is defined differently across
        instruments, each definition is shown with its source citation.
        Definitions may change when instruments are amended. Not legal advice.
      </p>
    </>
  );
}
