/**
 * discover-lep-map-types.mjs
 *
 * Calls /api/property for one test address per LGA and dumps every localProvision entry.
 * Run against the local dev server:
 *   node scripts/discover-lep-map-types.mjs
 * Or against production:
 *   BASE_URL=https://your-production-url.vercel.app node scripts/discover-lep-map-types.mjs
 */

const BASE_URL = process.env.BASE_URL || 'http://localhost:3003';

// One representative address per LGA, ordered by relevance / development activity.
// Choose addresses that are likely to have local provisions (near waterways, entertainment
// precincts, key sites, etc.) — boring residential streets often return nothing.
const TEST_ADDRESSES = [
  { lga: 'City of Sydney',    address: '1 Pitt Street, Sydney NSW 2000' },
  { lga: 'Inner West',        address: '120 Illawarra Road, Marrickville NSW 2204' },
  { lga: 'North Sydney',      address: '40 Mount Street, North Sydney NSW 2060' },
  { lga: 'Parramatta',        address: '383 Church Street, Parramatta NSW 2150' },
  { lga: 'Waverley',          address: '100 Oxford Street, Bondi Junction NSW 2022' },
  { lga: 'Randwick',          address: '1 High Street, Randwick NSW 2031' },
  { lga: 'Woollahra',         address: '1 Ocean Street, Woollahra NSW 2025' },
  { lga: 'Ku-ring-gai',       address: '828 Pacific Highway, Gordon NSW 2072' },
  { lga: 'Ryde',              address: '1 Devlin Street, Ryde NSW 2112' },
  { lga: 'Blacktown',         address: '1 Kildare Road, Blacktown NSW 2148' },
];

async function fetchProperty(address) {
  const url = `${BASE_URL}/api/property?address=${encodeURIComponent(address)}&includeConstraints=true`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${address}`);
  const json = await res.json();
  return json?.data;
}

async function main() {
  console.log(`Hitting ${BASE_URL}\n`);
  console.log('='.repeat(80));

  const report = [];

  for (const { lga, address } of TEST_ADDRESSES) {
    process.stdout.write(`[${lga}] ${address} ... `);
    try {
      const data = await fetchProperty(address);
      const provisions = data?.constraints?.localProvisions ?? [];
      console.log(`${provisions.length} local provision(s)`);

      if (provisions.length === 0) {
        report.push({ lga, address, provisions: [] });
        continue;
      }

      for (const p of provisions) {
        console.log(`  mapType:     ${p.mapType ?? '(null)'}`);
        console.log(`  epiName:     ${p.epiName ?? '(null)'}`);
        console.log(`  clauseNumber:${p.clauseNumber ?? '(not mapped)'}`);
        console.log(`  title:       ${p.title ?? ''}`);
        console.log(`  class:       ${p.class ?? ''}`);
        console.log(`  legUrl:      ${p.legislationUrl ?? '(none)'}`);
        if (p.clauseNumber && p.legislationUrl) {
          console.log(`  deepLink:    ${p.legislationUrl}#sec.${p.clauseNumber}  ✅`);
        } else if (p.legislationUrl) {
          console.log(`  deepLink:    ${p.legislationUrl}  ⚠️  (no clause anchor)`);
        }
        console.log();
      }

      report.push({ lga, address, provisions });
    } catch (err) {
      console.log(`ERROR: ${err.message}`);
      report.push({ lga, address, error: err.message });
    }
  }

  // Summary table
  console.log('='.repeat(80));
  console.log('SUMMARY — unknown mapType codes needing clause mappings:\n');
  for (const { lga, provisions = [] } of report) {
    const unknown = provisions.filter(p => !p.clauseNumber && p.mapType);
    if (unknown.length) {
      console.log(`  ${lga}:`);
      for (const p of unknown) {
        console.log(`    mapType="${p.mapType}"  epiName="${p.epiName}"  url=${p.legislationUrl}`);
      }
    }
  }
  console.log('\nDone.');
}

main().catch(err => { console.error(err); process.exit(1); });
