'use client';

import React, { useState } from 'react';
import {
  FileText, BookOpen, Workflow, Users, Home, ExternalLink,
  Zap, Clock, Landmark, AlertCircle, CheckCircle
} from 'lucide-react';
import Link from 'next/link';
import { COVERAGE_DISPLAY } from '@/lib/coverage';

export default function UserGuidePage() {
  const [activeTab, setActiveTab] = useState<'start' | 'understand' | 'workflows' | 'roles'>('start');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-slate-950 border-b border-slate-800/50 flex items-center justify-between px-4 py-3 md:py-4">
        <div className="flex items-center gap-4">
          <a href="/" className="hover:opacity-80 transition-opacity">
            <span className="text-base font-bold tracking-tight text-white">
              Plot<span className="text-teal-400">Detect</span>
            </span>
          </a>
          <div>
            <h1 className="text-lg md:text-xl font-semibold tracking-tight text-white">
              Complete User Guide
            </h1>
            <p className="text-slate-400 text-xs hidden sm:block">
              In-depth guide to NSW planning compliance
            </p>
          </div>
        </div>
        <Link
          href="/assessment"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-teal-600 text-white hover:bg-teal-500 transition-colors"
        >
          <Home className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Back to Assessment</span>
        </Link>
      </header>

      {/* Main Content */}
      <div className="max-w-5xl mx-auto px-4 py-6 md:py-8">
        {/* Tab Navigation */}
        <div className="bg-white border rounded-lg shadow-sm mb-6 overflow-hidden">
          <div className="grid grid-cols-2 md:grid-cols-4" role="tablist">
            <button
              role="tab"
              onClick={() => setActiveTab('start')}
              className={`px-4 py-3 text-xs md:text-sm font-medium transition-colors ${
                activeTab === 'start'
                  ? 'bg-teal-600 text-white'
                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
              }`}
            >
              <FileText className="h-4 w-4 mx-auto mb-1" />
              Getting Started
            </button>
            <button
              role="tab"
              onClick={() => setActiveTab('understand')}
              className={`px-4 py-3 text-xs md:text-sm font-medium transition-colors ${
                activeTab === 'understand'
                  ? 'bg-teal-600 text-white'
                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
              }`}
            >
              <BookOpen className="h-4 w-4 mx-auto mb-1" />
              SEPP • LEP • DCP
            </button>
            <button
              role="tab"
              onClick={() => setActiveTab('workflows')}
              className={`px-4 py-3 text-xs md:text-sm font-medium transition-colors ${
                activeTab === 'workflows'
                  ? 'bg-teal-600 text-white'
                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Workflow className="h-4 w-4 mx-auto mb-1" />
              Workflows
            </button>
            <button
              role="tab"
              onClick={() => setActiveTab('roles')}
              className={`px-4 py-3 text-xs md:text-sm font-medium transition-colors ${
                activeTab === 'roles'
                  ? 'bg-teal-600 text-white'
                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Users className="h-4 w-4 mx-auto mb-1" />
              For Your Role
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="bg-white border rounded-lg shadow-sm p-4 md:p-8">

          {/* Getting Started Tab */}
          {activeTab === 'start' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-2">Getting Started</h2>
                <p className="text-sm md:text-base text-gray-600">Three simple steps to assess any NSW property</p>
              </div>

              <div className="space-y-4">
                <div className="flex gap-3 md:gap-4 items-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold text-sm">
                    1
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 mb-1 text-sm md:text-base">Enter an Address</h3>
                    <p className="text-xs md:text-sm text-gray-600">
                      Type any NSW property address in the search bar. PlotDetect automatically fetches
                      live planning data from NSW Planning Portal, including:
                    </p>
                    <ul className="text-xs md:text-sm text-gray-600 list-disc ml-5 mt-2 space-y-1">
                      <li>Zone classification (R2, B4, etc.)</li>
                      <li>Height and FSR limits</li>
                      <li>Heritage conservation area status</li>
                      <li>Environmental constraints (flood, bushfire, ANEF, mine subsidence, landslide, contaminated land, water catchment, biodiversity, coastal, acid sulfate)</li>
                      <li>Former council area (for amalgamated councils)</li>
                    </ul>
                  </div>
                </div>

                <div className="flex gap-3 md:gap-4 items-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold text-sm">
                    2
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 mb-1 text-sm md:text-base">Navigate the Three Tabs</h3>
                    <p className="text-xs md:text-sm text-gray-600 mb-3">
                      Results are organized into three regulatory layers. Check all three tabs:
                    </p>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="bg-purple-50 border border-purple-200 rounded p-2 text-center">
                        <div className="text-xs font-bold text-purple-700">SEPP</div>
                        <div className="text-xs text-purple-600">State Policies</div>
                      </div>
                      <div className="bg-amber-50 border border-amber-200 rounded p-2 text-center">
                        <div className="text-xs font-bold text-amber-700">LEP</div>
                        <div className="text-xs text-amber-600">Zone Rules</div>
                      </div>
                      <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
                        <div className="text-xs font-bold text-green-700">DCP</div>
                        <div className="text-xs text-green-600">Local Controls</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 md:gap-4 items-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold text-sm">
                    3
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 mb-1 text-sm md:text-base">Review Provisions</h3>
                    <p className="text-xs md:text-sm text-gray-600 mb-2">
                      Each tab shows provisions organized by topic. Use these features:
                    </p>
                    <ul className="text-xs md:text-sm text-gray-600 list-disc ml-5 space-y-1">
                      <li><strong>Expand cards</strong> to see detailed requirements</li>
                      <li><strong>Click PDF icons</strong> to view original document pages</li>
                      <li><strong>Use topic filters</strong> (DCP tab) to show only relevant provisions</li>
                      <li><strong>Download PDF report</strong> for complete compliance package</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 md:p-4 mt-6">
                <p className="text-xs md:text-sm text-teal-900">
                  <strong>💡 Critical:</strong> All three tabs apply to your property. Checking only one tab
                  gives an incomplete picture. Always review SEPP + LEP + DCP for full compliance assessment.
                </p>
              </div>
            </div>
          )}

          {/* Understanding SEPP/LEP/DCP Tab */}
          {activeTab === 'understand' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-2">Understanding SEPP • LEP • DCP</h2>
                <p className="text-sm md:text-base text-gray-600">NSW planning has three regulatory layers that work together</p>
              </div>

              {/* Visual Hierarchy */}
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 md:p-4 bg-purple-50 border-l-4 border-purple-600 rounded-r-lg">
                  <Landmark className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-purple-900 text-sm md:text-base">Layer 1: SEPP (State Environmental Planning Policy)</div>
                    <div className="text-xs md:text-sm text-purple-700 mt-1">State-wide rules covering E&C, BASIX, Heritage, Apartment Design</div>
                  </div>
                  <div className="text-xs font-bold text-purple-600 flex-shrink-0">HIGHEST</div>
                </div>

                <div className="flex items-center justify-center">
                  <div className="text-gray-400">↓</div>
                </div>

                <div className="flex items-start gap-3 p-3 md:p-4 bg-amber-50 border-l-4 border-amber-600 rounded-r-lg">
                  <FileText className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-amber-900 text-sm md:text-base">Layer 2: LEP (Local Environmental Plan)</div>
                    <div className="text-xs md:text-sm text-amber-700 mt-1">Council zones and limits: Height, FSR, Land Use Permissibility</div>
                  </div>
                </div>

                <div className="flex items-center justify-center">
                  <div className="text-gray-400">↓</div>
                </div>

                <div className="flex items-start gap-3 p-3 md:p-4 bg-green-50 border-l-4 border-green-600 rounded-r-lg">
                  <FileText className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-green-900 text-sm md:text-base">Layer 3: DCP (Development Control Plan)</div>
                    <div className="text-xs md:text-sm text-green-700 mt-1">Detailed local design rules: Setbacks, Character, Materials</div>
                  </div>
                  <div className="text-xs font-bold text-green-600 flex-shrink-0">DETAILED</div>
                </div>
              </div>

              {/* Detailed Explanations */}
              <div className="space-y-4 mt-8">

                {/* SEPP Details */}
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                  <h3 className="font-bold text-purple-900 mb-2 text-sm md:text-base">SEPP — State Environmental Planning Policy</h3>
                  <p className="text-xs md:text-sm text-purple-800 mb-3">
                    <strong>What it is:</strong> State-wide rules that apply across all of NSW, overriding local controls where inconsistent
                  </p>
                  <p className="text-xs md:text-sm text-purple-700 mb-2"><strong>What you'll find in PlotDetect:</strong></p>
                  <ul className="text-xs md:text-sm text-purple-700 list-disc ml-5 space-y-1">
                    <li><strong>Pattern Book CDC:</strong> 10-day fast-track approval for new single-dwelling homes using government pattern book designs</li>
                    <li><strong>Exempt & Complying Development:</strong> Standards for small-scale work (decks, fences, carports, pools) with 20-day certifier approval</li>
                    <li><strong>BASIX:</strong> Water and energy sustainability targets for all new dwellings</li>
                    <li><strong>Apartment Design Guide:</strong> Design standards for residential flat buildings (3+ units)</li>
                    <li><strong>Heritage:</strong> State heritage item protections (additional to local heritage controls)</li>
                    <li><strong>Housing:</strong> TOD precincts, low-rise housing diversity, design quality principles</li>
                  </ul>
                </div>

                {/* LEP Details */}
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <h3 className="font-bold text-amber-900 mb-2 text-sm md:text-base">LEP — Local Environmental Plan</h3>
                  <p className="text-xs md:text-sm text-amber-800 mb-3">
                    <strong>What it is:</strong> Council-specific zoning rules and development limits that define what can be built where
                  </p>
                  <p className="text-xs md:text-sm text-amber-700 mb-2"><strong>What you'll find in PlotDetect:</strong></p>
                  <ul className="text-xs md:text-sm text-amber-700 list-disc ml-5 space-y-1">
                    <li><strong>Zone:</strong> Land use classification (R2 Low Density Residential, B4 Mixed Use, etc.)</li>
                    <li><strong>Height limits:</strong> Maximum building height for the zone (e.g., 8.5m for single dwelling)</li>
                    <li><strong>FSR limits:</strong> Maximum floor space ratio (e.g., 0.5:1 means 500m² floor space on 1000m² lot)</li>
                    <li><strong>Land use table:</strong> What uses are permitted, prohibited, or require consent in this zone</li>
                    <li><strong>Heritage Conservation Areas:</strong> HCA boundaries and objectives for heritage properties</li>
                    <li><strong>Environmental Constraints:</strong> Flood planning area, bushfire prone land, aircraft noise (ANEF), mine subsidence district, landslide risk, contaminated land register, drinking water catchment, terrestrial biodiversity, coastal management areas, acid sulfate soils</li>
                  </ul>
                </div>

                {/* DCP Details */}
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <h3 className="font-bold text-green-900 mb-2 text-sm md:text-base">DCP — Development Control Plan</h3>
                  <p className="text-xs md:text-sm text-green-800 mb-3">
                    <strong>What it is:</strong> Detailed local design rules (typically 100-200 provisions per property) that guide how development should look and function
                  </p>
                  <p className="text-xs md:text-sm text-green-700 mb-2"><strong>What you'll find in PlotDetect:</strong></p>
                  <ul className="text-xs md:text-sm text-green-700 list-disc ml-5 space-y-1">
                    <li><strong>Setbacks:</strong> Minimum distances from boundaries (front, side, rear)</li>
                    <li><strong>Character controls:</strong> Building materials, roof forms, fencing styles, street presentation</li>
                    <li><strong>Heritage controls:</strong> Rules for Heritage Conservation Areas (demolition, additions, materials)</li>
                    <li><strong>Parking:</strong> Required parking spaces, driveway widths, garage dimensions</li>
                    <li><strong>Landscaping:</strong> Deep soil zones, tree retention, front yard landscaping requirements</li>
                    <li><strong>Private open space:</strong> Minimum courtyard and yard sizes</li>
                    <li><strong>Solar access:</strong> Overshadowing controls for neighbours</li>
                    <li><strong>Privacy:</strong> Window placement, screening requirements</li>
                  </ul>
                </div>

              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 md:p-4 mt-6">
                <p className="text-xs md:text-sm text-blue-900">
                  <strong>⚠️ Important:</strong> All three layers apply simultaneously. Your development
                  must comply with SEPP <em>and</em> LEP <em>and</em> DCP requirements. State policies (SEPP)
                  override local rules where inconsistent, but most provisions work together cumulatively.
                </p>
              </div>
            </div>
          )}

          {/* Workflows Tab */}
          {activeTab === 'workflows' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-2">Approval Pathways & Workflows</h2>
                <p className="text-sm md:text-base text-gray-600">Four different pathways to development approval in NSW</p>
              </div>

              {/* Pathway Comparison */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
                <div className="bg-emerald-50 border-2 border-emerald-500 rounded-lg p-3 text-center">
                  <Zap className="h-5 w-5 text-emerald-600 mx-auto mb-1" />
                  <div className="font-bold text-emerald-700 text-xs md:text-sm">Pattern Book</div>
                  <div className="text-emerald-600 text-xs">10 days</div>
                </div>
                <div className="bg-purple-50 border-2 border-purple-500 rounded-lg p-3 text-center">
                  <Clock className="h-5 w-5 text-purple-600 mx-auto mb-1" />
                  <div className="font-bold text-purple-700 text-xs md:text-sm">E&C CDC</div>
                  <div className="text-purple-600 text-xs">20 days</div>
                </div>
                <div className="bg-amber-50 border-2 border-amber-500 rounded-lg p-3 text-center">
                  <Landmark className="h-5 w-5 text-amber-600 mx-auto mb-1" />
                  <div className="font-bold text-amber-700 text-xs md:text-sm">Heritage</div>
                  <div className="text-amber-600 text-xs">30-90 days</div>
                </div>
                <div className="bg-blue-50 border-2 border-blue-500 rounded-lg p-3 text-center">
                  <FileText className="h-5 w-5 text-blue-600 mx-auto mb-1" />
                  <div className="font-bold text-blue-700 text-xs md:text-sm">Standard DA</div>
                  <div className="text-blue-600 text-xs">30-90 days</div>
                </div>
              </div>

              {/* Workflow 1: Pattern Book CDC */}
              <div className="bg-emerald-50 border-l-4 border-emerald-600 rounded-r-lg p-4 md:p-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-emerald-900 text-sm md:text-lg flex items-center gap-2">
                    <span className="bg-emerald-600 text-white px-2 py-0.5 rounded text-xs font-bold">PATHWAY 1</span>
                    Pattern Book CDC (10-Day Fast Track)
                  </h3>
                  <Zap className="h-5 w-5 text-emerald-600 flex-shrink-0" />
                </div>

                <div className="bg-white border border-emerald-200 rounded-lg p-3 mb-4">
                  <p className="text-xs md:text-sm text-emerald-900">
                    <strong>New single-dwelling homes only.</strong> NSW Government Pattern Book designs get 10-day CDC approval.
                    PlotDetect checks 217 exclusion triggers + 199 numeric standards automatically.
                  </p>
                </div>

                <ol className="space-y-3 text-xs md:text-sm text-emerald-900">
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-emerald-200 text-emerald-800 flex items-center justify-center text-xs">1</span>
                    <div className="flex-1 min-w-0">
                      <strong>SEPP Tab → Pattern Book CDC Card</strong>
                      <p className="text-emerald-700 mt-1">Check eligibility status. Green = eligible. Red = blocked (shows which triggers failed).
                      PlotDetect automatically scans property against all 217 exclusion triggers including heritage, lot size, slope, bushfire, flood, tree preservation.</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-emerald-200 text-emerald-800 flex items-center justify-center text-xs">2</span>
                    <div className="flex-1 min-w-0">
                      <strong>Review 199 Numeric Standards</strong>
                      <p className="text-emerald-700 mt-1">Site coverage, setbacks, height limits, parking spaces, landscaping percentages — all must comply with Pattern Book standards (often stricter than normal DCP).</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-emerald-200 text-emerald-800 flex items-center justify-center text-xs">3</span>
                    <div className="flex-1 min-w-0">
                      <strong>Planning Controls tab → Check Zone Permissibility</strong>
                      <p className="text-emerald-700 mt-1">Dwelling house must be permitted in the zone (usually R2, R3, R4). Check height and FSR limits.</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-emerald-200 text-emerald-800 flex items-center justify-center text-xs">4</span>
                    <div className="flex-1 min-w-0">
                      <strong>DCP Tab → Verify No HCA/Heritage Restrictions</strong>
                      <p className="text-emerald-700 mt-1">Pattern Book excluded on any heritage-listed property or Heritage Conservation Area. Also check for local character controls that might restrict design.</p>
                    </div>
                  </li>
                </ol>

                <div className="mt-4 flex items-start gap-2 p-3 bg-white border border-emerald-200 rounded-lg">
                  <AlertCircle className="h-4 w-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs md:text-sm text-emerald-900">
                      <strong>Common blockers:</strong> Heritage conservation area, narrow lot (&lt;15m frontage),
                      steep slope (&gt;20%), acid sulfate soil, flood planning area, bushfire prone land,
                      tree preservation order, contaminated land, rail/airport noise zone.
                    </p>
                  </div>
                </div>
              </div>

              {/* Workflow 2: E&C CDC */}
              <div className="bg-purple-50 border-l-4 border-purple-600 rounded-r-lg p-4 md:p-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-purple-900 text-sm md:text-lg flex items-center gap-2">
                    <span className="bg-purple-600 text-white px-2 py-0.5 rounded text-xs font-bold">PATHWAY 2</span>
                    Exempt & Complying Development (CDC)
                  </h3>
                  <Clock className="h-5 w-5 text-purple-600 flex-shrink-0" />
                </div>

                <div className="bg-white border border-purple-200 rounded-lg p-3 mb-4">
                  <p className="text-xs md:text-sm text-purple-900">
                    <strong>Small-scale additions and alterations.</strong> Decks, garages, pools, fences, carports.
                    Certifier approval only (no council DA). Must meet all SEPP Housing 2021 standards.
                  </p>
                </div>

                <ol className="space-y-3 text-xs md:text-sm text-purple-900">
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-purple-200 text-purple-800 flex items-center justify-center text-xs">1</span>
                    <div className="flex-1 min-w-0">
                      <strong>SEPP Tab → Exempt & Complying Card</strong>
                      <p className="text-purple-700 mt-1">Select work type (Deck/Garage/Pool/Fence). PlotDetect shows applicable standards and numeric limits parsed from SEPP provisions.</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-purple-200 text-purple-800 flex items-center justify-center text-xs">2</span>
                    <div className="flex-1 min-w-0">
                      <strong>Check All SEPP Provisions</strong>
                      <p className="text-purple-700 mt-1">Area limits, height limits, setbacks, materials, visibility, access — every standard must pass. Click PDF icons to verify exact wording for certifier documentation.</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-purple-200 text-purple-800 flex items-center justify-center text-xs">3</span>
                    <div className="flex-1 min-w-0">
                      <strong>Planning Controls tab → Confirm Use Permitted</strong>
                      <p className="text-purple-700 mt-1">Base land use must be allowed in zone. For example, pools require dwelling house to be permitted.</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-purple-200 text-purple-800 flex items-center justify-center text-xs">4</span>
                    <div className="flex-1 min-w-0">
                      <strong>DCP Tab → Check Local Controls Don't Prohibit</strong>
                      <p className="text-purple-700 mt-1">Some councils add restrictions beyond SEPP. Check DCP provisions don't conflict. Heritage properties often have stricter fencing/material controls.</p>
                    </div>
                  </li>
                </ol>

                <div className="mt-4 p-3 bg-white border border-purple-200 rounded-lg">
                  <CheckCircle className="h-4 w-4 text-purple-600 inline mr-2" />
                  <span className="text-xs md:text-sm text-purple-900">
                    <strong>Pro tip:</strong> E&C compliance requires ALL THREE layers to pass. Don't skip LEP or DCP checks — they can still block complying development.
                  </span>
                </div>
              </div>

              {/* Workflow 3: Heritage */}
              <div className="bg-amber-50 border-l-4 border-amber-600 rounded-r-lg p-4 md:p-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-amber-900 text-sm md:text-lg flex items-center gap-2">
                    <span className="bg-amber-600 text-white px-2 py-0.5 rounded text-xs font-bold">PATHWAY 3</span>
                    Heritage Property Assessment
                  </h3>
                  <Landmark className="h-5 w-5 text-amber-600 flex-shrink-0" />
                </div>

                <div className="bg-white border border-amber-200 rounded-lg p-3 mb-4">
                  <p className="text-xs md:text-sm text-amber-900">
                    <strong>Properties in Heritage Conservation Areas (HCA) or listed heritage items.</strong>
                    Additional design controls apply. Heritage statements usually required. Inner West has 63 HCAs.
                  </p>
                </div>

                <ol className="space-y-3 text-xs md:text-sm text-amber-900">
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-amber-200 text-amber-800 flex items-center justify-center text-xs">1</span>
                    <div className="flex-1 min-w-0">
                      <strong>Property Summary Panel → Check Heritage Status</strong>
                      <p className="text-amber-700 mt-1">Shows if property is in HCA or heritage item. Note the HCA name (e.g., "Annandale North HCA").</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-amber-200 text-amber-800 flex items-center justify-center text-xs">2</span>
                    <div className="flex-1 min-w-0">
                      <strong>Planning Controls tab → HCA Card → Read Objectives</strong>
                      <p className="text-amber-700 mt-1">Each HCA has specific conservation objectives describing heritage significance and character. Design must align with these objectives.</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-amber-200 text-amber-800 flex items-center justify-center text-xs">3</span>
                    <div className="flex-1 min-w-0">
                      <strong>DCP Tab → Heritage Provisions</strong>
                      <p className="text-amber-700 mt-1">Controls for demolition, additions, materials, roofs, fencing, signage, solar panels. Marrickville has area-specific provisions for 36 HCAs (check both general + area-specific).</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-amber-200 text-amber-800 flex items-center justify-center text-xs">4</span>
                    <div className="flex-1 min-w-0">
                      <strong>SEPP Tab → Check State Heritage Register</strong>
                      <p className="text-amber-700 mt-1">If state-listed item, additional SEPP (Biodiversity & Conservation 2021) rules apply on top of local controls.</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-amber-200 text-amber-800 flex items-center justify-center text-xs">5</span>
                    <div className="flex-1 min-w-0">
                      <strong>All Tabs → Standard Controls Still Apply</strong>
                      <p className="text-amber-700 mt-1">Heritage is <em>in addition to</em> normal LEP (height/FSR) and DCP (setbacks/parking) requirements. All provisions cumulate.</p>
                    </div>
                  </li>
                </ol>

                <div className="mt-4 p-3 bg-white border border-amber-200 rounded-lg">
                  <p className="text-xs md:text-sm text-amber-900">
                    <strong>Heritage tip:</strong> Consult council heritage advisor before lodging DA.
                    Heritage Impact Statement required. Consider architect with heritage experience.
                    Pattern Book CDC and most E&C work excluded on heritage properties.
                  </p>
                </div>
              </div>

              {/* Workflow 4: Standard DA */}
              <div className="bg-blue-50 border-l-4 border-blue-600 rounded-r-lg p-4 md:p-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-blue-900 text-sm md:text-lg flex items-center gap-2">
                    <span className="bg-blue-600 text-white px-2 py-0.5 rounded text-xs font-bold">PATHWAY 4</span>
                    Standard Development Application
                  </h3>
                  <FileText className="h-5 w-5 text-blue-600 flex-shrink-0" />
                </div>

                <div className="bg-white border border-blue-200 rounded-lg p-3 mb-4">
                  <p className="text-xs md:text-sm text-blue-900">
                    <strong>Most common pathway.</strong> New buildings, major alterations, additions over E&C limits,
                    commercial, multi-dwelling. Council assessment required. 30-90 day timeline.
                  </p>
                </div>

                <ol className="space-y-3 text-xs md:text-sm text-blue-900">
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-blue-200 text-blue-800 flex items-center justify-center text-xs">1</span>
                    <div className="flex-1 min-w-0">
                      <strong>Planning Controls tab → Primary Development Standards</strong>
                      <p className="text-blue-700 mt-1">Check three mandatory requirements: (1) Is use permitted in zone? (2) Does design meet height limit? (3) Does design meet FSR limit? These are pass/fail — no variations without clause 4.6 justification.</p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-blue-200 text-blue-800 flex items-center justify-center text-xs">2</span>
                    <div className="flex-1 min-w-0">
                      <strong>DCP Tab → Design Controls (Bulk of Assessment)</strong>
                      <p className="text-blue-700 mt-1">
                        PlotDetect organizes ~100-200 provisions by topic: Parking, Setbacks, Landscaping, Character,
                        Solar Access, Privacy, Waste. Review each applicable category. Use topic filters to focus on relevant provisions.
                        Check precinct-specific controls (Inner West has 102 precincts with unique requirements).
                      </p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-blue-200 text-blue-800 flex items-center justify-center text-xs">3</span>
                    <div className="flex-1 min-w-0">
                      <strong>SEPP Tab → State Policy Overlays</strong>
                      <p className="text-blue-700 mt-1">
                        Check applicable state policies: BASIX (all dwellings), Apartment Design Guide (3+ units),
                        Heritage (if applicable), Transport-Oriented Development (if near station),
                        Housing (design quality principles for multi-dwelling).
                      </p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-blue-200 text-blue-800 flex items-center justify-center text-xs">4</span>
                    <div className="flex-1 min-w-0">
                      <strong>Export PDF Report for DA Package</strong>
                      <p className="text-blue-700 mt-1">Click "Download PDF Report" to generate compliance checklist with all provisions, PDF page references, and property summary. Use this to brief your architect/designer on all applicable controls.</p>
                    </div>
                  </li>
                </ol>

                <div className="mt-4 p-3 bg-white border border-blue-200 rounded-lg">
                  <p className="text-xs md:text-sm text-blue-900">
                    <strong>DA prep tip:</strong> DCP is usually the longest section (100+ provisions).
                    Use topic filters to focus on relevant controls. Click "View PDF" icons to verify exact wording.
                    PlotDetect filters {COVERAGE_DISPLAY.provisionsTotal} provisions down to ~100 relevant ones for your specific property.
                  </p>
                </div>
              </div>

              {/* DA Mode & SEE Drafting */}
              <div className="bg-teal-50 border-l-4 border-teal-600 rounded-r-lg p-4 md:p-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-teal-900 text-sm md:text-lg flex items-center gap-2">
                    <span className="bg-teal-600 text-white px-2 py-0.5 rounded text-xs font-bold">DA MODE</span>
                    DA Mode: Annotation &amp; SEE Draft
                  </h3>
                  <CheckCircle className="h-5 w-5 text-teal-600 flex-shrink-0" />
                </div>

                <div className="bg-white border border-teal-200 rounded-lg p-3 mb-4">
                  <p className="text-xs md:text-sm text-teal-900">
                    <strong>Record compliance notes against each DCP provision and export a Statement of Environmental Effects draft.</strong>{' '}
                    DA Mode is built around a three-step workflow shown with large ①②③ labels in the DCP tab.
                    Assessment is non-linear — work by topic, across multiple sessions, at your own pace.
                    The session auto-saves and persists across page reloads.
                  </p>
                </div>

                <ol className="space-y-4 text-xs md:text-sm text-teal-900">
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-teal-200 text-teal-800 flex items-center justify-center text-xs">①</span>
                    <div className="flex-1 min-w-0">
                      <strong>Enable DA Mode</strong>
                      <p className="text-teal-700 mt-1">
                        The DA Mode button sits at the top left of the DCP tab with a large ① label.
                        Toggle it on — the button turns teal — to unlock the development description form
                        (② panel) and annotation controls on every provision.
                      </p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-teal-200 text-teal-800 flex items-center justify-center text-xs">②</span>
                    <div className="flex-1 min-w-0">
                      <strong>Set Development Type &amp; Run Triage</strong>
                      <p className="text-teal-700 mt-1">
                        The ② panel has two fields: development type (dropdown — pergola, driveway,
                        extension, etc.) and works description (free text: dimensions, materials, location).
                        Together these form the SEE introduction sentence.
                      </p>
                      <p className="text-teal-700 mt-2">
                        Click <strong>Run triage →</strong> to open the triage dialog. Answer 6 factual
                        yes/no questions: new impervious surfaces, trees affected, pool or spa, new fencing,
                        parking or driveway works, signage. Provisions are excluded only when their trigger
                        is factually impossible — &#8220;Don&#8217;t know&#8221; always keeps provisions in scope.
                      </p>
                      <p className="text-teal-700 mt-2">
                        <strong>First-class passengers:</strong> If the property is in a Heritage Conservation
                        Area or Precinct, those provision groups are shown first in the scope summary and cannot
                        be triaged out — they are always in scope. After triage, the ② panel shows a persistent
                        scope summary: Heritage layer count (all 300+ heritage provisions across subtopics
                        like Additions, Demolition, Character), other included topic counts, and excluded topics
                        (collapsible). A live completion counter shows assessed / triaged out / still to review.
                      </p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-teal-200 text-teal-800 flex items-center justify-center text-xs">③</span>
                    <div className="flex-1 min-w-0">
                      <strong>Review &amp; Annotate Provisions</strong>
                      <p className="text-teal-700 mt-1">
                        Use topic filter chips above the provisions list to focus on one topic at a time
                        (Heritage, Setbacks, Parking, etc.). For each provision, select
                        <strong> Complies</strong>, <strong>Varies</strong>, or <strong>N/A</strong>
                        and type a compliance note. Saves automatically as you work.
                      </p>
                      <p className="text-teal-700 mt-1">
                        Triaged-out provisions are locked as &#8220;N/A &#183; set by intake&#8221; — no manual
                        action required. Work across sessions: the completion counter in the ② panel
                        always shows exactly where you are.
                      </p>
                    </div>
                  </li>
                  <li className="flex gap-2 md:gap-3">
                    <span className="font-bold flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full bg-teal-200 text-teal-800 flex items-center justify-center text-xs">4</span>
                    <div className="flex-1 min-w-0">
                      <strong>Export SEE Draft PDF</strong>
                      <p className="text-teal-700 mt-1">
                        Click <strong>Export SEE Draft</strong>. If provisions remain unannotated, the dialog
                        names the count — you decide whether to export now or continue reviewing.
                        The PDF includes annotated provisions, compliance notes, and a cover page with confirmed
                        triage answers as an audit trail. Re-export as many times as needed as the design evolves.
                        Each export is a dated snapshot; the session stays fully editable after export.
                      </p>
                    </div>
                  </li>
                </ol>

                <div className="mt-4 p-3 bg-white border border-teal-200 rounded-lg space-y-2">
                  <p className="text-xs md:text-sm text-teal-900">
                    <strong>Why structured triage?</strong> Free-text filtering by AI creates liability risk (false negatives). Structured triage only excludes provisions when their trigger is factually impossible &#8212; legally defensible, no interpretation required.
                  </p>
                  <p className="text-xs md:text-sm text-teal-900">
                    <strong>Multi-session work:</strong> Return any time and the ② completion counter shows where you left off — Heritage 12/47, Setbacks 0/18 — so you know exactly where to continue without any re-orientation.
                  </p>
                </div>
              </div>

            </div>
          )}

          {/* For Your Role Tab */}
          {activeTab === 'roles' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-2">How to Use PlotDetect — By Role</h2>
                <p className="text-sm md:text-base text-gray-600">Tailored guidance for different professionals</p>
              </div>

              {/* Town Planners */}
              <div className="bg-emerald-50 border-l-4 border-emerald-600 rounded-r-lg p-4">
                <h3 className="font-bold text-emerald-900 mb-3 flex items-center gap-2 text-sm md:text-base">
                  <span className="bg-emerald-600 text-white px-2 py-1 rounded text-xs md:text-sm">Town Planners</span>
                </h3>
                <ul className="space-y-2 text-xs md:text-sm text-emerald-800">
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>DA prep acceleration:</strong> Use PlotDetect to understand complete regulatory context (SEPP/LEP/DCP) in 60 seconds instead of 2 hours of PDF reading</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Clause references:</strong> PDF page numbers link directly to source documents for accurate citation in planning reports</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Policy hierarchy:</strong> Understand how State policies (SEPP) interact with local controls (LEP/DCP) — PlotDetect shows override relationships</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Pattern Book feasibility:</strong> Quickly assess if site eligible for 10-day Pattern Book CDC before recommending slower DA pathway</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Export for clients:</strong> Download PDF report with complete compliance checklist to send to clients</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>DA Mode &#8212; SEE drafting:</strong> Enable DA Mode (① label, top of DCP tab) to unlock annotation controls. Set development type and description in the ② panel, run triage to confirm scope (Heritage HCA and Precinct provisions are always included as first-class passengers), then annotate provisions (③) by topic across sessions. Export a Statement of Environmental Effects draft with confirmed triage answers as an audit trail on the cover page. Re-export at any stage as the design evolves.</span>
                  </li>
                </ul>
              </div>

              {/* Architects */}
              <div className="bg-violet-50 border-l-4 border-violet-600 rounded-r-lg p-4">
                <h3 className="font-bold text-violet-900 mb-3 flex items-center gap-2 text-sm md:text-base">
                  <span className="bg-violet-600 text-white px-2 py-1 rounded text-xs md:text-sm">Architects</span>
                </h3>
                <ul className="space-y-2 text-xs md:text-sm text-violet-800">
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Pre-design feasibility:</strong> Check LEP height/FSR limits + DCP setbacks before starting schematic design — avoid redesign loops</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Pattern Book screening:</strong> Identify if site eligible for 10-day Pattern Book CDC — huge value-add for clients seeking fast approval</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Character controls:</strong> DCP character provisions define materials, roof forms, fencing styles — use these to guide design language</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>ADG compliance:</strong> For apartments (3+ units), check SEPP tab Apartment Design Guide card for detailed design criteria (solar access, cross-ventilation, storage)</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Heritage HCAs:</strong> Heritage conservation areas have specific design controls for additions/alterations — understand these before proposing materials/forms</span>
                  </li>
                </ul>
              </div>

              {/* Developers */}
              <div className="bg-orange-50 border-l-4 border-orange-600 rounded-r-lg p-4">
                <h3 className="font-bold text-orange-900 mb-3 flex items-center gap-2 text-sm md:text-base">
                  <span className="bg-orange-600 text-white px-2 py-1 rounded text-xs md:text-sm">Developers</span>
                </h3>
                <ul className="space-y-2 text-xs md:text-sm text-orange-800">
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Site acquisition due diligence:</strong> Enter address → see height/FSR limits, zone, heritage status in 30 seconds — inform purchase decisions</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Pattern Book CDC fast-track:</strong> Check if site eligible for 10-day approval pathway — significantly de-risks timeline and holding costs</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Development potential:</strong> LEP FSR limit × lot size = maximum GFA (e.g., 0.5:1 FSR on 600m² = 300m² max floor space)</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Pathway comparison:</strong> SEPP tab shows cross-pathway analysis — Pattern Book vs E&C vs Standard DA — choose fastest viable pathway</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Heritage red flags:</strong> Heritage conservation area = slower DA pathway + heritage impact statement required — factor into timeline/budget</span>
                  </li>
                </ul>
              </div>

              {/* Certifiers */}
              <div className="bg-slate-50 border-l-4 border-slate-600 rounded-r-lg p-4">
                <h3 className="font-bold text-slate-900 mb-3 flex items-center gap-2 text-sm md:text-base">
                  <span className="bg-slate-600 text-white px-2 py-1 rounded text-xs md:text-sm">Certifiers</span>
                </h3>
                <ul className="space-y-2 text-xs md:text-sm text-slate-800">
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>CDC pre-screening:</strong> Use E&C workflow to verify all three compliance layers (SEPP + LEP + DCP) before accepting CDC engagement</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Pattern Book CDC eligibility:</strong> Check Pattern Book card shows 217 exclusion triggers — identify blockers before client engages architect</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>PDF verification:</strong> Click PDF icons to view original SEPP/LEP/DCP pages and verify provision text for audit trail</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Cross-check DCP controls:</strong> Don't stop at E&C SEPP — DCP controls can still apply to complying development (e.g., heritage fencing materials)</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Heritage flags:</strong> Property summary shows heritage status — check DCP heritage card if flagged (often blocks CDC pathway)</span>
                  </li>
                </ul>
              </div>

            </div>
          )}

        </div>

        {/* Footer */}
        <div className="mt-6 md:mt-8">
          <div className="bg-white border rounded-lg shadow-sm p-4 md:p-6 mb-4">
            <h3 className="font-bold text-gray-900 mb-2 text-sm md:text-base">Need More Help?</h3>
            <p className="text-xs md:text-sm text-gray-600 mb-4">
              PlotDetect shows planning provisions from official NSW sources. For specific advice
              on your project, consult a qualified certifier, architect, or town planner.
            </p>
            <div className="flex gap-3 justify-center flex-wrap text-xs md:text-sm">
              <a
                href="https://www.planningportal.nsw.gov.au/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                NSW Planning Portal
              </a>
              <a
                href="https://legislation.nsw.gov.au/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                NSW Legislation
              </a>
              <Link
                href="/quick-guide"
                className="inline-flex items-center gap-1 text-teal-600 hover:underline"
              >
                Quick Start Guide
              </Link>
            </div>
          </div>

          <p className="text-xs text-gray-500 text-center">
            PlotDetect Complete User Guide · Last updated February 2026
          </p>
        </div>
      </div>
    </div>
  );
}
