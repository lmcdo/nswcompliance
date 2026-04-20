import 'maplibre-gl/dist/maplibre-gl.css';
import Link from 'next/link';

export default function ToolsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/canibuildit" className="flex items-center gap-2">
            <span className="font-bold text-gray-900 text-base tracking-tight">canibuildit</span>
            <span className="text-xs text-gray-400 font-normal hidden sm:block">by PlotDetect</span>
          </Link>
          <a
            href="mailto:hello@plotdetect.com.au"
            className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            Contact
          </a>
        </div>
      </header>
      <main>{children}</main>
      <footer className="border-t border-gray-100 mt-24">
        <div className="max-w-2xl mx-auto px-6 py-8 flex items-center justify-between text-xs text-gray-400">
          <span>© 2026 PlotDetect Pty Ltd</span>
          <span>NSW planning data only. Not legal advice.</span>
        </div>
      </footer>
    </div>
  );
}
