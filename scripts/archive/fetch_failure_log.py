import urllib.request

logs = [
    ("parramatta", "https://d3gm2hf49xd6jj.cloudfront.net/a01d59d4-9372-412e-909a-1da798e07eee/a01d59d4-9372-412e-909a-1da798e07eee.log"),
    ("hills",      "https://d3gm2hf49xd6jj.cloudfront.net/37148a8b-5ae0-4f7b-b959-3c0257218aab/37148a8b-5ae0-4f7b-b959-3c0257218aab.log"),
]
for name, url in logs:
    print(f"\n{'='*50}")
    print(f"Log: {name}")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            text = r.read().decode("utf-8", errors="replace")
            # Last 2000 chars — errors are at the end
            print(text[-2000:])
    except Exception as e:
        print(f"Error: {e}")
