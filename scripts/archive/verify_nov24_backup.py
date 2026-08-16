"""Verify Nov 24 backup before restoring."""
import json

backup_file = 'backups/regulatory_provisions_4layer_complete_20251124_081014.json'

print("\n" + "="*70)
print("VERIFYING NOV 24 BACKUP")
print("="*70)

with open(backup_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Handle both formats: list or dict with metadata
if isinstance(data, list):
    provisions = data
    metadata = {}
else:
    metadata = data.get('metadata', {})
    provisions = data.get('data', [])

print(f"\nBackup file: {backup_file}")
print(f"Total provisions: {len(provisions)}")

# Check enrichment stats if available
if metadata:
    enrichment_stats = metadata.get('enrichment_stats', {})
    if enrichment_stats:
        print(f"\nEnrichment stats:")
        for key, value in enrichment_stats.items():
            print(f"  {key}: {value}")

# Check v2_is_actionable distribution
actionable_true = sum(1 for p in provisions if p.get('v2_is_actionable') is True)
actionable_false = sum(1 for p in provisions if p.get('v2_is_actionable') is False)
actionable_null = sum(1 for p in provisions if p.get('v2_is_actionable') is None)

print(f"\nv2_is_actionable distribution:")
print(f"  TRUE:  {actionable_true:,}")
print(f"  FALSE: {actionable_false:,}")
print(f"  NULL:  {actionable_null:,}")

# Check sample provisions
print(f"\nSample provisions:")
for i in [0, len(provisions)//2, -1]:
    p = provisions[i]
    print(f"\n  Provision {i}:")
    print(f"    ID: {p.get('id')}")
    print(f"    Document: {p.get('document_id')}")
    print(f"    v2_is_actionable: {p.get('v2_is_actionable')}")
    print(f"    v2_dcp_layer: {p.get('v2_dcp_layer')}")

print("\n" + "="*70)
if actionable_true >= 11000:
    print("[SUCCESS] Backup looks good - has ~11,835 actionable provisions")
    print("Ready to restore!")
else:
    print("[WARNING] Backup may not have correct actionable classification")
print("="*70 + "\n")
