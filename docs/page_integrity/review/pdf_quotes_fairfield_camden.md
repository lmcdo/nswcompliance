# Fairfield / Camden dwelling_house setback rows vs PDF
PDFs (local, no download; DB citation_source_path source-pdfs/dcps/... does not exist in the worktree): data/dcps/fairfield-ch5-dwelling-houses.pdf (60pp, printed 146-205), data/dcps/camden-part4-residential-dwelling-controls.pdf (58pp, printed P4-n).

## Fairfield (Ch 5A Dwelling Houses, heading 5A.2.3 Setbacks)
pdf_page convention: PRINTED page number. DB 153/154 are one too high for these clauses (front is printed 152, side/rear printed 153).
- 709 front 4.5m (DB p153): PDF idx 7 / printed 152, 5A.2.3.1 Front Setback Controls. "a) Any part of the detached single dwelling (except landscaping and retaining walls) must be located within 1.5 metres of the average existing front street setback. b) The average setback is calculated from the adjoining four houses on either side..." "f) The dwelling front setback must be in accordance with control (a). In cases where control (a) equates to a minimum setback less than 4.5 metres, the dwelling front setback must be a minimum of 4.5 metres." Value matches only as a FLOOR. CONDITIONAL: rule is average of 4 neighbours each side +/-1.5m, never below 4.5m. Not an unconditional 4.5m. Garage/carport 5.5m separate (d).
- 710 side 0.9m ground (DB p154): printed 153, 5A.2.3.2. "a) Side setbacks must be a minimum of 900mm on ground level." Matches; effectively unconditional at ground level. Note b) "upper floor side walls on southern and western boundaries require a minimum 1.5m setback, other wall sides require a minimum of 900mm" is NOT stored.
- 711 side 4.0m (p154): printed 153. "d) For a proposal with a combined void space greater than 20m2, the upper floor side setback must be a minimum of 4m from the south and west boundaries of the property." Matches; CONDITIONAL (void >20m2, upper floor, S/W boundaries).
- 1494 rear 0.9m (p154, no citation_source_path): printed 153. PDF has NO ground-floor rear 900mm control: a) says "Side setbacks" only. DB quote "Side and rear setbacks for all ground floor walls must be a minimum of 900mm" is NOT in this PDF. Rear 0.9m = NO (unsupported; this PDF). c) "The upper floor rear walls must be set back by at least 4 metres from rear boundaries where they adjoin residential properties." is the only rear control (upper floor, conditional) and is not stored as a number. Row should be treated as wrong/unverified. (Possibly from citywide DCP fairfield-citywide-dcp-2013.pdf; not checked.)
- Corner: "a) Corner sites require a minimum secondary setback of 1.5 metres." (5A.2.3.3) not stored. Battleaxe: 1.5m all boundaries (g).

## Camden (Part 4 Residential Dwelling Controls, "Setbacks", Table 4-2, printed P4-7/P4-8)
pdf_page convention: 1-BASED PDF INDEX. DB 11 = idx 10 = printed P4-8 (Table 4-2). Matches.
Front tiers, verbatim (Table 4-2): "The setback of a dwelling house and any attached development from a primary road must not be less than the average setback from the primary road of the 2 nearest dwelling houses on the same side of the primary road. If there are not 2 dwelling houses within 40m of the lot on the same side of the primary road, the dwelling house and any attached development must have a minimum setback from the primary road as shown in the following: Lot size / Minimum setback: < or equal to 900m2 = 4.5m (A reduced front setback of 3.5m where the development is fronting open space); >900m2-1,500m2 = 6.5m; >1,500m2 = 10m."
Lot 640.98 m2 => <=900 tier = 4.5m, but ONLY if fewer than 2 dwelling houses within 40m on same side; otherwise the average setback of the 2 nearest. 3.5m if fronting open space.
- 690 front 4.5m: value matches tier; CONDITIONAL (the 40m / average rule above). Stored condition text is accurate.
- 691 side 0.9m: "Side setback 0.9m". Matches; unconditional in Table 4-2 (note: applies except where area-specific control or registered building envelope; battle-axe lots measured per Fig 4-3).
- 1063 rear 4m: "Rear setback - single storey dwelling or single storey portion of a two storey dwelling (min) 4m". Matches; CONDITIONAL on storey.
- 1064 rear 6m: "Rear setback - two storey portion of a two storey dwelling (min) 6m". Matches; CONDITIONAL on two-storey portion.
- Secondary setback "2m" (not stored): "A greater secondary setback may be required if the proposed development does not positively address the secondary street".
- Corner lots: rear is boundary opposite the shorter frontage (note p P4-8).

## Summary table
| id | LGA | type | value | PDF match | Conditionality |
|709|fairfield|front|4.5|floor only|CONDITIONAL: avg of 4 neighbours each side, +/-1.5m, min 4.5|
|710|fairfield|side|0.9|yes|ground level only; upper S/W 1.5m unstored|
|711|fairfield|side|4.0|yes|CONDITIONAL void >20m2, upper floor, S/W|
|1494|fairfield|rear|0.9|NO (not in PDF)|n/a|
|690|camden|front|4.5|yes (lot<=900)|CONDITIONAL <2 houses within 40m, else average|
|691|camden|side|0.9|yes|unconditional|
|1063|camden|rear|4|yes|CONDITIONAL single storey|
|1064|camden|rear|6|yes|CONDITIONAL two-storey portion|
