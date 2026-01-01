"""
Quick script to update mechanics_items.csv with verified items from test_bulk_items.py
"""
import csv
import json
import os

os.chdir('/Users/targoon/Pokemon/pokemon_rnb_helper')

# Load verified items from test_bulk_items
with open('data/verified_items.json') as f:
    verified = set(json.load(f))

print(f"Loaded {len(verified)} verified items from test_bulk_items.py")

# Read current CSV
rows = []
with open('mechanics_items.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Update verified items
updated_count = 0
for row in rows:
    if row['Name'].strip() in verified:
        if 'Unverified' in row['Status']:
            row['Status'] = 'Verified (Tested)'
            # Append test evidence
            current_evidence = row['Evidence']
            if 'Test: test_bulk_items.py' not in current_evidence:
                row['Evidence'] = current_evidence + ' | Test: test_bulk_items.py'
            updated_count += 1

print(f"Updated {updated_count} items to 'Verified (Tested)' status")

# Write back
with open('mechanics_items.csv', 'w', encoding='utf-8', newline='') as f:
    fieldnames = ['Name', 'Status', 'Evidence', 'Details']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ mechanics_items.csv updated successfully")
print(f"Run audit_engine.py again to see updated counts")
