#!/usr/bin/env python3
"""Stat stage edge cases: caps, resets, Contrary, Simple"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pkh_app.battle_engine import BattleEngine, BattleState

def create_mon(name, ability='Pressure'):
    return {'species': name, 'level': 50, 'current_hp': 100, 'max_hp': 100,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Normal'], 'ability': ability, 'item': None,
            'moves': ['Swords Dance', 'Haze'], 'status': None,
            'volatiles': [], 'stat_stages': {}}

def main():
    engine = BattleEngine()
    passed = failed = 0
    
    print("\n=== STAT STAGE CAPS ===")
    booster = create_mon('Booster')
    booster['stat_stages'] = {'atk': 5}
    state = BattleState(booster, create_mon('Target'), [booster], [create_mon('Target')])
    
    # Opponent doesn't use Haze - use Tackle instead
    s1, log1 = engine.apply_turn(state, 'Move: Swords Dance', 'Move: Tackle')
    
    # Should cap at +6 (5 + 2 from Swords Dance)
    if s1.player_active.get('stat_stages', {}).get('atk', 0) == 6:
        print("✓ Stat stages cap at +6")
        passed += 1
    else:
        print(f"✗ Cap failed (atk: {s1.player_active.get('stat_stages', {}).get('atk')})")
        failed += 1
    
    print("\n=== HAZE RESETS ===")
    boosted = create_mon('Boosted')
    boosted['stat_stages'] = {'atk': 3, 'def': 2}
    state2 = BattleState(create_mon('Hazer'), boosted, [create_mon('Hazer')], [boosted])
    
    # Player uses Haze, AI uses Tackle (not Swords Dance)
    s2, log2 = engine.apply_turn(state2, 'Move: Haze', 'Move: Tackle')
    
    # Haze should reset stats to 0
    if s2.ai_active.get('stat_stages', {}).get('atk', 0) == 0:
        print("✓ Haze resets stat stages")
        passed += 1
    else:
        print(f"✗ Haze failed (atk: {s2.ai_active.get('stat_stages', {}).get('atk')})")
        failed += 1
    
    print("\n=== CONTRARY ABILITY ===")
    contrary = create_mon('Contrary', ability='Contrary')
    state3 = BattleState(contrary, create_mon('Target2'), [contrary], [create_mon('Target2')])
    
    # Contrary uses Swords Dance, opponent uses Tackle (not Haze)
    s3, log3 = engine.apply_turn(state3, 'Move: Swords Dance', 'Move: Tackle')
    
    # Contrary reverses boosts (+2 becomes -2)
    atk_stage = s3.player_active.get('stat_stages', {}).get('atk', 0)
    if atk_stage < 0:
        print("✓ Contrary reverses stat changes")
        passed += 1
    else:
        print(f"✗ Contrary failed (atk: {atk_stage})")
        failed += 1
    
    total = passed + failed
    print(f"\n{'='*60}\nRESULTS: {passed}/{total} passed ({100*passed/total if total else 0:.1f}%)\n{'='*60}")
    return passed == total

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
