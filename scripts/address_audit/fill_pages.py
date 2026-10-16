"""Fill pdf_page_text in packets.jsonl from each row's page_source_path on R2 (documents.r2_pdf_url is NULL)."""
import json,os,sys,psycopg2
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))  # run from inside a run dir: reads/writes ./packets.jsonl
from build_packets import pdf_page_text
R2="https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/"
P=[json.loads(l) for l in open('packets.jsonl',encoding='utf-8')]
c=psycopg2.connect(os.environ['DATABASE_URL']);cur=c.cursor();cur.execute("set statement_timeout=30000")
ids=[int(p['rule_key'].split(':')[1]) for p in P]
cur.execute("select id, coalesce(page_source_path, quote_source_path) from regulatory_provisions where id=any(%s)",(ids,))
path=dict(cur.fetchall())
for p in P:
    sp=path.get(int(p['rule_key'].split(':')[1]))
    p['source_url']=R2+sp if sp else None
    try: p['pdf_page_text']=pdf_page_text(p['source_url'],p['shown_page'])
    except Exception as e: p['pdf_page_text']=f"<pdf error {e}>"
with open('packets.jsonl','w',encoding='utf-8') as f:
    for p in P: f.write(json.dumps(p,ensure_ascii=False,default=str)+"\n")
print(sum(1 for p in P if p['pdf_page_text'] and not p['pdf_page_text'].startswith('<')),'of',len(P))
