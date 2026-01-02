#!/usr/bin/env python3
"""
Test script to verify move implementations are functional, not just "aware"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pkh_app.battle_engine import BattleEngine, BattleState
import json

def create_test_mon(name, moves, hp=100):
    """Create a test Pokemon"""
    return {
        'species': name,
        'species_id': name.lower(),
        'level': 50,
        'current_hp': hp,
        'max_hp': hp,
        'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
        'types': ['Normal'],
        'ability': 'Pressure',
        'item': None,
        'moves': moves,
        'status': None,
        'volatiles': [],
        'stat_stages': {}
    }

def test_move_execution(engine, move_name, description):
    """Test if a move actually executes without errors"""
    print(f"\n{'='*60}")
    print(f"Testing: {move_name} - {description}")
    print('='*60)
    
    state = BattleState({}, {}, [], [])
    state.player_active = create_test_mon('Attacker', [move_name])
    state.ai_active = create_test_mon('Defender', ['Tackle'])
    state.player_party = [state.player_active]
    state.ai_party = [state.ai_active]
    
    try:
        new_state, log = engine.apply_turn(state, f'Move: {move_name}', 'Move: Tackle')
        print(f"✓ Move executed successfully")
        print(f"Log entries: {len(log)}")
        for entry in log[:10]:  # Show first 10 log entries
            print(f"  {entry}")
        
        # Check if move had any effect
        if move_name in ['Stockpile', 'Focus Energy', 'Minimize']:
            if new_state.player_active.get('volatiles'):
                print(f"✓ Volatiles applied: {new_state.player_active['volatiles']}")
            else:
                print(f"⚠ WARNING: No volatiles applied for {move_name}")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Use local damage calculator (no calc_client needed)
    engine = BattleEngine()
    
    # Test moves we claim to have implemented
    test_cases = [
        ('Stockpile', 'Multi-state move with stat boosts'),
        ('Swallow', 'Consumes stockpile for healing'),
        ('Spit Up', 'Consumes stockpile for damage'),
        ('Trump Card', 'Variable BP based on PP'),
        ('Salt Cure', 'Residual damage volatile'),
        ('Syrup Bomb', 'Speed-lowering volatile'),
        ('Tar Shot', 'Fire weakness volatile'),
        ('Roost', 'Healing with type removal'),
        ('Glaive Rush', 'Double damage next turn'),
        ('Focus Punch', 'Fails if hit'),
        ('Beak Blast', 'Burns on contact during charge'),
        ('Endure', 'Survival at 1 HP'),
        ('Power Trick', 'Swap Atk/Def stats'),
        ('Minimize', 'Evasion boost + vulnerability'),
        ('Defense Curl', 'Def boost + Rollout power'),
        ('Perish Song', '3-turn countdown'),
        ('Magnet Rise', 'Ground immunity'),
        ('Wish', 'Delayed healing'),
        ('Safeguard', 'Status protection'),
        ('Attract', '50% immobilize'),
        ('Fling', 'Throw item'),
        ('Imprison', 'Seal moves'),
        ('No Retreat', 'All-stat boost + trap'),
    ]
    
    results = []
    for move, desc in test_cases:
        success = test_move_execution(engine, move, desc)
        results.append((move, success))
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"Passed: {passed}/{total} ({100*passed/total:.1f}%)")
    
    if passed < total:
        print("\nFailed moves:")
        for move, success in results:
            if not success:
                print(f"  - {move}")

if __name__ == '__main__':
    main()
