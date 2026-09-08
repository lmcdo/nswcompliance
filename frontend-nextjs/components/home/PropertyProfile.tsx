'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import {
  Droplets, Flame, Sun, Eye, Radio, Home, FileSearch,
  MapPin, Ruler, Building2, Shield, ChevronRight,
  AlertTriangle,
} from 'lucide-react';

const AerialTile = dynamic(
  () => import('@/components/reports/AerialTile').then(m => m.AerialTile),
  { ssr: false, loading: () => <div className="w-full h-full bg-gray-100 animate-pulse rounded-xl" /> }
);

interface PropertyData {
  address: string;
  lat: number;
  lng: number;
  zone: string | null;
  zoneDescription: string | null;
  lga: string | null;
  maxHeight: string | null;
  maxFsr: string | null;
  heritage: boolean;
  heritageItemName: string | null;
  floodProne: boolean;
  lotArea: number | null;
  lotPolygon: { type: 'Polygon'; coordinates: number[][][] } | null;
  landValue: string | null;
  propertyArea: string | null;
}

interface ToolItem {
  key: string;
  title: string;
  detail: string;
  href: string;
  badge: string;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
}

const BUYING_TOOLS: ToolItem[] = [
  {
    key: 'flood',
    title: 'Flood Screening',
    detail: 'Statutory flood zone, council flood study depths, satellite water history.',
    href: '/reports/flood',
    badge: 'Free + $49 report',
    icon: Droplets,
    iconColor: 'text-blue-600 bg-blue-50',
  },
  {
    key: 'bushfire',
    title: 'Bushfire Pre-Screen',
    detail: 'RFS Bush Fire Prone Land status and BAL band estimate.',
    href: '/reports/bushfire',
    badge: 'Free',
    icon: Flame,
    iconColor: 'text-orange-600 bg-orange-50',
  },
  {
    key: 'pre-da',
    title: 'Pre-DA Site History',
    detail: '8 years of satellite change detection + DA records + heritage.',
    href: '/reports/pre-da-history',
    badge: '$49 report',
    icon: FileSearch,
    iconColor: 'text-purple-600 bg-purple-50',
  },
];

const BUILDING_TOOLS: ToolItem[] = [
  {
    key: 'granny-flat',
    title: 'Granny Flat Checker',
    detail: 'SEPP eligibility, structure detection, rental yield estimate.',
    href: '/reports/granny-flat',
    badge: 'Free + $49 report',
    icon: Home,
    iconColor: 'text-teal-600 bg-teal-50',
  },
  {
    key: 'shadow',
    title: 'Shadow Detector',
    detail: 'ADG shadow analysis at 9am, noon, and 3pm on winter solstice.',
    href: '/reports/shadow',
    badge: '$29 report',
    icon: Eye,
    iconColor: 'text-slate-600 bg-slate-50',
  },
  {
    key: 'threat-radar',
    title: 'Threat Radar',
    detail: 'Every DA and CDC within 500m — with weekly alerts.',
    href: '/reports/threat-radar',
    badge: 'Free',
    icon: Radio,
    iconColor: 'text-violet-600 bg-violet-50',
  },
];

const YIELD_TOOLS: ToolItem[] = [
  {
    key: 'solar',
    title: 'Solar Yield',
    detail: 'Roof geometry, orientation, and estimated annual kWh.',
    href: '/reports/solar-yield',
    badge: '$19 report',
    icon: Sun,
    iconColor: 'text-amber-600 bg-amber-50',
  },
  {
    key: 'granny-flat-yield',
    title: 'Granny Flat Checker',
    detail: 'Could this property earn $280–$340/week extra? Zone, lot size, SEPP rules.',
    href: '/reports/granny-flat',
    badge: 'Free + $49 report',
    icon: Home,
    iconColor: 'text-teal-600 bg-teal-50',
  },
];

export function PropertyProfile() {
  const searchParams = useSearchParams();
  const addressParam = searchParams?.get('address') ?? '';

  const [data, setData] = useState<PropertyData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!addressParam.trim()) return;

    let cancelled = false;
    setLoading(true);
    setError('');
    setData(null);

    fetch(`/api/property/profile?address=${encodeURIComponent(addressParam)}`)
      .then(async (res) => {
        if (!res.ok) {
          const json = await res.json().catch(() => ({}));
          throw new Error(json.error || 'Property lookup failed');
        }
        return res.json();
      })
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [addressParam]);

  if (!addressParam.trim()) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-20 text-center">
        <p className="text-gray-500">No address provided. <Link href="/" className="text-teal-600 underline underline-offset-2">Search from the homepage</Link>.</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      {loading && (
        <div className="flex flex-col items-center py-20 text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Looking up property...</p>
          <p className="text-xs text-gray-400 mt-1">Checking NSW Planning Portal</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {error}
        </div>
      )}

      {data && (
        <div className="space-y-10">
          {/* Header */}
          <div>
            <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
              <MapPin className="h-3.5 w-3.5" />
              <span>{data.lga ?? 'NSW'}</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{data.address}</h1>
          </div>

          {/* Map + summary grid */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Aerial map — square-ish aspect */}
            <div className="lg:col-span-3 rounded-xl overflow-hidden border border-gray-200 aspect-[4/3]">
              {data.lotPolygon ? (
                <AerialTile lat={data.lat} lng={data.lng} lotPolygon={data.lotPolygon} />
              ) : (
                <AerialTile lat={data.lat} lng={data.lng} />
              )}
            </div>

            {/* Key facts */}
            <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 self-start">
              <PropertyFact
                icon={Building2}
                label="Zone"
                value={data.zoneDescription ?? data.zone ?? 'Unknown'}
              />
              <PropertyFact icon={MapPin} label="LGA" value={data.lga ?? 'Unknown'} />
              <PropertyFact icon={Ruler} label="Max height" value={data.maxHeight ? `${data.maxHeight}m` : 'N/A'} />
              <PropertyFact icon={Building2} label="FSR" value={data.maxFsr ?? 'N/A'} />
              <PropertyFact icon={MapPin} label="Lot area" value={data.lotArea ? `${data.lotArea.toLocaleString()} m²` : data.propertyArea ?? 'N/A'} />
              <PropertyFact
                icon={data.heritage ? AlertTriangle : Shield}
                label="Heritage"
                value={data.heritage ? 'Yes' : 'No'}
                sub={data.heritageItemName}
                alert={data.heritage}
              />
              <PropertyFact
                icon={Droplets}
                label="Flood planning"
                value={data.floodProne ? 'Yes' : 'No'}
                alert={data.floodProne}
              />
            </div>
          </div>

          {/* Tool cards — grouped by intent */}
          <div className="space-y-10">
            <ToolGroup
              title="Buying a property?"
              subtitle="Your conveyancer will ask for flood and bushfire status. Get the data before they do."
              tools={BUYING_TOOLS}
              address={data.address}
            />
            <ToolGroup
              title="Planning to build?"
              subtitle="Check what's possible, what's planned nearby, and whether your build will create objections."
              tools={BUILDING_TOOLS}
              address={data.address}
            />
            <ToolGroup
              title="Evaluating yield?"
              subtitle="Estimate income potential before you buy or before you quote."
              tools={YIELD_TOOLS}
              address={data.address}
            />
          </div>

          {/* Disclaimer */}
          <p className="text-xs text-gray-400 leading-relaxed">
            Data sourced from NSW Planning Portal. Results are indicative only and do not constitute planning advice.
            Always consult a registered town planner or certifier before making planning or property decisions.
          </p>
        </div>
      )}
    </div>
  );
}

function ToolGroup({
  title,
  subtitle,
  tools,
  address,
}: {
  title: string;
  subtitle: string;
  tools: ToolItem[];
  address: string;
}) {
  return (
    <div>
      <h2 className="text-lg font-bold text-gray-900 mb-1">{title}</h2>
      <p className="text-sm text-gray-500 mb-4">{subtitle}</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {tools.map((tool) => {
          const Icon = tool.icon;
          const href = `${tool.href}?address=${encodeURIComponent(address)}`;
          return (
            <Link
              key={tool.key}
              href={href}
              className="group flex items-start gap-4 rounded-xl border border-gray-200 bg-white p-4 transition-all hover:border-gray-300 hover:shadow-sm"
            >
              <div className={`shrink-0 rounded-lg p-2.5 ${tool.iconColor}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <h3 className="text-sm font-semibold text-gray-900">{tool.title}</h3>
                  <ChevronRight className="h-4 w-4 text-gray-300 group-hover:text-gray-500 transition-colors shrink-0" />
                </div>
                <p className="text-xs text-gray-500 leading-relaxed mb-2">{tool.detail}</p>
                <span className="text-[11px] font-medium text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full">
                  {tool.badge}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function PropertyFact({
  icon: Icon,
  label,
  value,
  sub,
  alert,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sub?: string | null;
  alert?: boolean;
}) {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${alert ? 'text-amber-500' : 'text-gray-400'}`} />
      <div className="min-w-0">
        <p className="text-xs text-gray-400">{label}</p>
        <p className={`text-sm font-medium ${alert ? 'text-amber-700' : 'text-gray-900'}`}>{value}</p>
        {sub && <p className="text-xs text-gray-500 truncate">{sub}</p>}
      </div>
    </div>
  );
}
