/**
 * The LEP height and FSR limits from the /api/capacity/calculate response held as lepClauseData.
 *
 * That route nests them as capacity.maxHeight / capacity.maxFSR. DA mode, the SEE standards and
 * the SEE property context read lepClauseData.height_limit / .fsr, which do not exist, so DA mode
 * never showed the limits or the proposed-height / proposed-GFA inputs and no proposed-vs-limit
 * check ran (found 2026-10-19). One reader for both shapes.
 *
 * prior-art-checked: no shared accessor existed; the three readers each read the missing field.
 */
export interface LepLimits {
  height: number | undefined;
  fsr: number | undefined;
}

const num = (v: unknown): number | undefined => {
  const n = typeof v === 'string' ? parseFloat(v) : typeof v === 'number' ? v : NaN;
  return Number.isFinite(n) && n > 0 ? n : undefined;
};

export function lepLimits(lepClauseData: Record<string, any> | null | undefined): LepLimits {
  const d = lepClauseData ?? {};
  return {
    height: num(d.capacity?.maxHeight) ?? num(d.height_limit),
    fsr: num(d.capacity?.maxFSR) ?? num(d.fsr),
  };
}
