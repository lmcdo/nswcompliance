import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Can I Build a Granny Flat? — Free NSW Eligibility Check',
  description: 'Instant granny flat eligibility check for any NSW property. Based on SEPP Housing 2021 lot area, zoning, and exclusion rules. Free — no signup required.',
};

export default function CanIBuildItLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-bold text-gray-900 text-base tracking-tight">canibuildit<span className="text-teal-600">.com.au</span></span>
          </Link>
          <a
            href="mailto:hello@canibuildit.com.au"
            className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            Contact
          </a>
        </div>
      </header>
      <main>{children}</main>
      <footer className="border-t border-gray-100 mt-24">
        <div className="max-w-2xl mx-auto px-6 py-8 flex items-center justify-between text-xs text-gray-400">
          <span>© 2026 canibuildit.com.au</span>
          <span>NSW planning data only. Not legal advice.</span>
        </div>
      </footer>
    </div>
  );
}
