# Action Item: Integrate test_bulk_items.py with Audit Engine

## Problem

The audit engine shows **147 unverified items**, but `test_bulk_items.py` has already verified **81 items** (40 type boosters, 18 gems, 17 resist berries, 6 manual items). These verifications are not reflected in `mechanics_items.csv`.

## Root Cause

`test_bulk_items.py` exports results to `data/verified_items.json` but does NOT integrate with the audit engine's verification tracking system.

## Solution

Modify `test_bulk_items.py` to record test evidence in a format the audit engine recognizes.

### Option 1: Direct CSV Update (Recommended)

Update `test_bulk_items.py` to modify `mechanics_items.csv` after tests pass:

```python
def update_audit_csv(verified_items):
    """Update mechanics_items.csv with test evidence"""
    import csv
    
    # Read current CSV
    rows = []
    with open('mechanics_items.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Update verified items
    for row in rows:
        if row['Name'] in verified_items:
            row['Status'] = 'Verified (Tested)'
            row['Evidence'] = f"Logic: {row['Evidence']} | Test: test_bulk_items.py"
    
    # Write back
    with open('mechanics_items.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Name', 'Status', 'Evidence', 'Details'])
        writer.writeheader()
        writer.writerows(rows)

# Add to end of run_suite()
update_audit_csv(verified_items)
print(f"Updated mechanics_items.csv with {len(verified_items)} verified items")
```

### Option 2: Test Evidence File

Create a standardized test evidence file that the audit engine reads:

```python
# In test_bulk_items.py
def export_test_evidence(verified_items):
    """Export test evidence for audit engine"""
    evidence = {
        'test_file': 'test_bulk_items.py',
        'test_date': datetime.now().isoformat(),
        'verified_items': [
            {
                'name': item,
                'test_type': 'damage_calculation',
                'status': 'PASS'
            }
            for item in verified_items
        ]
    }
    
    with open('data/test_evidence_items.json', 'w') as f:
        json.dump(evidence, f, indent=2)

# Then modify audit_engine.py to read this file
```

### Option 3: Pytest Integration

Convert `test_bulk_items.py` to proper pytest format with markers:

```python
@pytest.mark.item_verification
@pytest.mark.parametrize("item_name,expected_modifier", [
    ("Charcoal", 1.2),
    ("Fire Gem", 1.3),
    # ...
])
def test_type_booster_item(item_name, expected_modifier):
    # Test logic here
    pass

# Then audit_engine can detect pytest markers
```

## Implementation Steps

1. ✅ Choose Option 1 (simplest integration)
2. Add `update_audit_csv()` function to `test_bulk_items.py`
3. Call it after all tests pass
4. Re-run `test_bulk_items.py`
5. Re-run `audit_engine.py` to verify update
6. Confirm unverified count drops from 147 to 66

## Expected Result

After integration:

- **Before**: 147 unverified (10 verified)
- **After**: 66 unverified (91 verified)
- **Reduction**: 81 items moved from "Unverified" to "Verified (Tested)"

## Files to Modify

1. `tools/test_bulk_items.py` - Add CSV update logic
2. Optional: `tools/audit_engine.py` - Add test evidence reading

---

## Alternative: Just Re-categorize Manually

If integration is too complex, can manually update the 81 items in the CSV:

```bash
# Quick script to update CSV
python3 -c "
import csv
import json

with open('data/verified_items.json') as f:
    verified = set(json.load(f))

rows = []
with open('mechanics_items.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Name'] in verified:
            row['Status'] = 'Verified (Tested)'
            row['Evidence'] = row['Evidence'] + ' | Test: test_bulk_items.py'
        rows.append(row)

with open('mechanics_items.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Name', 'Status', 'Evidence', 'Details'])
    writer.writeheader()
    writer.writerows(rows)

print('Updated CSV with verified items')
"
```
