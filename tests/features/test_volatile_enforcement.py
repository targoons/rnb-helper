import sys
import os
import unittest
import traceback

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from pkh_app.battle_engine import BattleEngine, BattleState

class DummyCalc:
    def get_damage_rolls(self, attacker, defender, moves, field):
        return [{'damage': [100], 'damage_rolls': [100], 'crit_rolls': [0], 'type_effectiveness': 1.0}]

class TestVolatileEnforcement(unittest.TestCase):
    def setUp(self):
        self.engine = BattleEngine(calc_client=DummyCalc())
        self.player_mon = {
            'species': 'Charizard',
            'max_hp': 400,
            'current_hp': 400,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Fire', 'Flying'],
            'moves': ['Flamethrower', 'Recover', 'Toxic', 'Tackle'],
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
            'moves': ['Tackle'],
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

    def test_taunt_enforcement(self):
        print("\nTesting Taunt Enforcement...")
        self.player_mon['volatiles'] = ['taunt']
        self.player_mon['taunt_turns'] = 3
        log = []
        # Toxic is Status
        self.engine.execute_turn_action(self.state, 'player', 'Toxic', 'ai', log)
        self.assertTrue(any("can't use status moves due to taunt" in l for l in log))
        self.assertIsNone(self.ai_mon.get('status'))
        
        # Flamethrower is Special/Attack
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Flamethrower', 'ai', log)
        self.assertEqual(self.ai_mon['current_hp'], 300)

    def test_encore_enforcement(self):
        print("\nTesting Encore Enforcement...")
        self.player_mon['volatiles'] = ['encore']
        self.player_mon['encore_move'] = 'Flamethrower'
        self.player_mon['encore_turns'] = 3
        log = []
        # Try to use Tackle
        self.engine.execute_turn_action(self.state, 'player', 'Tackle', 'ai', log)
        self.assertTrue(any("forced to use Flamethrower" in l for l in log))
        # Tackle damage should NOT be applied. AI HP should be 400.
        self.assertEqual(self.ai_mon['current_hp'], 400)
        
        # Try to use Flamethrower
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Flamethrower', 'ai', log)
        self.assertEqual(self.ai_mon['current_hp'], 300)

    def test_disable_enforcement(self):
        print("\nTesting Disable Enforcement...")
        self.player_mon['volatiles'] = ['disable']
        self.player_mon['disable_move'] = 'Flamethrower'
        self.player_mon['disable_turns'] = 3
        log = []
        # Try to use Flamethrower
        self.engine.execute_turn_action(self.state, 'player', 'Flamethrower', 'ai', log)
        self.assertTrue(any("Flamethrower is disabled" in l for l in log))
        self.assertEqual(self.ai_mon['current_hp'], 400)
        
        # Try to use Tackle
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Tackle', 'ai', log)
        self.assertEqual(self.ai_mon['current_hp'], 300)

    def test_heal_block_enforcement(self):
        print("\nTesting Heal Block Enforcement...")
        self.player_mon['volatiles'] = ['healblock']
        self.player_mon['healblock_turns'] = 3
        log = []
        # Recover is healing
        self.engine.execute_turn_action(self.state, 'player', 'Recover', 'ai', log)
        self.assertTrue(any("can't use healing moves due to Heal Block" in l for l in log))
        
        # Also check end-of-turn
        self.player_mon['item'] = 'Leftovers'
        self.player_mon['_rich_item'] = {'name': 'Leftovers', 'healRatio': [1, 16]}
        self.player_mon['current_hp'] = 300
        log = []
        self.engine._apply_residual(self.player_mon, 'items', self.state, log)
        self.assertEqual(self.player_mon['current_hp'], 300) # Blocked

    def test_embargo_enforcement(self):
        print("\nTesting Embargo Enforcement...")
        self.player_mon['volatiles'] = ['embargo']
        self.player_mon['embargo_turns'] = 5
        self.player_mon['item'] = 'Leftovers'
        self.player_mon['_rich_item'] = {'name': 'Leftovers', 'healRatio': [1, 16]}
        self.player_mon['current_hp'] = 300
        
        log = []
        self.engine._apply_residual(self.player_mon, 'items', self.state, log)
        self.assertEqual(self.player_mon['current_hp'], 300) # Blocked

    def test_destiny_bond(self):
        print("\nTesting Destiny Bond...")
        self.ai_mon['volatiles'] = ['destiny_bond']
        self.player_mon['current_hp'] = 400
        # Player uses Tackle (100 damage) -> AI (400) goes to 300? No, let's make it faint.
        self.ai_mon['current_hp'] = 100
        
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Tackle', 'ai', log)
        
        print(f"AI HP: {self.ai_mon['current_hp']}")
        print(f"Player HP: {self.player_mon['current_hp']}")
        # AI fainted, so Destiny Bond should trigger and faint Player.
        self.assertTrue(any("took its attacker down with it" in l for l in log))
        self.assertEqual(self.player_mon['current_hp'], 0)

if __name__ == '__main__':
    unittest.main()
