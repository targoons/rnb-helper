"""
Phase 2 Item Tests: Important Items
- HP Berries (Sitrus, Oran, Berry Juice)
- Status Berries (Lum, Persim, etc)
- Terrain Seeds (Electric, Grassy, Misty, Psychic)
"""
import sys
import os
import json
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkh_app.battle_engine import BattleEngine
from pkh_app.mechanics import Mechanics

# --- Helpers ---

def make_mon(species, types=None, stats=None, item='No Item', ability='No Ability', moves=None, hp=None, max_hp=None, spe=None, spa=None, spd=None, atk=None, def_stat=None, side='player'):
    if stats is None: stats = {}
    if moves is None: moves = ['Splash']
    if types is None: types = ['Normal']
    
    if spe is not None: stats['spe'] = spe
    if spa is not None: stats['spa'] = spa
    if spd is not None: stats['spd'] = spd
    if atk is not None: stats['atk'] = atk
    if def_stat is not None: stats['def'] = def_stat
    
    for s in ['hp', 'atk', 'def', 'spa', 'spd', 'spe']:
        if s not in stats: stats[s] = 100
        
    return {
        'species': species,
        'types': types,
        'item': item,
        'ability': ability,
        'moves': moves,
        'stats': stats,
        'stat_stages': {'atk':0, 'def':0, 'spa':0, 'spd':0, 'spe':0, 'acc':0, 'eva':0},
        'current_hp': hp if hp is not None else (max_hp if max_hp is not None else 100),
        'max_hp': max_hp if max_hp is not None else 100,
        'volatiles': [],
        'side': side
    }

def setup_engine():
    state = type('State', (), {'fields': {}, 'player_party': [], 'ai_party': [], 'get_hash': lambda: 0})()
    engine = BattleEngine(state)
    state.fields = {'weather': None, 'terrain': None}
    state.last_moves = {}
    
    if not hasattr(engine, 'rich_data'):
        engine.rich_data = {'moves': {}, 'abilities': {}, 'items': {}}
        
    # Mock items logic
    items_to_add = {
        'Sitrus Berry': {'name': 'Sitrus Berry', 'isBerry': True, 'healRatio': [1, 4], 'threshold': 0.5},
        'Oran Berry': {'name': 'Oran Berry', 'isBerry': True, 'healConstant': 10, 'threshold': 0.5},
        'Berry Juice': {'name': 'Berry Juice', 'isBerry': True, 'healConstant': 20, 'threshold': 0.5},
        'Lum Berry': {'name': 'Lum Berry', 'isBerry': True},
        'Persim Berry': {'name': 'Persim Berry', 'isBerry': True},
        'Cheri Berry': {'name': 'Cheri Berry', 'isBerry': True},
        'Electric Seed': {'name': 'Electric Seed'},
        'Grassy Seed': {'name': 'Grassy Seed'},
        'Misty Seed': {'name': 'Misty Seed'},
        'Psychic Seed': {'name': 'Psychic Seed'}
    }
    for name, data in items_to_add.items():
        engine.rich_data['items'][name] = data
        
    return engine, state

# --- Tests ---

def test_hp_berries():
    print("\n=== Testing HP Berries ===")
    verified = []
    
    # 1. Sitrus Berry
    print("Testing Sitrus Berry...")
    try:
        engine, state = setup_engine()
        # HP < 50%
        mon = make_mon('Snorlax', hp=40, max_hp=100, item='Sitrus Berry', side='player')
        
        # Populate rich item on mon manually or verify logic retrieves it
        mon['_rich_item'] = engine.rich_data['items']['Sitrus Berry']
        
        log = []
        # Simulate damage reaction
        # Method: execute_post_damage_reactions(self, state, attacker, defender, damage_applied, move_data, log)
        engine.execute_post_damage_reactions(
            state=state, 
            attacker=make_mon('Dummy', side='ai'),
            defender=mon,
            damage_applied=10, 
            move_data={'name': 'Tackle', 'category': 'Physical'}, 
            log=log
        )
        
        if mon['current_hp'] == 65: # 40 + 25
            print("PASS: Sitrus Berry healed 25% HP")
            verified.append('Sitrus Berry')
        else:
            print(f"FAIL: HP {mon['current_hp']} (exp 65)")
    except Exception as e:
        print(f"ERROR Sitrus: {e}")
        
    return verified

def test_status_berries():
    print("\n=== Testing Status Berries ===")
    verified = []
    
    # 1. Lum Berry
    print("Testing Lum Berry...")
    try:
        engine, state = setup_engine()
        mon = make_mon('Machamp', item='Lum Berry', side='player')
        mon['status'] = 'brn'
        
        log = []
        # Method: _check_status_triggers(self, state, mon, log)
        engine._check_status_triggers(state, mon, log)
        
        if mon['status'] is None:
            print("PASS: Lum Berry cured status")
            verified.append('Lum Berry')
        else:
            print(f"FAIL: Status is {mon['status']}")
    except Exception as e:
        print(f"ERROR Lum: {e}")

    # 2. Persim Berry (Confusion)
    print("Testing Persim Berry...")
    try:
        engine, state = setup_engine()
        mon = make_mon('Machamp', item='Persim Berry', side='player')
        mon['volatiles'].append('confusion')
        
        log = []
        engine._check_status_triggers(state, mon, log)
        
        if 'confusion' not in mon['volatiles']:
            print("PASS: Persim Berry cured confusion")
            verified.append('Persim Berry')
        else:
             print("FAIL: Still confused")
    except Exception as e:
        print(f"ERROR Persim: {e}")

    # 3. Cheri Berry (Paralysis)
    print("Testing Cheri Berry...")
    try:
        engine, state = setup_engine()
        mon = make_mon('Machamp', item='Cheri Berry', side='player')
        mon['status'] = 'par'
        
        log = []
        engine._check_status_triggers(state, mon, log)
        
        if mon['status'] is None:
            print("PASS: Cheri Berry cured paralysis")
            verified.append('Cheri Berry')
        else:
             print(f"FAIL: Status is {mon['status']}")
    except Exception as e:
        print(f"ERROR Cheri: {e}")
        
    return verified

def test_terrain_seeds():
    print("\n=== Testing Terrain Seeds ===")
    verified = []
    
    seeds = [
        ('Electric Seed', 'Electric', 'def'),
        ('Grassy Seed', 'Grassy', 'def'),
        ('Misty Seed', 'Misty', 'spd'),
        ('Psychic Seed', 'Psychic', 'spd')
    ]
    
    for item_name, terrain, stat in seeds:
        print(f"Testing {item_name}...")
        try:
            engine, state = setup_engine()
            mon = make_mon('Tapu Koko', item=item_name, side='player')
            
            # Set terrain
            state.fields['terrain'] = terrain
            
            log = []
            # Method: apply_switch_in_items(self, state, side, mon, log)
            engine.apply_switch_in_items(state, 'player', mon, log)
            
            boost = mon['stat_stages'][stat]
            consumed = mon['item'] is None
            
            if boost == 1 and consumed:
                print(f"PASS: {item_name} boosted {stat} +1 in {terrain} Terrain")
                verified.append(item_name)
            else:
                print(f"FAIL: Boost {boost}, Consumed {consumed}")
                
        except Exception as e:
            print(f"ERROR {item_name}: {e}")
            
    return verified

def run_phase2_tests():
    all_verified = []
    all_verified.extend(test_hp_berries())
    all_verified.extend(test_status_berries())
    all_verified.extend(test_terrain_seeds())
    
    if all_verified:
        try:
            from test_bulk_items import update_audit_csv
            update_audit_csv(all_verified)
        except ImportError:
            print("Could not import update_audit_csv logic")

if __name__ == "__main__":
    run_phase2_tests()
