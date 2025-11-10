/**
 * Water Rights MVP - Demo Data
 * Realistic mock data for demo and outreach purposes
 *
 * Farmer: John Murphy, Glenview Farms, Griffith NSW
 * Water Year: 2024-25 (July 2024 - June 2025)
 */

export interface Entitlement {
  id: number;
  source: string;
  valley: string;
  category: string;
  categoryCode: string;
  volumeML: number;
  allocationPct: number;
  allocationML: number;
  usedML: number;
  remainingML: number;
  usedPct: number;
  status: 'compliant' | 'warning' | 'danger';
  walNumber: string;
}

export interface AllocationAnnouncement {
  id: number;
  date: string;
  valley: string;
  source: string;
  allocations: {
    category: string;
    percentage: number;
    change: number;
    trend: 'up' | 'down' | 'unchanged';
  }[];
  highlights: string[];
  damLevels: {
    name: string;
    percentage: number;
    volumeGL: number;
  }[];
  nextReviewDate: string;
  pdfUrl: string;
}

export interface UsageEntry {
  id: number;
  date: string;
  entitlementId: number;
  volumeML: number;
  purpose: string;
  source: 'telemetry' | 'manual' | 'iwas';
  meterReading?: number;
}

export interface Alert {
  id: number;
  type: 'supplementary' | 'allocation_change' | 'usage_warning' | 'compliance' | 'system';
  severity: 'info' | 'warning' | 'urgent';
  title: string;
  message: string;
  timestamp: string;
  expiresAt?: string;
  actionLabel?: string;
  actionUrl?: string;
  read: boolean;
}

export interface DamLevel {
  name: string;
  currentPct: number;
  currentVolumeGL: number;
  capacityGL: number;
  trend: 'rising' | 'falling' | 'stable';
  lastUpdated: string;
}

// Farmer Profile
export const demoFarmer = {
  id: 1,
  firstName: 'John',
  lastName: 'Murphy',
  email: 'john.murphy@glenviewfarms.com.au',
  phone: '+61 2 6962 1234',
  farmName: 'Glenview Farms',
  farmAddress: '145 Irrigation Way, Griffith NSW 2680',
  location: {
    lat: -34.2903,
    lng: 146.0399
  },
  crops: ['Rice', 'Cotton', 'Wheat'],
  hectares: 450,
  accountStatus: 'active',
  memberSince: '2018-03-15',
};

// Entitlements
export const demoEntitlements: Entitlement[] = [
  {
    id: 1,
    source: 'Murrumbidgee Regulated River',
    valley: 'Murrumbidgee',
    category: 'General Security',
    categoryCode: 'GS',
    volumeML: 800,
    allocationPct: 45,
    allocationML: 360,
    usedML: 220,
    remainingML: 140,
    usedPct: 61,
    status: 'warning',
    walNumber: '12GS345678',
  },
  {
    id: 2,
    source: 'Murrumbidgee Regulated River',
    valley: 'Murrumbidgee',
    category: 'High Security',
    categoryCode: 'HS',
    volumeML: 200,
    allocationPct: 95,
    allocationML: 190,
    usedML: 50,
    remainingML: 140,
    usedPct: 26,
    status: 'compliant',
    walNumber: '12HS987654',
  },
  {
    id: 3,
    source: 'Murrumbidgee Regulated River',
    valley: 'Murrumbidgee',
    category: 'Supplementary',
    categoryCode: 'SUPP',
    volumeML: 150,
    allocationPct: 0, // Not allocated until flow event
    allocationML: 0,
    usedML: 0,
    remainingML: 0,
    usedPct: 0,
    status: 'compliant',
    walNumber: '12SP456123',
  },
  {
    id: 4,
    source: 'Murray Regulated River',
    valley: 'Murray',
    category: 'General Security',
    categoryCode: 'GS',
    volumeML: 100,
    allocationPct: 60,
    allocationML: 60,
    usedML: 35,
    remainingML: 25,
    usedPct: 58,
    status: 'warning',
    walNumber: '15GS234567',
  },
];

// Calculate total allocation summary
export const totalAllocationSummary = {
  totalEntitlementML: demoEntitlements.reduce((sum, e) => sum + e.volumeML, 0),
  totalAllocationML: demoEntitlements.reduce((sum, e) => sum + e.allocationML, 0),
  totalUsedML: demoEntitlements.reduce((sum, e) => sum + e.usedML, 0),
  totalRemainingML: demoEntitlements.reduce((sum, e) => sum + e.remainingML, 0),
  overallUsedPct: Math.round((demoEntitlements.reduce((sum, e) => sum + e.usedML, 0) / demoEntitlements.reduce((sum, e) => sum + e.allocationML, 0)) * 100),
  overallStatus: 'compliant' as const,
  lastUpdated: '2024-12-28T08:15:00Z',
};

// Allocation History (12 months)
export const allocationHistory = [
  { month: 'Jul', date: '2024-07-01', GS_Murr: 0, HS_Murr: 95, GS_Murray: 18 },
  { month: 'Aug', date: '2024-08-01', GS_Murr: 15, HS_Murr: 95, GS_Murray: 22 },
  { month: 'Sep', date: '2024-09-01', GS_Murr: 22, HS_Murr: 95, GS_Murray: 28 },
  { month: 'Oct', date: '2024-10-01', GS_Murr: 30, HS_Murr: 95, GS_Murray: 35 },
  { month: 'Nov', date: '2024-11-01', GS_Murr: 35, HS_Murr: 95, GS_Murray: 45 },
  { month: 'Dec', date: '2024-12-01', GS_Murr: 40, HS_Murr: 95, GS_Murray: 55 },
  { month: 'Jan', date: '2025-01-01', GS_Murr: 45, HS_Murr: 95, GS_Murray: 60 },
  { month: 'Feb', date: '2025-02-01', GS_Murr: null, HS_Murr: null, GS_Murray: null }, // Future
  { month: 'Mar', date: '2025-03-01', GS_Murr: null, HS_Murr: null, GS_Murray: null },
  { month: 'Apr', date: '2025-04-01', GS_Murr: null, HS_Murr: null, GS_Murray: null },
  { month: 'May', date: '2025-05-01', GS_Murr: null, HS_Murr: null, GS_Murray: null },
  { month: 'Jun', date: '2025-06-01', GS_Murr: null, HS_Murr: null, GS_Murray: null },
];

// Recent Allocation Announcements
export const recentAnnouncements: AllocationAnnouncement[] = [
  {
    id: 1,
    date: '2024-12-16',
    valley: 'Murrumbidgee',
    source: 'Murrumbidgee Regulated River',
    allocations: [
      { category: 'General Security', percentage: 45, change: 5, trend: 'up' },
      { category: 'High Security', percentage: 95, change: 0, trend: 'unchanged' },
      { category: 'Conveyance', percentage: 100, change: 0, trend: 'unchanged' },
    ],
    highlights: [
      'Improved inflows from recent rainfall (45mm over catchment)',
      'Blowering Dam at 67% capacity',
      'Burrinjuck Dam at 82% capacity',
      'Strong seasonal outlook for summer',
    ],
    damLevels: [
      { name: 'Blowering Dam', percentage: 67, volumeGL: 1003 },
      { name: 'Burrinjuck Dam', percentage: 82, volumeGL: 820 },
    ],
    nextReviewDate: '2025-01-02',
    pdfUrl: 'https://water.dpie.nsw.gov.au/allocations/murrumbidgee-2024-12-16.pdf',
  },
  {
    id: 2,
    date: '2024-12-09',
    valley: 'Murray',
    source: 'Murray Regulated River',
    allocations: [
      { category: 'General Security', percentage: 60, change: 5, trend: 'up' },
      { category: 'High Security', percentage: 100, change: 0, trend: 'unchanged' },
    ],
    highlights: [
      'Increased flows from Snowy Scheme releases',
      'Hume Dam at 85% capacity',
      'Victorian allocation also increased',
    ],
    damLevels: [
      { name: 'Hume Dam', percentage: 85, volumeGL: 2557 },
      { name: 'Dartmouth Dam', percentage: 92, volumeGL: 3522 },
    ],
    nextReviewDate: '2025-01-08',
    pdfUrl: 'https://water.dpie.nsw.gov.au/allocations/murray-2024-12-09.pdf',
  },
  {
    id: 3,
    date: '2024-12-01',
    valley: 'Murrumbidgee',
    source: 'Murrumbidgee Regulated River',
    allocations: [
      { category: 'General Security', percentage: 40, change: 5, trend: 'up' },
      { category: 'High Security', percentage: 95, change: 0, trend: 'unchanged' },
    ],
    highlights: [
      'Gradual improvement in allocations',
      'Seasonal flows supporting increase',
      'Environmental water requirements met',
    ],
    damLevels: [
      { name: 'Blowering Dam', percentage: 64, volumeGL: 956 },
      { name: 'Burrinjuck Dam', percentage: 79, volumeGL: 790 },
    ],
    nextReviewDate: '2024-12-16',
    pdfUrl: 'https://water.dpie.nsw.gov.au/allocations/murrumbidgee-2024-12-01.pdf',
  },
];

// Usage History
export const usageHistory: UsageEntry[] = [
  // December 2024
  { id: 15, date: '2024-12-27', entitlementId: 1, volumeML: 5.2, purpose: 'Rice paddock 3 irrigation', source: 'telemetry', meterReading: 220.0 },
  { id: 14, date: '2024-12-26', entitlementId: 1, volumeML: 4.8, purpose: 'Rice paddock 2 irrigation', source: 'telemetry', meterReading: 214.8 },
  { id: 13, date: '2024-12-25', entitlementId: 1, volumeML: 0.0, purpose: 'No irrigation - Christmas', source: 'telemetry', meterReading: 210.0 },
  { id: 12, date: '2024-12-24', entitlementId: 1, volumeML: 6.1, purpose: 'Rice paddocks 1 & 3', source: 'telemetry', meterReading: 210.0 },
  { id: 11, date: '2024-12-23', entitlementId: 1, volumeML: 5.5, purpose: 'Rice paddock 2', source: 'telemetry', meterReading: 203.9 },
  { id: 10, date: '2024-12-22', entitlementId: 1, volumeML: 0.0, purpose: 'No irrigation - rain event (18mm)', source: 'telemetry', meterReading: 198.4 },
  { id: 9, date: '2024-12-21', entitlementId: 1, volumeML: 5.8, purpose: 'Rice paddock 1', source: 'telemetry', meterReading: 198.4 },

  // High Security usage
  { id: 8, date: '2024-12-20', entitlementId: 2, volumeML: 3.2, purpose: 'Cotton irrigation', source: 'telemetry', meterReading: 50.0 },
  { id: 7, date: '2024-12-15', entitlementId: 2, volumeML: 4.5, purpose: 'Cotton irrigation', source: 'telemetry', meterReading: 46.8 },

  // November 2024
  { id: 6, date: '2024-11-30', entitlementId: 1, volumeML: 25.0, purpose: 'November total - Rice irrigation peak', source: 'manual' },
  { id: 5, date: '2024-11-15', entitlementId: 4, volumeML: 12.0, purpose: 'Murray entitlement - Cotton', source: 'manual' },

  // October 2024
  { id: 4, date: '2024-10-31', entitlementId: 1, volumeML: 20.0, purpose: 'October total - Rice establishment', source: 'manual' },

  // September 2024
  { id: 3, date: '2024-09-30', entitlementId: 1, volumeML: 18.0, purpose: 'September total - Pre-irrigation', source: 'manual' },

  // August 2024
  { id: 2, date: '2024-08-31', entitlementId: 1, volumeML: 15.0, purpose: 'August total - Limited irrigation', source: 'manual' },

  // July 2024
  { id: 1, date: '2024-07-31', entitlementId: 1, volumeML: 5.0, purpose: 'July total - Minimal irrigation', source: 'manual' },
];

// Monthly Usage Summary
export const monthlyUsageSummary = [
  { month: 'Jul', year: 2024, totalML: 5, avgDailyML: 0.16 },
  { month: 'Aug', year: 2024, totalML: 15, avgDailyML: 0.48 },
  { month: 'Sep', year: 2024, totalML: 18, avgDailyML: 0.60 },
  { month: 'Oct', year: 2024, totalML: 20, avgDailyML: 0.65 },
  { month: 'Nov', year: 2024, totalML: 25, avgDailyML: 0.83 },
  { month: 'Dec', year: 2024, totalML: 32, avgDailyML: 1.03 }, // Partial month
];

// Alerts
export const demoAlerts: Alert[] = [
  {
    id: 1,
    type: 'supplementary',
    severity: 'urgent',
    title: '🚨 Supplementary Access Declared - Act Now!',
    message: 'Supplementary water access is available on Murrumbidgee Regulated River. Window closes in 38 hours. You can order up to 150 ML during this event.',
    timestamp: '2024-12-27T10:00:00Z',
    expiresAt: '2024-12-29T18:00:00Z',
    actionLabel: 'Order Water via WaterNSW',
    actionUrl: 'https://iportal.waternsw.com.au/water-ordering',
    read: false,
  },
  {
    id: 2,
    type: 'allocation_change',
    severity: 'info',
    title: 'Allocation Increased to 45%',
    message: 'General Security allocation for Murrumbidgee has increased from 40% to 45% (+5%). Your allocation is now 360 ML. Updated Dec 16, 2024.',
    timestamp: '2024-12-16T17:00:00Z',
    actionLabel: 'View Full Statement',
    actionUrl: 'https://water.dpie.nsw.gov.au/allocations/murrumbidgee-2024-12-16.pdf',
    read: false,
  },
  {
    id: 3,
    type: 'usage_warning',
    severity: 'warning',
    title: 'Approaching Allocation Limit',
    message: 'You have used 61% of your General Security allocation (220 of 360 ML). At current usage rate (5.2 ML/day), you will exceed allocation in approximately 27 days.',
    timestamp: '2024-12-27T08:00:00Z',
    actionLabel: 'View Usage Details',
    actionUrl: '/water-demo/usage',
    read: true,
  },
  {
    id: 4,
    type: 'system',
    severity: 'info',
    title: 'Telemetry Update Successful',
    message: 'Your water meter readings have been updated automatically. Latest reading: 220.0 ML (Dec 27, 08:15 AM).',
    timestamp: '2024-12-27T08:15:00Z',
    read: true,
  },
  {
    id: 5,
    type: 'compliance',
    severity: 'info',
    title: '✅ Compliance Status: Compliant',
    message: 'All your water accounts are within allocation limits. Total remaining: 305 ML across all entitlements.',
    timestamp: '2024-12-27T00:00:00Z',
    actionLabel: 'View Dashboard',
    actionUrl: '/water-demo',
    read: true,
  },
];

// Dam Levels
export const currentDamLevels: DamLevel[] = [
  {
    name: 'Blowering Dam',
    currentPct: 67,
    currentVolumeGL: 1003,
    capacityGL: 1494,
    trend: 'rising',
    lastUpdated: '2024-12-27T06:00:00Z',
  },
  {
    name: 'Burrinjuck Dam',
    currentPct: 82,
    currentVolumeGL: 820,
    capacityGL: 1000,
    trend: 'stable',
    lastUpdated: '2024-12-27T06:00:00Z',
  },
  {
    name: 'Hume Dam',
    currentPct: 85,
    currentVolumeGL: 2557,
    capacityGL: 3006,
    trend: 'rising',
    lastUpdated: '2024-12-27T06:00:00Z',
  },
];

// Market Pricing (for trading view)
export const waterMarketPrices = {
  murrumbidgee: {
    valley: 'Murrumbidgee',
    temporaryAllocation: {
      currentPrice: 185,
      currency: 'AUD',
      unit: 'ML',
      change24h: 8,
      volumeAvailable: 450,
      lastTrade: '2024-12-26T14:30:00Z',
    },
    permanentEntitlement: {
      currentPrice: 3200,
      currency: 'AUD',
      unit: 'ML',
      change24h: -50,
      volumeAvailable: 25,
      lastTrade: '2024-12-24T11:15:00Z',
    },
  },
  murray: {
    valley: 'Murray',
    temporaryAllocation: {
      currentPrice: 220,
      currency: 'AUD',
      unit: 'ML',
      change24h: 15,
      volumeAvailable: 320,
      lastTrade: '2024-12-27T10:00:00Z',
    },
    permanentEntitlement: {
      currentPrice: 4500,
      currency: 'AUD',
      unit: 'ML',
      change24h: 100,
      volumeAvailable: 18,
      lastTrade: '2024-12-26T16:45:00Z',
    },
  },
};

// Helper functions
export function getEntitlementById(id: number): Entitlement | undefined {
  return demoEntitlements.find(e => e.id === id);
}

export function getUnreadAlerts(): Alert[] {
  return demoAlerts.filter(a => !a.read);
}

export function getActiveAlerts(): Alert[] {
  const now = new Date();
  return demoAlerts.filter(a => {
    if (!a.expiresAt) return true;
    return new Date(a.expiresAt) > now;
  });
}

export function calculateDaysUntilExceed(entitlementId: number): number | null {
  const entitlement = getEntitlementById(entitlementId);
  if (!entitlement || entitlement.allocationML === 0) return null;

  const remainingML = entitlement.remainingML;
  const recentUsage = usageHistory
    .filter(u => u.entitlementId === entitlementId && u.date >= '2024-12-01')
    .reduce((sum, u) => sum + u.volumeML, 0);

  const daysInPeriod = 27; // December 1-27
  const avgDailyUsage = recentUsage / daysInPeriod;

  if (avgDailyUsage <= 0) return null;

  return Math.floor(remainingML / avgDailyUsage);
}
