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
        if 'item' in obj or 'item_id' in obj or 'itemId' in obj:
            ival = obj.get('item', obj.get('item_id', obj.get('itemId')))
            if ival is not None:
                item_val = str(ival)
                if item_val in ITEMS_MAP:
                    obj['item'] = ITEMS_MAP[item_val]
                else:
                    obj['item'] = item_val
                # Harmonize key
                obj['item_id'] = item_val

        # Resolve Species
        if 'species_id' in obj or 'speciesId' in obj:
            sid_val = obj.get('species_id', obj.get('speciesId'))
            if sid_val is not None:
                sid = str(sid_val)
                obj['species_id'] = sid # Harmonize to string species_id
                if sid in SPECIES_MAP:
                    obj['species'] = SPECIES_MAP[sid]
                    if 'name' not in obj or not obj['name']:
                        obj['name'] = SPECIES_MAP[sid]
        
        # Normalize Stats and Stages
        if 'stats' in obj:
            s_map = {'atk': 'atk', 'def': 'def', 'sp_atk': 'spa', 'sp_def': 'spd', 'speed': 'spe', 'spa': 'spa', 'spd': 'spd', 'spe': 'spe'}
            obj['stats'] = {s_map.get(k, k): v for k, v in obj['stats'].items()}
            
        if 'stat_stages' in obj:
            # Map keys and normalize values (v-6)
            s_map = {'atk': 'atk', 'def': 'def', 'sp_atk': 'spa', 'sp_def': 'spd', 'speed': 'spe', 'spa': 'spa', 'spd': 'spd', 'spe': 'spe', 'accuracy': 'acc', 'evasion': 'eva'}
            new_stages = {}
            for k, v in obj['stat_stages'].items():
                new_k = s_map.get(k, k)
                # If value > 6, it might be 0-12. If it's already -6 to 6, this might be tricky.
                # In R&B Lua, it's always 0-12 in the raw state.
                # However, some systems might already have -6 to 6.
                # Safety: if any value is > 6, or all are >= 0 and we see a 12, it's 0-12.
                # But safer to just assume 0-12 is the source.
                if isinstance(v, int):
                    # We'll stick to subtracting 6 if it's within 0-12 range.
                    if 0 <= v <= 12:
                        new_stages[new_k] = v - 6
                    else:
                        new_stages[new_k] = v
                else:
                    new_stages[new_k] = v
            obj['stat_stages'] = new_stages

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

