
import unittest
from unittest.mock import MagicMock
from app.battle_engine import BattleEngine, BattleState

class TestBattleEngine(unittest.TestCase):
    def setUp(self):
        self.calc_client = MagicMock()
        self.engine = BattleEngine(self.calc_client)

    def test_flash_fire_flag(self):
        """Test that Flash Fire ability sets the flash_fire flag on the defender."""
        self.calc_client.get_damage_rolls.return_value = [{
            'moveName': 'Flamethrower',
            'type': 'Fire',
            'damage_rolls': [10],
            'desc': 'It hits.'
        }]

        attacker = {
            'species': 'Arcanine',
            'current_hp': 100,
            'max_hp': 100,
            'stats': {'atk': 100},
            'ability': 'Intimidate'
        }
        defender = {
            'species': 'Ninetales',
            'current_hp': 100,
            'max_hp': 100,
            'stats': {'def': 100},
            'ability': 'Flash Fire'
        }

        state = BattleState(
            player_active=attacker,
            ai_active=defender,
            player_party=[],
            ai_party=[]
        )

        log = []
        self.engine.execute_turn_action(state, 'player', 'Move: Flamethrower', 'ai', log)

        self.assertTrue(defender.get('flash_fire'), "Flash Fire flag should be True")
        self.assertEqual(defender['current_hp'], 100, "Should take no damage")
        self.assertIn("  Ninetales's Fire power rose (Flash Fire)!", log)

    def test_sap_sipper(self):
        """Test that Sap Sipper boosts Attack and grants immunity to Grass moves."""
        self.calc_client.get_damage_rolls.return_value = [{
            'moveName': 'Vine Whip',
            'type': 'Grass',
            'damage_rolls': [10],
            'desc': 'It hits.'
        }]

        attacker = {
            'species': 'Bulbasaur',
            'current_hp': 100,
            'max_hp': 100,
            'stats': {'atk': 100}
        }
        defender = {
            'species': 'Azumarill',
            'current_hp': 100,
            'max_hp': 100,
            'stats': {'def': 100},
            'ability': 'Sap Sipper',
            'stat_stages': {'atk': 0}
        }

        state = BattleState(
            player_active=attacker,
            ai_active=defender,
            player_party=[],
            ai_party=[]
        )

        log = []
        self.engine.execute_turn_action(state, 'player', 'Move: Vine Whip', 'ai', log)

        self.assertEqual(defender['current_hp'], 100, "Should take no damage")
        self.assertEqual(defender['stat_stages']['atk'], 1, "Attack should rise by 1")
        self.assertIn("  Azumarill's Attack rose (Sap Sipper)!", log)

    def test_storm_drain(self):
        """Test that Storm Drain boosts SpA and grants immunity to Water moves."""
        self.calc_client.get_damage_rolls.return_value = [{
            'moveName': 'Water Gun',
            'type': 'Water',
            'damage_rolls': [10],
            'desc': 'It hits.'
        }]

        attacker = {
            'species': 'Squirtle',
            'current_hp': 100,
            'max_hp': 100
        }
        defender = {
            'species': 'Gastrodon',
            'current_hp': 100,
            'max_hp': 100,
            'ability': 'Storm Drain',
            'stat_stages': {'spa': 0}
        }

        state = BattleState(
            player_active=attacker,
            ai_active=defender,
            player_party=[],
            ai_party=[]
        )

        log = []
        self.engine.execute_turn_action(state, 'player', 'Move: Water Gun', 'ai', log)

        self.assertEqual(defender['current_hp'], 100, "Should take no damage")
        self.assertEqual(defender['stat_stages']['spa'], 1, "Sp. Atk should rise by 1")
        self.assertIn("  Gastrodon's Sp. Atk rose (Storm Drain)!", log)

if __name__ == '__main__':
    unittest.main()
