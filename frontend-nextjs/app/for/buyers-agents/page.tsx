import type { Metadata } from 'next';
import Link from 'next/link';
import { Radar, Droplets, Flame, Building2, ArrowRight } from 'lucide-react';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'For Buyers Agents — PlotDetect',
  description: 'Satellite hazard screening for shortlisted properties. Flood, bushfire, granny flat, and DA monitoring in one workflow.',
};

export default function BuyersAgentsPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-16 pb-12">
        <div className="flex items-center gap-2 mb-4">
          <Radar className="w-5 h-5 text-violet-600" />
          <span className="text-xs font-semibold uppercase tracking-widest text-violet-600">
            For buyers agents
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
          Screen shortlisted properties in minutes, not hours
        </h1>
        <p className="text-gray-500 text-lg max-w-xl">
          Your clients expect you to know the risks before they bid.
          PlotDetect gives you flood depth, bushfire BAL, granny flat eligibility,
          and DA activity for any NSW address — instantly.
        </p>
      </section>

      {/* What you get */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <h2 className="text-xl font-bold text-gray-900 mb-6">
          One address, every hazard
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            {
              icon: Droplets,
              iconColor: 'text-blue-600',
              title: 'Flood depth, not just flood zone',
              description: 'ARI return period depths from council flood studies. Know how deep it floods, not just whether the overlay exists.',
            },
            {
              icon: Flame,
              iconColor: 'text-orange-600',
              title: 'Bushfire BAL + clearing requirements',
              description: 'Bush Fire Prone Land status, estimated BAL band, and 10/50 vegetation clearing obligations.',
            },
            {
              icon: Building2,
              iconColor: 'text-teal-600',
              title: 'Granny flat yield screening',
              description: 'SEPP eligibility, satellite structure detection, and rental yield estimate — filters investment properties fast.',
            },
            {
              icon: Radar,
              iconColor: 'text-violet-600',
              title: 'Threat Radar monitoring',
              description: 'Weekly DA alerts within 200m of any property. Know before your client\'s neighbour breaks ground.',
            },
          ].map(({ icon: Icon, iconColor, title, description }) => (
            <div key={title} className="rounded-xl border border-gray-200 p-5">
              <Icon className={`w-5 h-5 ${iconColor} mb-2`} />
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="bg-gray-50 border-y border-gray-100 py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Pricing for professionals</h2>
          <p className="text-gray-500 mb-6">
            All instant checks are free. Reports are one-off purchases.
            Monitoring is per-property monthly.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-2xl font-bold text-gray-900">Free</p>
              <p className="text-sm text-gray-500 mt-1">8 instant checks</p>
              <p className="text-xs text-gray-400 mt-2">
                Flood, bushfire, granny flat, conveyancing, threat radar, shadow, solar, site history.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-2xl font-bold text-gray-900">$39–$49</p>
              <p className="text-sm text-gray-500 mt-1">Per property report</p>
              <p className="text-xs text-gray-400 mt-2">
                Professional PDF with full analysis. Pass through as a disbursement.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-2xl font-bold text-gray-900">$9/mo</p>
              <p className="text-sm text-gray-500 mt-1">Per property monitoring</p>
              <p className="text-xs text-gray-400 mt-2">
                Weekly DA alerts within 200m. Monthly digest. Cancel anytime.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-12">
        <div className="rounded-xl border border-violet-200 bg-violet-50 p-8 text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Start with a free property check
          </h2>
          <p className="text-sm text-gray-600 mb-6 max-w-md mx-auto">
            Enter any NSW address and see what PlotDetect surfaces — free, no account required.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/reports"
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 transition-colors"
            >
              Try the tools
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="mailto:hello@plotdetect.com.au?subject=Buyers%20agent%20enquiry"
              className="inline-flex items-center gap-2 px-6 py-2.5 text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:border-gray-300 transition-all"
            >
              hello@plotdetect.com.au
            </a>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
