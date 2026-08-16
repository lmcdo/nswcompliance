import json

recs = json.load(open('validation_output/ground_truth/cc_records.json'))
qualified = [r for r in recs if 450 <= r.get('lot_area_m2', 0) <= 5000]
qualified_sorted = sorted(qualified, key=lambda r: r['lot_area_m2'], reverse=True)

print(f'Total records: {len(recs)}')
print(f'450-5000m2 (target range): {len(qualified)}')
print()
print('Top 20 by lot size (these are next batch):')
for r in qualified_sorted[:20]:
    print(f"  {r['lot_area_m2']:>7.0f}m2  {r['address']:<45}  CC={r['cc_date']}")
