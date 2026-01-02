
import sys
import os
import logging
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pkh_app.battle_engine import BattleEngine, BattleState

def test_priority():
    logging.basicConfig(level=logging.ERROR)
    # Mock Calc Client
    engine = BattleEngine(MagicMock())
    
    # 1. Base Priority
    print("\n--- Test 1: Base Priority ---")
    prio = engine.get_move_priority('Extreme Speed', {'ability': 'None'})
    print(f"Extreme Speed Priority: {prio} (Expected: 2)")
    
    prio = engine.get_move_priority('Quick Attack', {'ability': 'None'})
    print(f"Quick Attack Priority: {prio} (Expected: 1)")
    
    prio = engine.get_move_priority('Trick Room', {'ability': 'None'})
    print(f"Trick Room Priority: {prio} (Expected: -7)")
    
    # 2. Prankster
    print("\n--- Test 2: Prankster ---")
    attacker = {'ability': 'Prankster'}
    prio = engine.get_move_priority('Tail Whip', attacker) # Status
    print(f"Prankster Tail Whip: {prio} (Expected: 1)")
    
    prio = engine.get_move_priority('Tackle', attacker) # Physical
    print(f"Prankster Tackle: {prio} (Expected: 0)")
    
    # 3. Gale Wings
    print("\n--- Test 3: Gale Wings ---")
    attacker = {'ability': 'Gale Wings', 'current_hp': 100, 'max_hp': 100}
    prio = engine.get_move_priority('Brave Bird', attacker) # Flying
    print(f"Gale Wings (Full HP) Brave Bird: {prio} (Expected: 1)")
    
    attacker['current_hp'] = 99
    prio = engine.get_move_priority('Brave Bird', attacker)
    print(f"Gale Wings (Hurt) Brave Bird: {prio} (Expected: 0)")
    
    # 4. Triage
    print("\n--- Test 4: Triage ---")
    attacker = {'ability': 'Triage'}
    prio = engine.get_move_priority('Synthesis', attacker) # Heal
    print(f"Triage Synthesis: {prio} (Expected: 3)")
    
    prio = engine.get_move_priority('Absorb', attacker) # Drain (Heal)
    print(f"Triage Absorb: {prio} (Expected: 3)")
    
    prio = engine.get_move_priority('Tackle', attacker)
    print(f"Triage Tackle: {prio} (Expected: 0)")

if __name__ == "__main__":
    test_priority()
