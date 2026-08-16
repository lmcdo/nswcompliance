#!/usr/bin/env python3
"""Try various S3 mirror URLs for remaining councils."""
import sys
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

base = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf"

# Try various naming patterns
attempts = [
    # Parramatta
    f"{base}/PARRAMATTA/Parramatta%20DCP%202011.pdf",
    f"{base}/PARRAMATTA/Parramatta%20Development%20Control%20Plan%202011.pdf",
    f"{base}/CITY+OF+PARRAMATTA/City+of+Parramatta+DCP.pdf",
    f"{base}/CITY%20OF%20PARRAMATTA/City%20of%20Parramatta%20DCP.pdf",
    # Northern Beaches
    f"{base}/NORTHERN+BEACHES/Northern+Beaches+DCP+2022.pdf",
    f"{base}/NORTHERN%20BEACHES/Northern%20Beaches%20DCP%202022.pdf",
    f"{base}/NORTHERN+BEACHES/Warringah+DCP+2011.pdf",
    f"{base}/WARRINGAH/Warringah%20DCP%202011.pdf",
    f"{base}/PITTWATER/Pittwater%20DCP%2021.pdf",
    f"{base}/MANLY/Manly%20DCP%202013.pdf",
    # Inner West
    f"{base}/INNER+WEST/Inner+West+DCP.pdf",
    f"{base}/INNER%20WEST/Inner%20West%20DCP%202021.pdf",
    f"{base}/ASHFIELD/Ashfield+DCP+2007.pdf",
    f"{base}/ASHFIELD/Ashfield%20DCP%202007.pdf",
    f"{base}/MARRICKVILLE/Marrickville%20DCP%202011.pdf",
    f"{base}/LEICHHARDT/Leichhardt%20DCP%202013.pdf",
]

client = httpx.Client(timeout=30.0, follow_redirects=True)
for url in attempts:
    try:
        r = client.head(url)
        size = r.headers.get("content-length", "?")
        print(f"{r.status_code} {size:>12s} bytes  {url.split('/')[-1][:60]}")
    except Exception as e:
        print(f"ERR {type(e).__name__:20s} {url.split('/')[-1][:60]}")
client.close()
