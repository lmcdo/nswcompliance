import Link from 'next/link';

export default function PropertyLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-semibold text-gray-900 text-base tracking-tight">
              canibuildit<span className="text-teal-600">.com.au</span>
            </span>
          </Link>
          <nav className="flex items-center gap-4">
            <Link href="/reports" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
              All tools
            </Link>
            <Link href="/pricing" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
              Pricing
            </Link>
          </nav>
        </div>
      </header>
      <main>{children}</main>
      <footer className="border-t border-gray-100 mt-16">
        <div className="max-w-5xl mx-auto px-6 py-6 text-center">
          <p className="text-xs text-gray-400">
            Results are indicative only and do not constitute planning advice. Always consult a registered town planner or certifier.
          </p>
        </div>
      </footer>
    </div>
  );
}
