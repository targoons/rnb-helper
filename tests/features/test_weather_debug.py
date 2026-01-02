"""
Detailed debug test to trace exactly where modifiers are applied.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkh_app.battle_engine import BattleEngine
from pkh_app import local_damage_calc
from pkh_app.mechanics import Mechanics

# Patch the damage calc function to show what's happening
original_calculate_damage = local_damage_calc.calculate_damage

def debug_calculate_damage(attacker, defender, move_name, move_data, field=None):
    result = original_calculate_damage(attacker, defender, move_name, move_data, field)
    print(f"\n[DAMAGE_CALC DEBUG]")
    print(f"  Move: {move_name}")
    print(f"  Base Power: {move_data.get('basePower')}")
    print(f"  Damage rolls: {result['damage_rolls'][:3]}... (showing first 3)")
    print(f"  Effectiveness: {result['effectiveness']}")
    print(f"  STAB: {result['is_stab']}")
    return result

local_damage_calc.calculate_damage = debug_calculate_damage

def test_detailed():
    state = type('State', (), {'fields': {}, 'player_party': [], 'ai_party': [], 'get_hash': lambda: 0})()
    engine = BattleEngine(state)
    
    attacker = {
        'species': 'Greninja',
        'types': ['Water'],  # Remove Dark to simplify
        'stats': {'spa': 100},
        'stat_stages': {'atk':0, 'def':0, 'spa':0, 'spd':0, 'spe':0, 'acc':0, 'eva':0},
        'current_hp': 100,
        'max_hp': 100,
        'side': 'player',
        'volatiles': [],
        'ability': 'No Ability',
        'level': 50
    }
    
    defender = {
        'species': 'Charizard',
        'types': ['Fire'],  # Remove Flying to simplify
        'stats': {'spd': 100},
        'stat_stages': {'atk':0, 'def':0, 'spa':0, 'spd':0, 'spe':0, 'acc':0, 'eva':0},
        'current_hp': 100,
        'max_hp': 100,
        'side': 'ai',
        'volatiles': [],
        'ability': 'No Ability',
        'level': 50
    }
    
    state.player_active = attacker
    state.ai_active = defender
    state.player_party = [attacker]
    state.ai_party = [defender]
    state.fields = {
        'active_mons': [attacker, defender],
        'weather': 'Rain'
    }
    state.last_moves = {}
    
    engine.enrich_state(state)
    
    move_data = {
        'name': 'Surf',
        'type': 'Water',
        'category': 'Special',
        'basePower': 90
    }
    
    def _norm(s): return str(s).lower().replace(' ', '').replace('-', '').replace("'", "")
    
    engine.move_names = {'Surf': 'Surf'}
    if not hasattr(engine, 'rich_data'):
        engine.rich_data = {'moves': {}, 'abilities': {}, 'items': {}}
    engine.rich_data['moves'][_norm('Surf')] = move_data
    
    engine.enrich_state(state)
    
    print("=== Executing with Rain ===")
    log = []
    engine.execute_turn_action(state, 'player', 'Move: Surf', 'ai', log)
    
    print("\n[BATTLE LOG]")
    for l in log:
        print(f"  {l}")

if __name__ == "__main__":
    test_detailed()
