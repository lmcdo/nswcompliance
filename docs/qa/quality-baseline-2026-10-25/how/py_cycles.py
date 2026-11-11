"""Python import cycles (Tarjan SCC) over files under ROOT, using qa_live_files' resolver."""
import sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(Path(sys.argv[2]).resolve()))
import qa_live_files as q
q.ROOT = root
q.PY_SEARCH = [root, root / "scripts", root / "services", root / "src", root / "enrichment"]
q.literal_py = lambda text, here: []  # spawned scripts are not imports
files = [p for p in root.rglob("*.py") if not any(x in p.parts for x in ("node_modules", ".git", "venv", ".venv"))]
g = {f.resolve(): {e.resolve() for e in q.py_edges(f) if e.suffix == ".py"} for f in files}
idx, low, st, on, out, n = {}, {}, [], set(), [], [0]
sys.setrecursionlimit(100000)
def sc(v):
    idx[v] = low[v] = n[0]; n[0] += 1; st.append(v); on.add(v)
    for w in g.get(v, ()):
        if w not in g: continue
        if w not in idx: sc(w); low[v] = min(low[v], low[w])
        elif w in on: low[v] = min(low[v], idx[w])
    if low[v] == idx[v]:
        comp = []
        while True:
            w = st.pop(); on.discard(w); comp.append(w)
            if w == v: break
        if len(comp) > 1 or v in g[v]: out.append(sorted(c.relative_to(root).as_posix() for c in comp))
for v in g:
    if v not in idx: sc(v)
print(f"# files {len(g)} cycles {len(out)}")
for c in sorted(out, key=len, reverse=True): print(len(c), " | ".join(c))
