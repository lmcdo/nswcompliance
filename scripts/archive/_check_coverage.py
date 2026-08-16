# Probe Randwick DCP PDF URLs based on known pattern
import requests

base = "https://www.randwick.nsw.gov.au/__data/assets/pdf_file"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Known URLs from search results - extract the pattern
known = {
    'Volume-1-Parts-A-C': '/0020/13736/Randwick-Comprehensive-DCP-Volume-1-Parts-A-C.pdf',
    'Part-B-General-Controls': '/0003/13737/Part-B-General-Controls.pdf',
    'Low-Density-Residential': '/0004/13738/Low-Density-Residential.pdf',
    'Medium-Density-Residential': '/0005/13739/Medium-Density-Residential.pdf',
    'Neighbourhood-Centres': '/0004/13747/Neighbourhood-Centres-General-Controls.pdf',
    'Royal-Randwick-Racecourse': '/0018/13752/Royal-Randwick-Racecourse.pdf',
    'Newmarket-DCP': '/0009/176436/Newmarket-DCP.pdf',
}

# Try sequential IDs around 13736-13760
print("=== Probing sequential IDs around 13736-13760 ===")
for fid in range(13736, 13760):
    for sub in range(0, 21):
        url = f"{base}/{sub:04d}/{fid}/"
        try:
            r = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
            if r.status_code == 200:
                print(f"  HIT: {url} -> {r.url}")
        except:
            pass

print("\nDone")
