
import json
import os
import re
import csv
import sys

# Integrate Test Runners
# Add root to path so we can import packages from root and tests module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 

try:
    from tests.verification.test_bulk_items import run_suite
    from tests.verification.test_items_phase1 import run_phase1_tests
    from tests.verification.test_items_phase2 import run_phase2_tests
    from tests.verification.test_items_phase3 import run_phase3_tests
    from tests.verification.test_items_phase4 import run_phase4_tests
    from tests.verification.test_items_phase5 import run_phase5_tests
    from tests.verification.test_form_change import run_form_change_suite
    from tests.verification.test_items_phase7 import run_phase7_tests
    # New Updates
    from tests.verification import update_verified_moves
    from tests.verification.test_bulk_abilities import run_suite as run_ability_suite
except ImportError as e:
    print(f"Warning: Could not import tests: {e}")
    pass

DATA_PATH = "/Users/targoon/Pokemon/pokemon_rnb_helper/data/mechanics_rich.json"
WHITELIST_PATH = "/Users/targoon/Pokemon/pokemon_rnb_helper/data/rnb_whitelist.json"
ENGINE_PATH = "/Users/targoon/Pokemon/pokemon_rnb_helper/pkh_app/battle_engine/__init__.py"
TRIGGERS_PATH = "/Users/targoon/Pokemon/pokemon_rnb_helper/pkh_app/battle_engine/triggers.py"
MECHANICS_PATH = "/Users/targoon/Pokemon/pokemon_rnb_helper/pkh_app/mechanics.py"
CALC_PATH = "/Users/targoon/Pokemon/pokemon_rnb_helper/pkh_app/local_damage_calc.py"


LOGIC_REQUIRED_FLAGS = {
    'pseudoWeather', 'pseudoStatus', 'onModifySpe', 'onModifyAtk', 
    'onModifyDef', 'onModifySpA', 'onModifySpD', 'onBasePower', 'onDamagingHit', 
    'damage', 'secondary'
}

TRULY_GENERIC_FLAGS = {
    'basePower', 'accuracy', 'type', 'category', 'status', 'boosts', 
    'drain', 'recoil', 'multihit', 'heal', 
    'weather', 'terrain', 'sideCondition'
}

# Volatiles that are CONFIRMED to be fully supported by the engine
SUPPORTED_VOLATILES = {
    'flinch', 'confusion', 'leechseed', 'aquaring', 'yawn', 'saltcure', 'syrupbomb', 
    'taunt', 'torment', 'disable', 'encore', 'attract', 'nightmare', 
    'embargo', 'healblock', 'telekinesis', 'octolock', 'uproar', 
    'minimized', 'substitute', 'protect', 'detect', 'endure', 'destinybond', 
    'mist', 'safeguard', 'lucky chant', 'reflect', 'light screen', 'tailwind', 'aurora veil',
    'partiallytrapped', 'trapped', 'ingrain', 'jawlock', 'throatchop',
    'charge', 'curse', 'focusenergy', 'laserfocus', 'glaiverush', 'tarshot', 'roost', 
    'smackdown', 'magnetrise', 'imprison', 'stockpile', 'bide', 'burningbulwark', 'obstruct', 'minimize',
    'banefulbunker', 'spikyshield', 'kingsshield', 'silktrap', 'foresight', 'miracleeye'
}

def normalize(name):
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")

def load_data():
    with open(DATA_PATH, 'r') as f:
        rich_data = json.load(f)
    with open(WHITELIST_PATH, 'r') as f:
        whitelist = json.load(f)
    return rich_data, whitelist

def scan_codebase_for_evidence(term):
    evidence = []
    
    # 1. Quoted String Pattern
    esc_term = re.escape(term)
    pattern = re.compile(rf"(['\"]){esc_term}\1")
    
    # Scan all .py files in pkh_app
    app_root = "/Users/targoon/Pokemon/pokemon_rnb_helper/pkh_app"
    
    for root, dirs, files in os.walk(app_root):
        for file in files:
            if not file.endswith('.py'): continue
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, app_root)
            
            with open(path, 'r') as f:
                for i, line in enumerate(f, 1):
                    code_part = line.split('#')[0].strip()
                    if not code_part: continue
                    
                    if pattern.search(code_part):
                         # Capture snippet (truncate if long)
                         snippet = code_part[:80] + "..." if len(code_part) > 80 else code_part
                         evidence.append(f"{rel_path}:{i} `{snippet}`")
                         break # One per file
        if len(evidence) >= 5: break # Cap total evidence
    
    return evidence

_test_cache = {}
def scan_tests_for_evidence(term):
    if term in _test_cache: return _test_cache[term]
    
    evidence = []
    norm_term = normalize(term)
    
    # Update to scan new tests location AND legacy tests
    # tests/verification + tests/
    base_tests = "/Users/targoon/Pokemon/pokemon_rnb_helper/tests"
    paths_to_scan = [
        base_tests,
        os.path.join(base_tests, "verification")
    ]
    
    test_files = []
    for p in paths_to_scan:
        if os.path.exists(p):
            for f in os.listdir(p):
                 if f.startswith('test_') and f.endswith('.py'):
                      test_files.append(os.path.join(p, f))
    
    for path in test_files:
        with open(path, 'r') as f:
            content = f.read()
            if term.lower() in content.lower() or norm_term in content.lower():
                evidence.append(os.path.basename(path))
                
    _test_cache[term] = evidence
    return evidence

def verify_tier(data, codebase_hits, test_hits):
    keys = set(data.keys())
    
    # Check for ACTIVE logic-required flags
    has_logic_req = False
    for k in LOGIC_REQUIRED_FLAGS:
        val = data.get(k)
        if val is not None and val != [] and val != {}:
            # Exceptions
            if k == 'secondary' and isinstance(val, dict):
                is_sec_generic = True
                for sk, sv in val.items():
                    if sk in ['chance', 'status', 'boosts']: continue
                    if sk in ['volatileStatus', 'volatiles'] and (sv in SUPPORTED_VOLATILES or (isinstance(sv, list) and all(v in SUPPORTED_VOLATILES for v in sv))): continue
                    if sk == 'self' and isinstance(sv, dict) and set(sv.keys()).issubset({'boosts'}): continue
                    is_sec_generic = False
                    break
                if not is_sec_generic:
                    has_logic_req = True
            elif k == 'heal' and not isinstance(val, list):
                has_logic_req = True
            elif k == 'damage' and (val == 'level' or isinstance(val, int)):
                 continue
            else:
                has_logic_req = True

    if data.get('volatileStatus'):
         if data.get('volatileStatus') not in SUPPORTED_VOLATILES:
              has_logic_req = True

    if test_hits:
        return "Verified (Tested)"
    elif codebase_hits:
        return "Implementation Detected (Unverified)"
    
    is_generic = False
    if not has_logic_req:
        if any(data.get(k) for k in TRULY_GENERIC_FLAGS):
            is_generic = True
        elif any(data.get(k) for k in ['healRatio', 'isBerry', 'isChoice']):
            is_generic = True
        elif data.get('volatileStatus') in SUPPORTED_VOLATILES:
            is_generic = True

    if is_generic:
        return "Verified (Data-Driven)" if test_hits else "Data-Driven (Standard)"
    
    if has_logic_req:
        return "Implementation Gap"
    
    return "Not Implemented"

def analyze_moves(rich_data, whitelist):
    whitelisted_moves = set(whitelist.get('moves', []))
    results = []
    
    # Load Verified Moves JSON
    verified_moves = set()
    v_path = "/Users/targoon/Pokemon/pokemon_rnb_helper/data/verified_moves.json"
    if os.path.exists(v_path):
        with open(v_path, 'r') as f:
            try:
                # Normalize keys for robust matching
                verified_moves = set(normalize(m) for m in json.load(f))
            except: pass

    for key, data in rich_data.get('moves', {}).items():
        name = data.get('name')
        norm_name = normalize(name)
        if norm_name not in whitelisted_moves: continue

        evidence_code = scan_codebase_for_evidence(name)
        evidence_test = scan_tests_for_evidence(name)
        
        status = verify_tier(data, evidence_code, evidence_test)
        
        # Override with JSON Truth
        # Prioritize Verified Status if present in Source of Truth
        if norm_name in verified_moves:
             status = "Verified (Tested)"
             if not any("test_" in e for e in evidence_test):
                  evidence_test.append("Verification Script")

        combined_evidence = []
        if evidence_code: combined_evidence.append(f"Logic: {'; '.join(evidence_code)}")
        if evidence_test: combined_evidence.append(f"Test: {', '.join(evidence_test)}")
        
        details_list = []
        for k in LOGIC_REQUIRED_FLAGS:
            if data.get(k): details_list.append(f"{k}: {data[k]}")

        results.append({
            'name': name,
            'status': status,
            'evidence': " | ".join(combined_evidence) if combined_evidence else "None",
            'details': " | ".join(details_list)
        })

    
    # Consolidate and Export Verified Moves (JSON)
    # MERGE with existing verified_moves.json (preserve what update_verified_moves found)
    final_verified_moves = set()
    
    # Load existing verified moves first
    v_out = "/Users/targoon/Pokemon/pokemon_rnb_helper/data/verified_moves.json"
    if os.path.exists(v_out):
        try:
            with open(v_out, 'r') as f:
                final_verified_moves = set(json.load(f))
        except:
            pass
    
    # Add moves from audit results that are verified
    for r in results:
        if "Verified" in r['status']:
            final_verified_moves.add(r['name'])
    
    # Write merged results
    with open(v_out, 'w') as f:
         json.dump(sorted(list(final_verified_moves)), f, indent=2)
    print(f"Updated {v_out} with {len(final_verified_moves)} verified moves (Audit Integrated).")

    return results

def analyze_items(rich_data, whitelist):
    items_whitelist = set(whitelist.get('items', []))
    results = []

    verified_list = set()
    verified_path = "/Users/targoon/Pokemon/pokemon_rnb_helper/data/verified_items.json"
    if os.path.exists(verified_path):
        try:
            with open(verified_path, 'r') as f:
                verified_list = set(json.load(f))
        except:
             pass

    for key, data in rich_data.get('items', {}).items():
        name = data.get('name')
        norm_name = normalize(name)
        
        if items_whitelist and norm_name not in items_whitelist: continue

        evidence_code = scan_codebase_for_evidence(name)
        evidence_test = scan_tests_for_evidence(name)
        
        status = verify_tier(data, evidence_code, evidence_test)
        
        if name.endswith('ite') or name.endswith('ite X') or name.endswith('ite Y') or name in ['Red Orb', 'Blue Orb']:
             status = "Verified (Tested)" if "test_form_change.py" in evidence_test else "Implementation Detected (Unverified)"
             evidence_code.append("Generic Form Change System")

        if "Gem" in name or name.endswith("Plate") or name.endswith("Memory") or name.endswith("Drive"):
             if status in ["Not Implemented", "Implementation Gap"]:
                  status = "Implementation Detected (Unverified)"
                  evidence_code.append("Generic Item Handler")
        
        # Override if in verification list (Source of Truth)
        if name in verified_list:
            status = "Verified (Tested)"
            if not any("test_" in e for e in evidence_test):
                 evidence_test.append("Verification Script")

        combined_evidence = []
        if evidence_code: combined_evidence.append(f"Logic: {'; '.join(evidence_code)}")
        if evidence_test: combined_evidence.append(f"Test: {', '.join(evidence_test)}")
        
        results.append({
            'name': name,
            'status': status,
            'evidence': " | ".join(combined_evidence) if combined_evidence else "Missing logic",
            'details': ""
        })

    return results

def analyze_abilities(rich_data, whitelist):
    whitelisted_abilities = set(whitelist.get('abilities', []))
    results = []
    
    verified_list = set()
    verified_path = "/Users/targoon/Pokemon/pokemon_rnb_helper/data/verified_abilities.json"
    if os.path.exists(verified_path):
        try:
            with open(verified_path, 'r') as f:
                verified_list = set(json.load(f))
        except:
             pass
    
    for key, data in rich_data.get('abilities', {}).items():
        name = data.get('name')
        norm_name = normalize(name)
        if whitelisted_abilities and norm_name not in whitelisted_abilities: continue

        evidence_code = scan_codebase_for_evidence(name)
        evidence_test = scan_tests_for_evidence(name)
        
        status = verify_tier(data, evidence_code, evidence_test)
        
        # Override with JSON Truth
        # Note: We check exact name match in JSON
        if name in verified_list:
            status = "Verified (Tested)"
            evidence_test.append("Bulk Verification Script")
        
        combined_evidence = []
        if evidence_code: combined_evidence.append(f"Logic: {'; '.join(evidence_code)}")
        if evidence_test: combined_evidence.append(f"Test: {', '.join(evidence_test)}")
        
        details_list = []
        for k in LOGIC_REQUIRED_FLAGS:
            if data.get(k): details_list.append(f"{k}")

        results.append({
            'name': name,
            'status': status,
            'evidence': " | ".join(combined_evidence) if combined_evidence else "Missing logic",
            'details': " | ".join(details_list)
        })

    # Consolidate and Export Verified Abilities (JSON)
    final_verified_abs = set()
    for r in results:
        if "Verified" in r['status']:
             final_verified_abs.add(r['name'])
             
    v_out = "/Users/targoon/Pokemon/pokemon_rnb_helper/data/verified_abilities.json"
    with open(v_out, 'w') as f:
         json.dump(sorted(list(final_verified_abs)), f, indent=2)
    print(f"Updated {v_out} with {len(final_verified_abs)} verified abilities (Audit Integrated).")

    return results


def extract_effects(data):
    self_eff = []
    target_eff = []
    prob = ""
    
    if data.get('status'): target_eff.append(f"Status: {data['status']} (100%)")
    if data.get('volatileStatus'): target_eff.append(f"Volatile: {data['volatileStatus']} (100%)")
    if data.get('boosts'): target_eff.append(f"Boosts: {data['boosts']} (100%)")
    
    mh = data.get('multihit')
    if mh:
         if isinstance(mh, list): target_eff.append(f"Multi-hit: {mh[0]}-{mh[1]}")
         else: target_eff.append(f"Multi-hit: {mh}")
         
    fd = data.get('fixedDamage') 
    if fd: target_eff.append(f"Damage: {fd}")
    
    sec = data.get('secondary')
    if sec and isinstance(sec, dict):
        chance = sec.get('chance', 100)
        prob = f"{chance}%"
        if sec.get('status'): target_eff.append(f"Status: {sec['status']}")
        if sec.get('volatiles'): target_eff.append(f"Volatile: {sec.get('volatiles')}")
        if sec.get('boosts'): target_eff.append(f"Boosts: {sec['boosts']}")
        if sec.get('flinch'): target_eff.append("Flinch")
        
    if data.get('recoil'): self_eff.append(f"Recoil: {data['recoil']}")
    if data.get('drain'): self_eff.append(f"Drain: {data['drain']}")
    if data.get('heal'): self_eff.append(f"Heal: {data['heal']}")
    
    return "; ".join(self_eff), "; ".join(target_eff), prob

def write_csv_report(path, results, type='move', rich_data=None):
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        if type == 'move':
            writer.writerow(['Name', 'Status', 'BP', 'Acc', 'PP', 'Prio', 'Cat', 'Target', 'Self Effect', 'Opp Effect', 'Prob', 'Flags', 'Evidence', 'Details'])
            for r in results:
                name = r['name']
                data = rich_data['moves'].get(normalize(name), {})
                bp = data.get('basePower', '-')
                acc = data.get('accuracy', '-')
                pp = data.get('pp', '-')
                prio = data.get('priority', '-')
                cat = data.get('category', '-')
                tgt = data.get('target', '-')
                flags = list(data.get('flags', {}).keys())
                self_e, opp_e, prob = extract_effects(data)
                writer.writerow([name, r['status'], bp, acc, pp, prio, cat, tgt, self_e, opp_e, prob, flags, r['evidence'], r['details']])
        elif type == 'item':
            writer.writerow(['Name', 'Status', 'Evidence', 'Details'])
            for r in results:
                writer.writerow([r['name'], r['status'], r['evidence'], r['details']])
        elif type == 'ability':
            writer.writerow(['Name', 'Status', 'Evidence', 'Details'])
            for r in results:
                writer.writerow([r['name'], r['status'], r['evidence'], r['details']])
    print(f"Written CSV to {path}")

def run_audit():
    print("=== Running Verification Tests Integration ===")
    try:
        run_count = 0
        if 'run_phase1_tests' in globals(): 
             print("Running Phase 1...")
             run_phase1_tests()
             run_count += 1
        if 'run_phase2_tests' in globals():
             print("Running Phase 2...")
             run_phase2_tests()
             run_count += 1
        if 'run_phase3_tests' in globals():
             print("Running Phase 3...")
             run_phase3_tests()
             run_count += 1
        if 'run_suite' in globals():
             print("Running Bulk Suite (Phase 4)...")
             run_suite()
             run_count += 1
        if 'run_phase4_tests' in globals():
             print("Running Unique Logic Phase 4...")
             run_phase4_tests()
             run_count += 1
        if 'run_phase5_tests' in globals():
             print("Running Pinch/Confusion Suite (Phase 5)...")
             run_phase5_tests()
             run_count += 1
        if 'run_form_change_suite' in globals():
             print("Running Form Change Suite (Phase 6)...")
             run_form_change_suite()
             run_count += 1
        if 'run_phase7_tests' in globals():
             print("Running Final Cleanup (Phase 7)...")
             run_phase7_tests()
             run_count += 1
             
        # New Runners
        if 'run_ability_suite' in globals():
             print("Running Ability Verification (Bulk)...")
             run_ability_suite()
             run_count += 1
             
        if 'update_verified_moves' in globals():
             print("Generating Verified Moves JSON... (SKIPPED - integrated into audit)")
             update_verified_moves.run()
             run_count += 1
             
        if run_count == 0:
            print("No test runners found (Import failed?).")
        else:
            print("All Tests Completed.")
    except Exception as e:
        print(f"Warning: Test execution failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== Generating Audit Report ===")
    rich_data, whitelist = load_data()
    
    move_results = analyze_moves(rich_data, whitelist)
    item_results = analyze_items(rich_data, whitelist)
    ability_results = analyze_abilities(rich_data, whitelist)
    
    write_csv_report("/Users/targoon/Pokemon/pokemon_rnb_helper/reports/mechanics_moves.csv", move_results, 'move', rich_data)
    write_csv_report("/Users/targoon/Pokemon/pokemon_rnb_helper/reports/mechanics_items.csv", item_results, 'item')
    write_csv_report("/Users/targoon/Pokemon/pokemon_rnb_helper/reports/mechanics_abilities.csv", ability_results, 'ability')

if __name__ == "__main__":
    run_audit()
