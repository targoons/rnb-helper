
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkh_app.battle_engine import BattleEngine
from pkh_app.mechanics import Mechanics

# Mappings extracted from BattleEngine
TYPE_BOOST_ITEMS = {
   'Silk Scarf': 'Normal', 'Black Belt': 'Fighting', 'Fist Plate': 'Fighting',
   'Sharp Beak': 'Flying', 'Sky Plate': 'Flying', 'Poison Barb': 'Poison',
   'Toxic Plate': 'Poison', 'Soft Sand': 'Ground', 'Earth Plate': 'Ground',
   'Hard Stone': 'Rock', 'Stone Plate': 'Rock', 'Silver Powder': 'Bug',
   'Insect Plate': 'Bug', 'Spell Tag': 'Ghost', 'Spooky Plate': 'Ghost',
   'Metal Coat': 'Steel', 'Iron Plate': 'Steel', 'Charcoal': 'Fire',
   'Flame Plate': 'Fire', 'Mystic Water': 'Water', 'Splash Plate': 'Water',
   'Miracle Seed': 'Grass', 'Meadow Plate': 'Grass', 'Magnet': 'Electric',
   'Zap Plate': 'Electric', 'Twisted Spoon': 'Psychic', 'Mind Plate': 'Psychic',
   'Never-Melt Ice': 'Ice', 'Icicle Plate': 'Ice', 'Dragon Fang': 'Dragon',
   'Draco Plate': 'Dragon', 'Black Glasses': 'Dark', 'Dread Plate': 'Dark',
   'Pixie Plate': 'Fairy', 'Sea Incense': 'Water', 'Rose Incense': 'Grass',
   'Rock Incense': 'Rock', 'Odd Incense': 'Psychic', 'Wave Incense': 'Water',
   'Full Incense': 'Normal'
}

TYPE_RESIST_BERRIES = {
   'Occa Berry': 'Fire', 'Passho Berry': 'Water', 'Wacan Berry': 'Electric',
   'Rindo Berry': 'Grass', 'Yache Berry': 'Ice', 'Chople Berry': 'Fighting',
   'Kebia Berry': 'Poison', 'Shuca Berry': 'Ground', 'Coba Berry': 'Flying',
   'Payapa Berry': 'Psychic', 'Tanga Berry': 'Bug', 'Charti Berry': 'Rock',
   'Kasib Berry': 'Ghost', 'Haban Berry': 'Dragon', 'Colbur Berry': 'Dark',
   'Babiri Berry': 'Steel', 'Roseli Berry': 'Fairy', 'Chilan Berry': 'Normal'
}

# Gems (Generic)
TYPES = ['Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice', 'Fighting', 'Poison', 'Ground', 'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost', 'Dragon', 'Steel', 'Dark', 'Fairy']
GEMS = {f"{t} Gem": t for t in TYPES}

def get_rich_item_data(item_name):
    # Normalize name for checks
    norm_name = item_name.replace(" ", "").lower()
    
    # 1. Type Boosters (Plates, Charcoal, etc)
    if item_name in TYPE_BOOST_ITEMS:
        return {'name': item_name, 'onBasePower': 1.2, 'triggerType': TYPE_BOOST_ITEMS[item_name]}
        
    # 2. Resists Berries
    if item_name in TYPE_RESIST_BERRIES:
        res_type = TYPE_RESIST_BERRIES[item_name]
        return {'name': item_name, 'onSourceModifyDamage': 0.5, 'triggerType': res_type}
        
    # 3. Gems
    if "Gem" in item_name:
         # Generic Gem logic in Mechanics checks 'Gem' in name
         return {'name': item_name, 'onBasePower': 1.3}
         
    # 4. Manual Cases
    if item_name == "Life Orb":
         return {'name': 'Life Orb', 'onModifyDamage': 1.3} # Mechanics might not handle LO dmg boost generically?
         # Wait, LO is usually onModifyDamage 1.3. 
         # Mechanics.get_modifier handles 'onModifyDamage'.
    
    if item_name == "Choice Band": return {'name': 'Choice Band', 'onModifyAtk': 1.5}
    if item_name == "Choice Specs": return {'name': 'Choice Specs', 'onModifySpA': 1.5}
    if item_name == "Expert Belt": return {'name': 'Expert Belt', 'onBasePower': 1.2} # Condition handled in Mechanics
    
    return {}

def generate_boost_cases():
    cases = []
    # Plates / Standard
    for item, i_type in TYPE_BOOST_ITEMS.items():
        cases.append({
            "item": item,
            "category": "Type Booster",
            "attacker": {"species": "Mew", "types": [i_type], "item": item, "stats": {'atk': 100}, "moves": ["Test Move"]},
            "defender": {"species": "Mew", "types": ["Normal"] if i_type != 'Ghost' else ['Psychic'], "stat_stages": {'def': 0}, "stats": {'def': 100}},
            "move": {"name": "Test Move", "type": i_type, "category": "Physical", "basePower": 80},
            "expected_ratio": 1.2, # ~1.2x boost
            "description": f"{item} boosts {i_type}"
        })
    # Gems
    for item, i_type in GEMS.items():
        cases.append({
            "item": item,
            "category": "Gem",
            "attacker": {"species": "Mew", "types": [i_type], "item": item, "stats": {'atk': 100}, "moves": ["Test Move gem"]},
            "defender": {"species": "Mew", "types": ["Normal"] if i_type != 'Ghost' else ['Psychic'], "stat_stages": {'def': 0}, "stats": {'def': 100}},
            "move": {"name": "Test Move gem", "type": i_type, "category": "Physical", "basePower": 80},
            "expected_ratio": 1.3,
            "consume": True,
            "description": f"{item} boosts {i_type} (First Hit)"
        })
    return cases

def generate_resist_cases():
    cases = []
    for item, i_type in TYPE_RESIST_BERRIES.items():
        # Attacker uses Super Effective move of that type
        # Defender has berry and is weak to it (Normal is weak to Fighting)
        # But wait, berries trigger on SE.
        # We need a defender weak to the move type.
        # Def types: Use inverse map or just Mon mapping.
        # Simpler: Force effective > 1 by hacking context or choosing correct types.
        # Let's pick a defender type weak to i_type.
        
        weak_map = {
            'Fire': 'Grass', 'Water': 'Fire', 'Electric': 'Water', 'Grass': 'Water',
            'Ice': 'Grass', 'Fighting': 'Normal', 'Poison': 'Grass', 'Ground': 'Electric',
            'Flying': 'Fighting', 'Psychic': 'Fighting', 'Bug': 'Grass', 'Rock': 'Fire',
            'Ghost': 'Ghost', 'Dragon': 'Dragon', 'Dark': 'Ghost', 'Steel': 'Rock',
            'Fairy': 'Dragon', 'Normal': 'NoWeakness?' # Chilan Berry is Normal resist (rare)
        }
        
        def_type = weak_map.get(i_type, 'Normal')
        if i_type == 'Normal': continue # Chilan acts on Normal moves (not necessarily SE)
        
        cases.append({
            "item": item,
            "category": "Resist Berry",
            "attacker": {"species": "Mew", "types": [i_type], "stats": {'atk': 100}, "moves": ["Test Move SE"]},
            "defender": {"species": "Target", "types": [def_type], "item": item, "stats": {'def': 100}},
            "move": {"name": "Test Move SE", "type": i_type, "category": "Physical", "basePower": 80},
            "expected_ratio": 0.5,
            "consume": True,
            "description": f"{item} resists {i_type}"
        })
    return cases

MANUAL_CASES = [
    {
        "item": "Life Orb",
        "category": "Damage Booster",
        "attacker": {"species": "Mew", "item": "Life Orb", "stats": {'atk': 100}, "current_hp": 100, "max_hp": 100},
        "defender": {"species": "Mew", "stats": {'def': 100}},
        "move": {"name": "Tackle", "type": "Normal", "category": "Physical", "basePower": 80},
        "expected_ratio": 1.3,
        "check_logs": ["lost HP due to Life Orb"],
        "description": "Life Orb: 1.3x Dmg + Recoil"
    },
    {
        "item": "Choice Band",
        "category": "Stat Booster",
        "attacker": {"species": "Mew", "item": "Choice Band", "stats": {'atk': 100}},
        "defender": {"species": "Mew", "stats": {'def': 100}},
        "move": {"name": "Tackle", "type": "Normal", "category": "Physical", "basePower": 80},
        "expected_ratio": 1.5,
        "description": "Choice Band: 1.5x Atk"
    },
    {
        "item": "Choice Specs",
        "category": "Stat Booster",
        "attacker": {"species": "Mew", "item": "Choice Specs", "stats": {'spa': 100}},
        "defender": {"species": "Mew", "stats": {'spd': 100}},
        "move": {"name": "Ember", "type": "Fire", "category": "Special", "basePower": 80},
        "expected_ratio": 1.5,
        "description": "Choice Specs: 1.5x SpA"
    },
    {
        "item": "Expert Belt",
        "category": "Damage Booster",
        "attacker": {"species": "Mew", "item": "Expert Belt", "stats": {'atk': 100}},
        "defender": {"species": "Mew", "types": ["Grass"], "stats": {'def': 100}},
        "move": {"name": "Test Fire", "type": "Fire", "category": "Physical", "basePower": 80},
        "expected_ratio": 1.2,
        "description": "Expert Belt: 1.2x on SE"
    },
    {
        "item": "Rocky Helmet", # Defensive
        "category": "Reactive",
        "attacker": {"species": "Attacker", "stats": {'atk': 100}, "current_hp": 100, "max_hp": 100},
        "defender": {"species": "Defender", "item": "Rocky Helmet", "stats": {'def': 100}},
        "move": {"name": "Punch", "type": "Fighting", "category": "Physical", "flags": {'contact': 1}, "basePower": 40},
        "check_logs": ["hurt by Rocky Helmet"],
        "description": "Rocky Helmet: Recoil on contact"
    },
    {
        "item": "Leftovers", # Passive
        "category": "Passive",
        "attacker": {"species": "Healer", "item": "Leftovers", "current_hp": 50, "max_hp": 100},
        "defender": {"species": "Dummy", "stats": {'def': 100}},
        "move": {"name": "Splash", "type": "Normal", "category": "Status"},
        "check_logs": ["healed by Leftovers"],
        "description": "Leftovers: Heal at end of turn"
    }
]

def run_suite():
    print("Generating Test Cases...")
    all_cases = generate_boost_cases() + generate_resist_cases() + MANUAL_CASES
    cases = all_cases  # Run all test cases instead of filtering
    print(f"DEBUG: Running Spell Tag test. Defender Types: {all_cases[0]['defender_types'] if 'defender_types' in all_cases[0] else 'Unknown'}")
    # We can't easily access the engine state here directly as it's created inside run_boost_case
    # But we can verify the move type injection logic in run_boost_case by adding a print there.
    print(f"Total Cases: {len(cases)}")
    
    passed = 0
    failed = 0
    
    verified_items = []
    
    # Patch Random for Determinism
    import random
    original_uniform = random.uniform
    original_random = random.random
    original_choice = random.choice
    
    random.uniform = lambda a, b: b # Always max roll
    random.random = lambda: 0.999 # Close to 1.0 but within bounds usually
    # Patch choice to pick last element (Max Damage in sorted rolls)
    random.choice = lambda seq: seq[-1] if seq else None
    
    try:
        for idx, case in enumerate(cases):
            item_name = case.get('item', 'Unknown')
            print(f"[{idx+1}/{len(cases)}] Testing {item_name}...", end=" ")
            
            # Setup Battle
            state = type('State', (), {'fields': {}, 'player_party': [], 'ai_party': [], 'get_hash': lambda: 0})()
            engine = BattleEngine()
            
            attacker = case.get('attacker').copy()
            defender = case.get('defender').copy()
            
            # Defaults
            for mon in [attacker, defender]:
                if 'types' not in mon: mon['types'] = ['Normal']
                if 'stats' not in mon: mon['stats'] = {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100}
                if 'current_hp' not in mon: mon['current_hp'] = mon.get('max_hp', 100)
                if 'max_hp' not in mon: mon['max_hp'] = 100
                if 'volatiles' not in mon: mon['volatiles'] = []
                # Ensure stat stages
                if 'stat_stages' not in mon: mon['stat_stages'] = {'atk':0, 'def':0, 'spa':0, 'spd':0, 'spe':0, 'acc':0, 'eva':0}
                
            attacker['side'] = 'player'
            defender['side'] = 'ai'
            state.player_active = attacker
            state.ai_active = defender
            # Ensure refs are consistent logic-wise
            attacker['ability'] = attacker.get('ability') or 'No Ability' 
            
            state.player_party = [attacker]
            state.ai_party = [defender]
            state.last_moves = {}
            state.fields['active_mons'] = [attacker, defender]
            
            # Enrich
            engine.enrich_state(state)
            
            # Prepare Move
            move = case.get('move')
            if not hasattr(engine, 'rich_data'):
                 engine.rich_data = {'moves': {}, 'abilities': {}, 'items': {}}
            if not hasattr(engine, 'move_names'):
                 engine.move_names = {}

            def _norm(s): return str(s).lower().replace(' ', '').replace('-', '').replace("'", "")
            
            # Inject Current Case Move
            engine.move_names[move['name']] = move['name']
            engine.rich_data['moves'][_norm(move['name'])] = move
            
            # Inject Common Manual Moves if needed (Tackle, Ember)
            # Inject Item Data (mocking mechanics_rich.json)
            if item_name != 'Unknown':
                 i_data = get_rich_item_data(item_name)
                 if i_data:
                      engine.rich_data['items'][_norm(item_name)] = i_data
            
            # Also inject Defender Item if different
            def_item = defender.get('item')
            if def_item and def_item != item_name:
                 i_data = get_rich_item_data(def_item)
                 if i_data:
                      engine.rich_data['items'][_norm(def_item)] = i_data

            # RE-ENRICH State to apply new rich data
            engine.enrich_state(state) # Enrich does lookup in rich_data['items']

            # CONTROL RUN (If ratio expected)
            print(f"DEBUG: Attacker Types: {attacker['types']}")
            print(f"DEBUG: Defender Types: {defender['types']}")
            print(f"DEBUG: Move Type: {move['type']}")
            m_key = move['name'].lower().replace(' ', '').replace('-', '').replace("'", "")
            print(f"DEBUG: Engine Move Info: {engine.rich_data['moves'].get(m_key)}")


            # CONTROL RUN (If ratio expected)
            control_damage = 0
            if 'expected_ratio' in case:
                # Remove item for control
                orig_item = attacker.get('item')
                orig_def_item = defender.get('item')
                # Also clear rich items if engine.enrich_state populated them
                orig_rich = attacker.get('_rich_item')
                attacker['item'] = None
                attacker['_rich_item'] = {} 
                defender['item'] = None
                defender['_rich_item'] = {}
                
                log_c = []
                engine.execute_turn_action(state, 'player', f"Move: {move['name']}", 'ai', log_c)
                # Extract Damage
                for l in log_c:
                    if "(-" in l and "dmg)" in l:
                         try:
                            control_damage = int(l.split("(-")[1].split(" dmg)")[0])
                         except: pass
                
                # Reset Items
                attacker['item'] = orig_item
                attacker['_rich_item'] = orig_rich if orig_rich is not None else {}
                defender['item'] = orig_def_item
                # Restore defender rich item
                if orig_def_item:
                     def_data = get_rich_item_data(orig_def_item)
                     defender['_rich_item'] = def_data if def_data else {}
                else:
                     defender['_rich_item'] = {}
                
                # Check Double Counting
                if idx == 17: # Testing Charcoal (Index might shift, check by name)
                     pass
                if item_name == 'Charcoal':
                     print(f"    DEBUG: Charcoal Rich Item: {attacker.get('_rich_item')}")
                
                # Reset HP
                attacker['current_hp'] = attacker['max_hp']
                defender['current_hp'] = defender['max_hp']

            # TEST RUN
            log = []
            engine.execute_turn_action(state, 'player', f"Move: {move['name']}", 'ai', log)
            
            # End of Turn (for Leftovers etc)
            if case.get('category') == 'Passive':
                # Use Mechanics directly or generic battle engine loop function?
                # BattleEngine logic for end of turn is scattered or in `run_turn_loop`.
                # Let's use `Mechanics.apply_end_turn_effects` manually.
                Mechanics.apply_end_turn_effects(state, log)
                
            # Analysis
            msg = "PASS"
            is_pass = True
            
            # 1. Ratio Check
            if 'expected_ratio' in case:
                test_damage = 0
                for l in log:
                    if "(-" in l and "dmg)" in l:
                         try:
                            test_damage = int(l.split("(-")[1].split(" dmg)")[0])
                         except: pass
                
                if control_damage == 0:
                     # Avoid div/0 if control did 0 damage (Splash etc)
                     ratio = 1.0
                else:
                     ratio = test_damage / control_damage
                     
                # Tolerance
                exp = case['expected_ratio']
                if not (exp - 0.15 <= ratio <= exp + 0.15):
                    msg = f"FAIL (Ratio {ratio:.2f} != {exp})"
                    is_pass = False
            
            # 2. Log Check
            if 'check_logs' in case:
                found_all = True
                for fragment in case['check_logs']:
                    if not any(fragment in l for l in log):
                        found_all = False
                        msg = f"FAIL (Missing log: '{fragment}')"
                        is_pass = False
                        break
            
            # 3. Consumption Check
            if case.get('consume'):
                # Check if item is gone
                relevant_mon = defender if case['category'] == 'Resist Berry' else attacker
                if relevant_mon.get('item') is not None:
                     msg = "FAIL (Item not consumed)"
                     is_pass = False
                     
            print(msg)
            if not is_pass:
                failed += 1
                print("  Logs:", log)
                print(f"  Control Damage: {control_damage}, Test Damage: {test_damage}")
            else:
                passed += 1
                verified_items.append(item_name)
    finally:
        random.uniform = original_uniform
        random.random = original_random
        random.choice = original_choice

            
    print(f"\nFinal Results: {passed} Passed, {failed} Failed")
    
    # Update audit CSV and JSON with verified items
    try:
        from .audit_utils import update_audit_with_verified
        update_audit_with_verified(verified_items)
    except ImportError:
        # Fallback inline if utils missing (or during refactor)
        print("Warning: audit_utils not found, creating local JSON only")
        with open('data/verified_items.json', 'w') as f:
             json.dump(verified_items, f, indent=2)

if __name__ == "__main__":
    run_suite()
