import { DuplexCheckWidget } from '@/components/tools/DuplexCheckWidget';
import { getWidgetPartner } from '@/lib/widget-partners';

/**
 * /embed/upzoning — iframe-embeddable duplex eligibility checker.
 *
 * prior-art-checked: follows the existing app/embed/<tool>/page.tsx pattern
 * (layout.tsx handles domain logging + noindex); this is the upzoning tool's
 * embed, which did not exist. Branding resolves ONLY by ?ref=<slug> against
 * the in-repo registry — free-form partner/cta params were removed after the
 * PR #790 review found they allowed a registered builder's name to be paired
 * with an arbitrary CTA URL. Unknown or missing ref renders the unbranded
 * checker with no partner CTA.
 */
export default function EmbedUpzoningPage({
  searchParams,
}: {
  searchParams: { ref?: string | string[] };
}) {
  const partner = getWidgetPartner(searchParams.ref);

  return (
    <div className="px-4 py-5">
      <DuplexCheckWidget
        partnerName={partner?.name ?? null}
        ctaUrl={partner?.ctaUrl ?? null}
        refSlug={partner?.slug ?? null}
      />
      <p className="mt-4 text-center text-xs text-gray-400">
        <a href="https://plotdetect.com.au" target="_blank" rel="noopener">
          Powered by PlotDetect
        </a>{' '}
        · Data: NSW Planning Portal, Spatial Services NSW
      </p>
    </div>
  );
}
