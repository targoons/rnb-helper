
import unittest
from unittest.mock import MagicMock
from pkh_app.battle_engine import BattleEngine, BattleState

class TestConsumables(unittest.TestCase):
    def setUp(self):
        self.calc_client = MagicMock()
        self.engine = BattleEngine(self.calc_client)

    def test_focus_sash_unburden(self):
        """Test Focus Sash survival and Unburden activation."""
        self.calc_client.get_damage_rolls.return_value = [{
            'moveName': 'Close Combat',
            'type': 'Fighting',
            'damage_rolls': [200], # Fatal damage
            'category': 'Physical'
        }]

        attacker = {
            'species': 'Machamp',
            'current_hp': 100,
            'max_hp': 100,
            'stats': {'atk': 200},
            'ability': 'No Guard'
        }
        defender = {
            'species': 'Hawlucha',
            'current_hp': 100,
            'max_hp': 100,
            'stats': {'def': 50},
            'ability': 'Unburden',
            'item': 'Focus Sash'
        }

        state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
        log = []
        
        self.engine.execute_turn_action(state, 'player', 'Move: Close Combat', 'ai', log)
        
        self.assertEqual(defender['current_hp'], 1, "Should survive with 1 HP")
        self.assertIsNone(defender.get('item'), "Item should be consumed")
        self.assertTrue(defender.get('unburden_active'), "Unburden should be active")
        self.assertIn("hung on using its Focus Sash", str(log))
        self.assertIn("became unburdened", str(log))

    def test_sitrus_berry(self):
        """Test Sitrus Berry healing at < 50% HP."""
        self.calc_client.get_damage_rolls.return_value = [{
            'moveName': 'Tackle',
            'type': 'Normal',
            'damage_rolls': [60], # Brings to 40/100 (<50%)
            'category': 'Physical'
        }]
        
        attacker = {'species': 'Rattata', 'current_hp': 100, 'max_hp': 100}
        defender = {
            'species': 'Snorlax', 
            'current_hp': 100, 
            'max_hp': 100, 
            'item': 'Sitrus Berry',
            'ability': 'Thick Fat'
        }
        
        state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
        log = []
        
        self.engine.execute_turn_action(state, 'player', 'Move: Tackle', 'ai', log)
        
        # Damage 60 -> 40 HP. Sitrus heals 25 (1/4 of 100). Total 65.
        self.assertEqual(defender['current_hp'], 65, "Should heal 25 HP from 40 HP")
        self.assertIsNone(defender.get('item'))
        self.assertIn("restored HP using its Sitrus Berry", str(log))

    def test_weak_armor(self):
        """Test Weak Armor stat changes on Physical hit."""
        self.calc_client.get_damage_rolls.return_value = [{
            'moveName': 'Tackle',
            'type': 'Normal',
            'category': 'Physical',
            'damage_rolls': [10]
        }]
        
        attacker = {'species': 'Rattata', 'current_hp': 100}
        defender = {
            'species': 'Skarmory', 
            'current_hp': 100, 
            'max_hp': 100, 
            'ability': 'Weak Armor',
            'stats': {'def': 100, 'spe': 100}
        }
        
        state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
        log = []
        self.engine.execute_turn_action(state, 'player', 'Move: Tackle', 'ai', log)
        
        stages = defender.get('stat_stages', {})
        self.assertEqual(stages.get('def'), -1, "Defense should fall")
        self.assertEqual(stages.get('spe'), 2, "Speed should rise sharply")
        self.assertIn("Weak Armor", str(log))

if __name__ == '__main__':
    unittest.main()
