/**
 * PartnerAttribution — co-branding line for white-label tool embeds.
 *
 * Renders "A free <check> from <partner>" above an embedded check when the
 * ?ref=<slug> resolved to a registered widget partner (lib/widget-partners.ts).
 * Presentation only: the partner name comes from the registry (registry-only,
 * no free-form params — PR #790 review finding) and it NEVER affects the
 * check's computed result. Renders nothing for an unbranded (no-partner) embed,
 * so the public/direct embed is unchanged.
 *
 * The duplex embed does its own branding inside DuplexCheckWidget; this covers
 * the flood, granny-flat, overshadowing, solar and development-activity embeds,
 * whose tool components carry no branding slot of their own.
 */
export function PartnerAttribution({
  partnerName,
  checkLabel,
}: {
  /** Registered partner display name, or null for an unbranded embed */
  partnerName?: string | null;
  /** Plain-English name of the check, e.g. "flood risk check" */
  checkLabel: string;
}) {
  if (!partnerName) return null;
  return (
    <p className="mb-3 text-center text-sm text-gray-500">
      A free {checkLabel} from{' '}
      <span className="font-semibold text-gray-700">{partnerName}</span>
    </p>
  );
}
