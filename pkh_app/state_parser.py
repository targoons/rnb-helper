import json
import time
import re

def to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def normalize_keys(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            new_k = to_snake_case(k)
            new_obj[new_k] = normalize_keys(v)
        return new_obj
    elif isinstance(obj, list):
        return [normalize_keys(i) for i in obj]
    else:
        return obj


import os

# Load Maps
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_json_map(path):
    p = os.path.join(BASE_DIR, path)
    if os.path.exists(p):
        with open(p, 'r') as f:
            return json.load(f)
    return {}

ITEMS_MAP = load_json_map("data/item_ids.json")
SPECIES_MAP = load_json_map("data/species.json")

def resolve_ids(obj):
    if isinstance(obj, dict):
        # Resolve Item
        if 'item' in obj and isinstance(obj['item'], int):
            # Check if valid ID
            if str(obj['item']) in ITEMS_MAP:
                obj['item'] = ITEMS_MAP[str(obj['item'])]
            else:
                 # Keep as int or set to None?
                 pass 
        
        # Resolve Species
        if 'species_id' in obj:
            # Lua uses speciesId string "123". state_parser might see int or string depending on JSON loader?
            # Lua writes "speciesId": "123". So it's string.
            # But wait, Lua line 297: string.format(' "speciesId": "%d"', ...).
            # So it is a string in JSON.
            sid = str(obj['species_id'])
            if sid in SPECIES_MAP:
                obj['species'] = SPECIES_MAP[sid]
                # We can also set 'name' if missing
                if 'name' not in obj or not obj['name']:
                    obj['name'] = SPECIES_MAP[sid]
        
        # Recurse
        for k, v in obj.items():
            resolve_ids(v)
            
    elif isinstance(obj, list):
        for i in obj:
            resolve_ids(i)
    return obj

def parse_state(file_path):
    """
    Reads the JSON state, normalizes keys, and resolves IDs to names.
    """
    data = None
    for attempt in range(3):
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Empty file")
                data = json.loads(content)
                break
        except (json.JSONDecodeError, ValueError, IOError) as e:
            time.sleep(0.1)
    
    if data:
        normalized = normalize_keys(data)
        return resolve_ids(normalized)
    return None

