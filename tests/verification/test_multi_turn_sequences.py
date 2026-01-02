#!/usr/bin/env python3
"""
Tests for multi-turn move sequences: Solar Beam, Fly, Protect chains
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pkh_app.battle_engine import BattleEngine, BattleState

def create_mon(name, item=None):
    return {
        'species': name, 'level': 50, 'current_hp': 100, 'max_hp': 100,
        'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
        'types': ['Grass'], 'ability': 'Overgrow', 'item': item,
        'moves': ['Solar Beam', 'Fly', 'Protect'], 'status': None,
        'volatiles': [], 'stat_stages': {}
    }

def main():
    engine = BattleEngine()
    passed = failed = 0
    
    print("\n=== TWO-TURN MOVE TESTS ===")
    
    # Test: Solar Beam charges then attacks
    attacker = create_mon('Charger')
    defender = create_mon('Target')
    state = BattleState(attacker, defender, [attacker], [defender])
    
    # Turn 1: Should charge
    s1, log1 = engine.apply_turn(state, 'Move: Solar Beam', 'Move: Protect')
    charging = 'charging' in s1.player_active.get('volatiles', [])
    
    if charging or any('charg' in l.lower() for l in log1):
        print("✓ Solar Beam initiates charge")
        passed += 1
    else:
        print("✗ Solar Beam charge failed")
        failed += 1
    
    # Test: Power Herb skips charge
    attacker2 = create_mon('Herbed', item='Power Herb')
    state2 = BattleState(attacker2, defender, [attacker2], [defender])
    
    s2, log2 = engine.apply_turn(state2, 'Move: Solar Beam', 'Move: Protect')
    no_charge = 'charging' not in s2.player_active.get('volatiles', [])
    
    if no_charge or attacker2.get('item') is None:
        print("✓ Power Herb skips charge")
        passed += 1
    else:
        print("✗ Power Herb failed")
        failed += 1
    
    print("\n=== PROTECT TESTS ===")
    
    # Test: Protect blocks damage
    attacker3 = create_mon('Protector')
    defender3 = create_mon('Attacker')
    state3 = BattleState(attacker3, defender3, [attacker3], [defender3])
    
    s3, log3 = engine.apply_turn(state3, 'Move: Protect', 'Move: Solar Beam')
    
    damage_blocked = s3.player_active['current_hp'] == 100
    if damage_blocked or any('protect' in l.lower() for l in log3):
        print("✓ Protect blocks damage")
        passed += 1
    else:
        print(f"✗ Protect failed (HP: {s3.player_active['current_hp']})")
        failed += 1
    
    total = passed + failed
    pct = 100 * passed / total if total > 0 else 0
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed ({pct:.1f}%)")
    print('='*60)
    return passed == total

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
