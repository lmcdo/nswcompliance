import type { Metadata } from 'next';
import Link from 'next/link';
import { GRANNY_FLAT_LGA_SLUG_MAP } from '@/lib/lga-data/granny-flat-lgas';
import { FLOOD_LGA_SLUG_MAP } from '@/lib/lga-data/flood-lgas';
import { SOLAR_LGA_SLUG_MAP } from '@/lib/lga-data/solar-lgas';
import { SHADOW_LGA_SLUG_MAP } from '@/lib/lga-data/shadow-lgas';
import { THREAT_RADAR_LGA_SLUG_MAP } from '@/lib/lga-data/threat-radar-lgas';
import { BUSHFIRE_LGA_SLUG_MAP } from '@/lib/lga-data/bushfire-lgas';
import { PRE_DA_HISTORY_LGA_SLUG_MAP } from '@/lib/lga-data/pre-da-history-lgas';

export const metadata: Metadata = {
  title: 'Browse NSW Planning Tools by Council Area — PlotDetect',
  description:
    'Find granny flat eligibility, flood risk, solar yield, shadow analysis, DA monitoring, bushfire screening, and site history tools for every NSW council area.',
};

const TOOLS = [
  { label: 'Granny Flat', prefix: '/granny-flat', map: GRANNY_FLAT_LGA_SLUG_MAP, color: 'bg-teal-600' },
  { label: 'Flood', prefix: '/flood-risk', map: FLOOD_LGA_SLUG_MAP, color: 'bg-blue-600' },
  { label: 'DA Monitor', prefix: '/threat-radar', map: THREAT_RADAR_LGA_SLUG_MAP, color: 'bg-amber-600' },
  { label: 'Solar', prefix: '/solar-potential', map: SOLAR_LGA_SLUG_MAP, color: 'bg-yellow-600' },
  { label: 'Shadow', prefix: '/shadow', map: SHADOW_LGA_SLUG_MAP, color: 'bg-slate-600' },
  { label: 'Bushfire', prefix: '/bushfire', map: BUSHFIRE_LGA_SLUG_MAP, color: 'bg-red-600' },
  { label: 'Site History', prefix: '/pre-da-history', map: PRE_DA_HISTORY_LGA_SLUG_MAP, color: 'bg-violet-600' },
] as const;

// Collect all unique slugs across all tools, sorted alphabetically by display name
function getAllLgas() {
  const slugNameMap = new Map<string, string>();
  for (const tool of TOOLS) {
    for (const [slug, data] of Object.entries(tool.map)) {
      if (!slugNameMap.has(slug)) {
        slugNameMap.set(slug, (data as { name: string }).name);
      }
    }
  }
  return [...slugNameMap.entries()]
    .sort((a, b) => a[1].localeCompare(b[1]))
    .map(([slug, name]) => ({ slug, name }));
}

export default function BrowsePage() {
  const allLgas = getAllLgas();

  return (
    <div className="max-w-6xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
        NSW Planning Tools by Council Area
      </h1>
      <p className="mt-2 text-gray-500">
        {allLgas.length} council areas, {TOOLS.length} tools. Click any cell to run that tool for
        the selected council.
      </p>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-6 mb-8">
        {TOOLS.map((t) => (
          <span key={t.prefix} className="flex items-center gap-1.5 text-xs text-gray-600">
            <span className={`w-2.5 h-2.5 rounded-sm ${t.color} inline-block`} />
            {t.label}
          </span>
        ))}
      </div>

      {/* Grid */}
      <div className="space-y-1">
        {allLgas.map(({ slug, name }) => (
          <div key={slug} className="flex items-center gap-2">
            <span className="w-44 shrink-0 text-sm text-gray-900 font-medium truncate">
              {name}
            </span>
            <div className="flex gap-1.5">
              {TOOLS.map((tool) => {
                const hasPage = slug in tool.map;
                if (!hasPage) {
                  return (
                    <span
                      key={tool.prefix}
                      className="w-20 h-8 rounded border border-gray-100 bg-gray-50"
                      title={`${tool.label} — not available for ${name}`}
                    />
                  );
                }
                return (
                  <Link
                    key={tool.prefix}
                    href={`${tool.prefix}/${slug}`}
                    className={`w-20 h-8 rounded border border-gray-200 bg-white flex items-center justify-center text-xs text-gray-600 hover:border-teal-400 hover:text-teal-700 transition-colors`}
                    title={`${tool.label} for ${name}`}
                  >
                    {tool.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <p className="mt-8 text-xs text-gray-400 text-center">
        Data sourced from the NSW Planning Portal, Bureau of Meteorology, European Space Agency,
        NSW Rural Fire Service, and NSW ePlanning Portal. Not legal advice.
      </p>
    </div>
  );
}
