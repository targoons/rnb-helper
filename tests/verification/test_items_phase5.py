
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkh_app.battle_engine import BattleEngine

def create_mock_state():
    state = type('State', (), {
        'fields': {'active_mons': []}, 
        'player_party': [], 
        'ai_party': [], 
        'last_moves': {}, 
        'get_hash': lambda: 0
    })()
    return state

def run_pinch_berry_test(item_name, expected_stat, expected_boost=1, trigger_hp_pct=0.25):
    print(f"Testing {item_name} (Boosts {expected_stat} at <= {trigger_hp_pct*100}% HP)...")
    
    state = create_mock_state()
    engine = BattleEngine(state)
    
    # 24/100 HP is under 25%
    attacker = {
        'species': 'Mew', 
        'item': item_name, 
        'types': ['Psychic'], 
        'max_hp': 100,
        'current_hp': 24, 
        'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
        'stat_stages': {'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0},
        'moves': ['Splash']
    }
    
    attacker['side'] = 'player'
    defender = {'species': 'Target', 'stats': {'def': 100}, 'side': 'ai', 'current_hp': 100, 'max_hp': 100}
    
    state.player_active = attacker
    state.ai_active = defender
    state.player_party = [attacker]
    state.ai_party = [defender]
    state.fields['active_mons'] = [attacker, defender]
    
    log = []
    
    engine.execute_turn_action(state, 'player', "Move: Splash", 'ai', log)
    
    # Check Stat Boost
    actual_boost = attacker['stat_stages'].get(expected_stat, 0)
    is_consumed = attacker.get('item') is None
    
    if actual_boost == expected_boost and is_consumed:
        print(f"PASS: {item_name} boosted {expected_stat} by {actual_boost}")
        return [item_name]
    else:
        print(f"FAIL: {item_name} -> Boost: {actual_boost}, Consumed: {is_consumed}")
        # print("Logs:", log)
        return []

def run_custap_test():
    print("Testing Custap Berry (Priority at <= 25% HP)...")
    state = create_mock_state()
    engine = BattleEngine(state)
    
    attacker = {
        'species': 'Mew', 
        'item': 'Custap Berry', 
        'max_hp': 100,
        'current_hp': 24, # 24%
        'turn_priority_mod': 0
    }
    state.player_active = attacker
    state.ai_active = {}
    
    log = []
    try:
        from pkh_app.mechanics import Mechanics
        Mechanics.apply_start_turn_effects(attacker, state, log)
        
        if attacker.get('turn_priority_mod') == 1 and attacker.get('item') is None:
             print("PASS: Custap Berry activated (Priority +1)")
             return ['Custap Berry']
        else:
             print(f"FAIL: Priority {attacker.get('turn_priority_mod')}, Item: {attacker.get('item')}")
             return []
    except ImportError:
        print("Could not import Mechanics")
        return []

def run_wiki_berry_test(item_name):
    print(f"Testing {item_name} (Healing)...")
    
    state = create_mock_state()
    engine = BattleEngine(state)
    
    attacker = {
        'species': 'Mew', 
        'item': item_name, 
        'max_hp': 100,
        'current_hp': 10, # 10%
        'nature': 'Hardy',
        'types': ['Psychic'],
        'moves': ['Splash'],
        'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100}
    }
    attacker['side'] = 'player'
    defender = {'species': 'Target', 'side': 'ai', 'current_hp': 100, 'max_hp': 100, 'stats': {'def': 100}}
    
    state.player_active = attacker
    state.ai_active = defender
    state.player_party = [attacker]
    state.ai_party = [defender]
    state.fields['active_mons'] = [attacker, defender]

    log = []
    engine.execute_turn_action(state, 'player', "Move: Splash", 'ai', log)
    
    # 10 + 33 = 43 or 10 + 50 = 60?
    if attacker['current_hp'] > 10 and attacker.get('item') is None:
         print(f"PASS: {item_name} healed to {attacker['current_hp']}")
         return [item_name]
    else:
         print(f"FAIL: {item_name} (HP: {attacker['current_hp']})")
         return []

def run_phase5_tests():
    verified = []
    
    # 1. Stat Boosters
    verified.extend(run_pinch_berry_test('Liechi Berry', 'atk', 1))
    verified.extend(run_pinch_berry_test('Ganlon Berry', 'def', 1))
    verified.extend(run_pinch_berry_test('Petaya Berry', 'spa', 1))
    verified.extend(run_pinch_berry_test('Apicot Berry', 'spd', 1))
    verified.extend(run_pinch_berry_test('Salac Berry', 'spe', 1))
    
    # 2. Others
    # Starf Berry is random, we assume it works if consumption triggers
    
    # 3. Custap
    verified.extend(run_custap_test())
    
    # 4. Confusion
    verified.extend(run_wiki_berry_test('Wiki Berry'))
    verified.extend(run_wiki_berry_test('Mago Berry'))
    verified.extend(run_wiki_berry_test('Aguav Berry'))
    verified.extend(run_wiki_berry_test('Iapapa Berry'))
    verified.extend(run_wiki_berry_test('Figy Berry'))
    
    # Update Audit
    try:
        from .audit_utils import update_audit_with_verified
        update_audit_with_verified(verified)
    except ImportError:
        pass

if __name__ == "__main__":
    run_phase5_tests()
