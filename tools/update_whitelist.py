
import json
import os

def normalize(name):
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")

def update_whitelist():
    whitelist_path = "data/rnb_whitelist.json"
    verified_path = "data/verified_items.json"
    
    with open(whitelist_path, 'r') as f:
        whitelist = json.load(f)
        
    with open(verified_path, 'r') as f:
        verified_items = json.load(f)
        
    current_whitelist_items = set(whitelist.get('items', []))
    
    added_count = 0
    for item in verified_items:
        norm_item = normalize(item)
        if norm_item not in current_whitelist_items:
             whitelist['items'].append(norm_item)
             added_count += 1
             
    whitelist['items'].sort()
    
    with open(whitelist_path, 'w') as f:
        json.dump(whitelist, f, indent=4)
        
    print(f"Added {added_count} verified items to whitelist.")

if __name__ == "__main__":
    update_whitelist()
