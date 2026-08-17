// prior-art-checked: reuse not viable because no module converts Google Solar's
// DC figure to delivered energy — this rule did not exist anywhere until this
// branch, and the flagged files share only vocabulary. Four sweeps on
// origin/main 307c743f: (1) DB — no stored column holds a delivered figure;
// (2) python — services/solar_yield.py is the AUTHORITY for the factors and is
// deliberately mirrored here rather than duplicated in four components;
// (3) frontend — the conversion existed as four inline copies introduced
// earlier on this same branch, which adversarial review showed disagreeing
// three different ways, and this file replaces all four; (4) plans/memory —
// the product assurance position records solar as a pass-through with no
// delivered figure at all.
/**
 * Delivered solar energy — one implementation, imported by every surface.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * Google Solar returns `yearlyEnergyDcKwh`: energy at the panel, before the
 * inverter. That figure was rendered as "Calculated yield … kWh/year" with
 * nothing saying DC, and then monetised — overstating the annual saving by 21%
 * and the ten-year return by nearly tenfold.
 *
 * The first correction put the conversion inline on four surfaces. Adversarial
 * review then found three separate ways the four copies disagreed: one rejected
 * a numeric string, one treated a real zero as missing, one implied a DC
 * conversion that had not happened. Four implementations of one rule is the
 * defect; this module is the fix.
 *
 * `services/solar_yield.py` remains the authority for the FACTORS. The Python
 * test suite reads this file and asserts both figures match it, because there
 * is no import boundary between Python and TypeScript to enforce it.
 */

// PVWatts applies TWO defaults, not one: the 14.08% system loss does NOT
// include the inverter, which PVWatts models separately at 96%. Applying only
// the first leaves delivered output about 4% too high — the bug this file's
// first draft shipped with.
export const PVWATTS_SYSTEM_LOSS = 0.1408;
export const PVWATTS_INVERTER_EFFICIENCY = 0.96;
export const DC_TO_DELIVERED =
  (1 - PVWATTS_SYSTEM_LOSS) * PVWATTS_INVERTER_EFFICIENCY;

/** Rounded whole-percent gap between DC and delivered. Currently 18. */
export const DELIVERED_LOSS_PCT = Math.round((1 - DC_TO_DELIVERED) * 100);

/**
 * A usable delivered figure, or null.
 *
 * The two failure modes pull in OPPOSITE directions and no single numeric
 * comparison separates them:
 *   - `0` is a REAL zero and must be kept. Rejecting it substitutes a derived
 *     positive number, so a roof recorded as delivering nothing gets reported
 *     as delivering something.
 *   - `''` is schema drift and must NOT become 0. `Number('')` is 0, so any
 *     guard that only coerces will serve zero yield as though measured.
 * Only the raw value distinguishes them, so this inspects the type first.
 * A numeric STRING is accepted, because JSON round-trips through stores that
 * stringify numbers.
 */
export function usableDelivered(v: unknown): number | null {
  if (typeof v === 'number') return Number.isFinite(v) && v >= 0 ? v : null;
  if (typeof v === 'string' && v.trim() !== '') {
    const n = Number(v);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }
  return null;
}

/**
 * Delivered energy for a payload holding either or both fields.
 *
 * Returns null when NEITHER is usable — absence stays absence rather than
 * becoming 0, which would render as a real roof generating nothing.
 */
export function deliveredKwhFrom(dc: unknown, delivered: unknown): number | null {
  const d = usableDelivered(delivered);
  if (d != null) return d;
  const raw = usableDelivered(dc);
  return raw == null ? null : raw * DC_TO_DELIVERED;
}

/**
 * The sentence that explains the gap, sized to what is actually known.
 *
 * When no DC figure is present there was no conversion to describe, so it must
 * not claim one — the earlier copy said "Reported at the panel (DC), less about
 * 18%" even when the DC number was absent and the delivered figure had been
 * supplied directly.
 */
export function deliveryBasisText(dc: unknown): string {
  const raw = usableDelivered(dc);
  const losses =
    `NREL PVWatts v8's ${(PVWATTS_SYSTEM_LOSS * 100).toFixed(2)}% system losses ` +
    `(soiling, shading, mismatch, wiring, ageing) and its separate ` +
    `${PVWATTS_INVERTER_EFFICIENCY * 100}% inverter efficiency`;
  if (raw == null) {
    return `Delivered output as supplied. Where it is derived, the gap from ` +
           `energy at the panel is about ${DELIVERED_LOSS_PCT}% — ${losses}.`;
  }
  return `${Math.round(raw).toLocaleString()} kWh/year at the panel (DC), ` +
         `less about ${DELIVERED_LOSS_PCT}% — ${losses}.`;
}
