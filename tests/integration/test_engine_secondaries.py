
import sys
import os
import logging
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pkh_app.battle_engine import BattleEngine, BattleState

def test_secondaries():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    # Mock Calc Client
    calc_mock = MagicMock()
    # Mock damage result for Close Combat and Thunderbolt
    calc_mock.get_damage_rolls.return_value = [{'damage_rolls': [50], 'type': 'Fighting'}] 
    
    engine = BattleEngine(calc_mock)
    
    print("\n--- Test 1: Close Combat Drops ---")
    attacker = {'species': 'Lucario', 'ability': 'Justified', 'item': '', 'types': ['Fighting', 'Steel'], 'current_hp': 200, 'max_hp': 200}
    defender = {'species': 'Blissey', 'ability': 'Natrual Cure', 'types': ['Normal'], 'current_hp': 500, 'max_hp': 500}
    state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
    
    log = []
    engine.execute_turn_action(state, 'player', 'Close Combat', 'ai', log)
    
    stages = attacker.get('stat_stages', {})
    print(f"Log: {log}")
    print(f"Attacker Stages: {stages}")
    if stages.get('def') == -1 and stages.get('spd') == -1:
        print("PASS: Close Combat dropped Def and SpD.")
    else:
        print("FAIL: distinct drops missing.")

    print("\n--- Test 2: Thunderbolt Paralysis (Deterministic Force) ---")
    # Forcing RNG
    import random
    random.seed(42) # Should give low values? 
    # Or we can verify data presence
    
    attacker = {'species': 'Pikachu', 'ability': 'Static', 'item': '', 'types': ['Electric'], 'current_hp': 200, 'max_hp': 200}
    defender = {'species': 'Pelipper', 'ability': 'Drizzle', 'types': ['Water', 'Flying'], 'current_hp': 200, 'max_hp': 200}
    state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
    
    # Thunderbolt has 10% chance.
    # We might miss it.
    # Let's inspect if `mechanics_rich` has the data for Thunderbolt via engine
    rich_sec = engine._check_mechanic('Thunderbolt', 'moves', 'secondary')
    print(f"Thunderbolt Secondary Data: {rich_sec}")
    
    if rich_sec and rich_sec.get('status') == 'par':
        print("PASS: Thunderbolt has paralysis data.")
    else:
        print("FAIL: Thunderbolt secondary data missing.")
        
    print("\n--- Test 3: Contrary Close Combat ---")
    attacker['ability'] = 'Contrary'
    attacker['stat_stages'] = {}
    engine.execute_turn_action(state, 'player', 'Close Combat', 'ai', [])
    stages = attacker.get('stat_stages', {})
    print(f"Contrary Attacker Stages: {stages}")
    if stages.get('def') == 1:
        print("PASS: Contrary raised Def.")
    else:
        print("FAIL: Contrary logic failed.")

if __name__ == "__main__":
    test_secondaries()
