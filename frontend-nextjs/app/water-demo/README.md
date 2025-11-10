# WaterRight MVP - Demo Application

**Water Allocation Management for Australian Farmers**

This demo showcases a professional SaaS application for real-time water allocation tracking and compliance management.

---

## 🎯 Demo Purpose

This demo is designed for:
- **Investor pitches** - Show product vision and UX
- **Farmer outreach** - Demonstrate value proposition
- **Partner discussions** - Showcase technical capabilities
- **Market validation** - Test feature priorities

---

## 🚀 Quick Start

### Running the Demo

```bash
# Navigate to frontend directory
cd frontend-nextjs

# Install dependencies (if not already installed)
npm install

# Run development server
npm run dev

# Open in browser
http://localhost:3000/water-demo
```

### Demo Pages

1. **Login Page**: `/water-demo/login`
   - Professional login UI with value proposition
   - Partner SSO option (Murrumbidgee Irrigation)

2. **Dashboard Home**: `/water-demo`
   - Water account summary (total allocation, used, remaining)
   - Urgent supplementary alert (time-sensitive)
   - Quick stats (entitlements, market prices, alerts)
   - Entitlements breakdown preview
   - Dam storage levels
   - Latest allocation announcement

3. **Entitlements**: `/water-demo/entitlements`
   - Detailed breakdown by valley
   - Individual entitlement cards with progress bars
   - Summary statistics
   - Export and management options

4. **Usage Tracking**: `/water-demo/usage`
   - Telemetry integration status
   - Manual water usage entry form
   - Monthly usage chart
   - Recent usage history (last 30 days)
   - CSV import/export

5. **Alerts Center**: `/water-demo/alerts`
   - Supplementary access alert with countdown timer
   - Allocation change notifications
   - Usage warnings
   - Compliance status updates
   - Notification settings (email, SMS, push)

---

## 📊 Demo Data

The demo uses realistic mock data based on actual Murrumbidgee Valley water allocations:

### Demo Farmer Profile
- **Name**: John Murphy
- **Farm**: Glenview Farms, Griffith NSW
- **Crops**: Rice, Cotton, Wheat
- **Farm Size**: 450 hectares

### Water Entitlements (4 total)
1. **General Security - Murrumbidgee**: 800 ML (45% allocation)
   - Used: 220 ML (61%)
   - Remaining: 140 ML
   - Status: ⚠️ Warning

2. **High Security - Murrumbidgee**: 200 ML (95% allocation)
   - Used: 50 ML (26%)
   - Remaining: 140 ML
   - Status: ✅ Compliant

3. **Supplementary - Murrumbidgee**: 150 ML (0% - awaiting flow event)
   - 🚨 ACTIVE ALERT: Supplementary access declared (38 hours remaining)

4. **General Security - Murray**: 100 ML (60% allocation)
   - Used: 35 ML (58%)
   - Remaining: 25 ML
   - Status: ⚠️ Warning

### Total Summary
- **Total Allocation**: 610 ML (across all entitlements)
- **Total Used**: 305 ML (50%)
- **Total Remaining**: 305 ML (50%)
- **Overall Status**: ✅ Compliant

### Recent Allocations
- **Dec 16, 2024**: Murrumbidgee GS increased 40% → 45% (+5%)
- **Dec 9, 2024**: Murray GS increased 55% → 60% (+5%)

### Dam Levels (Current)
- **Blowering Dam**: 67% capacity (1,003 GL / 1,494 GL)
- **Burrinjuck Dam**: 82% capacity (820 GL / 1,000 GL)
- **Hume Dam**: 85% capacity (2,557 GL / 3,006 GL)

### Water Market Prices
- **Murrumbidgee Temporary**: $185/ML (↑ +$8 in 24h)
- **Murray Temporary**: $220/ML (↑ +$15 in 24h)

---

## 🎨 Design & Components

### Technology Stack
- **Framework**: Next.js 14 with App Router
- **UI Library**: Shadcn/UI (Tailwind CSS + Radix UI)
- **Icons**: Lucide React
- **Charts**: Custom-built bar charts

### Color Palette
- **Primary**: #0077BE (Deep Water Blue)
- **Secondary**: #00A9E0 (Light Blue)
- **Success**: #00C851 (Green - Compliant)
- **Warning**: #FFB700 (Yellow - Near Limit)
- **Danger**: #FF4444 (Red - Over Limit)
- **Accent**: #33B5E5 (Aqua - Supplementary Alerts)

### Key Components

1. **WaterAccountSummaryCard** (`components/water-demo/WaterAccountSummaryCard.tsx`)
   - Total allocation display
   - Usage progress bar
   - Status badges
   - Quick actions

2. **EntitlementCard** (`components/water-demo/EntitlementCard.tsx`)
   - Individual entitlement details
   - Category-specific icons
   - Progress visualization
   - Status messages

3. **UsageHistoryChart** (`components/water-demo/UsageHistoryChart.tsx`)
   - Monthly bar chart
   - Usage trends
   - Peak usage identification

4. **SupplementaryAlert** (`components/water-demo/SupplementaryAlert.tsx`)
   - Countdown timer
   - Urgency-based styling
   - Action buttons
   - Historical context

---

## 📸 Screenshot Guide

### For Pitch Decks & Marketing

**Recommended Screenshots:**

1. **Hero Shot**: Dashboard Home
   - Viewport: 1920×1080 (desktop)
   - State: Show supplementary alert active
   - Capture: Full page with header

2. **Feature Focus**: Entitlements Page
   - Viewport: 1920×1080
   - State: Show multiple entitlements with different statuses
   - Capture: Focus on card grid

3. **Mobile View**: Dashboard on Mobile
   - Viewport: 375×812 (iPhone 13)
   - State: Same as hero shot
   - Capture: Responsive layout

4. **Alert Detail**: Alerts Center
   - Viewport: 1920×1080
   - State: Show urgent supplementary alert with countdown
   - Capture: Supplementary alert card close-up

5. **Usage Tracking**: Usage page with chart
   - Viewport: 1920×1080
   - State: Show monthly chart + recent entries
   - Capture: Focus on chart visualization

### How to Capture

```bash
# Method 1: Browser DevTools
1. Open page in Chrome/Edge
2. Press F12 → Toggle Device Toolbar (Ctrl+Shift+M)
3. Set resolution (1920×1080 or 375×812)
4. Right-click → "Capture screenshot"

# Method 2: Browser Extensions
- Use "GoFullPage" or "Awesome Screenshot"
- Capture full page or visible area

# Method 3: Command Line (Playwright)
npx playwright screenshot http://localhost:3000/water-demo mockups/screenshots/dashboard.png --viewport-size=1920,1080
```

---

## 🎤 Demo Script

### 5-Minute Pitch Demo

**Opening (30 seconds)**
> "Meet John Murphy, a rice farmer in Griffith. He manages 800 ML of water allocation across multiple entitlements. Let me show you how WaterRight helps him avoid $264,000 penalties and never miss water opportunities."

**Dashboard Tour (2 minutes)**
1. **Show summary card**: "John's used 61% of his allocation - approaching the limit"
2. **Point to urgent alert**: "RIGHT NOW there's a supplementary flow event - he has 38 hours to order water"
3. **Show market prices**: "Current price is $185/ML, up $8 today"
4. **Quick actions**: "One click to order water or log usage"

**Entitlements Deep Dive (1 minute)**
1. **Navigate to entitlements**: "John has 4 water entitlements across 2 valleys"
2. **Show General Security**: "His main allocation - 45% this year, he's used 220 of 360 ML"
3. **Show High Security**: "Premium allocation - 95% reliability, still has 140 ML left"
4. **Show Supplementary**: "Waiting for flow events - the alert we saw is for THIS entitlement"

**Usage Tracking (1 minute)**
1. **Show telemetry integration**: "Readings updated automatically every 15 minutes"
2. **Show monthly chart**: "Peak usage in November during rice irrigation"
3. **Show manual entry**: "Can also manually log usage - takes 5 seconds"

**Alerts (30 seconds)**
1. **Show countdown timer**: "38 hours until supplementary window closes"
2. **Show notification settings**: "Email, SMS, and push notifications"

**Closing (30 seconds)**
> "WaterRight saves farmers from penalties, helps them catch every water opportunity, and automates compliance. Starting at $75/month - avoiding one penalty pays for 10+ years."

---

## 🔧 Customization for Different Audiences

### For Farmers
- Emphasize: Compliance, penalties avoided, time savings
- Demo flow: Login → Dashboard → Alerts → Usage tracking
- Key message: "Never exceed allocation, never miss supplementary access"

### For Investors
- Emphasize: Market size, scalability, technical architecture
- Demo flow: Dashboard → All pages → Show responsive mobile
- Key message: "$50M underserved market, 90% code reuse from proven platform"

### For Partners (Murrumbidgee Irrigation)
- Emphasize: White-label capabilities, customer value, integration
- Demo flow: Login (show MI branding) → Dashboard → Entitlements
- Key message: "Add intelligence layer to your telemetry infrastructure"

---

## 🚧 Known Limitations (Demo Only)

This is a **static demo** with mock data. Features not implemented:
- ❌ No real database connection
- ❌ No authentication (login goes straight to dashboard)
- ❌ No actual API calls (allocation data is static)
- ❌ Forms don't save (manual entry is UI only)
- ❌ Countdown timer is client-side only
- ❌ Charts are custom-built (not using Recharts)

These are **intentional** - the demo is designed to showcase UX and features, not backend implementation.

---

## 📁 File Structure

```
app/water-demo/
├── page.tsx                    # Dashboard home
├── layout.tsx                  # Demo layout wrapper
├── login/
│   └── page.tsx               # Login page
├── entitlements/
│   └── page.tsx               # Entitlements breakdown
├── usage/
│   └── page.tsx               # Usage tracking
├── alerts/
│   └── page.tsx               # Alerts center
└── README.md                  # This file

components/water-demo/
├── WaterAccountSummaryCard.tsx
├── EntitlementCard.tsx
├── UsageHistoryChart.tsx
└── SupplementaryAlert.tsx

lib/
└── demo-data.ts               # Mock data (600+ lines)
```

---

## 🎯 Next Steps After Demo

1. **Feedback Collection**
   - What features resonated most?
   - What's missing or confusing?
   - Willingness to pay at $75/month?

2. **Technical Implementation**
   - Build real backend (FastAPI + PostgreSQL)
   - Integrate NSW DPIE allocation scraping
   - Connect telemetry provider APIs
   - Implement authentication

3. **Pilot Program**
   - Target: 20 farmers in Murrumbidgee Valley
   - Duration: 3 months
   - Goal: Validate product-market fit

4. **Go-to-Market**
   - Partner with Murrumbidgee Irrigation
   - Leverage NSW Government Telemetry Uplift Program
   - Expand to Murray, Lachlan valleys

---

## 📞 Contact & Feedback

For questions about this demo or the WaterRight product:
- **Email**: [Your email]
- **GitHub**: [Your repo]
- **Demo Link**: [Deployed demo URL if available]

---

## 📝 Version History

- **v1.0** (2025-01-28): Initial demo with 5 pages, 4 custom components, 600+ lines of mock data
- Screens: Login, Dashboard, Entitlements, Usage, Alerts
- Tech: Next.js 14, Shadcn/UI, Tailwind CSS

---

**Built with ❤️ for Australian farmers** 🌾💧
