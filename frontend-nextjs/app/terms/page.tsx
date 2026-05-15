import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteNav } from '@/components/marketing/SiteNav';
import { SiteFooter } from '@/components/marketing/SiteFooter';

export const metadata: Metadata = {
  title: 'Terms of Service — PlotDetect',
  description: 'Terms governing your use of PlotDetect property intelligence tools.',
};

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-white">
      <SiteNav />

      <article className="max-w-3xl mx-auto px-6 py-14 prose prose-sm prose-gray">
        <h1>Terms of Service</h1>
        <p className="text-gray-500 text-sm">Last updated: April 2026</p>

        <h2>1. Acceptance</h2>
        <p>
          By using plotdetect.com.au (&ldquo;the Service&rdquo;), you agree to these terms. If you
          do not agree, do not use the Service. These terms are governed by the laws of New South
          Wales, Australia.
        </p>

        <h2>2. What the Service provides</h2>
        <p>
          PlotDetect provides indicative property intelligence reports based on publicly
          available NSW planning data, satellite imagery, and spatial datasets. Reports cover:
        </p>
        <ul>
          <li>Granny flat eligibility (SEPP Housing 2021)</li>
          <li>Flood risk assessment</li>
          <li>Solar yield estimates</li>
          <li>Shadow analysis</li>
          <li>Nearby DA and CDC activity (Threat Radar)</li>
          <li>Pre-DA site history</li>
        </ul>

        <h2>3. Not professional advice</h2>
        <p>
          Results produced by this Service are <strong>indicative only</strong> and do not constitute
          planning advice, legal advice, engineering advice, or a substitute for a section 10.7
          planning certificate. You must consult a registered town planner, building certifier, or
          solicitor before making any planning or property decision.
        </p>
        <p>
          We do not accept liability for any decision made based on results produced by this Service.
        </p>

        <h2>4. Data accuracy</h2>
        <p>
          We source data from the NSW Planning Portal, NSW Spatial Services, and other government
          datasets. These datasets may contain errors, omissions, or outdated information. Zoning,
          planning controls, and flood overlays change over time. Results reflect data at the time of
          the query and may not reflect the current state of any planning instrument.
        </p>
        <p>
          Satellite-derived outputs (structure detection, solar yield, shadow analysis) are estimates
          based on available imagery and computational models. They are not surveys and may not be
          accurate for all properties.
        </p>

        <h2>5. Paid reports and subscriptions</h2>
        <p>
          Paid reports are delivered via email as PDF attachments. If you do not receive your report
          within 30 minutes of payment, contact us at{' '}
          <a href="mailto:hello@plotdetect.com.au">hello@plotdetect.com.au</a>.
        </p>
        <p>
          Threat Radar monitoring is a monthly subscription charged by Stripe. You may cancel at any
          time via your Stripe billing portal. Cancellation takes effect at the end of the current
          billing period. We do not offer refunds for partial billing periods.
        </p>
        <p>
          For one-time reports, we offer a full refund within 7 days if the report fails to generate
          or if the address was not found in our coverage area. Contact us to request a refund.
        </p>

        <h2>6. Prohibited use</h2>
        <p>You may not:</p>
        <ul>
          <li>Scrape or automate requests to the Service without written permission</li>
          <li>Resell or redistribute report data without written permission</li>
          <li>Use the Service to generate reports for bulk commercial data aggregation</li>
          <li>Attempt to circumvent payment for paid reports</li>
        </ul>

        <h2>7. Intellectual property</h2>
        <p>
          The software, design, and compiled outputs of this Service are owned by PlotDetect. You may
          use reports you have purchased for your own personal or business purposes. You may not
          reproduce or redistribute reports without attribution.
        </p>
        <p>
          Underlying government data (NSW Planning Portal, spatial datasets) is subject to Creative
          Commons licensing as published by the respective NSW government agencies.
        </p>

        <h2>8. Limitation of liability</h2>
        <p>
          To the maximum extent permitted by law, PlotDetect&rsquo;s liability for any claim arising
          from use of this Service is limited to the amount you paid for the report or service in
          question. We are not liable for indirect, consequential, or economic loss.
        </p>

        <h2>9. Changes to these terms</h2>
        <p>
          We may update these terms at any time. Continued use of the Service after changes are
          published constitutes acceptance of the updated terms.
        </p>

        <h2>10. Contact</h2>
        <p>
          <a href="mailto:hello@plotdetect.com.au">hello@plotdetect.com.au</a>
        </p>
      </article>

      <SiteFooter />
    </main>
  );
}
