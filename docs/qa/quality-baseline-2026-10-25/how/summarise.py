"""Step 1 summary: each tool's count, whole repo and live-only (served+scheduled), worst 5."""
import json, re, sys
from collections import Counter
from pathlib import Path
R = Path(sys.argv[1]); S = Path(sys.argv[2])
live = {}
for line in (R.parent / "live_files.tsv").read_text(encoding="utf-8").splitlines():
    if line.startswith("#"): continue
    c, p = line.split("\t"); live[p] = c
L = {p for p, c in live.items() if c in ("served", "scheduled")}
def rel(p):
    p = str(p).replace("\\", "/"); s = str(S).replace("\\", "/")
    return p[len(s):].lstrip("/") if p.lower().startswith(s.lower()) else p.lstrip("./")
def fe(p): return "frontend-nextjs/" + rel(p) if not rel(p).startswith("frontend-nextjs/") else rel(p)
def j(name): return json.loads((R / f"{name}.out").read_text(encoding="utf-8"))
rows = []
def row(metric, allc, livec, worst): rows.append((metric, allc, livec, worst))
# ruff
for name in ("ruff_default_try2", "ruff_swallowed_try2"):
    hits = [rel(m.group(1)) for m in re.finditer(r"^(.+?\.py):\d+:\d+:", (R/f"{name}.out").read_text(encoding="utf-8"), re.M)]
    lv = Counter(h for h in hits if h in L)
    row(name, len(hits), sum(lv.values()), lv.most_common(5))
# radon cc: functions graded D-F (cc > 20)
cc = j("radon_cc"); bad = []
for f, blocks in cc.items():
    if not isinstance(blocks, list): continue
    for b in blocks:
        if isinstance(b, dict) and b.get("complexity", 0) > 20: bad.append((rel(f), b["name"], b["complexity"]))
lb = sorted([b for b in bad if b[0] in L], key=lambda x: -x[2])
row("functions cc>20 (D-F)", len(bad), len(lb), [(f"{b[0]}:{b[1]}", b[2]) for b in lb[:5]])
mi = j("radon_mi"); lowmi = [(rel(f), v["mi"]) for f, v in mi.items() if isinstance(v, dict) and v.get("rank") in ("C",)]
lm = sorted([m for m in lowmi if m[0] in L], key=lambda x: x[1])
row("files MI grade C", len(lowmi), len(lm), [(a, round(b, 1)) for a, b in lm[:5]])
# vulture
vh = [rel(m.group(1)) for m in re.finditer(r"^(.+?\.py):\d+:", (R/"vulture.out").read_text(encoding="utf-8"), re.M)]
lv = Counter(h for h in vh if h in L); row("vulture dead code (80%+)", len(vh), sum(lv.values()), lv.most_common(5))
# bandit high
bd = j("bandit")["results"]; hi = [r for r in bd if r["issue_severity"] == "HIGH"]
lh = [r for r in hi if rel(r["filename"]) in L]
row("bandit HIGH", len(hi), len(lh), Counter(f"{rel(r['filename'])} {r['test_id']}" for r in lh).most_common(5))
med = [r for r in bd if r["issue_severity"] == "MEDIUM"]
row("bandit MEDIUM", len(med), sum(1 for r in med if rel(r["filename"]) in L), Counter(r["test_id"] for r in med if rel(r["filename"]) in L).most_common(5))
# pip-audit
for name in ("pip_audit_api", "pip_audit_monitors"):
    d = j(name)["dependencies"]; v = [x for x in d if x.get("vulns")]
    row(name + " pkgs w/ CVE", len(v), len(v), [(x["name"], x["version"], len(x["vulns"]), sorted({f for y in x["vulns"] for f in y.get("fix_versions", [])})[-1:]) for x in v])
# eslint
es = j("eslint_try3"); le = [f for f in es if fe(f["filePath"]) in L]
row("eslint errors", sum(f["errorCount"] for f in es), sum(f["errorCount"] for f in le), [])
row("eslint warnings", sum(f["warningCount"] for f in es), sum(f["warningCount"] for f in le), sorted(((fe(f["filePath"]), f["warningCount"]) for f in le if f["warningCount"]), key=lambda x: -x[1])[:5])
# npm audit
na = j("npm_audit")["metadata"]["vulnerabilities"]; row("npm audit (high, critical)", (na.get("high"), na.get("critical")), "n/a (package level)", [])
# knip
kn = j("knip_try3"); unused_files = [fe(f["name"]) for i in kn["issues"] for f in i.get("files", [])]
unused_exports = [(fe(i["file"]), len(i.get("exports", []))) for i in kn["issues"] if i.get("exports")]
row("knip unused files", len(unused_files), sum(1 for f in unused_files if f in L), [f for f in unused_files if f in L][:5])
row("knip unused exports", sum(n for _, n in unused_exports), sum(n for f, n in unused_exports if f in L), sorted([e for e in unused_exports if e[0] in L], key=lambda x: -x[1])[:5])
# cycles
md = j("madge_circular"); row("TS import cycles (madge)", len(md), sum(1 for c in md if all(fe(x) in L for x in c)), md)
pc = [l.split(" ", 1)[1].split(" | ") for l in (R/"py_cycles.out").read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
row("Python import cycles", len(pc), sum(1 for c in pc if any(x in L for x in c)), pc)
# jscpd
jr = json.loads((R/"jscpd"/"jscpd-report.json").read_text(encoding="utf-8"))
tot = jr["statistics"]["total"]; row("jscpd duplicated lines %", round(tot["percentage"], 2), "see live calc", [])
dup = Counter(); lines = Counter()
for d in jr["duplicates"]:
    for side in ("firstFile", "secondFile"):
        f = rel(d[side]["name"]); dup[f] += d["lines"]
live_dup = {f: n for f, n in dup.items() if f in L}
lc = {l.split("\t")[1]: int(l.split("\t")[0]) for l in (R/"line_counts.out").read_text(encoding="utf-8").splitlines() if "\t" in l}
live_lines = sum(n for f, n in lc.items() if f in L)
row("jscpd dup lines in live files", sum(dup.values()), f"{sum(live_dup.values())} of {live_lines} ({100*sum(live_dup.values())/max(live_lines,1):.1f}%, upper bound)", sorted(live_dup.items(), key=lambda x: -x[1])[:5])
big = sorted([(f, n) for f, n in lc.items() if n > 500], key=lambda x: -x[1])
row("files > 500 lines", len(big), sum(1 for f, _ in big if f in L), [b for b in big if b[0] in L][:5])
print(f"live files scored: {len(L)}")
for m, a, l, w in rows:
    print(f"\n## {m}\n  all={a}  live={l}")
    for x in (w if isinstance(w, list) else [])[:5]: print("   ", x)
