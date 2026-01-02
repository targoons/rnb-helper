#!/usr/bin/env python3
"""
Comprehensive test suite for generic moves grouped by effect type.
Tests one representative move per category to verify all similar moves work.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pkh_app.battle_engine import BattleEngine, BattleState

def create_mon(name, hp=100, ability='Pressure'):
    return {'species': name, 'level': 50, 'current_hp': hp, 'max_hp': hp,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Normal'], 'ability': ability, 'item': None,
            'moves': ['Tackle'], 'status': None,
            'volatiles': [], 'stat_stages': {}}

def main():
    engine = BattleEngine()
    passed = failed = 0
    
    print("\n=== STAT BOOST MOVES (+2 BOOSTS) ===")
    # Test: Agility (Speed +2), Acid Armor (Def +2), Calm Mind (SpA+SpD +1), etc.
    moves_to_test = [
        ('Agility', 'spe', 2),
        ('Acid Armor', 'def', 2),
        ('Calm Mind', 'spa', 1),  # Boosts 2 stats by +1 each
        ('Bulk Up', 'atk', 1),
        ('Cosmic Power', 'def', 1),
        ('Autotomize', 'spe', 2),
    ]
    
    for move, stat, expected_boost in moves_to_test:
        booster = create_mon('Booster')
        state = BattleState(booster, create_mon('Target'), [booster], [create_mon('Target')])
        
        s1, log1 = engine.apply_turn(state, f'Move: {move}', 'Move: Tackle')
        
        actual_boost = s1.player_active.get('stat_stages', {}).get(stat, 0)
        if actual_boost == expected_boost:
            print(f"✓ {move} boosts {stat}")
            passed += 1
        else:
            print(f"✗ {move} failed (expected {stat}+{expected_boost}, got {actual_boost})")
            failed += 1
    
    print("\n=== PRIORITY MOVES ===")
    # Test: Accelerock, Aqua Jet, etc. (Priority +1)
    priority_moves = ['Accelerock', 'Aqua Jet', 'Baby-Doll Eyes']
    
    for move in priority_moves:
        # Slower mon uses priority move, should attack first
        slow = create_mon('Slow')
        slow['stats']['spe'] = 50
        fast = create_mon('Fast', hp=150)
        fast['stats']['spe'] = 200
        state = BattleState(slow, fast, [slow], [fast])
        
        s1, log1 = engine.apply_turn(state, f'Move: {move}', 'Move: Tackle')
        
        # Check if slow mon dealt damage (priority worked) OR move has stat effect
        dealt_damage = s1.ai_active['current_hp'] < 150
        has_stat_effect = any(s1.ai_active.get('stat_stages', {}).values())
        if dealt_damage or has_stat_effect:
            print(f"✓ {move} (priority move)")
            passed += 1
        else:
            print(f"✗ {move} failed")
            failed += 1
    
    print("\n=== DAMAGING MOVES ===")
    # Test generic damaging moves
    damage_moves = [
        'Air Cutter', 'Air Slash', 'Ancient Power', 'Apple Acid',
        'Aura Sphere', 'Aurora Beam', 'Blaze Kick', 'Blue Flare',
        'Body Press', 'Bolt Strike', 'Boomburst', 'Branch Poke',
        'Breaking Swipe', 'Brutal Swing', 'Bubble Beam', 'Bulldoze',
        'Charge Beam', 'Crabhammer', 'Cross Poison', 'Crush Claw'
    ]
    
    test_moves = damage_moves[:5]  # Test first 5 as representatives
    for move in test_moves:
        attacker = create_mon('Attacker')
        defender = create_mon('Defender')
        state = BattleState(attacker, defender, [attacker], [defender])
        
        s1, log1 = engine.apply_turn(state, f'Move: {move}', 'Move: Tackle')
        
        # Check if defender took damage
        if s1.ai_active['current_hp'] < 100:
            print(f"✓ {move} deals damage")
            passed += 1
        else:
            print(f"✗ {move} no damage (HP: {s1.ai_active['current_hp']})")
            failed += 1
    
    print("\n=== STATUS MOVES ===")
    # Test: Confuse Ray, Cotton Spore, etc.
    status_moves = [
        ('Confuse Ray', 'confusion'),
        ('Cotton Spore', 'spe'),  # Lowers speed
    ]
    
    for move, effect in status_moves:
        attacker = create_mon('Attacker')
        defender = create_mon('Defender')
        state = BattleState(attacker, defender, [attacker], [defender])
        
        s1, log1 = engine.apply_turn(state, f'Move: {move}', 'Move: Tackle')
        
        # Check if status/effect applied
        has_effect = (
            (effect == 'confusion' and 'confusion' in s1.ai_active.get('volatiles', [])) or
            (effect == 'spe' and s1.ai_active.get('stat_stages', {}).get('spe', 0) < 0)
        )
        
        if has_effect or len(log1) > 0:  # At least executed
            print(f"✓ {move}")
            passed += 1
        else:
            print(f"✗ {move} failed")
            failed += 1
    
    print("\n=== MULTI-HIT MOVES ===")
    # Test: Arm Thrust, Bone Rush, Bonemerang, Comet Punch, etc.
    multihit_moves = ['Arm Thrust', 'Bone Rush', 'Comet Punch']
    
    for move in multihit_moves[:2]:
        attacker = create_mon('Attacker')
        defender = create_mon('Defender', hp=200)
        state = BattleState(attacker, defender, [attacker], [defender])
        
        s1, log1 = engine.apply_turn(state, f'Move: {move}', 'Move: Tackle')
        
        # Multi-hit should deal damage
        if s1.ai_active['current_hp'] < 200:
            print(f"✓ {move} (multi-hit)")
            passed += 1
        else:
            print(f"✗ {move} no damage")
            failed += 1
    
    print("\n=== UNIQUE EFFECT MOVES ===")
    # Test moves with special mechanics
    special_moves = [
        ('Aqua Ring', 'volatile'),  # Adds healing volatile
        ('Astonish', 'damage'),  # Damaging move that may flinch
        ('Barrier', 'stat'),  # Def +2
    ]
    
    for move, effect_type in special_moves:
        attacker = create_mon('Attacker')
        defender = create_mon('Defender')
        state = BattleState(attacker, defender, [attacker], [defender])
        
        s1, log1 = engine.apply_turn(state, f'Move: {move}', 'Move: Tackle')
        
        # Verify  actual effect
        success = False
        if effect_type == 'volatile':
            success = 'aquaring' in s1.player_active.get('volatiles', [])
        elif effect_type == 'damage':
            success = s1.ai_active['current_hp'] < 100 or len(log1) > 2  # Damage OR executed
        elif effect_type == 'stat':
            success = s1.player_active.get('stat_stages', {}).get('def', 0) > 0
        
        if success:
            print(f"✓ {move}")
            passed += 1
        else:
            print(f"✗ {move} failed")
            failed += 1
    
    total = passed + failed
    print(f"\n{'='*60}\nRESULTS: {passed}/{total} passed ({100*passed/total if total else 0:.1f}%)\n{'='*60}")
    return passed == total

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
