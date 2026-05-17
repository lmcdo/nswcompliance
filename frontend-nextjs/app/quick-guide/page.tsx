'use client';

import React from 'react';
import { Home, Zap, Clock, FileText, Building2, Landmark, CheckCircle, AlertCircle } from 'lucide-react';
import Link from 'next/link';

const DCP_ENABLED = process.env.NEXT_PUBLIC_DCP_ENABLED === 'true';

export default function QuickGuidePage() {
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
              Quick Start Guide
            </h1>
            <p className="text-slate-400 text-xs hidden sm:block">
              NSW planning assessment — approval pathways explained
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
      <div className="max-w-4xl mx-auto px-4 py-6 md:py-8 space-y-6">

        {/* Regulatory Hierarchy */}
        <div className="bg-white border rounded-lg shadow-sm p-4 md:p-6">
          <h2 className="text-base md:text-lg font-bold text-gray-900 mb-4">NSW Planning System (3 Layers)</h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
              <Landmark className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-purple-900 text-sm">SEPP (State Environmental Planning Policy)</div>
                <div className="text-xs text-purple-700 mt-0.5">State-wide rules: Exempt &amp; Complying, BASIX, Heritage, Apartment Design Guide, Low &amp; Mid-Rise Housing</div>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <Building2 className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-amber-900 text-sm">LEP (Local Environmental Plan)</div>
                <div className="text-xs text-amber-700 mt-0.5">Council zones and limits: Height, FSR, Land Use Permissibility, Environmental Constraints (Flood, Bushfire, ANEF, Mine Subsidence, Landslide, Contaminated Land, Water Catchment, Biodiversity, Coastal, Acid Sulfate)</div>
              </div>
            </div>
            <div className={`flex items-start gap-3 p-3 rounded-lg border ${DCP_ENABLED ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
              <FileText className={`h-5 w-5 flex-shrink-0 mt-0.5 ${DCP_ENABLED ? 'text-green-600' : 'text-gray-400'}`} />
              <div className="flex-1 min-w-0">
                <div className={`font-semibold text-sm ${DCP_ENABLED ? 'text-green-900' : 'text-gray-500'}`}>
                  DCP (Development Control Plan)
                  {!DCP_ENABLED && <span className="ml-2 text-xs font-normal text-gray-400">— coming soon</span>}
                </div>
                <div className={`text-xs mt-0.5 ${DCP_ENABLED ? 'text-green-700' : 'text-gray-400'}`}>
                  {DCP_ENABLED
                    ? 'Detailed local design rules: Setbacks, Landscaping, Character, Parking'
                    : 'Detailed local design rules (setbacks, landscaping, parking). Register interest in the DCP tab to be notified when your council is available.'}
                </div>
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-500 text-center mt-4 px-2">
            ⚠️ All three layers apply to every development — verify each before issuing approvals
          </p>
        </div>

        {/* Pathways Overview */}
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
          <h3 className="font-semibold text-teal-900 mb-2 text-sm">Approval Pathways</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <div className="bg-white border border-emerald-300 rounded p-2 text-center">
              <div className="font-bold text-emerald-700">Pattern Book</div>
              <div className="text-emerald-600">10 days</div>
            </div>
            <div className="bg-white border border-purple-300 rounded p-2 text-center">
              <div className="font-bold text-purple-700">E&amp;C CDC</div>
              <div className="text-purple-600">20 days</div>
            </div>
            <div className="bg-white border border-amber-300 rounded p-2 text-center">
              <div className="font-bold text-amber-700">Heritage</div>
              <div className="text-amber-600">30–90 days</div>
            </div>
            <div className="bg-white border border-blue-300 rounded p-2 text-center">
              <div className="font-bold text-blue-700">Standard DA</div>
              <div className="text-blue-600">30–90 days</div>
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
                <strong>New single-dwelling homes only.</strong> NSW Government Pattern Book designs get 10-day CDC approval. PlotDetect checks eligibility triggers and numeric standards automatically.
              </p>
            </div>
            <div className="space-y-3">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">1</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">SEPP Tab → Pattern Book CDC Card</div>
                  <div className="text-xs text-gray-600 mt-1">Check eligibility. Green = eligible. Red = blocked (shows which triggers failed).</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">2</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Review Numeric Standards</div>
                  <div className="text-xs text-gray-600 mt-1">Site coverage, setbacks, height limits, parking — all must comply.</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">3</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls Tab → Confirm Zone Permissibility</div>
                  <div className="text-xs text-gray-600 mt-1">Dwelling house must be permitted in zone (R2, R3, R4). Check height and FSR limits apply.</div>
                </div>
              </div>
              {DCP_ENABLED && (
                <div className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">4</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900 text-sm">DCP Tab → Verify No HCA/Heritage Restrictions</div>
                    <div className="text-xs text-gray-600 mt-1">Pattern Book excluded on heritage properties.</div>
                  </div>
                </div>
              )}
            </div>
            <div className="mt-4 flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-900">
                <strong>Common blockers:</strong> Heritage conservation area, narrow lot (&lt;15m), steep slope (&gt;20%), acid sulfate soil, flood zone, bushfire zone.
              </p>
            </div>
          </div>
        </div>

        {/* Pathway 2: E&C CDC */}
        <div className="bg-white border border-purple-300 rounded-lg shadow-sm overflow-hidden">
          <div className="bg-purple-100 border-b border-purple-300 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-purple-700" />
              <h2 className="text-base md:text-lg font-bold text-purple-900">Exempt &amp; Complying Development (CDC)</h2>
            </div>
            <span className="bg-purple-600 text-white px-2 py-0.5 rounded text-xs font-bold">20 DAYS</span>
          </div>
          <div className="p-4 md:p-6">
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-4">
              <p className="text-xs md:text-sm text-purple-900">
                <strong>Small-scale additions.</strong> Decks, garages, pools, fences, carports. Certifier approval only — no council DA. Must meet all SEPP (Exempt and Complying Development Codes) 2008 standards.
              </p>
            </div>
            <div className="space-y-3">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">1</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">SEPP Tab → Exempt &amp; Complying Card</div>
                  <div className="text-xs text-gray-600 mt-1">Select work type (Deck / Garage / Pool / Fence / Carport). PlotDetect shows applicable SEPP standards with clause references.</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">2</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">CDC Eligibility Screener</div>
                  <div className="text-xs text-gray-600 mt-1">Enter proposed height and floor area. Screener checks heritage status, zone, lot area, and numeric limits against SEPP provisions. Items marked unknown must be verified directly from the PDF.</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">3</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Click PDF Icons to Verify Wording</div>
                  <div className="text-xs text-gray-600 mt-1">Each provision has a page icon linking to the exact SEPP page image from the official document. Use this for certifier documentation.</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">4</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls Tab → Confirm Use Permitted &amp; Check Overlays</div>
                  <div className="text-xs text-gray-600 mt-1">Base land use must be allowed in zone. Check Local Provisions / Planning Overlays for any SEPP or instrument constraints (e.g. Aerotropolis buffer, Acid Sulfate).</div>
                </div>
              </div>
            </div>
            <div className="mt-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
              <p className="text-xs text-purple-900">
                <strong>Compliance requirement:</strong> Verify all provisions against the current{' '}
                <a
                  href="https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                >
                  SEPP (Exempt and Complying Development Codes) 2008
                </a>{' '}
                before issuing a CDC. PlotDetect is a preliminary screener only.
              </p>
            </div>
          </div>
        </div>

        {/* Pathway 3: Heritage */}
        <div className="bg-white border border-amber-300 rounded-lg shadow-sm overflow-hidden">
          <div className="bg-amber-100 border-b border-amber-300 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Landmark className="h-5 w-5 text-amber-700" />
              <h2 className="text-base md:text-lg font-bold text-amber-900">Heritage Property Assessment</h2>
            </div>
            <span className="bg-amber-600 text-white px-2 py-0.5 rounded text-xs font-bold">30–90 DAYS</span>
          </div>
          <div className="p-4 md:p-6">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
              <p className="text-xs md:text-sm text-amber-900">
                <strong>Properties in Heritage Conservation Areas or listed as heritage items.</strong> Additional design controls apply. Heritage statements usually required for DA.
              </p>
            </div>
            <div className="space-y-3">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">1</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Property Summary Panel → Check Heritage Status</div>
                  <div className="text-xs text-gray-600 mt-1">Shows if property is in an HCA or is a heritage item. Note the HCA name.</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">2</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls Tab → Heritage &amp; LEP Clause 5.10</div>
                  <div className="text-xs text-gray-600 mt-1">HCA conservation objectives and significance statement. Heritage items require consent under Clause 5.10 of the LEP for any works. CDC excluded for heritage items.</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">3</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">SEPP Tab → Check State Heritage Register</div>
                  <div className="text-xs text-gray-600 mt-1">If state-listed, additional SEPP (Biodiversity &amp; Conservation 2021) provisions apply.</div>
                </div>
              </div>
              {DCP_ENABLED ? (
                <div className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">4</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900 text-sm">DCP Tab → Heritage Provisions</div>
                    <div className="text-xs text-gray-600 mt-1">Controls for demolition, additions, materials, roofs, fencing, signage.</div>
                  </div>
                </div>
              ) : (
                <div className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">4</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900 text-sm">Standard Controls Still Apply</div>
                    <div className="text-xs text-gray-600 mt-1">Heritage is in addition to normal LEP (height/FSR) requirements. Check Planning Controls tab for all applicable development standards.</div>
                  </div>
                </div>
              )}
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
            <span className="bg-blue-600 text-white px-2 py-0.5 rounded text-xs font-bold">30–90 DAYS</span>
          </div>
          <div className="p-4 md:p-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
              <p className="text-xs md:text-sm text-blue-900">
                <strong>Most common pathway.</strong> New buildings, major alterations, additions over E&amp;C limits, commercial, multi-dwelling. Council assessment required.
              </p>
            </div>
            <div className="space-y-3">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">1</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls Tab → Primary Development Standards</div>
                  <div className="text-xs text-gray-600 mt-1">Check: (1) Use permitted in zone? (2) Height limit? (3) FSR limit? These are mandatory LEP controls.</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">2</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">Planning Controls Tab → Environmental Constraints</div>
                  <div className="text-xs text-gray-600 mt-1">Flood, bushfire, acid sulfate, ANEF, mine subsidence, landslide, biodiversity, coastal — each triggers specific assessment requirements.</div>
                </div>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">3</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-900 text-sm">SEPP Tab → State Policy Overlays</div>
                  <div className="text-xs text-gray-600 mt-1">BASIX (all dwellings), Apartment Design Guide (3+ units), Heritage, Low &amp; Mid-Rise Housing reforms, Transport-Oriented Development (near stations).</div>
                </div>
              </div>
              {DCP_ENABLED ? (
                <div className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">4</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900 text-sm">DCP Tab → Council Design Controls</div>
                    <div className="text-xs text-gray-600 mt-1">Setbacks, landscaping, character, parking, solar access, privacy. Use topic filters and DA Mode for structured assessment.</div>
                  </div>
                </div>
              ) : (
                <div className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">4</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900 text-sm">DCP Council Controls — Register Interest</div>
                    <div className="text-xs text-gray-600 mt-1">Detailed setback, landscaping, and design controls from the DCP are coming. Register interest in the DCP tab to be notified when your council is available.</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* DA Mode section — DCP only */}
        {DCP_ENABLED && (
          <div className="bg-teal-50 border border-teal-300 rounded-lg shadow-sm overflow-hidden">
            <div className="bg-teal-600 text-white px-4 py-3 flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              <h2 className="text-base md:text-lg font-bold">DA Mode: Annotation &amp; SEE Draft</h2>
            </div>
            <div className="p-4 md:p-6">
              <p className="text-xs md:text-sm text-teal-900 mb-3">
                <strong>For Standard DAs.</strong> Activate DA Mode in the DCP tab to annotate provisions and export a pre-populated Statement of Environmental Effects draft.
              </p>
              <p className="text-xs text-gray-600">
                Enable DA Mode → set development type → run triage → annotate provisions → export SEE PDF.
                Each N/A exclusion traces to a confirmed intake answer. See the DCP tab for the full workflow.
              </p>
            </div>
          </div>
        )}

        {/* Navigation Tips */}
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
          <h3 className="font-semibold text-teal-900 mb-3 text-sm flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            Quick Navigation Tips
          </h3>
          <div className="space-y-2 text-xs text-teal-900">
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>Property Summary (left panel):</strong> Zone, height limit, FSR, heritage status at a glance</span>
            </div>
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>PDF Icons:</strong> Click to view the exact page from the original SEPP or LEP document</span>
            </div>
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>Planning Overlays (LEP tab):</strong> Flags SEPP spatial overlays and LEP local provisions that apply to the property — check these even for CDC work</span>
            </div>
            <div className="flex gap-2">
              <span className="text-teal-600">•</span>
              <span><strong>CDC Eligibility Screener:</strong> Preliminary only — always verify against current legislation before issuing a certificate</span>
            </div>
            {DCP_ENABLED && (
              <>
                <div className="flex gap-2">
                  <span className="text-teal-600">•</span>
                  <span><strong>Topic / Document toggle (DCP tab):</strong> Topic view = keyword search; Document view = navigate by DCP chapter matching the printed document</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-teal-600">•</span>
                  <span><strong>Chapter dismiss (DA Mode):</strong> Hover a chapter in the sidebar → × button dismisses all provisions with a stated reason, recorded in SEE Schedule B</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center pt-4">
          <p className="text-xs text-gray-500 mb-3">
            PlotDetect · Quick Start Guide · March 2026
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
