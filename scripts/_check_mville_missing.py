import os, requests, psycopg2
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PlotDetect/1.0)"}
# Use the final redirect URL
HUB_URL = "https://www.innerwest.nsw.gov.au/development-controls-lep-and-dcp/marrickville-development-control-plan-dcp"

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()
cur.execute("SELECT council_url FROM dcp_chapter_registry WHERE council = 'marrickville'")
registered = {r[0] for r in cur.fetchall() if r[0]}
conn.close()

resp = requests.get(HUB_URL, headers=HEADERS, timeout=30)
soup = BeautifulSoup(resp.text, "html.parser")

new = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if ".pdf" not in href.lower():
        continue
    if href.startswith("/"):
        href = "https://www.innerwest.nsw.gov.au" + href
    if href not in registered:
        label = a.get_text(strip=True) or "(no label)"
        new.append((label, href))

print(f"Unregistered PDFs on marrickville hub: {len(new)}\n")
for label, href in new:
    print(f"  {label}")
    print(f"  {href}\n")
