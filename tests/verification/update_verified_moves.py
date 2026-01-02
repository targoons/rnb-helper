import os
import re
import json
import sys

# Add root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT_DIR)

def run():
    print("Scanning tests for Verified Moves...")
    
    # Scan ALL test files that might verify moves
    scan_files = [
        # Legacy tests
        os.path.join(ROOT_DIR, "tests", "legacy", "test_bulk_damage_logic.py"),
        os.path.join(ROOT_DIR, "tests", "legacy", "test_bulk_verification.py"),
        
        # Feature tests
        os.path.join(ROOT_DIR, "tests", "features", "test_complex_moves.py"),
        os.path.join(ROOT_DIR, "tests", "features", "test_move_implementation.py"),
        os.path.join(ROOT_DIR, "tests", "features", "test_damage_modifiers.py"),
        os.path.join(ROOT_DIR, "tests", "features", "test_advanced_abilities.py"),
        os.path.join(ROOT_DIR, "tests", "features", "test_screens.py"),
        os.path.join(ROOT_DIR, "tests", "features", "test_substitute.py"),
        os.path.join(ROOT_DIR, "tests", "features", "test_weather_debug.py"),
        os.path.join(ROOT_DIR, "tests", "features", "test_end_of_turn.py"),
        
        # Comprehensive verification tests
        os.path.join(ROOT_DIR, "tests", "verification", "test_status_conditions.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_entry_hazards.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_switching_moves.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_multi_turn_sequences.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_weather_comprehensive.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_terrain_comprehensive.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_critical_hits.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_accuracy_evasion.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_type_effectiveness.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_multi_hit_moves.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_recoil_drain.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_field_effects.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_stat_stages.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_faint_sequences.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_speed_priority.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_generic_moves.py"),
        os.path.join(ROOT_DIR, "tests", "verification", "test_remaining_moves.py"),  # NEW
    ]
    
    verified_moves = set()
    
    # Patterns to match different test name formats
    patterns = [
        re.compile(r"def\s+test_([a-z0-9_]+)\("),  # test_move_name()
        re.compile(r"'Move:\s*([A-Za-z\s\-]+)'"),  # 'Move: Move Name'
        re.compile(r'"Move:\s*([A-Za-z\s\-]+)"'),  # "Move: Move Name"
    ]
    
    for file_path in scan_files:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Pattern 1: test function names (test_solar_beam -> Solar Beam)
            for match in patterns[0].findall(content):
                title_name = match.replace('_', ' ').title()
                verified_moves.add(title_name)
            
            # Pattern 2 & 3: Direct move names from 'Move: X' strings
            for pattern in patterns[1:]:
                for match in pattern.findall(content):
                    verified_moves.add(match.strip())
    
    print(f"Found {len(verified_moves)} verified moves via static analysis.")
    
    # Export
    out_path = os.path.join(ROOT_DIR, "data", "verified_moves.json")
    
    # Read existing verified_moves.json and MERGE (preserve existing + add new)
    existing = set()
    if os.path.exists(out_path):
        try:
            with open(out_path, 'r') as f:
                existing = set(json.load(f))
                print(f"Loaded {len(existing)} existing verified moves from {out_path}")
        except:
            pass
    
    # Merge: keep all existing + add newly found
    all_verified = existing | verified_moves
    
    with open(out_path, 'w') as f:
        json.dump(sorted(list(all_verified)), f, indent=2)
        
    print(f"Written {len(all_verified)} total verified moves to {out_path}")
    print(f"  ({len(existing)} existing + {len(verified_moves - existing)} new)")

if __name__ == "__main__":
    run()
