import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { DefinedTermJsonLd, BreadcrumbJsonLd } from '@/lib/json-ld';
import {
  DATA_DICTIONARY_FIELDS,
  getDataDictionaryField,
} from '@/lib/data-dictionary';

interface Props {
  params: { slug: string };
}

export function generateStaticParams() {
  return DATA_DICTIONARY_FIELDS.map((f) => ({ slug: f.slug }));
}

export function generateMetadata({ params }: Props): Metadata {
  const field = getDataDictionaryField(params.slug);
  if (!field) return {};
  return {
    title: `${field.name} — NSW Planning Data Dictionary — PlotDetect`,
    description: field.shortDefinition,
    openGraph: {
      title: `${field.name} — NSW Planning Data Dictionary`,
      description: field.shortDefinition,
      url: `/open-data/fields/${field.slug}`,
      siteName: 'PlotDetect',
      type: 'article',
    },
  };
}

export default function DataDictionaryFieldPage({ params }: Props) {
  const field = getDataDictionaryField(params.slug);
  if (!field) notFound();

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <DefinedTermJsonLd
        name={field.name}
        description={field.shortDefinition}
        url={`/open-data/fields/${field.slug}`}
        inDefinedTermSet="PlotDetect NSW Planning Data Dictionary"
      />
      <BreadcrumbJsonLd
        items={[
          { name: 'Open Data', href: '/open-data' },
          { name: field.name, href: `/open-data/fields/${field.slug}` },
        ]}
      />

      {/* Breadcrumb */}
      <nav className="mb-8 text-sm text-slate-500">
        <Link
          href="/open-data"
          className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
        >
          Open data
        </Link>
        <span className="mx-2">/</span>
        <span>Data dictionary</span>
      </nav>

      {/* Header */}
      <div className="mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          {field.name}
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed">
          {field.shortDefinition}
        </p>
      </div>

      {/* What this field is */}
      <section className="mb-10">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
          What this field is
        </h2>
        {field.explanation.map((para) => (
          <p key={para.slice(0, 40)} className="text-sm text-slate-600 leading-relaxed mb-3">
            {para}
          </p>
        ))}
      </section>

      {/* Source and licence */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 mb-10">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">
          Where it comes from
        </h2>
        <dl className="space-y-4">
          <div>
            <dt className="text-xs text-slate-500 uppercase tracking-wider font-medium">
              Authoritative source
            </dt>
            <dd className="text-sm text-slate-900 mt-0.5">
              <a
                href={field.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
              >
                {field.sourceName}
              </a>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500 uppercase tracking-wider font-medium">
              Licence
            </dt>
            <dd className="text-sm text-slate-900 mt-0.5">{field.licence}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500 uppercase tracking-wider font-medium">
              Attribution
            </dt>
            <dd className="text-sm text-slate-900 mt-0.5">{field.attribution}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500 uppercase tracking-wider font-medium">
              Currency
            </dt>
            <dd className="text-sm text-slate-900 mt-0.5">{field.currency}</dd>
          </div>
        </dl>
      </section>

      {/* Limits */}
      <section className="mb-10">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
          Limits of this field
        </h2>
        <ul className="space-y-2">
          {field.caveats.map((caveat) => (
            <li
              key={caveat.slice(0, 40)}
              className="text-sm text-slate-600 leading-relaxed pl-4 border-l-2 border-slate-200"
            >
              {caveat}
            </li>
          ))}
        </ul>
      </section>

      {/* Related pages */}
      <section className="mb-10">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
          Where this field appears on PlotDetect
        </h2>
        <div className="flex flex-wrap gap-2">
          {field.related.map((r) => (
            <Link
              key={r.href}
              href={r.href}
              className="inline-flex items-center rounded-lg border border-teal-200 bg-teal-50 px-4 py-2 text-sm font-medium text-teal-700 hover:bg-teal-100 transition-colors"
            >
              {r.label}
            </Link>
          ))}
        </div>
      </section>

      {/* All fields */}
      <section className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 sm:p-8">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
          All fields in the data dictionary
        </h2>
        <ul className="space-y-1.5">
          {DATA_DICTIONARY_FIELDS.map((f) => (
            <li key={f.slug}>
              {f.slug === field.slug ? (
                <span className="text-sm text-slate-900 font-semibold">
                  {f.name}
                </span>
              ) : (
                <Link
                  href={`/open-data/fields/${f.slug}`}
                  className="text-sm text-teal-600 hover:text-teal-800 underline underline-offset-2"
                >
                  {f.name}
                </Link>
              )}
            </li>
          ))}
        </ul>
      </section>

      <p className="text-xs text-slate-400 mt-10 leading-relaxed">
        This page documents a data field served by PlotDetect. It describes
        published government data and its sources; it is general information
        about the data, not planning advice for a specific property.
      </p>
    </div>
  );
}
