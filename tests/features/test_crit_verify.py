
from pkh_app.battle_engine import BattleEngine, BattleState
import logging

def test_crit_logic():
    # Setup mock state
    state = BattleState(
        player_active={'player': 'Pikachu'},
        ai_active={'ai': 'Charmander'},
        player_party=[],
        ai_party=[]
    )
    
    # Mock Calc Client response to avoid real API call issues for unit test
    class MockCalcClient:
        def get_damage_rolls(self, att, def_, moves, field):
            # Return dummy result with critRatio=1 (normal)
            return [{
                'moveName': moves[0],
                'damage_rolls': [100],
                'crit_rolls': [200], # 2x damage on crit
                'critRatio': 1,
                'category': 'Physical',
                'type': 'Normal'
            }]
            
    mock_calc = MockCalcClient()
    engine = BattleEngine(mock_calc)
    
    # helper to run calc
    def run_calc(attacker_volatiles=[]):
        attacker = {
            'species': 'Pikachu', 
            'current_hp': 100, 
            'max_hp': 100, 
            'stats': {'atk': 100},
            'volatiles': attacker_volatiles,
            'item': None,
            'ability': 'Static',
            '_rich_ability': {},
            'side': 'player'
        }
        defender = {
            'species': 'Charmander', 
            'current_hp': 100, 
            'max_hp': 100, 
            'stats': {'def': 100},
            'side': 'ai'
        }
        state.player_active = attacker
        state.ai_active = defender
        
        log = []
        move_name = 'Tackle'
        action = f"Move: {move_name}"
        # attacker_side based on side
        att_side = attacker['side']
        def_side = defender['side']
        engine.execute_turn_action(state, att_side, action, def_side, log)
        return log

    # Test 1: Normal Crit rate (Stage 0 -> 1/24 ~4%)
    # Run 1000 times
    crits = 0
    for _ in range(1000):
        log = run_calc()
        if any("Critical hit!" in line for line in log):
             crits += 1
             
    print(f"Stage 0 Crits (Expected ~41): {crits}")
    
    # Test 2: Focus Energy (Stage 2 -> 50%)
    crits_focus = 0
    for _ in range(1000):
        log = run_calc(['focusenergy'])
        if any("Critical hit!" in line for line in log):
             crits_focus += 1
             
    print(f"Stage 2 Crits (Expected ~500): {crits_focus}")

    # Assertions
    # Allow variance
    assert 20 < crits < 70, "Stage 0 crit rate aberrant"
    assert 450 < crits_focus < 550, "Stage 2 crit rate aberrant"
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_crit_logic()
