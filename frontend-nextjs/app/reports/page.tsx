import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Site Facts — NSW',
  description: 'Site Facts: the mapped facts about a NSW property, with the source of each.',
  openGraph: {
    title: 'Site Facts — PlotDetect',
    description: 'The mapped facts about a NSW property, with the source of each.',
    url: '/reports',
  },
};

interface Props {
  searchParams: Promise<{ address?: string | string[] }>;
}

export default async function ReportsLanding({ searchParams }: Props) {
  // An address may arrive from the homepage search (?address=). Pass it on so the
  // visitor does not have to re-type it. Empty/malformed param = the plain page.
  const params = await searchParams;
  const address = typeof params.address === 'string' ? params.address.trim() : '';
  const hrefSuffix = address ? `?address=${encodeURIComponent(address)}` : '';

  return (
    <div className="space-y-12">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 leading-tight">Site Facts</h1>
        <p className="mt-2 text-gray-500 max-w-xl">
          The mapped facts about a NSW property, with the source of each.
        </p>
      </div>

      {address && (
        <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">
          Address: <span className="font-medium text-teal-900">{address}</span>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href={`/reports/intelligence-brief${hrefSuffix}`}
          className="group block bg-white rounded-xl border border-gray-200 p-6 hover:border-gray-300 hover:shadow-sm transition-all"
        >
          <h2 className="font-semibold text-gray-900 group-hover:text-teal-700 transition-colors mb-2">
            Site Facts
          </h2>
          <p className="text-sm text-gray-400 leading-relaxed">
            Open Site Facts for an address.
          </p>
        </Link>
        <Link
          href={`/assessment${hrefSuffix}`}
          className="group block bg-white rounded-xl border border-gray-200 p-6 hover:border-gray-300 hover:shadow-sm transition-all"
        >
          <h2 className="font-semibold text-gray-900 group-hover:text-teal-700 transition-colors mb-2">
            Council Rules
          </h2>
          <p className="text-sm text-gray-400 leading-relaxed">
            The council&apos;s own rules for an address, in its words.
          </p>
        </Link>
      </div>
    </div>
  );
}
