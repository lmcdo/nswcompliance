'use client';

import Link from 'next/link';
import { useState } from 'react';

const TOOLS = [
  { label: 'Granny Flat', prefix: '/granny-flat' },
  { label: 'Flood Screening', prefix: '/flood-risk' },
  { label: 'DA Monitor', prefix: '/threat-radar' },
  { label: 'Solar', prefix: '/solar-potential' },
  { label: 'Shadow', prefix: '/shadow' },
  { label: 'Bushfire', prefix: '/bushfire' },
  { label: 'Planning Controls', prefix: '/planning-controls' },
  { label: 'Conveyancing', prefix: '/conveyancing' },
] as const;

const REGIONS = [
  {
    region: 'Greater Sydney \u2014 Inner & East',
    lgas: [
      { name: 'City of Sydney', slug: 'city-of-sydney' },
      { name: 'Inner West', slug: 'inner-west' },
      { name: 'Bayside', slug: 'bayside' },
      { name: 'Randwick', slug: 'randwick' },
      { name: 'Waverley', slug: 'waverley' },
      { name: 'Woollahra', slug: 'woollahra' },
      { name: 'Canada Bay', slug: 'canada-bay' },
      { name: 'Burwood', slug: 'burwood' },
      { name: 'Strathfield', slug: 'strathfield' },
    ],
  },
  {
    region: 'Greater Sydney \u2014 North',
    lgas: [
      { name: 'Northern Beaches', slug: 'northern-beaches' },
      { name: 'Ku-ring-gai', slug: 'ku-ring-gai' },
      { name: 'Hornsby', slug: 'hornsby' },
      { name: 'Lane Cove', slug: 'lane-cove' },
      { name: 'Ryde', slug: 'ryde' },
    ],
  },
  {
    region: 'Greater Sydney \u2014 West',
    lgas: [
      { name: 'Parramatta', slug: 'parramatta' },
      { name: 'Blacktown', slug: 'blacktown' },
      { name: 'The Hills Shire', slug: 'the-hills-shire' },
      { name: 'Penrith', slug: 'penrith' },
      { name: 'Hawkesbury', slug: 'hawkesbury' },
      { name: 'Cumberland', slug: 'cumberland' },
      { name: 'Fairfield', slug: 'fairfield' },
    ],
  },
  {
    region: 'Greater Sydney \u2014 South & Southwest',
    lgas: [
      { name: 'Campbelltown', slug: 'campbelltown' },
      { name: 'Camden', slug: 'camden' },
      { name: 'Liverpool', slug: 'liverpool' },
      { name: 'Sutherland Shire', slug: 'sutherland-shire' },
      { name: 'Georges River', slug: 'georges-river' },
      { name: 'Canterbury-Bankstown', slug: 'canterbury-bankstown' },
    ],
  },
  {
    region: 'Regional NSW',
    lgas: [
      { name: 'Wollongong', slug: 'wollongong' },
      { name: 'Wingecarribee', slug: 'wingecarribee' },
      { name: 'Clarence Valley', slug: 'clarence-valley' },
      { name: 'Yass Valley', slug: 'yass-valley' },
      { name: 'Bathurst Regional', slug: 'bathurst-regional' },
      { name: 'Tamworth Regional', slug: 'tamworth-regional' },
      { name: 'Forbes', slug: 'forbes' },
    ],
  },
];

export function BrowseByArea() {
  const [selected, setSelected] = useState(0);
  const tool = TOOLS[selected];

  return (
    <section id="browse-by-area" className="py-16 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-xl font-bold text-gray-900 mb-1">Browse by council area</h2>
        <p className="text-sm text-gray-500 mb-6">
          Select a tool, then pick a council to see results for that area.
        </p>

        {/* Tool selector */}
        <div className="flex flex-wrap gap-2 mb-8">
          {TOOLS.map((t, i) => (
            <button
              key={t.prefix}
              onClick={() => setSelected(i)}
              className={`text-sm px-4 py-1.5 rounded-full border transition-colors ${
                i === selected
                  ? 'bg-teal-600 text-white border-teal-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-teal-400 hover:text-teal-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* LGA grid */}
        <div className="space-y-8">
          {REGIONS.map(({ region, lgas }) => (
            <div key={region}>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">{region}</p>
              <div className="flex flex-wrap gap-2">
                {lgas.map(({ name, slug }) => (
                  <Link
                    key={slug}
                    href={`${tool.prefix}/${slug}`}
                    className="text-sm px-4 py-2 rounded-xl border border-gray-200 bg-white text-gray-700 hover:border-teal-400 hover:text-teal-700 transition-colors"
                  >
                    {name}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 flex items-center justify-between">
          <p className="text-xs text-gray-400">
            {REGIONS.reduce((n, r) => n + r.lgas.length, 0)} council areas across {TOOLS.length} tools
          </p>
          <Link
            href="/browse"
            className="text-xs text-teal-600 hover:text-teal-700 hover:underline"
          >
            View all councils and tools →
          </Link>
        </div>
      </div>
    </section>
  );
}
