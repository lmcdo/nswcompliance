import Link from 'next/link';

export default function ToolsLayout({ children }: { children: React.ReactNode }) {
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
        <div className="max-w-2xl mx-auto px-6 py-6 flex flex-wrap items-center justify-between gap-3 text-xs text-gray-400">
          <span>© 2026 canibuildit.com.au</span>
          <div className="flex flex-wrap gap-4">
            <Link href="/how-it-works" className="hover:text-gray-600 transition-colors">How it works</Link>
            <Link href="/partner" className="hover:text-gray-600 transition-colors">Embed program</Link>
            <Link href="/privacy" className="hover:text-gray-600 transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-gray-600 transition-colors">Terms</Link>
          </div>
        </div>
        <div className="max-w-2xl mx-auto px-6 pb-6">
          <p className="text-xs text-gray-300">NSW planning data only. Not legal or planning advice.</p>
        </div>
      </footer>
    </div>
  );
}
