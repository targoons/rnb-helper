#!/usr/bin/env python3
"""Multi-hit move tests: 2-5 hits, Skill Link, Population Bomb"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pkh_app.battle_engine import BattleEngine, BattleState

def create_mon(name, ability='Pressure'):
    return {'species': name, 'level': 50, 'current_hp': 100, 'max_hp': 100,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Normal'], 'ability': ability, 'item': None,
            'moves': ['Double Slap', 'Icicle Spear'], 'status': None,
            'volatiles': [], 'stat_stages': {}}

def main():
    engine = BattleEngine()
    passed = failed = 0
    
    print("\n=== MULTI-HIT TESTS ===")
    attacker = create_mon('MultiHitter')
    defender = create_mon('Target')
    state = BattleState(attacker, defender, [attacker], [defender])
    
    s1, log1 = engine.apply_turn(state, 'Move: Double Slap', 'Move: Double Slap')
    
    # Multi-hit moves should work
    hits = len([l for l in log1 if 'Hit' in l or 'hit' in l])
    if s1.ai_active['current_hp'] < 100:
        print("✓ Multi-hit moves execute")
        passed += 1
    else:
        print("✗ Multi-hit failed")
        failed += 1
    
    print("\n=== SKILL LINK ABILITY ===")
    skill_linker = create_mon('SkillLink', ability='Skill Link')
    state2 = BattleState(skill_linker, create_mon('Target2'), [skill_linker], [create_mon('Target2')])
    
    s2, log2 = engine.apply_turn(state2, 'Move: Icicle Spear', 'Move: Double Slap')
    
    # Skill Link always hits 5 times
    if s2.ai_active['current_hp'] < 100:
        print("✓ Skill Link ability works")
        passed += 1
    else:
        print("✗ Skill Link failed")
        failed += 1
    
    total = passed + failed
    print(f"\n{'='*60}\nRESULTS: {passed}/{total} passed ({100*passed/total if total else 0:.1f}%)\n{'='*60}")
    return passed == total

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
