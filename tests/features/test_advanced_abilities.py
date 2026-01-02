import sys
import os
sys.path.append(os.getcwd())
from pkh_app.battle_engine import BattleEngine
from pkh_app.mechanics import Mechanics

def test_technician():
    print("Testing Technician...")
    mon = {
        'species': 'Scizor',
        'ability': 'Technician',
        '_rich_ability': {'name': 'Technician', 'onBasePower': 1.5},
        'stats': {'atk': 100}
    }
    
    # 1. Weak Move (BP 40) -> Should be boosted
    move_weak = {'basePower': 40, 'name': 'Quick Attack', 'type': 'Normal'}
    mod_weak = Mechanics.get_modifier(mon, 'onBasePower', move_data=move_weak)
    print(f"  Weak Move (40 BP): Modifier = {mod_weak}")
    assert mod_weak == 1.5, f"Expected 1.5, got {mod_weak}"

    # 2. Strong Move (BP 90) -> Should NOT be boosted
    move_strong = {'basePower': 90, 'name': 'Bug Buzz', 'type': 'Bug'}
    mod_strong = Mechanics.get_modifier(mon, 'onBasePower', move_data=move_strong)
    print(f"  Strong Move (90 BP): Modifier = {mod_strong}")
    assert mod_strong == 1.0, f"Expected 1.0, got {mod_strong}"
    print("Technician Test Passed!")

def test_sheer_force_mechanics():
    print("\nTesting Sheer Force Logic (Mechanics level)...")
    mon = {
        'species': 'Nidoking', 
        'ability': 'Sheer Force',
        '_rich_ability': {'name': 'Sheer Force', 'onBasePower': 1.3},
    }
    
    # 1. Move with secondary -> Boosted
    move_sec = {'basePower': 90, 'secondary': {'chance': 10}, 'name': 'Sludge Bomb'}
    mod_sec = Mechanics.get_modifier(mon, 'onBasePower', move_data=move_sec)
    print(f"  Secondary Move: Modifier = {mod_sec}")
    # Note: Rich data uses 1.3000488... approx 1.3
    assert abs(mod_sec - 1.3) < 0.01, f"Expected ~1.3, got {mod_sec}"
    
    # 2. Move without secondary -> Not Boosted
    move_clean = {'basePower': 90, 'secondary': None, 'secondaries': None, 'name': 'Earthquake'}
    mod_clean = Mechanics.get_modifier(mon, 'onBasePower', move_data=move_clean)
    print(f"  Clean Move: Modifier = {mod_clean}")
    assert mod_clean == 1.0, f"Expected 1.0, got {mod_clean}"
    print("Sheer Force Mechanics Test Passed!")

if __name__ == "__main__":
    test_technician()
    test_sheer_force_mechanics()
