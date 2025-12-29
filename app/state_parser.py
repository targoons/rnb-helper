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

def parse_state(file_path):
    """
    Reads the JSON state and returns a structured object.
    Includes retry logic to handle potential read/write race conditions.
    Normalizes keys to snake_case.
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
            # print(f"Error parsing state (attempt {attempt+1}): {e}")
            time.sleep(0.1)
    
    if data:
        return normalize_keys(data)
    return None
