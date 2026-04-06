# frontend-nextjs — Standing Rules

## UI Bug Debugging Protocol (MANDATORY)
**When user reports UI showing wrong data:**
1. Read `COMPONENT_MAP.md` FIRST — it's in this directory
2. Look up the route/view → find which component renders it
3. Call production API with EXACT user parameters to verify data
4. Search codebase for exact UI text pattern to confirm component
5. Fix ONLY the component identified in step 2
6. Update COMPONENT_MAP.md if component tree has changed

**NEVER guess which component is used. ALWAYS use COMPONENT_MAP.md.**

## UI Copy
- Never truncate words in labels
- Use full prose: "429 provisions in this section" not "429 in section"
- Labels must be self-explanatory without context

## Reuse Existing Data
- When the API or frontend already has data available (from a previous fetch, passed as props, or in session state), use it directly
- Do NOT make redundant API calls or re-fetch data that is already accessible
- Check what data is already available before writing new fetch logic
- **Example:** If provision data is already in the component props, don't fetch it again from the API

## Reference Docs
- `COMPONENT_MAP.md` — route → component map. Read before any UI work
- `app/assessment/README.md` — assessment page UI details
- `docs/screencasts/INDEX.md` — screencast scripts
- `docs/user-stories/` — user story documents

## Satellite Product Reports UI
The `/reports/` route group is a separate section of the app with its own layout — no compliance UI.
Target users (solar installers, buyers agents, property investors) never see DCP/LEP/SEPP tabs.

Route structure:
```
app/reports/
  layout.tsx          ← separate nav, no compliance sidebar
  solar-yield/
  shadow/
  threat-radar/
  flood/
  granny-flat/
```

Can be served under a different domain via Vercel domain config without any code changes.
