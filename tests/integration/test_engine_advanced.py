
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pkh_app.battle_engine import BattleEngine, BattleState

def test_stance_change():
    print(">>> Testing Stance Change (Aegislash)...")
    calc = MagicMock()
    engine = BattleEngine(calc)
    
    # Shield -> Blade (Attacking)
    p_mon = {
        'species': 'Aegislash-Shield',
        'ability': 'Stance Change',
        'stats': {'atk': 50, 'def': 140, 'spa': 50, 'spd': 140, 'spe': 60},
        'current_hp': 100, 'max_hp': 100,
        'types': ['Steel', 'Ghost'],
        'moves': ['Iron Head', 'Kings Shield']
    }
    ai_mon = {'species': 'Target', 'current_hp': 100, 'max_hp': 100}
    state = BattleState(p_mon, ai_mon, [p_mon], [ai_mon])
    
    # Mock calculation
    calc.get_damage_rolls.return_value = [{'damage_rolls': [10], 'type': 'Steel'}]
    
    log = []
    # Mock _get_mechanic for move
    engine._get_mechanic = MagicMock(side_effect=lambda name, type: {'category': 'Physical', 'type': 'Steel'} if name == 'Iron Head' else ({'category': 'Status', 'type': 'Steel'} if name == 'Kings Shield' else None))
    
    engine.execute_turn_action(state, 'player', 'Move: Iron Head', 'ai', log)
    
    print(f"Species: {p_mon['species']}")
    print(f"Stats: {p_mon['stats']}")
    assert 'Blade' in p_mon['species']
    assert p_mon['stats']['atk'] == 140
    assert p_mon['stats']['def'] == 50
    print("  Stance Change (Blade) OK.")

    # Blade -> Shield (King's Shield)
    engine.execute_turn_action(state, 'player', 'Move: Kings Shield', 'ai', log)
    
    print(f"Species: {p_mon['species']}")
    assert 'Shield' in p_mon['species']
    assert p_mon['stats']['atk'] == 50
    assert p_mon['stats']['def'] == 140
    print("  Stance Change (Shield) OK.")

def test_protean():
    print("\n>>> Testing Protean (Cinderace)...")
    calc = MagicMock()
    engine = BattleEngine(calc)
    
    p_mon = {
        'species': 'Cinderace',
        'ability': 'Protean',
        'types': ['Fire'],
        'current_hp': 100,
        'max_hp': 100,
        'stats': {'spe': 100},
        'moves': ['Bounce']
    }
    ai_mon = {'species': 'Target', 'current_hp': 100, 'max_hp': 100}
    state = BattleState(p_mon, ai_mon, [p_mon], [ai_mon])
    
    # Mock calculation
    calc.get_damage_rolls.return_value = [{'damage_rolls': [10], 'type': 'Flying'}]
    
    log = []
    engine._get_mechanic = MagicMock(side_effect=lambda name, type: {'type': 'Flying'} if name == 'Bounce' else None)
    
    engine.execute_turn_action(state, 'player', 'Move: Bounce', 'ai', log)
    
    print(f"Types: {p_mon['types']}")
    assert p_mon['types'] == ['Flying']
    print("  Protean OK.")

def test_parental_bond():
    print("\n>>> Testing Parental Bond (Mega Kangaskhan)...")
    calc = MagicMock()
    engine = BattleEngine(calc)
    
    p_mon = {
        'species': 'Kangaskhan-Mega',
        'ability': 'Parental Bond',
        'current_hp': 100,
        'max_hp': 100,
        'stats': {'atk': 100},
        'moves': ['Return']
    }
    ai_mon = {
        'species': 'Target',
        'current_hp': 100,
        'max_hp': 100
    }
    state = BattleState(p_mon, ai_mon, [p_mon], [ai_mon])
    
    # Mock calculation for first hit
    calc.get_damage_rolls.return_value = [{'damage_rolls': [40], 'type': 'Normal'}]
    
    # Mock _get_mechanic for Move
    engine._get_mechanic = MagicMock(side_effect=lambda name, type: {'category': 'Physical', 'type': 'Normal'} if name == 'Return' else None)
    
    log = []
    engine.execute_turn_action(state, 'player', 'Move: Return', 'ai', log)
    
    # Hit 1 = 40 dmg. Hit 2 = 25% of 40 = 10 dmg. Total = 50 dmg.
    print(f"Defender HP: {ai_mon['current_hp']}")
    assert ai_mon['current_hp'] == 50
    print("  Parental Bond OK.")

def test_ghost_curse():
    print("\n>>> Testing Ghost Curse...")
    calc = MagicMock()
    engine = BattleEngine(calc)
    
    p_mon = {
        'species': 'Gengar',
        'types': ['Ghost', 'Poison'],
        'current_hp': 100,
        'max_hp': 100,
        'moves': ['Curse']
    }
    ai_mon = {
        'species': 'Target',
        'current_hp': 100,
        'max_hp': 100,
        'volatiles': []
    }
    state = BattleState(p_mon, ai_mon, [p_mon], [ai_mon])
    
    log = []
    engine.execute_turn_action(state, 'player', 'Move: Curse', 'ai', log)
    
    print(f"User HP: {p_mon['current_hp']}")
    print(f"Target Volatiles: {ai_mon['volatiles']}")
    assert p_mon['current_hp'] == 50
    assert 'curse' in ai_mon['volatiles']
    print("  Ghost Curse OK.")

def test_transform():
    print("\n>>> Testing Transform (Ditto)...")
    calc = MagicMock()
    engine = BattleEngine(calc)
    # Mock enrichment
    engine.rich_data = {'moves': {}, 'abilities': {}, 'items': {}}
    
    p_mon = {
        'species': 'Ditto',
        'ability': 'Limber',
        'current_hp': 100,
        'max_hp': 100,
        'stats': {'hp': 100, 'atk': 48},
        'moves': ['Transform']
    }
    ai_mon = {
        'species': 'Mew',
        'ability': 'Synchronize',
        'stats': {'hp': 400, 'atk': 236},
        'moves': ['Psychic', 'Thunderbolt'],
        'types': ['Psychic'],
        'max_hp': 400,
        'current_hp': 400
    }
    state = BattleState(p_mon, ai_mon, [p_mon], [ai_mon])
    
    # Mock _get_mechanic for Transform
    engine._get_mechanic = MagicMock(side_effect=lambda name, type: {'category': 'Status'} if name == 'Transform' else None)
    
    log = []
    engine.execute_turn_action(state, 'player', 'Move: Transform', 'ai', log)
    
    print(f"Transformed Species: {p_mon['species']}")
    print(f"Transformed Atk: {p_mon['stats']['atk']}")
    print(f"Transformed Ability: {p_mon['ability']}")
    print(f"Transformed Moves: {p_mon['moves']}")
    
    assert p_mon['species'] == 'Mew'
    assert p_mon['stats']['atk'] == 236
    assert p_mon['ability'] == 'Synchronize'
    assert 'Psychic' in p_mon['moves']
    print("  Transform OK.")

if __name__ == "__main__":
    try:
        test_stance_change()
        test_protean()
        test_parental_bond()
        test_ghost_curse()
        test_transform()
        print("\nALL BATCH 17 ADVANCED MECHANICS TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
