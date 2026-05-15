import Link from 'next/link';

export function SiteFooter() {
  return (
    <footer className="border-t border-gray-100 py-6 px-6">
      <div className="max-w-3xl mx-auto flex flex-wrap gap-4 text-xs text-gray-400">
        <Link href="/" className="hover:text-gray-600 transition-colors">Home</Link>
        <Link href="/reports" className="hover:text-gray-600 transition-colors">Tools</Link>
        <Link href="/how-it-works" className="hover:text-gray-600 transition-colors">How it works</Link>
        <Link href="/pricing" className="hover:text-gray-600 transition-colors">Pricing</Link>
        <Link href="/for/builders" className="hover:text-gray-600 transition-colors">Embed program</Link>
        <Link href="/contact" className="hover:text-gray-600 transition-colors">Contact</Link>
        <Link href="/privacy" className="hover:text-gray-600 transition-colors">Privacy</Link>
        <Link href="/terms" className="hover:text-gray-600 transition-colors">Terms</Link>
      </div>
      <div className="max-w-3xl mx-auto mt-4">
        <p className="text-xs text-gray-300">
          © {new Date().getFullYear()} PlotDetect — NSW property intelligence
        </p>
      </div>
    </footer>
  );
}
