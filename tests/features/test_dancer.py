import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkh_app.battle_engine import BattleEngine, BattleState

def test_dancer():
    print("Testing Dancer Ability...")
    engine = BattleEngine()
    
    # 1. Setup State: Oricorio (Dancer) vs Volcarona (using Quiver Dance)
    p1 = {
        'species': 'Volcarona', 
        'types': ['Bug', 'Fire'], 
        'max_hp': 100, 
        'current_hp': 100, 
        'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
        'stat_stages': {'spe': 0, 'spa': 0, 'spd': 0},
        'moves': ['Quiver Dance'],
        'ability': 'Flame Body'
    }
    
    p2 = {
        'species': 'Oricorio', 
        'types': ['Flying', 'Fire'], 
        'max_hp': 100, 
        'current_hp': 100, 
        'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
        'stat_stages': {'spe': 0, 'spa': 0, 'spd': 0},
        'moves': ['Peck'], # Doesn't need to know Quiver Dance
        'ability': 'Dancer'
    }
    
    state = BattleState(player_active=p1, ai_active=p2, player_party=[p1], ai_party=[p2])
    
    # 2. Execute Turn: Volcarona uses Quiver Dance
    # We use engine.execute_turn_action directly or through apply_turn if possible.
    # Let's use execute_turn_action to simulate the specific move.
    
    log = []
    # context is needed for execute_turn_action? No, arguments are:
    # state, attacker_side, action, defender_side, log, defender_action=None
    
    print("Executing Quiver Dance...")
    engine.execute_turn_action(state, 'player', 'Move: Quiver Dance', 'ai', log)
    
    # 3. Check Log for Dancer Trigger
    found_trigger = False
    for line in log:
        print(line)
        if "Oricorio's Dancer copied the dance" in line:
            found_trigger = True
            
    if found_trigger:
        print("\nSUCCESS: Dancer triggered!")
    else:
        print("\nFAILURE: Dancer did not trigger.")

    # 4. Negative Test: Swords Dance (Is a dance move) -> Should Trigger
    # Test a Non-Dance move? Tackle.
    print("\nTesting Non-Dance Move (Tackle)...")
    log = []
    engine.execute_turn_action(state, 'player', 'Move: Tackle', 'ai', log)
    
    found_trigger_neg = False
    for line in log:
        if "Oricorio's Dancer copied the dance" in line:
            found_trigger_neg = True
            
    if not found_trigger_neg:
        print("SUCCESS: Dancer did not trigger on Tackle.")
    else:
        print("FAILURE: Dancer triggered on Tackle!")

if __name__ == "__main__":
    test_dancer()
