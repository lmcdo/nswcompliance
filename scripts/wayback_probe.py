import requests

urls = [
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer?f=json",
    "https://metadata.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/0/query?where=1=1&outFields=*&f=json&resultRecordCount=3",
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/WMTSCapabilities.xml",
    "https://metadata.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer?f=json",
]

for url in urls:
    try:
        r = requests.get(url, timeout=10)
        print(f"[{r.status_code}] {url[:90]}")
        print(f"  {r.text[:200]}")
        print()
    except Exception as e:
        print(f"[ERR] {url[:90]}: {e}")
        print()
