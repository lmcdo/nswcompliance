import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'Privacy Policy — PlotDetect',
  description: 'How PlotDetect collects, uses, and protects your personal information.',
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <article className="max-w-3xl mx-auto px-6 py-14 prose prose-sm prose-gray">
        <h1>Privacy Policy</h1>
        <p className="text-gray-500 text-sm">Last updated: April 2026</p>

        <h2>Who we are</h2>
        <p>
          plotdetect.com.au is operated by PlotDetect (ABN pending), an Australian property intelligence
          service. This policy explains what personal information we collect, why we collect it, and how
          we use it.
        </p>

        <h2>What we collect</h2>
        <ul>
          <li>
            <strong>Property addresses</strong> you enter into our tools. These are used to run the
            analysis you request. We may store addresses to improve accuracy and log usage.
          </li>
          <li>
            <strong>Email addresses</strong> you provide voluntarily — either to receive a report, to
            subscribe to planning alerts, or to contact us. We use these to send you the content you
            requested and, with your consent, occasional product updates.
          </li>
          <li>
            <strong>Payment information</strong> for paid reports is handled entirely by Stripe. We do
            not store card numbers or payment credentials.
          </li>
          <li>
            <strong>Usage data</strong> including page views, tool interactions, and general analytics
            via PostHog. This data is anonymised and used to improve the product.
          </li>
        </ul>

        <h2>How we use your information</h2>
        <ul>
          <li>To deliver the report or service you requested</li>
          <li>To send transactional emails (report delivery, subscription confirmation)</li>
          <li>To improve the accuracy and coverage of our tools</li>
          <li>To contact you if you have asked us to</li>
        </ul>
        <p>
          We do not sell your personal information to third parties. We do not use your data for
          advertising targeting.
        </p>

        <h2>Third-party services</h2>
        <p>We use the following third-party services to operate the platform:</p>
        <ul>
          <li><strong>Stripe</strong> — payment processing</li>
          <li><strong>Resend</strong> — transactional email delivery</li>
          <li><strong>Supabase</strong> — database and storage (hosted in AWS Sydney)</li>
          <li><strong>PostHog</strong> — anonymous usage analytics</li>
          <li><strong>Vercel</strong> — website hosting</li>
          <li><strong>Google Maps</strong> — address autocomplete</li>
        </ul>
        <p>
          Each of these providers has their own privacy policy and security practices. Data is stored
          in Australia or the United States.
        </p>

        <h2>Email communications</h2>
        <p>
          If you provide your email address, we will send you the report or confirmation you requested.
          You can unsubscribe from any marketing communications at any time by replying to any email
          or contacting us directly.
        </p>
        <p>
          For Threat Radar monitoring subscriptions, you can cancel at any time via your Stripe billing
          portal. Cancellation stops both the subscription charge and future alert emails.
        </p>

        <h2>Data retention</h2>
        <p>
          We retain address and email data for up to 3 years to support product improvement and to
          allow re-delivery of reports if requested. You can request deletion of your data at any time.
        </p>

        <h2>Your rights</h2>
        <p>
          Under the Australian Privacy Act 1988, you have the right to access, correct, or request
          deletion of personal information we hold about you. To exercise these rights, contact us at{' '}
          <a href="mailto:privacy@plotdetect.com.au">privacy@plotdetect.com.au</a>.
        </p>

        <h2>Cookies</h2>
        <p>
          We use cookies for session management and anonymous analytics. We do not use advertising
          cookies or tracking pixels from ad networks.
        </p>

        <h2>Contact</h2>
        <p>
          Questions about this policy:{' '}
          <a href="mailto:privacy@plotdetect.com.au">privacy@plotdetect.com.au</a>
        </p>
      </article>

      <SiteFooter />
    </main>
  );
}
