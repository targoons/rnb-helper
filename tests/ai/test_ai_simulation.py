
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.mechanics import Mechanics
from pkh_app.simulation import Simulation
from pkh_app.ai_scorer import AIScorer
from tests.test_utils import create_mocked_engine

class MockCalcClient:
    def calc_damage(self, attacker, defender, move, field):
        # Calc Damage for single move
        m = move
        rolls = [10] # Default weak damage
        meta = {}
        
        if m == "StrongMove": rolls = [100]
        if m == "WeakMove": rolls = [10]
        if m == "RecoilMove": 
            rolls = [50]
            meta = {'recoil': [50, 100]}
        if m == "DrainMove":
            rolls = [50]
            meta = {'drain': [50, 100]}
        if m == "StatusMove":
            rolls = [0]
            meta = {'category': 'Status'}
        if m == "PriorityMove":
            rolls = [20]
            meta = {'priority': 1}
            
        res = {
            'moveName': m,
            'move': m,
            'damage_rolls': rolls,
            'category': meta.get('category', 'Physical'),
            'priority': meta.get('priority', 0)
        }
        res.update(meta)
        return res

class TestBattleSimulator(unittest.TestCase):
    def setUp(self):
        self.engine = create_mocked_engine()
        self.client = MockCalcClient()
        self.engine.calc_client = self.client # Override with specific test mock
        self.engine.damage_calculator.calc_client = self.client # Ensure calculator uses it too
        
        # Inject Custom Moves into Rich Data
        moves = {
            'StrongMove': {'id': 'strongmove', 'basePower': 100, 'type': 'Fighting', 'category': 'Physical'},
            'WeakMove': {'id': 'weakmove', 'basePower': 40, 'type': 'Normal', 'category': 'Physical'},
            'RecoilMove': {'id': 'recoilmove', 'basePower': 50, 'type': 'Normal', 'category': 'Physical', 'recoil': [50, 'damage']},
            'StatusMove': {'id': 'statusmove', 'basePower': 0, 'type': 'Normal', 'category': 'Status'},
            'PriorityMove': {'id': 'prioritymove', 'basePower': 40, 'type': 'Normal', 'category': 'Physical', 'priority': 1},
            'DrainMove': {'id': 'drainmove', 'basePower': 50, 'type': 'Grass', 'category': 'Special', 'drain': [50, 'damage']}
        }
        
        for name, data in moves.items():
            mid = name.lower()
            self.engine.rich_data['moves'][mid] = data
            self.engine.rich_data['moves'][mid]['name'] = name
            self.engine.move_names[name] = name

        self.scorer = AIScorer(self.client)
        self.sim = Simulation(self.engine, self.scorer)
        
        # Base State
        self.p_active = {'species': 'Hero', 'current_hp': 100, 'max_hp': 100, 'moves': ['StrongMove', 'WeakMove'], 'stats': {'spe': 100}}
        self.a_active = {'species': 'Villain', 'current_hp': 100, 'max_hp': 100, 'moves': ['StrongMove', 'WeakMove'], 'stats': {'spe': 90}} # Slower
        
        self.state = BattleState(
            player_active=self.p_active,
            ai_active=self.a_active,
            player_party=[self.p_active],
            ai_party=[self.a_active]
        )

    def test_01_speed_order(self):
        """Scenario 01: Speed Tie / Faster moves first"""
        # Hero (100) vs Villain (90). Hero should move first.
        # Action: Both use 'StrongMove' (100 dmg).
        # Expected: Hero moves, deals 100. Villain dies (0 HP) and CANNOT move.
        
        s, log = self.engine.apply_turn(self.state, "Move: StrongMove", "Move: StrongMove")
        
        self.assertEqual(s.ai_active['current_hp'], 0)
        self.assertEqual(s.player_active['current_hp'], 100) # Took no damage because Villain died
        self.assertIn("Hero used StrongMove", log[0])
        # Villain move shouldn't appear or should fail? Engine implementation:
        # "if not self.is_fainted(new_state, second[0]):" -> Correct.
        self.assertEqual(len([l for l in log if "Villain used" in l]), 0)

    def test_05_recoil(self):
        """Scenario 05: Recoil Damage"""
        # Hero uses RecoilMove (50 dmg, 50% recoil -> 25 dmg to self)
        s, log = self.engine.apply_turn(self.state, "Move: RecoilMove", "Move: StatusMove")
        
        self.assertEqual(s.ai_active['current_hp'], 50) # 100 - 50
        self.assertEqual(s.player_active['current_hp'], 75) # 100 - 25
        self.assertTrue(any("took recoil damage" in line and "25" in line for line in log))

    def test_12_switch_logic(self):
        """Scenario 12: Forced Switch or Voluntary Switch"""
        # Test Voluntary Switch
        active = self.state.player_active
        bench = {'species': 'BenchMon', 'current_hp': 100, 'max_hp': 100}
        self.state.player_party.append(bench)
        
        s, log = self.engine.apply_turn(self.state, "Switch: BenchMon", "Move: WeakMove")
        
        self.assertEqual(s.player_active['species'], 'BenchMon')
        self.assertIn("[PLAYER] switched to BenchMon", log[0]) # Priority
        self.assertIn("Villain used WeakMove", log[1]) # Villain hits new mon
        self.assertEqual(s.player_active['current_hp'], 90) # 100 - 10

if __name__ == '__main__':
    unittest.main()
