import logging
import sys
import os

# Add local helper to path
sys.path.append(os.getcwd())

from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.mechanics import Mechanics

def test_items_wave2():
    engine = BattleEngine(calc_client=None) # No calc client needed for logic checks
    
    # Mock Calc Client response structure
    class MockCalc:
        def get_damage_rolls(self, att, defn, moves, fields):
            return [{'damage_rolls': [100], 'type_effectiveness': 1.0}]
    
    engine.calc_client = MockCalc()
    
    # 1. Power Herb Test
    print("Testing Power Herb...")
    try:
        p_active = {'species': 'Venusaur', 'current_hp': 100, 'max_hp': 100, 'item': 'Power Herb', 'moves': ['Solar Beam'], 'types': ['Grass']}
        a_active = {'species': 'Charizard', 'current_hp': 100, 'max_hp': 100, 'types': ['Fire']}
        state = BattleState(p_active, a_active, [], [])
        
        log = []
        engine.execute_turn_action(state, 'player', 'Move: Solar Beam', 'ai', log)
        
        # Should NOT charge, should execute
        if p_active.get('charging'):
            print("FAIL: Power Herb did not prevent charging.")
        elif p_active.get('item') is not None:
             print("FAIL: Power Herb was not consumed.")
        else:
             print("PASS: Power Herb worked (instant move + consumed).")
             # Verify log
             if any('Power Herb' in l for l in log):
                  print("  (Log confirmed)")
    except Exception as e:
        print(f"Error testing Power Herb: {e}")

    # 2. Light Clay Test
    print("\nTesting Light Clay...")
    try:
        p_active = {'species': 'Grimmsnarl', 'current_hp': 100, 'max_hp': 100, 'item': 'Light Clay', 'moves': ['Reflect'], 'types': ['Dark', 'Fairy']}
        state = BattleState(p_active, a_active, [], [])
        
        log = []
        engine.execute_turn_action(state, 'player', 'Move: Reflect', 'ai', log)
        
        screen = state.fields['screens']['player'].get('reflect')
        if screen == 8:
            print(f"PASS: Light Clay extended Reflect to {screen} turns.")
        else:
            print(f"FAIL: Reflect duration is {screen} (Expected 8).")
    except Exception as e:
        print(f"Error testing Light Clay: {e}")
        
    # 3. Gems Test
    print("\nTesting Flying Gem...")
    try:
        # Mock engine to allow capturing 'total_mod' or check logs
        # Hard to check internal multiplier without mocking _get_modifier or intercepting
        # But we can check item consumption and log
        p_active = {'species': 'Talonflame', 'current_hp': 100, 'max_hp': 100, 'item': 'Flying Gem', 'moves': ['Acrobatics'], 'types': ['Fire', 'Flying']}
        state = BattleState(p_active, a_active, [], [])
        
        # Need rich data loaded for type checking?
        # Engine loads it. Assuming Acrobatics is Flying.
        # We need to ensure 'Acrobatics' is recognized as Flying.
        # We can inject it into engine.rich_data['moves'] just in case
        engine.rich_data['moves']['acrobatics'] = {'type': 'Flying', 'basePower': 55, 'category': 'Physical', 'name': 'Acrobatics'}
        
        log = []
        engine.execute_turn_action(state, 'player', 'Move: Acrobatics', 'ai', log)
        
        if p_active.get('item') is None:
             print("PASS: Flying Gem was consumed.")
             if any('Flying Gem strengthened' in l for l in log):
                  print("  (Log confirmed)")
        else:
             print("FAIL: Flying Gem was NOT consumed.")
    except Exception as e:
        print(f"Error testing Gems: {e}")

    # 4. Eviolite Test
    print("\nTesting Eviolite...")
    try:
        # Porygon2 (NFE)
        p_active = {'species': 'Porygon2', 'current_hp': 100, 'max_hp': 100, 'item': 'Eviolite', 'stats': {'def': 100, 'spd': 100}}
        a_active = {'species': 'Machamp', 'current_hp': 100, 'moves': ['Cross Chop']} # User
        
        state = BattleState(a_active, p_active, [], [])
        
        # We need to intercept the calc call to see the stats passed
        # Or blindly trust the code we just wrote.
        # Let's inspect the `execute_turn_action` by mocking calc_client.get_damage_rolls again to print defender stats
        class SpyCalc:
            def get_damage_rolls(self, att, defn, moves, fields):
                print(f"  [Spy] Defender Def: {defn['stats']['def']}, SpD: {defn['stats']['spd']}")
                return [{'damage_rolls': [100], 'type_effectiveness': 1.0}]
        
        engine.calc_client = SpyCalc()
        log = []
        engine.execute_turn_action(state, 'player', 'Move: Cross Chop', 'ai', log)
        
        # Expected: 100 * 1.5 = 150
        print("  (Check above logs for 150)")
        
    except Exception as e:
        print(f"Error testing Eviolite: {e}")

    except Exception as e:
        print(f"Error testing Eviolite: {e}")

    # Test Blunder Policy
    print("\nTesting Blunder Policy...")
    try:
        defender = {'species': 'Mew', 'types': ['Psychic'], 'current_hp': 100, 'max_hp': 100, 'stats': {'def': 100, 'spd': 100}, 'item': None}
        attacker = {'species': 'Machamp', 'types': ['Fighting'], 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 100, 'spe': 100}, 'item': 'Blunder Policy', 'stat_stages': {'spe': 0}}
        state = BattleState(attacker, defender, [], [])
        
        class DummyCalc:
             def get_damage_rolls(self, *args): return [{'damage_rolls': [0], 'type_effectiveness': 1.0}]
             
        engine = BattleEngine(DummyCalc())
        
        # Mock check_accuracy to FAIL (return False)
        original_check = Mechanics.check_accuracy
        Mechanics.check_accuracy = lambda a,b,c,d,e: False 
        
        log = []
        engine.execute_turn_action(state, 'player', 'Move: Cross Chop', 'ai', log)
        
        # Verify Speed Boost
        stage = attacker['stat_stages'].get('spe', 0)
        if stage == 2 and attacker.get('item') is None:
             print("PASS: Blunder Policy activated (+2 Speed, consumed).")
        else:
             print(f"FAIL: Blunder Policy state incorrect (Stage: {stage}, Item: {attacker.get('item')})")
        
        # Restore
        Mechanics.check_accuracy = original_check
        
    except Exception as e:
        print(f"Error testing Blunder Policy: {e}")

    # Test Eject Pack
    print("\nTesting Eject Pack...")
    try:
        defender = {'species': 'Mew', 'types': ['Psychic'], 'current_hp': 100, 'max_hp': 100, 'stats': {'def': 100}, 'item': None}
        attacker = {'species': 'Incineroar', 'types': ['Fire'], 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 100}, 'item': 'Eject Pack', 'stat_stages': {'atk': 0}}
        state = BattleState(attacker, defender, [], [])
        
        class DummyCalc:
             def get_damage_rolls(self, *args): return [{'damage_rolls': [0], 'type_effectiveness': 1.0}]
        engine = BattleEngine(DummyCalc())
        
        # Apply Intimidate-like drop logic manually via apply_boosts
        log = []
        engine._apply_boosts(attacker, {'atk': -1}, log)
        
        if attacker.get('must_switch') and attacker.get('item') is None:
             print("PASS: Eject Pack activated (must_switch set).")
        else:
             print(f"FAIL: Eject Pack state incorrect (Switch: {attacker.get('must_switch')}, Item: {attacker.get('item')})")
             
    except Exception as e:
        print(f"Error testing Eject Pack: {e}")
        
    # Test Mental Herb
    print("\nTesting Mental Herb...")
    try:
        attacker = {'species': 'Grimmsnarl', 'types': ['Dark'], 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 100}}
        defender = {'species': 'Mew', 'types': ['Psychic'], 'current_hp': 100, 'max_hp': 100, 
                    'stats': {'def': 100}, 'item': 'Mental Herb', 'volatiles': []}
        
        state = BattleState(attacker, defender, [], [])
        
        class DummyCalc:
             def get_damage_rolls(self, *args): return [{'damage_rolls': [0], 'type_effectiveness': 1.0}]
        engine = BattleEngine(DummyCalc())
        
        log = []
        # Attacker uses Taunt
        engine.execute_turn_action(state, 'player', 'Move: Taunt', 'ai', log)
        
        if 'taunt' not in defender.get('volatiles', []) and defender.get('item') is None:
             print("PASS: Mental Herb cured Taunt.")
        else:
             print(f"FAIL: Mental Herb failed (Volatiles: {defender.get('volatiles')}, Item: {defender.get('item')})")
             
    except Exception as e:
         print(f"Error testing Mental Herb: {e}")

if __name__ == "__main__":
    test_items_wave2()
