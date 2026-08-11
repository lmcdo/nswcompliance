/**
 * ToolCrossSell — contextual cross-sell strip shown after a tool result.
 *
 * Each tool passes its own `exclude` key so it doesn't cross-sell itself.
 * Cards are ordered by relevance: granny flat first (income angle), then
 * the other satellite checks.
 */

import React from 'react';

type ToolKey = 'solar-yield' | 'shadow-detector' | 'flood-truth' | 'threat-radar' | 'granny-flat' | 'pre-da-history' | 'bushfire' | 'conveyancing' | 'planning-controls' | 'climate-risk';

interface Card {
  title: string;
  body: string;
  href: string;
  label: string;
}

const ALL_CARDS: Record<ToolKey, (address: string) => Card> = {
  'granny-flat': (address) => ({
    title: 'Granny Flat Yield Predictor',
    body: 'Find out if your lot is eligible for a granny flat and estimate the rental income.',
    href: `/granny-flat?address=${encodeURIComponent(address)}`,
    label: 'Check granny flat eligibility →',
  }),
  'flood-truth': (address) => ({
    title: 'Wet Season Flood Truth',
    body: 'Verify flood risk with Sentinel-1 SAR imagery — required by certifiers before any new structure.',
    href: `/reports/flood?address=${encodeURIComponent(address)}`,
    label: 'Check flood risk →',
  }),
  'threat-radar': (address) => ({
    title: 'Neighbour Development Threat Radar',
    body: 'Monitor nearby DA applications that could block sunlight, views, or property value.',
    href: `/reports/threat-radar?address=${encodeURIComponent(address)}`,
    label: 'Check nearby DAs →',
  }),
  'shadow-detector': (address) => ({
    title: 'Construction Shadow Detector',
    body: 'Check whether a maximum-height building immediately north of your lot would shadow your property.',
    href: `/reports/shadow?address=${encodeURIComponent(address)}`,
    label: 'Check shadow risk →',
  }),
  'solar-yield': (address) => ({
    title: 'Rooftop Solar Yield Underwriter',
    body: 'Estimate solar panel output, system payback period, and 10-year return.',
    href: `/reports/solar-yield?address=${encodeURIComponent(address)}`,
    label: 'Check solar potential →',
  }),
  'pre-da-history': (address) => ({
    title: 'Pre-DA Site History',
    body: 'Eight years of satellite change detection cross-referenced with DA records and heritage overlays.',
    href: `/reports/pre-da-history?address=${encodeURIComponent(address)}`,
    label: 'Check site history →',
  }),
  'bushfire': (address) => ({
    title: 'Bushfire Pre-Screen',
    body: 'Check if an NSW property is on bushfire prone land and what that means for development.',
    href: `/reports/bushfire?address=${encodeURIComponent(address)}`,
    label: 'Check bushfire risk →',
  }),
  'conveyancing': (address) => ({
    title: 'Conveyancing Planning Disclosure',
    body: 'LEP controls, spatial overlays, valuation, heritage, and development feasibility for due diligence.',
    href: `/reports/conveyancing?address=${encodeURIComponent(address)}`,
    label: 'Check planning disclosure →',
  }),
  'planning-controls': (address) => ({
    title: 'Planning Controls Assessment',
    body: 'Full SEPP, LEP, and DCP controls for your property — setbacks, parking, height, landscaping with clause citations.',
    href: `/assessment?address=${encodeURIComponent(address)}`,
    label: 'See full planning controls →',
  }),
  'climate-risk': (address) => ({
    title: 'Climate Risk Score',
    body: 'Composite climate risk scoring — flood, bushfire, coastal, fire history, and NARCliM heat projections.',
    href: `/climate-risk?address=${encodeURIComponent(address)}`,
    label: 'Check climate risk →',
  }),
};

// Relevance order per tool — granny flat income angle always first when applicable
const ORDER: Record<ToolKey, ToolKey[]> = {
  'solar-yield':        ['planning-controls', 'granny-flat', 'shadow-detector', 'flood-truth', 'threat-radar'],
  'shadow-detector':    ['planning-controls', 'granny-flat', 'threat-radar', 'flood-truth', 'solar-yield'],
  'flood-truth':        ['planning-controls', 'granny-flat', 'threat-radar', 'shadow-detector', 'solar-yield'],
  'threat-radar':       ['planning-controls', 'granny-flat', 'flood-truth', 'shadow-detector', 'solar-yield'],
  'granny-flat':        ['planning-controls', 'flood-truth', 'threat-radar', 'shadow-detector', 'solar-yield'],
  'pre-da-history':     ['planning-controls', 'granny-flat', 'flood-truth', 'threat-radar', 'shadow-detector'],
  'bushfire':           ['planning-controls', 'granny-flat', 'flood-truth', 'threat-radar', 'shadow-detector'],
  'conveyancing':       ['planning-controls', 'granny-flat', 'flood-truth', 'threat-radar', 'bushfire'],
  'planning-controls':  ['granny-flat', 'flood-truth', 'threat-radar', 'shadow-detector', 'conveyancing'],
  'climate-risk':       ['flood-truth', 'bushfire', 'planning-controls', 'conveyancing', 'granny-flat'],
};

export function ToolCrossSell({
  currentTool,
  address,
  maxCards = 2,
}: {
  currentTool: ToolKey;
  address: string;
  maxCards?: number;
}) {
  if (!address.trim()) return null;

  const cards = ORDER[currentTool]
    .filter((key) => key !== currentTool)
    .slice(0, maxCards)
    .map((key) => ALL_CARDS[key](address));

  if (cards.length === 0) return null;

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Also check</p>
      <div className={`grid gap-3 ${cards.length > 1 ? 'sm:grid-cols-2' : ''}`}>
        {cards.map((card) => (
          <a
            key={card.href}
            href={card.href}
            className="block rounded-xl border border-gray-200 bg-white p-4 hover:border-teal-300 hover:shadow-sm transition-all"
          >
            <p className="text-sm font-semibold text-gray-900 mb-1">{card.title}</p>
            <p className="text-xs text-gray-500 mb-3 leading-relaxed">{card.body}</p>
            <span className="text-xs font-medium text-teal-600">{card.label}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
