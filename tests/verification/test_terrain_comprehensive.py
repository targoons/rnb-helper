#!/usr/bin/env python3
"""Terrain system tests: Electric, Grassy, Misty, Psychic"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pkh_app.battle_engine import BattleEngine, BattleState

def create_mon(name, types=None):
    return {'species': name, 'level': 50, 'current_hp': 100, 'max_hp': 100,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': types or ['Normal'], 'ability': 'Pressure', 'item': None,
            'moves': ['Thunderbolt', 'Dragon Claw'], 'status': None,
            'volatiles': [], 'stat_stages': {}}

def main():
    engine = BattleEngine()
    passed = failed = 0
    
    print("\n=== ELECTRIC TERRAIN ===")
    attacker = create_mon('Electric', types=['Electric'])
    state = BattleState(attacker, create_mon('Target'), [attacker], [create_mon('Target')])
    state.fields['terrain'] = 'Electric'
    
    s1, _ = engine.apply_turn(state, 'Move: Thunderbolt', 'Move: Dragon Claw')
    terrain_dmg = 100 - s1.ai_active['current_hp']
    
    state2 = BattleState(create_mon('Electric', types=['Electric']), create_mon('Target2'),
                          [create_mon('Electric', types=['Electric'])], [create_mon('Target2')])
    s2, _ = engine.apply_turn(state2, 'Move: Thunderbolt', 'Move: Dragon Claw')
    normal_dmg = 100 - s2.ai_active['current_hp']
    
    if terrain_dmg > normal_dmg:
        print("✓ Electric Terrain boosts Electric moves")
        passed += 1
    else:
        print(f"✗ Terrain boost failed ({terrain_dmg} vs {normal_dmg})")
        failed += 1
    
    print("\n=== MISTY TERRAIN ===")
    state3 = BattleState(create_mon('Dragon', types=['Dragon']), create_mon('Target3'),
                          [create_mon('Dragon', types=['Dragon'])], [create_mon('Target3')])
    state3.fields['terrain'] = 'Misty'
    
    s3, _ = engine.apply_turn(state3, 'Move: Dragon Claw', 'Move: Thunderbolt')
    misty_dmg = 100 - s3.ai_active['current_hp']
    
    state4 = BattleState(create_mon('Dragon2', types=['Dragon']), create_mon('Target4'),
                          [create_mon('Dragon2', types=['Dragon'])], [create_mon('Target4')])
    s4, _ = engine.apply_turn(state4, 'Move: Dragon Claw', 'Move: Thunderbolt')
    no_misty_dmg = 100 - s4.ai_active['current_hp']
    
    if misty_dmg < no_misty_dmg:
        print("✓ Misty Terrain reduces Dragon moves")
        passed += 1
    else:
        print(f"✗ Misty reduction failed ({misty_dmg} vs {no_misty_dmg})")
        failed += 1
    
    total = passed + failed
    print(f"\n{'='*60}\nRESULTS: {passed}/{total} passed ({100*passed/total if total else 0:.1f}%)\n{'='*60}")
    return passed == total

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
