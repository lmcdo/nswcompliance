#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cur = conn.cursor()

# Check kg tables
kg_entities = cur.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
kg_relationships = cur.execute("SELECT COUNT(*) FROM kg_relationships").fetchone()[0]

print(f"kg_entities: {kg_entities}")
print(f"kg_relationships: {kg_relationships}")

# Find visual-related relationships
visual_rels = cur.execute("""
    SELECT head, relation, tail 
    FROM kg_relationships 
    WHERE relation LIKE '%visual%' 
       OR relation LIKE '%image%' 
       OR relation LIKE '%diagram%' 
       OR relation LIKE '%figure%'
       OR relation LIKE '%illustration%'
       OR tail LIKE '%.png'
       OR tail LIKE '%.jpg'
    LIMIT 20
""").fetchall()

print(f"\nVisual relationships found: {len(visual_rels)}")
for h, r, t in visual_rels:
    print(f"  {h[:40]} --[{r}]--> {t[:40]}")

# Check if any entities are image paths
image_entities = cur.execute("""
    SELECT entity_name, entity_type 
    FROM kg_entities 
    WHERE entity_name LIKE '%.png' 
       OR entity_name LIKE '%.jpg' 
       OR entity_name LIKE '%/images/%'
       OR entity_type LIKE '%image%'
       OR entity_type LIKE '%diagram%'
    LIMIT 20
""").fetchall()

print(f"\nImage entities found: {len(image_entities)}")
for name, etype in image_entities:
    print(f"  {name[:60]} (type: {etype})")

conn.close()