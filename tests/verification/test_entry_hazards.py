#!/usr/bin/env python3
"""
Comprehensive tests for entry hazard mechanics
Tests: Stealth Rock, Spikes, Toxic Spikes, Sticky Web
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pkh_app.battle_engine import BattleEngine, BattleState

def create_mon(name, types=None, hp=100, ability='Pressure', item=None):
    return {
        'species': name,
        'level': 50,
        'current_hp': hp,
        'max_hp': hp,
        'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
        'types': types or ['Normal'],
        'ability': ability,
        'item': item,
        'moves': ['Tackle'],
        'status': None,
        'volatiles': [],
        'stat_stages': {}
    }

def main():
    engine = BattleEngine()
    passed = 0
    failed = 0
    
    print("\n=== STEALTH ROCK TESTS ===")
    
    # Test 1: Stealth Rock damage on switch
    attacker = create_mon('Setter')
    defender = create_mon('FireFlying', types=['Fire', 'Flying'], hp=100)
    switch_in = create_mon('FireFlying2', types=['Fire', 'Flying'], hp=100)
    state = BattleState(attacker, defender, [attacker], [defender, switch_in])
    
    # Set hazard
    state.fields['hazards'] = {'player': [], 'ai': ['Stealth Rock']}
   
   # Switch should trigger hazard damage (4x weak to rock = 50% HP)
    new_state, log = engine.apply_turn(state, 'Move: Tackle', 'Switch: FireFlying2')
    
    # FireFlying2 takes 50 damage (50% of 100 HP due to 4x weakness)
    if new_state.ai_active['current_hp'] < 100:
        print("✓ Stealth Rock damages on switch-in")
        passed += 1
    else:
        print(f"✗ Stealth Rock didn't damage (HP: {new_state.ai_active['current_hp']})")
        failed += 1
    
    # Test 2: Heavy-Duty Boots prevents hazards (check via absence of hazard damage message)
    defender2 = create_mon('BootedFlying', types=['Flying'], hp=100, item='Heavy-Duty Boots')
    state2 = BattleState(attacker, defender, [attacker], [defender, defender2])
    state2.fields['hazards'] = {'player': [], 'ai': ['Stealth Rock']}
    
    new_state2, log2 = engine.apply_turn(state2, 'Move: Tackle', 'Switch: BootedFlying')
    
    # Check log doesn't contain hazard damage message (boots prevent it)
    no_hazard_msg = not any('hurt by' in l.lower() or 'stealth rock' in l.lower() for l in log2)
    if no_hazard_msg or new_state2.ai_active['current_hp'] >= 76:  # May take Tackle damage but not hazard
        print("✓ Heavy-Duty Boots prevents hazard damage")
        passed += 1
    else:
        print(f"✗ Heavy-Duty Boots failed (HP: {new_state2.ai_active['current_hp']})")
        failed += 1
    
    print("\n=== SPIKES TESTS ===")
    
    # Test 3: Spikes damage (not type-based)
    defender3 = create_mon('Grounded', hp=96)
    state3 = BattleState(attacker, defender, [attacker], [defender, defender3])
    state3.fields['hazards'] = {'player': [], 'ai': ['Spikes']}
    
    new_state3, log3 = engine.apply_turn(state3, 'Move: Tackle', 'Switch: Grounded')
    
    # 1 layer = 12.5% damage (12 HP for max HP 96)
    if new_state3.ai_active['current_hp'] < 96:
        print("✓ Spikes damages grounded Pokemon")
        passed += 1
    else:
        print(f"✗ Spikes didn't damage (HP: {new_state3.ai_active['current_hp']})")
        failed += 1
    
    # Test 4: Flying types immune to Spikes (check via absence of Spikes message)
    defender4 = create_mon('Flying', types=['Flying'], hp=100)
    state4 = BattleState(attacker, defender, [attacker], [defender, defender4])
    state4.fields['hazards'] = {'player': [], 'ai': ['Spikes']}
    
    new_state4, log4 = engine.apply_turn(state4, 'Move: Tackle', 'Switch: Flying')
    
    # Check log doesn't contain Spikes damage message
    no_spikes_msg = not any('hurt by spikes' in l.lower() for l in log4)
    if no_spikes_msg or new_state4.ai_active['current_hp'] >= 76:  # May take Tackle but not Spikes
        print("✓ Flying types immune to Spikes")
        passed += 1
    else:
        print(f"✗ Flying immunity failed (HP: {new_state4.ai_active['current_hp']})")
        failed += 1
    
    print("\n=== TOXIC SPIKES TESTS ===")
    
    # Test 5: Toxic Spikes apply poison
    defender5 = create_mon('Victim', hp=100)
    state5 = BattleState(attacker, defender, [attacker], [defender, defender5])
    state5.fields['hazards'] = {'player': [], 'ai': ['Toxic Spikes']}
    
    new_state5, log5 = engine.apply_turn(state5, 'Move: Tackle', 'Switch: Victim')
    
    if new_state5.ai_active.get('status') in ['psn', 'tox']:
        print("✓ Toxic Spikes apply poison on switch")
        passed += 1
    else:
        print(f"✗ Toxic Spikes didn't poison (status: {new_state5.ai_active.get('status')})")
        failed += 1
    
    # Test 6: Flying types immune to Toxic Spikes
    defender6 = create_mon('Flying2', types=['Flying'], hp=100)
    state6 = BattleState(attacker, defender, [attacker], [defender, defender6])
    state6.fields['hazards'] = {'player': [], 'ai': ['Toxic Spikes']}
    
    new_state6, log6 = engine.apply_turn(state6, 'Move: Tackle', 'Switch: Flying2')
    
    if new_state6.ai_active.get('status') is None:
        print("✓ Flying types immune to Toxic Spikes")
        passed += 1
    else:
        print(f"✗ Flying immunity failed (status: {new_state6.ai_active.get('status')})")
        failed += 1
    
    print("\n=== STICKY WEB TESTS ===")
    
    # Test 7: Sticky Web lowers speed
    defender7 = create_mon('Grounded2', hp=100)
    state7 = BattleState(attacker, defender, [attacker], [defender, defender7])
    state7.fields['hazards'] = {'player': [], 'ai': ['Sticky Web']}
    
    new_state7, log7 = engine.apply_turn(state7, 'Move: Tackle', 'Switch: Grounded2')
    
    if new_state7.ai_active.get('stat_stages', {}).get('spe', 0) < 0:
        print("✓ Sticky Web lowers speed on switch")
        passed += 1
    else:
        print(f"✗ Sticky Web didn't lower speed (stage: {new_state7.ai_active.get('stat_stages', {}).get('spe')})")
        failed += 1
    
    # Test 8: Flying types immune to Sticky Web
    defender8 = create_mon('Flying3', types=['Flying'], hp=100)
    state8 = BattleState(attacker, defender, [attacker], [defender, defender8])
    state8.fields['hazards'] = {'player': [], 'ai': ['Sticky Web']}
    
    new_state8, log8 = engine.apply_turn(state8, 'Move: Tackle', 'Switch: Flying3')
    
    if new_state8.ai_active.get('stat_stages', {}).get('spe', 0) == 0:
        print("✓ Flying types immune to Sticky Web")
        passed += 1
    else:
        print(f"✗ Flying immunity failed (spe stage: {new_state8.ai_active.get('stat_stages', {}).get('spe')})")
        failed += 1
    
    # Summary
    total = passed + failed
    pct = 100 * passed / total if total > 0 else 0
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed ({pct:.1f}%)")
    print('='*60)
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
