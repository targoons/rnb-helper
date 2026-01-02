
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkh_app.battle_engine import BattleEngine
from pkh_app.mechanics import Mechanics

def create_mock_state():
    state = type('State', (), {
        'fields': {'active_mons': [], 'weather': None, 'terrain': None, 'trick_room': 0}, 
        'player_party': [], 
        'ai_party': [], 
        'last_moves': {}, 
        'get_hash': lambda: 0
    })()
    return state

def run_soul_dew_test():
    print("Testing Soul Dew (Base Power Boost for Lati@s)...")
    state = create_mock_state()
    soul_dew_data = {
        'name': 'Soul Dew', 
        'onBasePower': 1.2, 
        'triggerType': 'Psychic' 
    }
    attacker = {
        'species': 'Latias', 
        'item': 'Soul Dew', 
        '_rich_item': soul_dew_data,
        'types': ['Dragon', 'Psychic'], 
        'stats': {'spa': 100},
        'moves': ['Psychic'],
        'current_hp': 100, 'max_hp': 100
    }
    move_data = {'type': 'Psychic', 'basePower': 80, 'category': 'Special', 'name': 'Psychic'}
    defender = {'species': 'Target', 'types': ['Normal'], 'ability': 'None', 'current_hp': 100, 'max_hp': 100}
    state.fields['context'] = {'effectiveness': 1.0}
    
    bp_mod = Mechanics.get_modifier(attacker, 'onBasePower', move_data, state.fields, target=defender)
    if bp_mod >= 1.19:
        print(f"PASS: Soul Dew Boosted BP by {bp_mod}")
        return ['Soul Dew']
    else:
        print(f"FAIL: Soul Dew BP Mod: {bp_mod}")
        return []

def run_adrenaline_orb_test():
    print("Testing Adrenaline Orb (Intimidate -> Speed +1)...")
    state = create_mock_state()
    engine = BattleEngine(state)
    
    intimidate_data = {'name': 'Intimidate'}
    
    # Removed 'Inner Focus' to ensure Intimidate affects logic
    defender = {
        'species': 'Lucario', 'item': 'Adrenaline Orb', 
        'stats': {'spe': 100}, 'stat_stages': {'spe': 0, 'atk': 0},
        'ability': 'None', 
        '_rich_ability': {'name': 'None'},
        'side': 'ai',
        'current_hp': 100, 'max_hp': 100
    }
    
    attacker = {
        'species': 'Gyarados', 'ability': 'Intimidate', 
        '_rich_ability': intimidate_data,
        'side': 'player',
        'current_hp': 100, 'max_hp': 100
    }
    
    state.ai_active = defender
    state.player_active = attacker
    state.fields['active_mons'] = [attacker, defender]
    state.fields['context'] = {}
    
    log = []
    
    # Use apply_switch_in_abilities(state, side, mon, log)
    # This triggers Intimidate logic
    try:
        engine.apply_switch_in_abilities(state, 'player', attacker, log)
        
        if defender['stat_stages']['spe'] >= 1 and defender.get('item') is None:
             print("PASS: Adrenaline Orb activated by Intimidate")
             return ['Adrenaline Orb']
        else:
             print(f"FAIL: Speed Stage: {defender['stat_stages']['spe']}, Item: {defender.get('item')}")
             return []
    except Exception as e:
        print(f"Test Error: {e}")
        return []

def run_throat_spray_test():
    print("Testing Throat Spray (Sound Move -> SpA +1)...")
    state = create_mock_state()
    engine = BattleEngine(state)
    
    attacker = {
        'species': 'Primarina', 'item': 'Throat Spray',
        'stats': {'spa': 100}, 'stat_stages': {'spa': 0},
        'moves': ['Hyper Voice'],
        'current_hp': 100, 'max_hp': 100,
        'types': ['Water', 'Fairy']
    }
    attacker['side'] = 'player'
    defender = {'species': 'Target', 'current_hp': 100, 'max_hp': 100, 'stats': {'spd': 100}, 'types': ['Normal'], 'ability': 'None'}
    state.player_active = attacker
    state.ai_active = defender
    state.player_party = [attacker]
    state.ai_party = [defender]
    state.fields['active_mons'] = [attacker, defender]
    state.fields['context'] = {}
    
    log = []
    if not hasattr(engine, 'rich_data'): engine.rich_data = {'moves': {}, 'items': {}, 'abilities': {}}
    engine.rich_data['moves']['hypervoice'] = {'flags': {'sound': 1}, 'category': 'Special', 'basePower': 90, 'type': 'Normal'}
    
    try:
        engine.execute_turn_action(state, 'player', "Move: Hyper Voice", 'ai', log)
    except Exception as e:
        print(f"Throat Spray Exec Error: {e}")
    
    if attacker['stat_stages']['spa'] == 1 and attacker.get('item') is None:
         print("PASS: Throat Spray activated")
         return ['Throat Spray']
    else:
         print(f"FAIL: SpA Stage: {attacker['stat_stages']['spa']}, Item: {attacker.get('item')}")
         return []

def run_room_service_test():
    print("Testing Room Service (Trick Room -> Speed -1)...")
    state = create_mock_state()
    engine = BattleEngine(state)
    
    attacker = {
        'species': 'Snorlax', 'item': 'Room Service',
        'stats': {'spe': 100}, 'stat_stages': {'spe': 0},
        'current_hp': 100, 'max_hp': 100
    }
    state.fields['trick_room'] = 5 # Active
    
    log = []
    engine.apply_switch_in_items(state, 'player', attacker, log)
    
    if attacker['stat_stages']['spe'] == -1 and attacker.get('item') is None:
         print("PASS: Room Service activated")
         return ['Room Service']
    else:
         print(f"FAIL: Speed Stage: {attacker['stat_stages']['spe']}, Item: {attacker.get('item')}")
         return []

def run_phase4_tests():
    verified = []
    
    verified.extend(run_soul_dew_test())
    verified.extend(run_adrenaline_orb_test())
    verified.extend(run_throat_spray_test())
    verified.extend(run_room_service_test())
    
    # Update Audit
    try:
        from .audit_utils import update_audit_with_verified
        update_audit_with_verified(verified)
    except ImportError:
        pass

if __name__ == "__main__":
    run_phase4_tests()
