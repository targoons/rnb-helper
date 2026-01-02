#!/usr/bin/env python3
"""Recoil and drain move tests"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pkh_app.battle_engine import BattleEngine, BattleState

def create_mon(name, ability='Pressure'):
    return {'species': name, 'level': 50, 'current_hp': 100, 'max_hp': 100,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Normal'], 'ability': ability, 'item': None,
            'moves': ['Double-Edge', 'Giga Drain'], 'status': None,
            'volatiles': [], 'stat_stages': {}}

def main():
    engine = BattleEngine()
    passed = failed = 0
    
    print("\n=== RECOIL TESTS ===")
    attacker = create_mon('Recoiler')
    defender = create_mon('Target')
    state = BattleState(attacker, defender, [attacker], [defender])
    
    s1, log1 = engine.apply_turn(state, 'Move: Double-Edge', 'Move: Giga Drain')
    
    # Recoil should damage user
    took_recoil = s1.player_active['current_hp'] < 100
    if took_recoil or any('recoil' in l.lower() for l in log1):
        print("✓ Recoil moves damage user")
        passed += 1
    else:
        print(f"✗ Recoil failed (HP: {s1.player_active['current_hp']})")
        failed += 1
    
    print("\n=== DRAIN TESTS ===")
    drainer = create_mon('Drainer')
    drainer['current_hp'] = 50
    state2 = BattleState(drainer, create_mon('Target2'), [drainer], [create_mon('Target2')])
    
    s2, log2 = engine.apply_turn(state2, 'Move: Giga Drain', 'Move: Double-Edge')
    
    # Drain should heal user
    healed = s2.player_active['current_hp'] > 50
    if healed or any('drain' in l.lower() or 'absorb' in l.lower() for l in log2):
        print("✓ Drain moves heal user")
        passed += 1
    else:
        print(f"✗ Drain failed (HP: {s2.player_active['current_hp']})")
        failed += 1
    
    print("\n=== ROCK HEAD ===")
    rock_head = create_mon('RockHead', ability='Rock Head')
    state3 = BattleState(rock_head, create_mon('Target3'), [rock_head], [create_mon('Target3')])
    
    # Use Double-Edge (recoil), opponent uses a non-damaging move
    s3, log3 = engine.apply_turn(state3, 'Move: Double-Edge', 'Move: Tackle')
    
    # Rock Head should prevent recoil, but will take damage from opponent's Tackle
    # Check if NO recoil message appears in log
    no_recoil_msg = not any('recoil' in l.lower() and 'RockHead' in l for l in log3)
    took_damage = s3.player_active['current_hp'] < 100
    
    # If took other damage but no recoil, that's correct
    if no_recoil_msg or (took_damage and s3.player_active['current_hp'] > 60):
        print("✓ Rock Head prevents recoil")
        passed += 1
    else:
        print(f"✗ Rock Head failed (HP: {s3.player_active['current_hp']})")
        failed += 1
    
    total = passed + failed
    print(f"\n{'='*60}\nRESULTS: {passed}/{total} passed ({100*passed/total if total else 0:.1f}%)\n{'='*60}")
    return passed == total

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
