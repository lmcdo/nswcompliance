# Address audit: method (draft, 2026-11-04)

Feeds `docs/QUALITY_STATEMENT.md` section 3 and outreach claim OC-18 (`scripts/audit_rate_check.py`).
Tooling: `scripts/address_audit/`. Evidence: `data/address_audit/<date>-<run>/`.

## Limits first (measured 2026-11-04)

1. **The recorded sample cannot be re-drawn from its seed.** No seed is recorded for runs 6 to 9. The only seed in the
   repo is a docstring example (`--seed 20261015 --out run2`, `build_packets.py` line 9). The address draw also depends on
   live NSW address layers and the live product, and the rules drawn per address depend on the rules served that day.
2. **The first pass that chose which rules a person read is not the code now committed.** Re-running the committed
   `flag_packets.py` over the saved packets gives:

   | Run | Rules in run | Read by a person (recorded) | Sent to read by committed first pass today |
   |---|---|---|---|
   | 2026-10-16-run6 | 270 | 62 | 165 |
   | 2026-10-16-run7 | 290 | 70 | 191 |
   | 2026-10-16-run8 | 270 | 58 | 185 |
   | 2026-10-17-run9 | 290 | 0 (not read) | 198 |

   Every rule flagged then is still flagged now (run8: 31 of 31). The extra flags are almost all "rule names a place"
   (110 on run8) and "page heading names a place" (51 on run8 against 5 recorded). The committed file differs from the
   copy used at the time in the `IN_PLACE` pattern and one null guard (`diff` of the two files, 2026-11-04).
   Consequence: the recorded bound of 1.89 per 100 is for the looser pass actually used. Reading what the committed pass
   now flags would test more rules.
3. **Unread rules count as passing.** Of 830 rules, 190 were read. The bound divides by all 830. It is a bound on errors
   the code pass or the person found.
4. **Run 9 (290 rules, 85 to read) has no labels**, so it is outside the figure.

How to reproduce: the first-pass step re-runs from saved packets (it is deterministic given the packets and the code
version). The draw step re-runs only if the seed and the date are recorded. Section "Going forward" fixes the second.

## Sampling frame

- **Councils.** The 13 listed in `LGAS` in `build_packets.py`, with a per-council address count (Inner West 6, others 2).
- **Address.** A uniform random point inside the council polygon (NSW Administrative Boundaries, layer 8), then the nearest
  NSW geocoded address point within about 80 m. An address read in an earlier run is excluded.
- **Product lookup.** `/api/property` then `/api/provisions/for-property`, with the same query the assessment page sends.
  An address the product cannot find is recorded as `unfound_redrawn` and redrawn.
- **Rules.** Of the rules served at the address, 10 chosen at random (`rnd.sample`, or all if fewer).
- **Randomness.** `random.Random(seed)`. Pass `--seed` and `--out <date>-<run>`.

## Sample size rule

A run is 13 council targets, about 30 addresses, about 270 to 290 rules. The statement uses pooled runs inside 30 days and
needs at least 500 rules and 50 addresses (`MIN_PACKETS`, `MIN_ADDRESSES` in `audit_rate_check.py`).

## Which rules a person reads

`flag_packets.py <run>` flags a rule if any check fires: plan council differs from the house's council; a named place not
in the address; a rule limited to an area; a heritage rule at a house outside any heritage area; words not found on the
shown page (match below 0.90); numbers not on the shown page. It then adds a 10% random sample of the unflagged
(`random.Random(7)`, drawn in packet order). It never labels a rule right. Output: `to_read.jsonl`.

## Reader instructions

For each rule in `to_read.jsonl`, with `pdf_page_text` (the page shown to the user) and the property facts:

1. Is the rule's text the council's words on that page?
2. Does that page hold them?
3. Does the rule apply to this property: council, zone, precinct or area, heritage status?
4. Write one line of `labels.jsonl`: `rule_key`, `label`, `reason`, and `category` for serious ones.

## Error taxonomy

| Label | Meaning | Counts in the bound |
|---|---|---|
| `ok` | Words, page and property all match | no |
| `minor` | Cosmetic: a repeated heading, a clipped word | no |
| `unsure` | The reader cannot decide | yes, as serious |
| `severe` | See categories | yes |
| `unread` | Not read | no |

Severe categories seen: `wrong-area` (a rule for another property or area), `wrong-words` (words are not the council's).
The third serious kind in the statement is a page that does not hold the words.

## Second reader

Not yet in place for any recorded run. Rule for the next run: a second reader labels every `severe` and `unsure` rule and a
random 20 `ok` rules, blind to the first label. Disagreement on a serious label: the third reading is the council's PDF
page open in front of both, and the label stays `unsure` (counted as serious) until both agree. The agreement rate is recorded in the run folder.

## Rate and pass rule

`upper_bound_per_100(k, n) = chi2.ppf(0.95, 2(k+1)) / 2 / n * 100`, with k = severe + unsure, n = all rules in the pooled runs.
Pass (exit 0) only if rules >= 500, addresses >= 50, newest run <= 30 days old, bound < 2.0.
Current: `python scripts/audit_rate_check.py` prints 830 rules, 83 addresses, severe 6, unsure 3, bound 1.89.
A pass means no worse than the recorded baseline. It does not mean the rules are correct.

## Going forward (proposed, needs the owner's yes: a code change)

- `build_packets.py` writes `seed`, the script's git hash, the date and the council list into `summary.json`.
- `flag_packets.py` writes its git hash and the flag counts into the run folder.
- A re-draw check: same seed and same hash reproduces the address list; the rules drawn are compared as a set and any
  difference is listed.
- Run 9 is read, and the three older runs are re-read where the committed first pass now flags a rule they did not read.
