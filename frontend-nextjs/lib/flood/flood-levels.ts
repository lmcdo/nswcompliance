/**
 * Every flood level a lot sits in, most frequent flood first: "1%AEP, 0.2%AEP, PMF".
 *
 * The property route used to show rows[0].value, and the rows are sorted as TEXT, so "0.2%AEP" came before "1%AEP"
 * and a lot inside the 1-in-100-year flood area read as the rarer, milder 0.2% event (cross-review of #1506,
 * 2026-10-29). Nothing is chosen here: every level the map gives is listed. The order comes from the value itself --
 * a larger annual exceedance probability floods more often, so it goes first; PMF (probable maximum flood, the
 * rarest) goes after every AEP; anything else keeps its place after those.
 */
const AEP = /^\s*(\d+(?:\.\d+)?)\s*%\s*AEP\s*$/i;

function rank(v: string): [number, number] {
  const m = AEP.exec(v);
  if (m) return [0, -parseFloat(m[1])];
  if (/^\s*PMF\s*$/i.test(v)) return [1, 0];
  return [2, 0];
}

export function floodLevels(values: (string | null | undefined)[]): string | undefined {
  const seen = new Map<string, string>();
  for (const v of values) {
    const t = (v ?? '').trim();
    const m = AEP.exec(t);
    const key = m ? `${parseFloat(m[1])}%AEP` : t.toUpperCase();   // "1%AEP" and "1.0%AEP" are one level
    if (t && !seen.has(key)) seen.set(key, m ? `${parseFloat(m[1])}% AEP` : t);
  }
  const out = [...seen.values()].sort((a, b) => {
    const [ga, na] = rank(a.replace(' ', '')), [gb, nb] = rank(b.replace(' ', ''));
    return ga - gb || na - nb;
  });
  return out.length ? out.join(', ') : undefined;
}
