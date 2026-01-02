import sys
import os
import unittest
import traceback

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from pkh_app.battle_engine import BattleEngine, BattleState

class DummyCalc:
    def get_damage_rolls(self, attacker, defender, moves, field):
        return [{'damage': [0], 'type_effectiveness': 1.0}]

class TestEndOfTurn(unittest.TestCase):
    def setUp(self):
        self.engine = BattleEngine(calc_client=DummyCalc())
        self.player_mon = {
            'species': 'Charizard',
            'max_hp': 400,
            'current_hp': 400,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Fire', 'Flying'],
            'volatiles': [],
            'stat_stages': {},
            'item': None,
            'ability': 'Blaze',
            'level': 100
        }
        self.ai_mon = {
            'species': 'Blastoise',
            'max_hp': 400,
            'current_hp': 400,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Water'],
            'volatiles': [],
            'stat_stages': {},
            'item': None,
            'ability': 'Torrent',
            'level': 100
        }
        self.state = BattleState(
            player_party=[self.player_mon],
            ai_party=[self.ai_mon],
            player_active=self.player_mon,
            ai_active=self.ai_mon,
            fields={'weather': None, 'terrain': None, 'hazards': {'player': [], 'ai': []}, 'screens': {'player': {'reflect': 0, 'light_screen': 0, 'aurora_veil': 0}, 'ai': {'reflect': 0, 'light_screen': 0, 'aurora_veil': 0}}}
        )

    def test_leech_seed(self):
        print("\nTesting Leech Seed...")
        self.player_mon['current_hp'] = 400
        self.player_mon['volatiles'] = ['leech_seed']
        self.ai_mon['current_hp'] = 200
        
        log = []
        self.engine.handle_end_of_turn(self.state, log)
        
        # Player loses 1/8 of 400 = 50
        # AI restores 50
        print(f"Player HP: {self.player_mon['current_hp']} (Expected 350)")
        print(f"AI HP: {self.ai_mon['current_hp']} (Expected 250)")
        
        self.assertEqual(self.player_mon['current_hp'], 350)
        self.assertEqual(self.ai_mon['current_hp'], 250)

    def test_ghost_curse(self):
        print("\nTesting Ghost Curse...")
        self.player_mon['current_hp'] = 400
        self.player_mon['volatiles'] = ['curse']
        
        log = []
        self.engine.handle_end_of_turn(self.state, log)
        
        # Player loses 1/4 of 400 = 100
        print(f"Player HP: {self.player_mon['current_hp']} (Expected 300)")
        self.assertEqual(self.player_mon['current_hp'], 300)

    def test_perish_song(self):
        print("\nTesting Perish Song...")
        self.player_mon['volatiles'] = ['perish']
        self.player_mon['perish_turns'] = 3
        
        log = []
        # Turn 1
        self.engine.handle_end_of_turn(self.state, log)
        self.assertEqual(self.player_mon['perish_turns'], 2)
        
        # Turn 2
        self.engine.handle_end_of_turn(self.state, log)
        self.assertEqual(self.player_mon['perish_turns'], 1)
        
        # Turn 3
        self.engine.handle_end_of_turn(self.state, log)
        self.assertEqual(self.player_mon['perish_turns'], 0)
        self.assertEqual(self.player_mon['current_hp'], 0)
        print("Perish Song fainted the Pokemon.")

    def test_grassy_terrain_healing(self):
        print("\nTesting Grassy Terrain...")
        self.state.fields['terrain'] = 'Grassy'
        # Charizard is flying, so it shouldn't heal unless grounded
        self.player_mon['current_hp'] = 300
        log = []
        self.engine.handle_end_of_turn(self.state, log)
        self.assertEqual(self.player_mon['current_hp'], 300) # Still 300
        
        # Grounded mon (Blastoise)
        self.ai_mon['current_hp'] = 300
        self.engine.handle_end_of_turn(self.state, log)
        # Expected: 300 + 400/16 = 300 + 25 = 325
        print(f"AI HP: {self.ai_mon['current_hp']} (Expected 325)")
        self.assertEqual(self.ai_mon['current_hp'], 325)

    def test_black_sludge(self):
        print("\nTesting Black Sludge...")
        # 1. Poison type heals
        self.ai_mon['types'] = ['Poison']
        self.ai_mon['item'] = 'Black Sludge'
        self.ai_mon['_rich_item'] = {'name': 'Black Sludge', 'healRatio': [1, 8]} # Data says 1/8 but our logic should override or use it
        # Actually our logic FORCES 1/16 for heal.
        self.ai_mon['current_hp'] = 300
        log = []
        self.engine.handle_end_of_turn(self.state, log)
        # 300 + 400/16 = 325
        self.assertEqual(self.ai_mon['current_hp'], 325)
        
        # 2. Non-poison type hurts
        self.player_mon['types'] = ['Fire']
        # item name must be normalized in _apply_residual? No, handled by name.
        self.player_mon['item'] = 'Black Sludge'
        self.player_mon['_rich_item'] = {'name': 'Black Sludge', 'healRatio': [1, 8]}
        self.player_mon['current_hp'] = 400
        self.engine.handle_end_of_turn(self.state, log)
        # 400 - 400/8 = 350
        print(f"Player HP (Non-Poison Black Sludge): {self.player_mon['current_hp']} (Expected 350)")
        self.assertEqual(self.player_mon['current_hp'], 350)

    def test_magic_guard(self):
        print("\nTesting Magic Guard...")
        self.player_mon['ability'] = 'Magic Guard'
        self.player_mon['current_hp'] = 400
        self.player_mon['status'] = 'psn'
        self.player_mon['volatiles'] = ['leech_seed', 'curse']
        self.state.fields['weather'] = 'Sandstorm'
        
        log = []
        self.engine.handle_end_of_turn(self.state, log)
        # Should remain at 400 HP
        print(f"Magic Guard HP: {self.player_mon['current_hp']} (Expected 400)")
        self.assertEqual(self.player_mon['current_hp'], 400)

if __name__ == '__main__':
    unittest.main()
