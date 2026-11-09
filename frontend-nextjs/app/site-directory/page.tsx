import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Site directory | PlotDetect',
  description: 'The two products and the company pages on this site.',
  alternates: { canonical: '/site-directory' },
};

// Pilot focus: only the paths in lib/pilot-focus.ts PILOT_ALLOWED_LINKS are listed here.
interface DirItem {
  href: string;
  label: string;
  desc: string;
}
interface DirGroup {
  title: string;
  items: DirItem[];
}

const GROUPS: DirGroup[] = [
  {
    title: 'Products',
    items: [
      { href: '/assessment', label: 'Council Rules', desc: "The council's own rules for an address, in its words." },
      { href: '/reports/intelligence-brief', label: 'Site Facts', desc: 'The mapped facts about a property.' },
    ],
  },
  {
    title: 'Company & help',
    items: [
      { href: '/how-it-works', label: 'How it works', desc: 'How an address becomes an answer.' },
      { href: '/contact', label: 'Contact', desc: 'Get in touch.' },
      { href: '/privacy', label: 'Privacy', desc: 'Privacy policy.' },
      { href: '/terms', label: 'Terms', desc: 'Terms of use.' },
    ],
  },
];

export default function DirectoryPage() {
  return (
    <main className="max-w-5xl mx-auto px-6 py-12">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Site directory</h1>
        <p className="mt-2 text-slate-600 max-w-2xl leading-relaxed">
          The two products and the company pages on this site.
        </p>
      </header>

      <div className="space-y-10">
        {GROUPS.map((group) => (
          <section key={group.title}>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              {group.title}
            </h2>
            <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {group.items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="block h-full rounded-lg border border-slate-200 bg-white p-3 hover:border-teal-400 hover:shadow-sm transition-colors"
                  >
                    <span className="text-sm font-medium text-slate-900">{item.label}</span>
                    <p className="mt-1 text-xs text-slate-500 leading-snug">{item.desc}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}
