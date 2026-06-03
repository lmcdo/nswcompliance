import type { Metadata } from 'next';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';
import { BreadcrumbJsonLd } from '@/lib/json-ld';
import { BlogEmailCapture } from '@/components/marketing/BlogEmailCapture';

export const metadata: Metadata = {
  title: 'Insights — PlotDetect',
  description: 'Property intelligence insights: climate risk, planning compliance, flood data, and regulatory analysis for NSW property professionals.',
};

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <BreadcrumbJsonLd items={[
        { name: 'Home', href: '/' },
        { name: 'Blog', href: '/blog' },
      ]} />
      <SiteNav maxWidth="max-w-5xl" />
      <main>
        {children}
        <div className="max-w-3xl mx-auto px-4">
          <BlogEmailCapture />
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
