FAIL __tests__/components/compliance/state-level-housing-sepp-zone-from-lep.test.tsx
  ● Console

    console.log
      [StateLevelControls] Detected SEPPs: [ 'SEPP_HOUSING_2021' ]

      at log (components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/components/compliance/StateLevelControls.tsx:248:13)

    console.log
      [StateLevelControls] MU1 zone does not permit residential - excluding Housing SEPP (ADG, Secondary Dwellings)

      at log (components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/components/compliance/StateLevelControls.tsx:271:17)

    console.log
      [StateLevelControls] No structured SEPPs detected

      at log (components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/components/compliance/StateLevelControls.tsx:283:15)

    console.log
      [StateLevelControls] Fetching ADG requirements (RFB development type)

      at log (components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/components/compliance/StateLevelControls.tsx:194:15)

    console.log
      [StateLevelControls] Detected SEPPs: [ 'SEPP_HOUSING_2021' ]

      at log (components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/components/compliance/StateLevelControls.tsx:248:13)

    console.log
      [StateLevelControls] Fetching requirements for housing_2021

      at log (components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/components/compliance/StateLevelControls.tsx:295:17)

    console.log
      [StateLevelControls] Loaded 0 structured requirements, 0 transport requirements

      at log (components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/components/compliance/StateLevelControls.tsx:320:15)

  ● drops it when the LEP table prohibits every dwelling type

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: StringContaining "/api/lep/permissibility"
    Received
           1: "/api/sepp/structured-requirements", {"body": "{\"seppId\":\"housing_2021\",\"developmentType\":\"dual_occupancy\"}", "headers": {"Content-Type": "application/json"}, "method": "POST"}
           2: "/api/pathway/pattern-book-eligibility", {"body": "{\"propertyData\":{\"constraints\":{\"zone\":\"R2 Low Density Residential\",\"lga\":\"Test\",\"applicableSepps\":[\"SEPP_HOUSING_2021\"]}}}", "headers": {"Content-Type": "application/json"}, "method": "POST"}
           3: "/api/sepp/exempt-complying?zone=R2"

    Number of calls: 3

    Ignored nodes: comments, script, style
    <html>
      <head />
      <body>
        <div>
          <div
            class="space-y-4"
          >
            <div
              class="flex items-center gap-2 text-xs text-gray-500"
            >
              <span
                class="w-2 h-2 rounded-full bg-green-500 flex-shrink-0"
              />
              <span
                class="font-medium text-gray-700"
              >
                NSW State Planning Instruments
              </span>
              <span>
                ·
              </span>
              <span>
                Sourced live — NSW Planning Portal
              </span>
            </div>
            <div
              class="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-lg"
            >
              <div
                class="font-semibold text-amber-900 mb-1"
              >
                State Environmental Planning Policies
              </div>
              <div
                class="text-sm text-amber-800"
              >
                Mandatory state-wide requirements that apply to this property
              </div>
            </div>
            <div
              class="text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm border-purple-200 bg-purple-50"
              data-slot="card"
            >
              <div
                class="@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6 cursor-pointer hover:bg-purple-100/50 transition-colors"
                data-slot="card-header"
              >
                <div
                  class="flex items-center justify-between"
                >
                  <div
                    class="flex items-center gap-2"
                  >
                    <svg
                      aria-hidden="true"
                      class="lucide lucide-chevron-down h-5 w-5 text-purple-600"
                      fill="none"
                      height="24"
                      stroke="currentColor"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      viewBox="0 0 24 24"
                      width="24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="m6 9 6 6 6-6"
                      />
                    </svg>
                    <svg
                      aria-hidden="true"
                      class="lucide lucide-scale h-5 w-5 text-purple-600"
                      fill="none"
                      height="24"
                      stroke="currentColor"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      viewBox="0 0 24 24"
                      width="24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M12 3v18"
                      />
                      <path
                        d="m19 8 3 8a5 5 0 0 1-6 0zV7"
                      />
                      <path
                        d="M3 7h1a17 17 0 0 0 8-2 17 17 0 0 0 8 2h1"
                      />
                      <path
                        d="m5 8 3 8a5 5 0 0 1-6 0zV7"
                      />
                      <path
                        d="M7 21h10"
                      />
                    </svg>
                    <div
                      class="font-semibold text-lg text-purple-900"
                      data-slot="card-title"
                    >
                      SEPP Requirements
                    </div>
                  </div>
                  <div
                    class="flex items-center gap-2"
                  >
                    <span
                      class="inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive transition-[color,box-shadow] overflow-hidden border-transparent [a&]:hover:bg-primary/90 bg-purple-100 text-purple-800"
                      data-slot="badge"
                    >
                      State Policy
                    </span>
                  </div>
                </div>
                <p
                  class="text-sm text-purple-700 mt-1 ml-7"
                >
                  State Environmental Planning Policies - Mandatory requirements
                </p>
              </div>
              <div
                class="px-6 pt-0 space-y-4"
                data-slot="card-content"
              >
                <div
                  class="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-4"
                >
                  <div
                    class="text-sm font-semibold text-purple-900 mb-2"
                  >
                    Applicable State Policies (from Planning Portal)
                  </div>
                  <div
                    class="space-y-1 mb-2"
                  >
                    <div
                      class="text-xs text-purple-900"
                    >
                      ✓ 
                      SEPP (Housing) 2021
                       — structured requirements shown below
                    </div>
                  </div>
                </div>
                <p
                  class="text-sm text-gray-500 italic"
                >
                  No Housing SEPP structured requirements for this development type
                </p>
                <div
                  class="flex items-center gap-2 text-xs text-gray-600 border-t border-purple-100 pt-3 mt-4"
                >
                  <svg
                    aria-hidden="true"
                    class="lucide lucide-shield h-4 w-4 text-green-600 flex-shrink-0"
                    fill="none"
                    height="24"
                    stroke="currentColor"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    viewBox="0 0 24 24"
                    width="24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"
                    />
                  </svg>
                  <span>
                    Provision text sourced from NSW Planning Portal and SEPP instruments. Zone eligibility, heritage classification, and property-specific constraints require independent verification against current legislation.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>

      at toHaveBeenCalledWith (__tests__/components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/__tests__/components/compliance/state-level-housing-sepp-zone-from-lep.test.tsx:41:44)
      at runWithExpensiveErrorDiagnosticsDisabled (../../site-claims-copy/frontend-nextjs/node_modules/@testing-library/dom/dist/config.js:47:12)
      at checkCallback (../../site-claims-copy/frontend-nextjs/node_modules/@testing-library/dom/dist/wait-for.js:124:77)
      at checkRealTimersCallback (../../site-claims-copy/frontend-nextjs/node_modules/@testing-library/dom/dist/wait-for.js:118:16)
      at Timeout.task [as _onTimeout] (../../site-claims-copy/frontend-nextjs/node_modules/jsdom/lib/jsdom/browser/Window.js:579:19)

FAIL __tests__/components/compliance/adg-zone-warning-from-lep.test.tsx
  ● warns when the LEP table lists residential flat buildings as prohibited (R4 not on any typed list)

    Unable to find an element with the text: /lists residential flat buildings as prohibited/i. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.

    Ignored nodes: comments, script, style
    <body>
      <div>
        <div
          class="text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm border-purple-200 bg-gradient-to-br from-purple-50/80 to-white"
          data-slot="card"
        >
          <div
            class="@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6 pb-2"
            data-slot="card-header"
          >
            <div
              class="flex items-center justify-between"
            >
              <div
                class="flex items-center gap-2"
              >
                <svg
                  aria-hidden="true"
                  class="lucide lucide-building-2 w-5 h-5 text-purple-600"
                  fill="none"
                  height="24"
                  stroke="currentColor"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  viewBox="0 0 24 24"
                  width="24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M10 12h4"
                  />
                  <path
                    d="M10 8h4"
                  />
                  <path
                    d="M14 21v-3a2 2 0 0 0-4 0v3"
                  />
                  <path
                    d="M6 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2"
                  />
                  <path
                    d="M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16"
                  />
                </svg>
                <div
                  class="text-base font-semibold text-purple-900"
                  data-slot="card-title"
                />
              </div>
              <span
                class="inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive transition-[color,box-shadow] overflow-hidden [a&]:hover:bg-accent [a&]:hover:text-accent-foreground text-purple-700 border-purple-300 bg-purple-100/50"
                data-slot="badge"
              >
                STATUTORY
              </span>
            </div>
            <p
              class="text-xs text-gray-500 mt-1"
            >
              2015
               | Authority: 
              NSW
            </p>
          </div>
          <div
            class="px-6 pt-2"
            data-slot="card-content"
          >
            <div
              class="space-y-2"
            />
            <div
              class="mt-4 pt-3 border-t border-purple-100"
            >
              <div
                class="flex items-center justify-between mb-2"
              >
                <h4
                  class="text-xs font-semibold text-purple-800"
                >
                  Side/Rear Setbacks to Boundaries (3F-1)
                </h4>
                <div
                  class="flex items-center gap-2"
                />
              </div>
              <p
                class="text-xs text-gray-500 mb-2"
              >
                Min distance from windows/balconies to boundary
              </p>
              <table
                class="w-full text-xs"
              >
                <thead>
                  <tr
                    class="text-left text-gray-500"
                  >
                    <th
                      class="pb-1"
                    >
                      Building
                    </th>
                    <th
                      class="pb-1"
                    >
                      Living/Bed
                    </th>
                    <th
                      class="pb-1"
                    >
                      Bath/Store
                    </th>
                  </tr>
                </thead>
                <tbody
                  class="text-gray-700"
                >
                  <tr>
                    <td
                      class="py-0.5 text-gray-500"
                      colspan="3"
                    >
                      The separation table could not be read from the Apartment Design Guide. Open the guide to see the distances.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              class="mt-3 pt-2 border-t border-purple-100 flex items-center justify-between"
            >
              <span
                class="text-xs text-gray-500"
              >
                0
                 Design Criteria | ADG March 2023
              </span>
            </div>
          </div>
        </div>
      </div>
    </body>

      at waitForWrapper (../../site-claims-copy/frontend-nextjs/node_modules/@testing-library/dom/dist/wait-for.js:163:27)
      at ../../site-claims-copy/frontend-nextjs/node_modules/@testing-library/dom/dist/query-helpers.js:86:33
      at Object.findByText (__tests__/components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/__tests__/components/compliance/adg-zone-warning-from-lep.test.tsx:28:23)

  ● does not warn when the LEP table permits them (R2 is on the typed list)

    expect(received).toBeNull()

    Received: <div class="text-xs text-amber-800"><span class="font-medium">Zone R2</span> may prohibit or restrict apartment developments. Check LEP permissibility before proceeding.</div>

      at Object.toBeNull (__tests__/components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/__tests__/components/compliance/adg-zone-warning-from-lep.test.tsx:35:43)

  ● says not checked when the zone is not covered

    Unable to find an element with the text: /not checked against the LEP land use table/i. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.

    Ignored nodes: comments, script, style
    <body>
      <div>
        <div
          class="text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm border-purple-200 bg-gradient-to-br from-purple-50/80 to-white"
          data-slot="card"
        >
          <div
            class="@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6 pb-2"
            data-slot="card-header"
          >
            <div
              class="flex items-center justify-between"
            >
              <div
                class="flex items-center gap-2"
              >
                <svg
                  aria-hidden="true"
                  class="lucide lucide-building-2 w-5 h-5 text-purple-600"
                  fill="none"
                  height="24"
                  stroke="currentColor"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  viewBox="0 0 24 24"
                  width="24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M10 12h4"
                  />
                  <path
                    d="M10 8h4"
                  />
                  <path
                    d="M14 21v-3a2 2 0 0 0-4 0v3"
                  />
                  <path
                    d="M6 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2"
                  />
                  <path
                    d="M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16"
                  />
                </svg>
                <div
                  class="text-base font-semibold text-purple-900"
                  data-slot="card-title"
                />
              </div>
              <span
                class="inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive transition-[color,box-shadow] overflow-hidden [a&]:hover:bg-accent [a&]:hover:text-accent-foreground text-purple-700 border-purple-300 bg-purple-100/50"
                data-slot="badge"
              >
                STATUTORY
              </span>
            </div>
            <p
              class="text-xs text-gray-500 mt-1"
            >
              2015
               | Authority: 
              NSW
            </p>
          </div>
          <div
            class="px-6 pt-2"
            data-slot="card-content"
          >
            <div
              class="mb-3 p-2 bg-amber-50 border border-amber-200 rounded-md flex items-start gap-2"
            >
              <svg
                aria-hidden="true"
                class="lucide lucide-triangle-alert lucide-alert-triangle w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0"
                fill="none"
                height="24"
                stroke="currentColor"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                viewBox="0 0 24 24"
                width="24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"
                />
                <path
                  d="M12 9v4"
                />
                <path
                  d="M12 17h.01"
                />
              </svg>
              <div
                class="text-xs text-amber-800"
              >
                <span
                  class="font-medium"
                >
                  Zone 
                  R2
                </span>
                 may prohibit or restrict apartment developments. Check LEP permissibility before proceeding.
              </div>
            </div>
            <div
              class="space-y-2"
            />
            <div
              class="mt-4 pt-3 border-t border-purple-100"
            >
              <div
                class="flex items-center justify-between mb-2"
              >
                <h4
                  class="text-xs font-semibold text-purple-800"
                >
                  Side/Rear Setbacks to Boundaries (3F-1)
                </h4>
                <div
                  class="flex items-center gap-2"
                />
              </div>
              <p
                class="text-xs text-gray-500 mb-2"
              >
                Min distance from windows/balconies to boundary
              </p>
              <table
                class="w-full text-xs"
              >
                <thead>
                  <tr
                    class="text-left text-gray-500"
                  >
                    <th
                      class="pb-1"
                    >
                      Building
                    </th>
                    <th
                      class="pb-1"
                    >
                      Living/Bed
                    </th>
                    <th
                      class="pb-1"
                    >
                      Bath/Store
                    </th>
                  </tr>
                </thead>
                <tbody
                  class="text-gray-700"
                >
                  <tr>
                    <td
                      class="py-0.5 text-gray-500"
                      colspan="3"
                    >
                      The separation table could not be read from the Apartment Design Guide. Open the guide to see the distances.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              class="mt-3 pt-2 border-t border-purple-100 flex items-center justify-between"
            >
              <span
                class="text-xs text-gray-500"
              >
                0
                 Design Criteria | ADG March 2023
              </span>
            </div>
          </div>
        </div>
      </div>
    </body>

      at waitForWrapper (../../site-claims-copy/frontend-nextjs/node_modules/@testing-library/dom/dist/wait-for.js:163:27)
      at ../../site-claims-copy/frontend-nextjs/node_modules/@testing-library/dom/dist/query-helpers.js:86:33
      at Object.findByText (__tests__/components/compliance/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-zone-lists/frontend-nextjs/__tests__/components/compliance/adg-zone-warning-from-lep.test.tsx:41:23)

Test Suites: 2 failed, 2 total
Tests:       4 failed, 1 passed, 5 total
Snapshots:   0 total
Time:        3.824 s
Ran all test suites matching __tests__/components/compliance/state-level-housing-sepp-zone-from-lep.test.tsx|__tests__/components/compliance/adg-zone-warning-from-lep.test.tsx.
