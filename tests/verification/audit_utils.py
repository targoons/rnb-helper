import csv
import json
import os

def update_audit_with_verified(new_verified_items=None, json_path='data/verified_items.json', csv_path='reports/mechanics_items.csv'):
    """
    Updates the audit CSV and JSON source of truth with verified items.
    
    Args:
        new_verified_items (list): List of newly verified item names. Can be None if just syncing.
        json_path (str): Path to the JSON file storing verified items.
        csv_path (str): Path to the mechanics_items.csv file.
    """
    if new_verified_items is None:
        new_verified_items = []
        
    # 1. Update JSON Source of Truth
    existing_items = set()
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                existing_items = set(json.load(f))
        except Exception as e:
            print(f"Warning: Could not read {json_path}: {e}")
            
    # Merge
    all_verified = existing_items.union(set(new_verified_items))
    sorted_verified = sorted(list(all_verified))
    
    try:
        with open(json_path, 'w') as f:
            json.dump(sorted_verified, f, indent=2)
        if new_verified_items:
            print(f"Updated {json_path} (Total Verified: {len(sorted_verified)})")
    except Exception as e:
        print(f"Failed to update JSON: {e}")

    # 2. Update CSV using ALL verified items
    if not os.path.exists(csv_path):
        print(f"⚠️  Warning: {csv_path} not found - skipping audit update")
        return

    try:
        # Read current CSV
        rows = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Update verified items
        updated_count = 0
        for row in rows:
            if row['Name'].strip() in all_verified:
                # Mark as verified logic
                if 'Verified (Tested)' not in row['Status']:
                    row['Status'] = 'Verified (Tested)'
                    current_evidence = row['Evidence']
                    if 'Test: test_bulk_items.py' not in current_evidence: # Generic tag
                        row['Evidence'] = current_evidence + ' | Test: Verified Check'
                    updated_count += 1
        
        # Write back
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['Name', 'Status', 'Evidence', 'Details']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        if updated_count > 0:
            print(f"✅ Updated mechanics_items.csv: {updated_count} items marked as 'Verified (Tested)'")
        else:
            print("Audit CSV is up to date.")
            
    except Exception as e:
        print(f"⚠️  Warning: Failed to update audit CSV: {e}")
