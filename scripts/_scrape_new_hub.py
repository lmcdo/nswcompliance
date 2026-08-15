import os, requests, psycopg2
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup

HUB_URL = "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/leichhardt-dcp/leichhardt-dcp"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PlotDetect/1.0)"}

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()
cur.execute("SELECT council_url FROM dcp_chapter_registry WHERE council = 'leichhardt'")
registered = {r[0] for r in cur.fetchall() if r[0]}
conn.close()

resp = requests.get(HUB_URL, headers=HEADERS, timeout=30)
print(f"HTTP {resp.status_code}")
soup = BeautifulSoup(resp.text, "html.parser")

all_pdfs = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if ".pdf" not in href.lower():
        continue
    if href.startswith("/"):
        href = "https://www.innerwest.nsw.gov.au" + href
    label = a.get_text(strip=True) or "(no label)"
    all_pdfs.append((label, href))

print(f"\nTotal PDFs on page: {len(all_pdfs)}")
print("\n=== ALREADY REGISTERED ===")
for label, href in all_pdfs:
    if href in registered:
        print(f"  [ok] {label}")

print("\n=== NOT REGISTERED (new) ===")
for label, href in all_pdfs:
    if href not in registered:
        print(f"  [NEW] {label}")
        print(f"        {href}")
