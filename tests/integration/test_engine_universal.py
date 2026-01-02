
import sys
import os
import unittest
import logging
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pkh_app.battle_engine import BattleEngine, BattleState
from tests.test_utils import create_mocked_engine

class TestEngineUniversal(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.engine = create_mocked_engine()
        
    def _configure_mock(self, move_name, damage=10, meta=None):
        ret = {'damage_rolls': [damage], 'moveName': move_name, 'type': 'Normal'}
        if meta:
            ret.update(meta)
        self.engine.calc_client.calc_damage.return_value = ret

    def test_soundproof_vs_hyper_voice(self):
        """Test 1: Soundproof vs Hyper Voice"""
        attacker = {'species': 'Sylveon', 'ability': 'Pixilate', 'item': '', 'types': ['Fairy'], 'current_hp': 100, 'max_hp': 100}
        defender = {'species': 'Electrode', 'ability': 'Soundproof', 'item': '', 'types': ['Electric'], 'current_hp': 100, 'max_hp': 100}
        state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
        self.engine.enricher.enrich_state(state)
        
        # Explicit check
        is_immune, msg = self.engine.check_immunity(attacker, defender, 'Hyper Voice')
        self.assertTrue(is_immune, "Hyper Voice should be blocked by Soundproof")
        
        # Execute turn
        log = []
        self.engine.execute_turn_action(state, 'player', 'Move: Hyper Voice', 'ai', log)
        
        self.assertEqual(defender['current_hp'], 100, "Should take no damage")
        self.assertTrue(any("unaffected" in l or "Soundproof" in l for l in log), f"Log should mention block: {log}")

    def test_rough_skin_rocky_helmet(self):
        """Test 2: Tackle vs Rough Skin + Rocky Helmet"""
        attacker = {'species': 'Rattata', 'ability': 'Guts', 'item': '', 'types': ['Normal'], 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 100}}
        defender = {'species': 'Garchomp', 'ability': 'Rough Skin', 'item': 'Rocky Helmet', 'types': ['Dragon', 'Ground'], 'current_hp': 100, 'max_hp': 100, 'stats': {'def': 100}}
        state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
        self.engine.enricher.enrich_state(state)
        self._configure_mock('Tackle', damage=10)
        
        log = []
        self.engine.execute_turn_action(state, 'player', 'Move: Tackle', 'ai', log)
        
        # Rough Skin (1/8 -> 12.5 -> 12) + Rocky Helmet (1/6 -> 16.6 -> 16) = 28 damage
        expected_hp = 100 - 12 - 16 # 72
        self.assertLess(attacker['current_hp'], 100, "Attacker should take recoil")
        # Allow slight rounding diffs
        self.assertTrue(68 <= attacker['current_hp'] <= 76, f"Expected ~72 HP, got {attacker['current_hp']}")

    def test_protective_pads(self):
        """Test 3: Protective Pads vs Rocky Helmet"""
        attacker = {'species': 'Rattata', 'ability': 'Guts', 'item': 'Protective Pads', 'types': ['Normal'], 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 100}}
        defender = {'species': 'Ferrothorn', 'ability': 'Iron Barbs', 'item': 'Rocky Helmet', 'types': ['Steel', 'Grass'], 'current_hp': 100, 'max_hp': 100, 'stats': {'def': 100}}
        state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
        self.engine.enricher.enrich_state(state)
        self._configure_mock('Tackle', damage=10)
        
        log = []
        self.engine.execute_turn_action(state, 'player', 'Move: Tackle', 'ai', log)
        
        self.assertEqual(attacker['current_hp'], 100, "Protective Pads should prevent all contact effects")

    def test_recoil_double_edge(self):
        """Test 4: Recoil (Double-Edge 33%)"""
        attacker = {'species': 'Tauros', 'ability': 'Intimidate', 'item': '', 'types': ['Normal'], 'current_hp': 200, 'max_hp': 200, 'stats': {'atk': 100}}
        defender = {'species': 'Chansey', 'ability': 'Natural Cure', 'item': '', 'types': ['Normal'], 'current_hp': 500, 'max_hp': 500, 'stats': {'def': 100}}
        state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
        self.engine.enricher.enrich_state(state)
        
        # Mock Recoil return: [damage_dealt, text_desc]
        self._configure_mock('Double-Edge', damage=10, meta={'recoil': [33, 100]})
        
        # 10 damage -> 33% recoil = 3 damage. HP -> 197
        self.engine.execute_turn_action(state, 'player', 'Move: Double-Edge', 'ai', [])
        
        self.assertEqual(attacker['current_hp'], 197, f"Expected 197 HP (3 recoil), got {attacker['current_hp']}")

    def test_drain_absorb(self):
        """Test 5: Drain (Absorb 50%)"""
        attacker = {'species': 'Oddish', 'ability': 'Chlorophyll', 'item': '', 'types': ['Grass'], 'current_hp': 50, 'max_hp': 100, 'stats': {'spa': 100}}
        defender = {'species': 'Swampert', 'ability': 'Torrent', 'item': '', 'types': ['Water', 'Ground'], 'current_hp': 200, 'max_hp': 200, 'stats': {'spd': 100}}
        state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
        self.engine.enricher.enrich_state(state)
        
        self._configure_mock('Absorb', damage=10, meta={'drain': [50, 100]})
        
        # 10 damage -> 50% drain = 5 heal. HP 50 -> 55.
        self.engine.execute_turn_action(state, 'player', 'Move: Absorb', 'ai', [])
        
        self.assertEqual(attacker['current_hp'], 55, f"Expected 55 HP (5 heal), got {attacker['current_hp']}")

if __name__ == "__main__":
    unittest.main()
