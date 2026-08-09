#!/usr/bin/env python3
# prior-art-checked: reuse not viable because measure_control_page_corrections.py resolves
# by VALUE + wording, which is ambiguous in a 448-page plan (11 rows had 2-9 candidate
# pages each). This resolves by the document's own chapter/section numbering instead and
# is the recipe behind the 11 Waverley corrections -- committed so they are reproducible
# rather than a hand-run scratchpad, which is the exact failure the extraction post-mortem
# names. Nothing else parses section_ref against a running header: validate_dcp_setbacks.py,
# validate_control_source_values.py (#868), link_controls_to_provisions.py (#867) and
# numeric_control_review.py never open the header. Four sweeps 2026-08-09 vs f5acb080.
"""Locate a control's page via the document's OWN chapter/section numbering.

Read-only. Used to resolve the 11 Waverley rows whose value alone was ambiguous.

Our refs read 'C2.9(b)'. The PDF never writes that string. It puts the chapter code in
the running header ('Other Residential Development C2') and the section number in the
body ('2.9 LANDSCAPING'). So the locator is (chapter in header) AND (section heading in
body), not the ref verbatim.
"""
import os, sys, tempfile, re
from pathlib import Path
import psycopg2, fitz

WT = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\.claude\worktrees\controls-calibration")
sys.path.insert(0, str(WT / "scripts"))
from validate_controls_against_source_pdf import normalise, page_supports  # noqa: E402

for b in [WT, *WT.parents]:
    if (b / ".env").exists():
        for ln in (b / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        break

IDS = [629, 630, 631, 632, 633, 634, 557, 558, 559, 560, 561]
c = psycopg2.connect(host=os.environ["PGHOST"], user=os.environ["PGUSER"],
                     password=os.environ["PGPASSWORD"], dbname=os.environ["PGDATABASE"],
                     port=os.environ.get("PGPORT", "5432"), sslmode="require", connect_timeout=30)
c.set_session(readonly=True, autocommit=True)
cur = c.cursor()
cur.execute("""SELECT id,control_type,value_min,value_max,unit,source_text,pdf_page,section_ref
               FROM dcp_setback_controls WHERE id = ANY(%s) AND is_current ORDER BY id""", (IDS,))
rows = cur.fetchall()

pdf = Path(tempfile.gettempdir()) / "dcp_pdf_cache" / \
      "source-pdfs__dcps__waverley__v1.1-2026-03-16__waverley-dcp-2022.pdf"
doc = fitz.open(pdf)
pages = {i + 1: doc[i].get_text() for i in range(doc.page_count)}
norm = {p: normalise(t) for p, t in pages.items()}

# Chapter code -> the pages whose running header carries it.
chapter_pages: dict[str, list[int]] = {}
for p, t in norm.items():
    for m in re.finditer(r"\b(c\d{1,2})\s+waverley development control plan", t):
        chapter_pages.setdefault(m.group(1), []).append(p)
print("chapters found in headers:",
      {k: f"{min(v)}-{max(v)} ({len(v)}pp)" for k, v in sorted(chapter_pages.items())}, "\n")

REF = re.compile(r"^\s*(C\d{1,2})\.(\d{1,2})", re.I)
resolved = []
for (cid, ct, vmin, vmax, unit, txt, cited, ref) in rows:
    m = REF.match(ref or "")
    print("=" * 88)
    print(f"id={cid} {ct} {vmin}..{vmax}{unit or ''} cites p{cited} ref={ref}")
    if not m:
        print("  ref does not parse as C<chapter>.<section>")
        continue
    chap, sect = m.group(1).lower(), m.group(2)
    heading = re.compile(rf"(?<!\d)\b{chap[1:]}\.{sect}\s+[A-Z]", re.M)
    cands = []
    for p in chapter_pages.get(chap, []):
        if heading.search(pages[p]):
            cands.append(p)
    print(f"  chapter {chap.upper()} spans pages "
          f"{min(chapter_pages.get(chap, [0]))}-{max(chapter_pages.get(chap, [0]))}")
    print(f"  heading '{chap[1:]}.{sect}' found on: {cands or 'none'}")

    val_pages = [p for p, t in pages.items() if page_supports(txt, t, vmin, vmax)[0]]
    print(f"  value+wording on            : {val_pages}")
    # accept a value page within the heading's section (heading page .. +3)
    hits = [v for v in val_pages for h in cands if h <= v <= h + 3]
    print(f"  ---> value inside that section: {sorted(set(hits)) or 'none'}")
    if len(set(hits)) == 1:
        p = sorted(set(hits))[0]
        print(f"  ===> RESOLVED to page {p}  (cited {cited}, offset {p - cited:+d})")
        resolved.append({"id": cid, "cited_page": cited, "proposed_page": p,
                         "offset": p - cited, "ref": ref, "control_type": ct,
                         "basis": f"section heading {chap[1:]}.{sect} in chapter "
                                  f"{chap.upper()} at p{[h for h in cands if h <= p <= h+3][0]}"})
        raw = re.sub(r"\s+", " ", pages[p])
        print(f"       {raw[:300]}")
    else:
        print("  ===> STILL AMBIGUOUS — leave alone")

print("\n\nRESOLVED:", len(resolved), "of", len(rows))
import json
out = WT / "data" / "waverley_section_resolution.json"
out.write_text(json.dumps(resolved, indent=2), encoding="utf-8")
print("written:", out)
doc.close()
