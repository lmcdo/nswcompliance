# citation_proof.py hardening — iteration log (branch fix/citation-proof-nearest-heading)
Bench: `python <this folder>/bench.py <tag>` run from the worktree root. Output: bench_<tag>.csv + <tag>.log.
Sets: known_wrong = 368 numbers corrected 2026-10-30, judged under their OLD ref+text (must NOT be shown);
fixed_right = same rows under the corrected ref; known_right = 1,688 rows confirmed right by page checks.
"Shown" = proven or imprecise (frontend-nextjs/lib/citation-display.ts).

| run | change | known_wrong shown | fixed_right proven | known_right proven |
|---|---|---|---|---|
| baseline | origin/main a46b4c4b | 57 (21 proven + 36 imprecise) | 315 | 1017 |
| v1 | header only on rule's page; bookmark-restored picture numbers | 51 | 321 | 1017 |
| v2 | no "chapter in header + unchecked item" | 16 | 321 | 1017 |
| v3 | (run started before v4 code; ignore) | - | - | - |
| v4 | repeated wording judged on proven page; section+item must match printed sub-section; bookmarks overrule summary lines | 7 (6 proven + 1 imprecise) | 318 | 1017 |

v4 notes: fixed_right "lost" 7 = Woollahra D5/D6 rows 237306/237373/237463/237858/237863/237888/237890. They are
summary lines inside the chapter guide (D5.1.5 / D6.1.5 per bookmarks); today's renumber (D6.3->D6.4 etc) was ALSO
wrong. Checker now withholds their number = correct (shows page only).
Remaining 7 leaks: 160184 249160 249227 249277 249654 189964 220432 -> next iteration.
| v5 | heading inside the rule's span: rule must have opened under its parent | 4 | 318 | 1016 |
| v6 | same, without the word-count escape when the opening section is known | 3 | 318 | 1016 |

Remaining 3 (v6), each checked on the live page:
- 160184, 189964: the SAME wording is printed under both sections (Woollahra E4.3.2/E4.3.3 "refer to the SEPP 55
  guidelines..."; City of Sydney 3.16.12.14/.15 "(3) The replacement..."). The old citation is literally true for one
  copy. Not a false citation.
- 220432: the rule's opening words are printed on p1109 (9.3.5.2.1) and p1110 (9.3.5.2.2); its text cites figure
  9.3.5.2.2.2. Today's renumber to 9.3.5.2.1 is doubtful; the checker withholds the new number (safe).
Cost: 1 known-right rule lost (122395, CB "1.17", own clause number printed inside its span) -> shows page only.
| v7 | bookmark used only if its title is printed on its page (cross-review MEDIUM) | 3 | 318 | 1016 |
