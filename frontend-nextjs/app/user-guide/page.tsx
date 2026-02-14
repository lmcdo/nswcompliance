'use client';

import React, { useState } from 'react';
import { FileText, BookOpen, Workflow, Users, Home, ExternalLink } from 'lucide-react';
import Link from 'next/link';

export default function UserGuidePage() {
  const [activeTab, setActiveTab] = useState<'start' | 'understand' | 'workflows' | 'roles'>('start');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="relative border-b shadow-sm overflow-hidden flex">
        <div className="relative flex-shrink-0 bg-white">
          <svg className="h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
            <path d="M0 0 L16 0 Q36 14 28 28 Q20 42 36 56 L0 56 Z" fill="#0d9488" />
          </svg>
        </div>
        <a
          href="https://plotdetect.com.au/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 pr-4 py-3 md:py-4 bg-white hover:opacity-80 transition-opacity"
        >
          <img src="/logo.png" alt="PlotDetect" className="h-8 w-auto" />
          <span className="text-base font-semibold text-gray-900">PlotDetect</span>
        </a>
        <div className="flex-1 bg-teal-50 flex items-center gap-4 px-4 py-3 md:py-4">
          <div className="flex-1">
            <h1 className="text-lg md:text-xl font-semibold tracking-tight text-teal-800">
              User Guide
            </h1>
            <p className="text-teal-600 text-xs hidden sm:block">
              How to use PlotDetect for NSW planning compliance
            </p>
          </div>
          <Link
            href="/assessment"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border border-teal-600 bg-teal-600 text-white hover:bg-teal-700 transition-colors"
          >
            <Home className="h-3.5 w-3.5" />
            Back to Assessment
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Tab Navigation */}
        <div className="bg-white border rounded-lg shadow-sm mb-6 overflow-hidden">
          <div className="flex flex-wrap" role="tablist">
            <button
              role="tab"
              onClick={() => setActiveTab('start')}
              className={`flex-1 min-w-[140px] px-4 py-3 text-sm font-medium transition-colors ${
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
              className={`flex-1 min-w-[140px] px-4 py-3 text-sm font-medium transition-colors ${
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
              className={`flex-1 min-w-[140px] px-4 py-3 text-sm font-medium transition-colors ${
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
              className={`flex-1 min-w-[140px] px-4 py-3 text-sm font-medium transition-colors ${
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
        <div className="bg-white border rounded-lg shadow-sm p-6 md:p-8">
          {/* Getting Started Tab */}
          {activeTab === 'start' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Getting Started</h2>
                <p className="text-gray-600">Three simple steps to assess any NSW property</p>
              </div>

              <div className="space-y-4">
                <div className="flex gap-4 items-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold">
                    1
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">Enter an Address</h3>
                    <p className="text-sm text-gray-600">
                      Type any NSW property address in the search bar. PlotDetect automatically fetches
                      live planning data from NSW Planning Portal.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold">
                    2
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">Navigate the Three Tabs</h3>
                    <p className="text-sm text-gray-600 mb-2">
                      Results are organized into three regulatory layers:
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

                <div className="flex gap-4 items-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold">
                    3
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">Read Provisions</h3>
                    <p className="text-sm text-gray-600">
                      Click any provision to expand details. Use the PDF icon to view the original
                      page from the planning document.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mt-6">
                <p className="text-sm text-teal-900">
                  <strong>💡 Pro tip:</strong> All three tabs apply to your property. Check each tab
                  for a complete compliance picture.
                </p>
              </div>
            </div>
          )}

          {/* Understanding SEPP/LEP/DCP Tab */}
          {activeTab === 'understand' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Understanding SEPP • LEP • DCP</h2>
                <p className="text-gray-600">NSW planning has three regulatory layers that work together</p>
              </div>

              {/* Diagram */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <img
                  src="/sepp-lep-dcp-hierarchy-diagram.png"
                  alt="NSW Planning Hierarchy"
                  className="w-full h-auto max-w-2xl mx-auto"
                />
              </div>

              {/* SEPP */}
              <div className="bg-purple-50 border-l-4 border-purple-600 rounded-r-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded bg-purple-600 text-white flex items-center justify-center text-xs font-bold">
                    S
                  </div>
                  <h3 className="font-bold text-purple-900">SEPP — State Environmental Planning Policy</h3>
                </div>
                <p className="text-sm text-purple-800 mb-2">
                  <strong>What it is:</strong> State-wide rules that apply across all of NSW
                </p>
                <p className="text-sm text-purple-700 mb-2">
                  <strong>What you'll find:</strong>
                </p>
                <ul className="text-sm text-purple-700 list-disc ml-5 space-y-1">
                  <li><strong>Exempt & Complying Development:</strong> Standards for simple work (decks, fences, carports, pools)</li>
                  <li><strong>BASIX:</strong> Water and energy sustainability targets</li>
                  <li><strong>Apartment Design Guide:</strong> Standards for residential flat buildings</li>
                  <li><strong>Heritage:</strong> State heritage item protections</li>
                  <li><strong>Housing:</strong> TOD precincts, low-rise housing diversity</li>
                </ul>
              </div>

              {/* LEP */}
              <div className="bg-amber-50 border-l-4 border-amber-600 rounded-r-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded bg-amber-600 text-white flex items-center justify-center text-xs font-bold">
                    L
                  </div>
                  <h3 className="font-bold text-amber-900">LEP — Local Environmental Plan</h3>
                </div>
                <p className="text-sm text-amber-800 mb-2">
                  <strong>What it is:</strong> Council-specific zoning rules and development limits
                </p>
                <p className="text-sm text-amber-700 mb-2">
                  <strong>What you'll find:</strong>
                </p>
                <ul className="text-sm text-amber-700 list-disc ml-5 space-y-1">
                  <li><strong>Zone:</strong> What type of development is permitted (R2, B4, etc.)</li>
                  <li><strong>Height limits:</strong> Maximum building height for the zone</li>
                  <li><strong>FSR limits:</strong> Maximum floor space ratio</li>
                  <li><strong>Land use table:</strong> Permitted, prohibited, and requires-consent uses</li>
                  <li><strong>Special provisions:</strong> Heritage, foreshore, flood controls</li>
                </ul>
              </div>

              {/* DCP */}
              <div className="bg-green-50 border-l-4 border-green-600 rounded-r-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded bg-green-600 text-white flex items-center justify-center text-xs font-bold">
                    D
                  </div>
                  <h3 className="font-bold text-green-900">DCP — Development Control Plan</h3>
                </div>
                <p className="text-sm text-green-800 mb-2">
                  <strong>What it is:</strong> Detailed local design rules for your council area
                </p>
                <p className="text-sm text-green-700 mb-2">
                  <strong>What you'll find:</strong>
                </p>
                <ul className="text-sm text-green-700 list-disc ml-5 space-y-1">
                  <li><strong>Setbacks:</strong> How far buildings must be from boundaries</li>
                  <li><strong>Character controls:</strong> Building materials, roof forms, landscaping</li>
                  <li><strong>Heritage controls:</strong> Rules for heritage conservation areas</li>
                  <li><strong>Parking:</strong> Required parking spaces and driveway design</li>
                  <li><strong>Private open space:</strong> Minimum yard and courtyard sizes</li>
                </ul>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
                <p className="text-sm text-blue-900">
                  <strong>Important:</strong> All three layers apply simultaneously. Your development
                  must comply with SEPP <em>and</em> LEP <em>and</em> DCP requirements.
                </p>
              </div>
            </div>
          )}

          {/* Workflows Tab */}
          {activeTab === 'workflows' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Common Workflows</h2>
                <p className="text-gray-600">Step-by-step compliance pathways for different scenarios</p>
              </div>

              {/* Workflow 1: Complying Development */}
              <div className="border-l-4 border-emerald-600 rounded-r-lg bg-emerald-50 p-4">
                <h3 className="font-bold text-emerald-900 mb-3 flex items-center gap-2">
                  <span className="bg-emerald-600 text-white px-2 py-0.5 rounded text-xs">WORKFLOW 1</span>
                  Complying Development (E&C) Assessment
                </h3>

                {/* Diagram */}
                <div className="bg-white border border-emerald-200 rounded-lg p-4 mb-4">
                  <img
                    src="/userguidediagramforverify.png"
                    alt="E&C Compliance Pathway Flowchart"
                    className="w-full h-auto max-w-2xl mx-auto"
                  />
                </div>

                <ol className="space-y-3 text-sm text-emerald-900">
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">1.</span>
                    <div>
                      <strong>Check SEPP Tab → Exempt & Complying Development card</strong>
                      <p className="text-emerald-700">Select your work type (Deck, Fence, Carport, Pool) and verify ALL standards are met</p>
                    </div>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">2.</span>
                    <div>
                      <strong>Check LEP Tab → Land Use Zoning</strong>
                      <p className="text-emerald-700">Confirm the proposed use is permitted in the zone (not prohibited)</p>
                    </div>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">3.</span>
                    <div>
                      <strong>Check DCP Tab → Council Controls</strong>
                      <p className="text-emerald-700">Review any additional local requirements (character, materials, heritage)</p>
                    </div>
                  </li>
                </ol>

                <div className="bg-white rounded border border-emerald-200 p-3 mt-4">
                  <p className="text-xs text-emerald-800">
                    ✓ <strong>All three checks pass?</strong> Work may proceed as Complying Development (CDC pathway)<br />
                    ✗ <strong>Any check fails?</strong> Requires Development Application (DA pathway)
                  </p>
                </div>
              </div>

              {/* Workflow 2: Heritage Property */}
              <div className="border-l-4 border-purple-600 rounded-r-lg bg-purple-50 p-4">
                <h3 className="font-bold text-purple-900 mb-3 flex items-center gap-2">
                  <span className="bg-purple-600 text-white px-2 py-0.5 rounded text-xs">WORKFLOW 2</span>
                  Heritage Property Assessment
                </h3>

                {/* Diagram */}
                <div className="bg-white border border-purple-200 rounded-lg p-3 mb-4">
                  <img
                    src="/hierarchyandcompliance.png"
                    alt="Heritage Assessment Workflow"
                    className="w-full h-auto max-w-xl mx-auto"
                  />
                </div>

                <ol className="space-y-3 text-sm text-purple-900">
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">1.</span>
                    <div>
                      <strong>Check LEP Tab → HCA card</strong>
                      <p className="text-purple-700">Read heritage conservation area objectives and context</p>
                    </div>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">2.</span>
                    <div>
                      <strong>Check DCP Tab → Heritage provisions</strong>
                      <p className="text-purple-700">Review applicable heritage design controls for the HCA</p>
                    </div>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">3.</span>
                    <div>
                      <strong>Check SEPP Tab → Heritage (if State Heritage Register item)</strong>
                      <p className="text-purple-700">State-listed items have additional SEPP requirements beyond local controls</p>
                    </div>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">4.</span>
                    <div>
                      <strong>Check standard LEP and DCP controls</strong>
                      <p className="text-purple-700">Heritage properties must ALSO meet setbacks, height, FSR, and other standard requirements</p>
                    </div>
                  </li>
                </ol>

                <div className="bg-white rounded border border-purple-200 p-3 mt-4">
                  <p className="text-xs text-purple-800">
                    <strong>Note:</strong> Most heritage work requires DA with Heritage Impact Statement.
                    Consult council's heritage advisor early in the design process.
                  </p>
                </div>
              </div>

              {/* Workflow 3: Standard DA */}
              <div className="border-l-4 border-blue-600 rounded-r-lg bg-blue-50 p-4">
                <h3 className="font-bold text-blue-900 mb-3 flex items-center gap-2">
                  <span className="bg-blue-600 text-white px-2 py-0.5 rounded text-xs">WORKFLOW 3</span>
                  Standard Development Application (DA)
                </h3>

                {/* Diagram */}
                <div className="bg-white border border-blue-200 rounded-lg p-3 mb-4">
                  <img
                    src="/DAProcess.png"
                    alt="Standard DA Workflow"
                    className="w-full h-auto max-w-xl mx-auto"
                  />
                </div>

                <ol className="space-y-3 text-sm text-blue-900">
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">1.</span>
                    <div>
                      <strong>Check LEP Tab first</strong>
                      <p className="text-blue-700">Verify the proposed use is permitted, check height/FSR limits</p>
                    </div>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">2.</span>
                    <div>
                      <strong>Review DCP Tab for design controls</strong>
                      <p className="text-blue-700">Understand setbacks, landscaping, parking, character requirements</p>
                    </div>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-bold flex-shrink-0">3.</span>
                    <div>
                      <strong>Check SEPP Tab for applicable policies</strong>
                      <p className="text-blue-700">BASIX, ADG (for apartments), TOD provisions, etc.</p>
                    </div>
                  </li>
                </ol>

                <div className="bg-white rounded border border-blue-200 p-3 mt-4">
                  <p className="text-xs text-blue-800">
                    <strong>Pro tip:</strong> Use PlotDetect results to brief your architect/designer
                    on all applicable controls before starting design work.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* For Your Role Tab */}
          {activeTab === 'roles' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Tips for Your Role</h2>
                <p className="text-gray-600">How different professionals use PlotDetect</p>
              </div>

              {/* Certifiers */}
              <div className="bg-slate-50 border-l-4 border-slate-600 rounded-r-lg p-4">
                <h3 className="font-bold text-slate-900 mb-2 flex items-center gap-2">
                  <span className="bg-slate-600 text-white px-2 py-1 rounded text-sm">Certifiers</span>
                </h3>
                <ul className="space-y-2 text-sm text-slate-800">
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>CDC pathway:</strong> Use E&C workflow (Workflow 1 above) to verify all three compliance layers</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>PDF verification:</strong> Click PDF icons to view original pages and verify provision text</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Cross-check controls:</strong> Don't stop at E&C - DCP controls can still apply to complying development</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Heritage flags:</strong> Property summary shows heritage status - check DCP heritage card if flagged</span>
                  </li>
                </ul>
              </div>

              {/* Architects */}
              <div className="bg-violet-50 border-l-4 border-violet-600 rounded-r-lg p-4">
                <h3 className="font-bold text-violet-900 mb-2 flex items-center gap-2">
                  <span className="bg-violet-600 text-white px-2 py-1 rounded text-sm">Architects</span>
                </h3>
                <ul className="space-y-2 text-sm text-violet-800">
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Design constraints:</strong> Check LEP height/FSR limits before starting schematic design</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Setback controls:</strong> DCP tab shows minimum setbacks - use these for site layout</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Character requirements:</strong> DCP character controls define materials, roof forms, fencing styles</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>ADG compliance:</strong> For apartments, check SEPP tab ADG card for detailed design criteria</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Heritage HCAs:</strong> Heritage conservation areas have specific design controls for additions and alterations</span>
                  </li>
                </ul>
              </div>

              {/* Builders */}
              <div className="bg-orange-50 border-l-4 border-orange-600 rounded-r-lg p-4">
                <h3 className="font-bold text-orange-900 mb-2 flex items-center gap-2">
                  <span className="bg-orange-600 text-white px-2 py-1 rounded text-sm">Builders</span>
                </h3>
                <ul className="space-y-2 text-sm text-orange-800">
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Quick compliance check:</strong> Use E&C card to see if simple work (deck, fence, carport) can proceed as CDC</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Approval pathway:</strong> E&C workflow shows whether CDC or DA is required</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Setback verification:</strong> Check DCP setbacks before quoting fence or extension work</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Heritage awareness:</strong> If property is heritage-listed, flag to client that DA likely required</span>
                  </li>
                </ul>
              </div>

              {/* Planners */}
              <div className="bg-emerald-50 border-l-4 border-emerald-600 rounded-r-lg p-4">
                <h3 className="font-bold text-emerald-900 mb-2 flex items-center gap-2">
                  <span className="bg-emerald-600 text-white px-2 py-1 rounded text-sm">Town Planners</span>
                </h3>
                <ul className="space-y-2 text-sm text-emerald-800">
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Regulatory context:</strong> See all three layers (SEPP/LEP/DCP) for complete planning framework</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Pre-DA research:</strong> Use PlotDetect to understand site constraints before lodging DA</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Policy hierarchy:</strong> Understand how State policies (SEPP) interact with local controls (LEP/DCP)</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-teal-600 flex-shrink-0">✓</span>
                    <span><strong>Clause references:</strong> PDF page numbers link directly to source documents for citation in reports</span>
                  </li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <div className="bg-white border rounded-lg shadow-sm p-6 mb-4">
            <h3 className="font-bold text-gray-900 mb-2">Need More Help?</h3>
            <p className="text-sm text-gray-600 mb-4">
              PlotDetect shows planning provisions from official NSW sources. For specific advice
              on your project, consult a qualified certifier, architect, or town planner.
            </p>
            <div className="flex gap-3 justify-center flex-wrap">
              <a
                href="https://www.planningportal.nsw.gov.au/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                NSW Planning Portal
              </a>
              <a
                href="https://legislation.nsw.gov.au/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                NSW Legislation
              </a>
            </div>
          </div>

          <p className="text-xs text-gray-500">
            PlotDetect User Guide · Last updated February 2026
          </p>
        </div>
      </div>
    </div>
  );
}
