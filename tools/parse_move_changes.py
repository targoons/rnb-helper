import csv
import json
import re

CSV_PATH = "/Users/targoon/Pokemon/pokemon-run-and-bun/data/raw/move_changes.csv"
OUTPUT_PATH = "calc_service/custom_moves.json"

def parse_val(val):
    if not val or val == "None":
        return None
    if ">" in val:
        return val.split(">")[-1].strip().replace("%", "")
    return val

def main():
    moves = {}
    
    # 1. Parse CSV
    try:
        with open(CSV_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['Move'].strip()
                bp_str = parse_val(row['BP'])
                type_str = parse_val(row['Type'])
                
                move_data = {}
                if bp_str:
                    try:
                        move_data['bp'] = int(float(bp_str)) # handle "10.5" if any, though likely int
                    except:
                        pass
                
                if type_str:
                    move_data['type'] = type_str
                    
                if move_data:
                    moves[name] = move_data
                    
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # 2. Add specific logic overrides mentioned by user but maybe not in CSV fully
    # Hidden Power: Fixed 60 BP
    if 'Hidden Power' not in moves:
        moves['Hidden Power'] = {}
    moves['Hidden Power']['bp'] = 60
    
    # User said: Misty Explosion 100 > 200. CSV has this.
    # User said: Explosion Halves target defense. (Logic change, not stat).
    
    # Write JSON
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(moves, f, indent=4)
        
    print(f"Wrote {len(moves)} custom moves to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
