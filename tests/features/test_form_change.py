
import logging
import sys
import os

# Add local helper to path
sys.path.append(os.getcwd())

from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.mechanics import Mechanics

def test_form_changes():
    # Helper to create a dummy calc client
    class MockCalc:
        def get_damage_rolls(self, att, defn, moves, fields):
            return [{'damage_rolls': [100], 'type_effectiveness': 1.0}]

    engine = BattleEngine(calc_client=MockCalc())
    
    # 1. Mega Evolution Test (Charizard -> Mega X)
    print("Testing Mega Evolution (Charizard -> Mega X)...")
    try:
        p_active = {
            'species': 'Charizard', 
            'current_hp': 100, 'max_hp': 100, 
            'item': 'Charizardite X', 
            'moves': ['Flare Blitz'], 
            'types': ['Fire', 'Flying'],
            'ability': 'Blaze',
            'stats': {'hp': 78, 'at': 84, 'df': 78, 'sa': 109, 'sd': 85, 'sp': 100}
        }
        # Mock species data for the target form
        engine.pokedex['charizardmegax'] = {
            'name': 'Charizard-Mega-X',
            'types': ['Fire', 'Dragon'],
            'bs': {'hp': 78, 'at': 130, 'df': 111, 'sa': 130, 'sd': 85, 'sp': 100},
            'abilities': ['Tough Claws']
        }
        
        a_active = {'species': 'Ditto', 'current_hp': 100, 'max_hp': 100, 'types': ['Normal'], 'stats': {'hp': 100}}
        state = BattleState(p_active, a_active, [], [])
        
        log = []
        engine.enrich_state(state)
        engine._check_mega_evolution(state, 'player', log)
        
        if state.player_active['species'] == 'Charizard-Mega-X':
            print("PASS: Species changed to Charizard-Mega-X.")
            if 'Dragon' in state.player_active['types']:
                print("PASS: Types updated to Fire/Dragon.")
            else:
                print(f"FAIL: Types are {state.player_active['types']}")
            
            if state.player_active['ability'] == 'Tough Claws':
                print("PASS: Ability changed to Tough Claws.")
            else:
                print(f"FAIL: Ability is {state.player_active['ability']}")
        else:
            print(f"FAIL: Species is {state.player_active['species']}")
    except Exception as e:
        print(f"Error testing Mega Evolution: {e}")
        import traceback
        traceback.print_exc()

    # 2. Primal Reversion Test (Kyogre)
    print("\nTesting Primal Reversion (Kyogre)...")
    try:
        # Proper initialization for BattleState and perform_switch
        p_active_dummy = {'species': 'Magikarp', 'current_hp': 10, 'max_hp': 100, 'stats': {'hp': 100}}
        a_active = {'species': 'Ditto', 'current_hp': 100, 'max_hp': 100, 'stats': {'hp': 100}}
        p_party = [{
            'species': 'Kyogre', 
            'current_hp': 100, 'max_hp': 100, 
            'item': 'Blue Orb', 
            'ability': 'Drizzle',
            'types': ['Water'],
            'stats': {'hp': 100, 'at': 100, 'df': 100, 'sa': 150, 'sd': 140, 'sp': 90}
        }]
        
        # Mock species data for Primal Kyogre
        engine.pokedex['kyogreprimal'] = {
            'name': 'Kyogre-Primal',
            'types': ['Water'],
            'bs': {'hp': 100, 'at': 150, 'df': 90, 'sa': 180, 'sd': 160, 'sp': 90},
            'abilities': ['Primordial Sea']
        }
        
        state = BattleState(p_active_dummy, a_active, p_party, [])
        log = []
        # Switch Kyogre in
        engine.perform_switch(state, 'player', 'Kyogre', log)
        
        active = state.player_active
        if active['species'] == 'Kyogre-Primal':
            print("PASS: Species changed to Kyogre-Primal on switch-in.")
            if active['ability'] == 'Primordial Sea':
                print("PASS: Ability changed to Primordial Sea.")
        else:
            print(f"FAIL: Species is {active['species']}")
    except Exception as e:
        print(f"Error testing Primal Reversion: {e}")
        import traceback
        traceback.print_exc()

    # 3. Item Protection Test (Knock Off)
    print("\nTesting Item Protection (Knock Off vs Mega Stone)...")
    try:
        p_active = {
            'species': 'Gengar-Mega', 
            'item': 'Gengarite', 
            'current_hp': 100, 'max_hp': 100,
            'stats': {'hp': 100}
        }
        # Manually enrich for test
        p_active['_rich_item'] = {'megaStone': 'Gengar-Mega', 'name': 'Gengarite'}
        
        a_active = {
            'species': 'Machamp', 'current_hp': 100, 'max_hp': 100,
            'moves': ['Knock Off'],
            'stats': {'hp': 90, 'at': 130, 'df': 80, 'sa': 65, 'sd': 85, 'sp': 55}
        }
        state = BattleState(a_active, p_active, [], [])
        
        log = []
        # Corrected call to execute_turn_action
        engine.execute_turn_action(state, 'player', 'Move: Knock Off', 'ai', log)
        
        if state.ai_active['item'] == 'Gengarite': # Machamp (player) vs Gengar (ai)
            print("PASS: Gengarite was NOT knocked off.")
        else:
            print(f"FAIL: Gengarite was knocked off. Item: {state.ai_active.get('item')}")
    except Exception as e:
        print(f"Error testing Item Protection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_form_changes()
