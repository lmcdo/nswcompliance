import sys
sys.path.insert(0, '.')
from scripts.hub_scrapers.inner_west import scrape

chapters = scrape()
for c in chapters:
    print(c)
