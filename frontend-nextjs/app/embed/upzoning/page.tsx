import { DuplexCheckWidget } from '@/components/tools/DuplexCheckWidget';
import {
  getWidgetPartner,
  sanitizeCtaUrl,
  sanitizePartnerName,
} from '@/lib/widget-partners';

/**
 * /embed/upzoning — iframe-embeddable duplex eligibility checker.
 *
 * prior-art-checked: follows the existing app/embed/<tool>/page.tsx pattern
 * (layout.tsx handles domain logging + noindex); this is the upzoning tool's
 * embed, which did not exist. Partner branding resolves from the registry by
 * ?ref=<slug>; free-form ?partner=/?cta= params are accepted only through the
 * sanitizers and are IGNORED when ref matches a registered partner, so a
 * third party cannot iframe a registered brand with a swapped CTA target.
 */
export default function EmbedUpzoningPage({
  searchParams,
}: {
  searchParams: { ref?: string; partner?: string; cta?: string };
}) {
  const registered = searchParams.ref ? getWidgetPartner(searchParams.ref) : null;
  const partnerName = registered
    ? registered.name
    : sanitizePartnerName(searchParams.partner);
  const ctaUrl = registered ? registered.ctaUrl : sanitizeCtaUrl(searchParams.cta);

  return (
    <div className="px-4 py-5">
      <DuplexCheckWidget
        partnerName={partnerName}
        ctaUrl={ctaUrl}
        refSlug={registered?.slug ?? searchParams.ref ?? null}
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
