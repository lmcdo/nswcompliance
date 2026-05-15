import Link from 'next/link';

interface SiteNavProps {
  maxWidth?: string;
}

export function SiteNav({ maxWidth = 'max-w-3xl' }: SiteNavProps) {
  return (
    <nav className={`flex items-center justify-between px-6 py-4 ${maxWidth} mx-auto border-b border-gray-100`}>
      <Link href="/" className="text-base font-bold tracking-tight text-gray-900">
        Plot<span className="text-teal-600">Detect</span>
      </Link>
      <div className="flex items-center gap-4">
        <Link href="/how-it-works" className="text-sm text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">
          How it works
        </Link>
        <Link href="/pricing" className="text-sm text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">
          Pricing
        </Link>
        <Link href="/reports" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
          Tools →
        </Link>
      </div>
    </nav>
  );
}
