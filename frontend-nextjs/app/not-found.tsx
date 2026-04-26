import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="min-h-screen bg-white flex flex-col items-center justify-center px-6 text-center">
      <p className="text-5xl font-bold text-gray-100 mb-2">404</p>
      <h1 className="text-xl font-semibold text-gray-900 mb-2">Page not found</h1>
      <p className="text-sm text-gray-500 mb-8 max-w-sm">
        The address you entered doesn&apos;t match any page. Try one of the tools below.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Link
          href="/reports/granny-flat"
          className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          Granny Flat Check
        </Link>
        <Link
          href="/reports/flood"
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          Flood Risk
        </Link>
        <Link
          href="/"
          className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
        >
          All tools →
        </Link>
      </div>
      <p className="text-xs text-gray-300 mt-12">canibuildit.com.au</p>
    </main>
  );
}
