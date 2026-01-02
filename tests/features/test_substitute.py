import sys
import os
import unittest
import random
import traceback

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.mechanics import Mechanics

class DummyCalc:
    def get_damage_rolls(self, attacker, defender, moves, field):
        # Deterministic damage for testing: 40 damage per hit
        return [{'damage': [40], 'damage_rolls': [40], 'crit_rolls': [40], 'type_effectiveness': 1.0}]

class TestSubstitute(unittest.TestCase):
    def setUp(self):
        self.engine = BattleEngine(calc_client=DummyCalc())
        self.player_mon = {
            'species': 'Charizard',
            'max_hp': 200,
            'current_hp': 200,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Fire', 'Flying'],
            'moves': ['Substitute', 'Hyper Voice', 'Toxic', 'Tackle'],
            'volatiles': [],
            'stat_stages': {},
            'item': None,
            'ability': 'Blaze',
            'level': 100
        }
        self.ai_mon = {
            'species': 'Blastoise',
            'max_hp': 200,
            'current_hp': 200,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Water'],
            'moves': ['Tackle', 'Water Gun', 'Toxic'],
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

    def test_substitute_creation(self):
        print("\nTesting Substitute Creation...")
        log = []
        try:
            self.engine.execute_turn_action(self.state, 'player', 'Substitute', 'ai', log)
            
            print(f"Player HP: {self.player_mon['current_hp']}")
            print(f"Volatiles: {self.player_mon['volatiles']}")
            print(f"Sub HP: {self.player_mon.get('substitute_hp')}")
            
            self.assertEqual(self.player_mon['current_hp'], 150) # 200 - 50 (25%)
            self.assertIn('substitute', self.player_mon['volatiles'])
            self.assertEqual(self.player_mon['substitute_hp'], 50)
            self.assertTrue(any("put in a substitute" in l for l in log))
        except Exception:
            traceback.print_exc()
            self.fail("Substitute creation failed with exception")

    def test_substitute_blocks_damage(self):
        print("\nTesting Substitute Blocking Damage...")
        # Setup substitute
        self.player_mon['current_hp'] = 150
        self.player_mon['volatiles'] = ['substitute']
        self.player_mon['substitute_hp'] = 50
        
        log = []
        try:
            self.engine.execute_turn_action(self.state, 'ai', 'Tackle', 'player', log)
            
            print(f"Player HP: {self.player_mon['current_hp']}")
            print(f"Sub HP: {self.player_mon.get('substitute_hp')}")
            
            self.assertEqual(self.player_mon['current_hp'], 150) # Unchanged
            self.assertEqual(self.player_mon['substitute_hp'], 10) # 50 - 40
            self.assertTrue(any("substitute took damage" in l for l in log))
        except Exception:
            traceback.print_exc()
            self.fail("Substitute damage blocking failed with exception")

    def test_substitute_breaks(self):
        print("\nTesting Substitute Breaking...")
        # Setup substitute with low HP
        self.player_mon['current_hp'] = 150
        self.player_mon['volatiles'] = ['substitute']
        self.player_mon['substitute_hp'] = 30
        
        log = []
        try:
            # AI uses Tackle (40 damage) -> Should break sub
            self.engine.execute_turn_action(self.state, 'ai', 'Tackle', 'player', log)
            
            print(f"Player HP: {self.player_mon['current_hp']}")
            print(f"Volatiles: {self.player_mon['volatiles']}")
            
            self.assertEqual(self.player_mon['current_hp'], 150) # Unchanged
            self.assertNotIn('substitute', self.player_mon['volatiles'])
            self.assertTrue(any("substitute faded" in l for l in log))
        except Exception:
            traceback.print_exc()
            self.fail("Substitute break failed with exception")

    def test_substitute_blocks_status(self):
        print("\nTesting Substitute Blocking Status...")
        # Setup substitute
        self.ai_mon['volatiles'] = ['substitute']
        self.ai_mon['substitute_hp'] = 50
        
        log = []
        try:
            # Player uses Toxic
            self.engine.execute_turn_action(self.state, 'player', 'Toxic', 'ai', log)
            
            print(f"AI Status: {self.ai_mon.get('status')}")
            print(f"Log: {log}")
            
            self.assertIsNone(self.ai_mon.get('status'))
            self.assertTrue(any("blocked" in l.lower() for l in log))
        except Exception:
            traceback.print_exc()
            self.fail("Substitute status blocking failed with exception")

    def test_sound_move_bypasses_substitute(self):
        print("\nTesting Sound Move Bypass...")
        # Setup substitute
        self.ai_mon['volatiles'] = ['substitute']
        self.ai_mon['substitute_hp'] = 50
        
        log = []
        try:
            # Player uses Hyper Voice (Sound move)
            self.engine.execute_turn_action(self.state, 'player', 'Hyper Voice', 'ai', log)
            
            print(f"AI HP: {self.ai_mon['current_hp']}")
            print(f"Sub HP: {self.ai_mon.get('substitute_hp')}")
            
            self.assertEqual(self.ai_mon['current_hp'], 160) # 200 - 40
            self.assertEqual(self.ai_mon['substitute_hp'], 50) # Unchanged
        except Exception:
            traceback.print_exc()
            self.fail("Sound bypass failed with exception")

    def test_infiltrator_bypasses_substitute(self):
        print("\nTesting Infiltrator Bypass...")
        # Setup substitute
        self.ai_mon['volatiles'] = ['substitute']
        self.ai_mon['substitute_hp'] = 50
        
        # Player has Infiltrator
        self.player_mon['ability'] = 'Infiltrator'
        
        log = []
        try:
            # Player uses Tackle
            self.engine.execute_turn_action(self.state, 'player', 'Tackle', 'ai', log)
            
            print(f"AI HP: {self.ai_mon['current_hp']}")
            print(f"Sub HP: {self.ai_mon.get('substitute_hp')}")
            
            self.assertEqual(self.ai_mon['current_hp'], 160)
            self.assertEqual(self.ai_mon['substitute_hp'], 50)
        except Exception:
            traceback.print_exc()
            self.fail("Infiltrator bypass failed with exception")

if __name__ == '__main__':
    unittest.main()
