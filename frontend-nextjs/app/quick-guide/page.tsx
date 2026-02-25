'use client';

import React from 'react';
import { Home, Zap, Clock, FileText, Building2, Landmark, CheckCircle, AlertCircle } from 'lucide-react';
import Link from 'next/link';

export default function QuickGuidePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="relative border-b shadow-sm overflow-hidden flex bg-white">
        <div className="relative flex-shrink-0">
          <svg className="h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
            <path d="M0 0 L16 0 Q36 14 28 28 Q20 42 36 56 L0 56 Z" fill="#0d9488" />
          </svg>
        </div>
        <a
          href="https://plotdetect.com.au/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 pr-4 py-3 md:py-4 hover:opacity-80 transition-opacity"
        >
          <img src="/logo.png" alt="PlotDetect" className="h-8 w-auto" />
          <span className="text-base font-semibold text-gray-900">PlotDetect</span>
        </a>
        <div className="flex-1 bg-teal-50 flex items-center justify-between px-4 py-3 md:py-4">
          <div>
            <h1 className="text-lg md:text-xl font-semibold tracking-tight text-teal-800">
              Quick Start Guide
            </h1>
            <p className="text-teal-600 text-xs hidden sm:block">
              4 approval pathways explained
            </p>
          </div>
          <Link
            href="/assessment"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-teal-600 text-white hover:bg-teal-700 transition-colors"
          >
            <Home className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Back to Assessment</span>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-6 md:py-8 space-y-6">

        {/* Regulatory Hierarchy - Simple Visual */}
        <div className="bg-white border rounded-lg shadow-sm p-4 md:p-6">
          <h2 className="text-base md:text-lg font-bold text-gray-900 mb-4">NSW Planning System (3 Layers)</h2>
          <div className="space-y-3">
            {/* SEPP Layer */}
            <div className="flex items-start gap-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
              <Landmark className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-purple-900 text-sm">SEPP (State Environmental Planning Policy)</div>
                <div className="text-xs text-purple-700 mt-0.5">State-wide rules: Exempt & Complying, BASIX, Heritage, Apartment Design</div>
              </div>
            </div>
            {/* LEP Layer */}
            <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <Building2 className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-amber-900 text-sm">LEP (Local Environmental Plan)</div>
                <div className="text-xs text-amber-700 mt-0.5">Council zones and limits: Height, FSR, Land Use Permissibility, Environmental Constraints (Flood, Bushfire, ANEF, Mine Subsidence, Landslide, Contaminated Land, Water Catchment, Biodiversity, Coastal, Acid Sulfate)</div>
              </div>
            </div>
            {/* DCP Layer */}
            <div className="flex items-start gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <FileText className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-green-900 text-sm">DCP (Development Control Plan)</div>
                <div className="text-xs text-green-700 mt-0.5">Detailed local design rules: Setbacks, Landscaping, Character, Parking</div>
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-500 text-center mt-4 px-2">
            ⚠️ All three layers apply to every property — check all tabs in PlotDetect
          </p>
        </div>

        {/* Pathways Overview */}
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
          <h3 className="font-semibold text-teal-900 mb-2 text-sm">Choose Your Pathway</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <div className="bg-white border border-emerald-300 rounded p-2 text-center">
              <div className="font-bold text-emerald-700">Pattern Book</div>
              <div className="text-emerald-600">10 days</div>
            </div>
            <div className="bg-white border border-purple-300 rounded p-2 text-center">
              <div className="font-bold text-purple-700">E&C CDC</div>
              <div className="text-purple-600">20 days</div>
            </div>
            <div className="bg-white border border-amber-300 rounded p-2 text-center">
              <div className="font-bold text-amber-700">Heritage</div>
              <div className="text-amber-600">30-90 days</div>
            </div>
            <div className="bg-white border border-blue-300 rounded p-2 text-center">
              <div className="font-bold text-blue-700">Standard DA</div>
              <div className="text-blue-600">30-90 days</div>
            </div>
          </div>
        </div>

        {/* Pathway 1: Pattern Book CDC */}
        <div className="bg-white border-2 border-emerald-500 rounded-lg shadow-sm overflow-hidden">
          <div className="bg-emerald-500 text-white px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              <h2 className="text-base md:text-lg font-bold">Pattern Book CDC (10-Day Fast Track)</h2>
            </div>
            <span className="bg-emerald-600 px-2 py-0.5 rounded text-xs font-bold">FASTEST</span>
          </div>
          <div className="p-4 md:p-6">
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 mb-4">
              <p className="text-xs md:text-sm text-emerald-900">
                <strong>New single-dwelling homes only.</strong> NSW Government Pattern Book designs get 10-day CDC approval.
                PlotDetect checks 217 exclusion triggers + 199 numeric standards to determine eligibility.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">1</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">SEPP Tab → Pattern Book CDC Card</div>
                  <div className="text-xs text-gray-600 mt-1">Check eligibility status. Green = eligible. Red = blocked (shows which triggers failed).</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">2</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Review Numeric Standards</div>
                  <div className="text-xs text-gray-600 mt-1">Site coverage, setbacks, height limits, parking spaces — all must comply.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">3</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls tab → Check Zone Permissibility</div>
                  <div className="text-xs text-gray-600 mt-1">Dwelling house must be permitted in the zone (usually R2, R3, R4).</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">4</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">DCP Tab → Verify No HCA/Heritage Restrictions</div>
                  <div className="text-xs text-gray-600 mt-1">Pattern Book excluded on heritage properties.</div>
                </div>
              </div>
            </div>

            <div className="mt-4 flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-900">
                <strong>Common blockers:</strong> Heritage conservation area, narrow lot (&lt;15m), steep slope (&gt;20%),
                acid sulfate soil, flood zone, bushfire zone, tree preservation order.
              </p>
            </div>
          </div>
        </div>

        {/* Pathway 2: Exempt & Complying CDC */}
        <div className="bg-white border border-purple-300 rounded-lg shadow-sm overflow-hidden">
          <div className="bg-purple-100 border-b border-purple-300 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-purple-700" />
              <h2 className="text-base md:text-lg font-bold text-purple-900">Exempt & Complying Development (CDC)</h2>
            </div>
            <span className="bg-purple-600 text-white px-2 py-0.5 rounded text-xs font-bold">20 DAYS</span>
          </div>
          <div className="p-4 md:p-6">
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-4">
              <p className="text-xs md:text-sm text-purple-900">
                <strong>Small-scale additions and alterations.</strong> Decks, garages, pools, fences, carports.
                Certifier approval only (no council DA). Must meet all SEPP Housing 2021 standards.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">1</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">SEPP Tab → Exempt & Complying Card</div>
                  <div className="text-xs text-gray-600 mt-1">Select work type (Deck/Garage/Pool/Fence). PlotDetect shows applicable standards.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">2</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Check All SEPP Provisions</div>
                  <div className="text-xs text-gray-600 mt-1">Area limits, height limits, setbacks, materials — every standard must pass.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">3</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls tab → Confirm Use Permitted</div>
                  <div className="text-xs text-gray-600 mt-1">Base land use must be allowed in zone.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">4</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">DCP Tab → Check Local Controls Don't Prohibit</div>
                  <div className="text-xs text-gray-600 mt-1">Some councils add restrictions beyond SEPP. Check DCP provisions.</div>
                </div>
              </div>
            </div>

            <div className="mt-4 p-3 bg-teal-50 border border-teal-200 rounded-lg">
              <p className="text-xs text-teal-900">
                <strong>✓ Pro tip:</strong> Click PDF icons to view exact SEPP provision wording for certifier documentation.
              </p>
            </div>
          </div>
        </div>

        {/* Pathway 3: Heritage Properties */}
        <div className="bg-white border border-amber-300 rounded-lg shadow-sm overflow-hidden">
          <div className="bg-amber-100 border-b border-amber-300 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Landmark className="h-5 w-5 text-amber-700" />
              <h2 className="text-base md:text-lg font-bold text-amber-900">Heritage Property Assessment</h2>
            </div>
            <span className="bg-amber-600 text-white px-2 py-0.5 rounded text-xs font-bold">30-90 DAYS</span>
          </div>
          <div className="p-4 md:p-6">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
              <p className="text-xs md:text-sm text-amber-900">
                <strong>Properties in Heritage Conservation Areas (HCA) or listed heritage items.</strong>
                Additional design controls apply. Heritage statements usually required.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">1</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Property Summary Panel → Check Heritage Status</div>
                  <div className="text-xs text-gray-600 mt-1">Shows if property is in HCA or heritage item. Note the HCA name.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">2</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls tab → HCA Card → Read Objectives</div>
                  <div className="text-xs text-gray-600 mt-1">Each HCA has specific conservation objectives. Design must align with these.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">3</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">DCP Tab → Heritage Provisions</div>
                  <div className="text-xs text-gray-600 mt-1">Controls for demolition, additions, materials, roofs, fencing, signage. Some HCAs have area-specific provisions.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">4</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">SEPP Tab → Check State Heritage Register</div>
                  <div className="text-xs text-gray-600 mt-1">If state-listed item, additional SEPP (Biodiversity & Conservation 2021) rules apply.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">5</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">All Tabs → Standard Controls Still Apply</div>
                  <div className="text-xs text-gray-600 mt-1">Heritage is <em>in addition to</em> normal LEP (height/FSR) and DCP (setbacks/parking) requirements.</div>
                </div>
              </div>
            </div>

            <div className="mt-4 p-3 bg-amber-50 border border-amber-300 rounded-lg">
              <p className="text-xs text-amber-900">
                <strong>Heritage tip:</strong> Inner West has 63 HCAs. Marrickville has area-specific provisions for 36 HCAs.
                Always check both general heritage controls AND area-specific provisions if shown.
              </p>
            </div>
          </div>
        </div>

        {/* Pathway 4: Standard DA */}
        <div className="bg-white border border-blue-300 rounded-lg shadow-sm overflow-hidden">
          <div className="bg-blue-100 border-b border-blue-300 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-700" />
              <h2 className="text-base md:text-lg font-bold text-blue-900">Standard Development Application</h2>
            </div>
            <span className="bg-blue-600 text-white px-2 py-0.5 rounded text-xs font-bold">30-90 DAYS</span>
          </div>
          <div className="p-4 md:p-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
              <p className="text-xs md:text-sm text-blue-900">
                <strong>Most common pathway.</strong> New buildings, major alterations, additions over E&C limits,
                commercial, multi-dwelling. Council assessment required.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">1</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls tab → Primary Development Standards</div>
                  <div className="text-xs text-gray-600 mt-1">Check: (1) Use permitted in zone? (2) Height limit? (3) FSR limit? These are mandatory.</div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">2</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">DCP Tab → Design Controls (Bulk of Assessment)</div>
                  <div className="text-xs text-gray-600 mt-1">
                    PlotDetect organizes ~100-200 provisions by topic: Parking, Setbacks, Landscaping, Character,
                    Solar Access, Privacy, Waste. Review each applicable category. Check precinct-specific controls.
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">3</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">SEPP Tab → State Policy Overlays</div>
                  <div className="text-xs text-gray-600 mt-1">
                    BASIX (all dwellings), Apartment Design Guide (3+ units), Heritage (if applicable),
                    Transport-Oriented Development (if near station). Check each relevant SEPP section.
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">4</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Export PDF Report for DA Package</div>
                  <div className="text-xs text-gray-600 mt-1">Click "Download PDF Report" to generate compliance checklist with all provisions and PDF page references.</div>
                </div>
              </div>
            </div>

            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-xs text-blue-900">
                <strong>DA prep tip:</strong> DCP is usually the longest section. Use the topic filters (top of DCP tab)
                to focus on relevant provisions. Click "View PDF" icons to verify exact wording in original DCP document.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Reference Tips */}
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
          <h3 className="font-semibold text-teal-900 mb-3 text-sm flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            Quick Navigation Tips
          </h3>
          <div className="space-y-2 text-xs text-teal-900">
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>Property Summary Panel (left):</strong> Shows zone, height limit, FSR, heritage status at a glance</span>
            </div>
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>PDF Icons:</strong> Click to view exact page from original LEP/DCP/SEPP document</span>
            </div>
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>Topic Filters (DCP tab):</strong> Use to show only relevant provisions (Parking, Heritage, etc.)</span>
            </div>
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>Pathway Comparison Card (SEPP tab):</strong> Shows eligibility across all 4 pathways simultaneously</span>
            </div>
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>All Three Tabs Apply:</strong> Even if using CDC, still check LEP (use permitted?) and DCP (local restrictions?)</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center pt-4">
          <p className="text-xs text-gray-500 mb-3">
            PlotDetect · Quick Start Guide · February 2026
          </p>
          <Link
            href="/assessment"
            className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors text-sm font-medium"
          >
            <Home className="h-4 w-4" />
            Start Property Assessment
          </Link>
        </div>

      </div>
    </div>
  );
}
