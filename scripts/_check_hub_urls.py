import os, requests, psycopg2
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PlotDetect/1.0)"}

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

for council in ("marrickville", "ashfield"):
    cur.execute("""
        SELECT DISTINCT council_page_url, COUNT(*) as n
        FROM dcp_chapter_registry
        WHERE council = %s AND council_page_url IS NOT NULL
        GROUP BY council_page_url
    """, (council,))
    rows = cur.fetchall()
    print(f"\n=== {council} registered hub URLs ===")
    for r in rows:
        print(f"  {r[0]}  ({r[1]} chapters)")

    # Scrape each unique hub URL and count PDFs found
    seen_urls = set()
    for r in rows:
        hub_url = r[0]
        if hub_url in seen_urls:
            continue
        seen_urls.add(hub_url)
        try:
            resp = requests.get(hub_url, headers=HEADERS, timeout=15, allow_redirects=True)
            final_url = resp.url
            soup = BeautifulSoup(resp.text, "html.parser")
            pdfs = [a["href"] for a in soup.find_all("a", href=True) if ".pdf" in a["href"].lower()]
            print(f"  HTTP {resp.status_code} | final URL: {final_url}")
            print(f"  PDFs found on page: {len(pdfs)}")
            if final_url != hub_url:
                print(f"  *** REDIRECTS to different URL ***")
        except Exception as e:
            print(f"  ERROR: {e}")

conn.close()
