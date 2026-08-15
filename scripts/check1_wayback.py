import requests, json, math, re, sys

r = requests.get("https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer", params={"f":"json"}, timeout=20)
raw = r.json().get("Selection",[])
print(f"Total releases: {len(raw)}")

def d(name):
    m=re.search(r"(\d{4}-\d{2}-\d{2})",name)
    return m.group(1) if m else ""

rels=sorted([{"M":x["M"],"date":d(x["Name"])} for x in raw],key=lambda x:x["date"])
print(f"Earliest: {rels[0]}")
print(f"Latest:   {rels[-1]}")
in_range=[x for x in rels if "2017"<=x["date"][:4]<="2025"]
pre2020=[x for x in in_range if x["date"][:4]<="2019"]
print(f"2017-2025: {len(in_range)}  pre-2020: {len(pre2020)}")
for x in pre2020: print(f"  {x}")

# tile test
lat,lon,z=-33.9139,151.1554,19
n=2**z
tx=int((lon+180)/360*n)
ty=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
T="https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{M}/{z}/{y}/{x}"
for rel in ([pre2020[0]] if pre2020 else [])+([in_range[-1]] if in_range else []):
    tr=requests.get(T.format(M=rel["M"],z=z,y=ty,x=tx),timeout=10)
    print(f"Tile M={rel['M']} ({rel['date']}): {tr.status_code} {len(tr.content)}b {tr.headers.get('Content-Type','')[:20]}")
sys.stdout.flush()
