
from pkh_app.battle_engine import BattleEngine, BattleState
import logging

def test_overhaul():
    class MockCalcClient:
        def __init__(self):
            self.calls = []
            self.last_move_data = {}

        def get_damage_rolls(self, att, def_, moves, field):
            call = {'att': att.copy(), 'def': def_.copy(), 'moves': moves}
            # Deep copy stats to be safe
            call['att']['stats'] = att.get('stats', {}).copy()
            call['def']['stats'] = def_.get('stats', {}).copy()
            self.calls.append(call)
            
            move_id = moves[0]
            move_data = self.last_move_data.get(move_id, {
                'moveName': move_id,
                'damage_rolls': [10],
                'critRatio': 1,
                'category': 'Physical',
                'type': 'Normal'
            })
            return [move_data]

    mock_calc = MockCalcClient()
    engine = BattleEngine(mock_calc)
    
    # helper for turn
    def run_turn(state, p_action, a_action):
        return engine.apply_turn(state, p_action, a_action)

    # Inject mock data into engine's rich_data for testing logic flags
    engine.rich_data['moves']['bodypress'] = {'name': 'Body Press', 'useSourceDef': True, 'category': 'Physical'}
    engine.rich_data['moves']['psystrike'] = {'name': 'Psystrike', 'useTargetDef': True, 'category': 'Special'}
    engine.rich_data['moves']['foulplay'] = {'name': 'Foul Play', 'useTargetAtk': True, 'category': 'Physical'}
    engine.rich_data['moves']['hyperbeam'] = {'name': 'Hyper Beam', 'flags': {'recharge': 1}, 'category': 'Special'}
    engine.rich_data['moves']['meanlook'] = {'name': 'Mean Look', 'category': 'Status'}
    engine.rich_data['moves']['bind'] = {'name': 'Bind', 'volatileStatus': 'partiallytrapped', 'category': 'Physical'}
    engine.rich_data['moves']['tackle'] = {'name': 'Tackle', 'category': 'Physical'}
    engine.rich_data['moves']['splash'] = {'name': 'Splash', 'category': 'Status'}

    print("--- Testing Stat Overrides ---")
    state = BattleState(
        player_active={'species': 'Pikachu', 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 10, 'def': 50}, 'types': ['Electric'], 'side': 'player', 'volatiles': []},
        ai_active={'species': 'Charmander', 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 80, 'def': 30, 'spd': 40}, 'types': ['Fire'], 'side': 'ai', 'volatiles': []},
        player_party=[],
        ai_party=[]
    )
    engine.enrich_state(state)

    # 1. Body Press (useSourceDef)
    mock_calc.last_move_data['Body Press'] = {
        'moveName': 'Body Press', 'damage_rolls': [10], 'critRatio': 1, 'category': 'Physical', 'type': 'Fighting',
        'useSourceDef': True
    }
    mock_calc.calls = []
    state, _ = run_turn(state, 'Move: Body Press', 'Move: Tackle')
    bp_call = next(c for c in mock_calc.calls if c['moves'][0] == 'Body Press')
    print(f"Body Press Atk (Expected 50): {bp_call['att']['stats']['atk']}")
    assert bp_call['att']['stats']['atk'] == 50

    # 2. Psystrike (useTargetDef)
    mock_calc.last_move_data['Psystrike'] = {
        'moveName': 'Psystrike', 'damage_rolls': [10], 'critRatio': 1, 'category': 'Special', 'type': 'Psychic',
        'useTargetDef': True
    }
    mock_calc.calls = []
    state, _ = run_turn(state, 'Move: Psystrike', 'Move: Tackle')
    ps_call = next(c for c in mock_calc.calls if c['moves'][0] == 'Psystrike')
    print(f"Psystrike Target SpD (Expected 30): {ps_call['def']['stats']['spd']}")
    assert ps_call['def']['stats']['spd'] == 30

    # 3. Foul Play (useTargetAtk)
    mock_calc.last_move_data['Foul Play'] = {
        'moveName': 'Foul Play', 'damage_rolls': [10], 'critRatio': 1, 'category': 'Physical', 'type': 'Dark',
        'useTargetAtk': True
    }
    mock_calc.calls = []
    state, _ = run_turn(state, 'Move: Foul Play', 'Move: Tackle')
    fp_call = next(c for c in mock_calc.calls if c['moves'][0] == 'Foul Play')
    print(f"Foul Play Atk (Expected 80): {fp_call['att']['stats']['atk']}")
    assert fp_call['att']['stats']['atk'] == 80

    print("--- Testing Recharge ---")
    mock_calc.last_move_data['Hyper Beam'] = {
        'moveName': 'Hyper Beam', 'damage_rolls': [10], 'critRatio': 1, 'category': 'Special', 'type': 'Normal',
        'flags': {'recharge': 1}
    }
    state.player_active['current_hp'] = 100
    state, log = run_turn(state, 'Move: Hyper Beam', 'Move: Splash')
    assert 'mustrecharge' in state.player_active['volatiles']
    
    state, log = run_turn(state, 'Move: Tackle', 'Move: Splash')
    print(f"Recharge log: {log}")
    assert any("must recharge" in line for line in log)
    assert 'mustrecharge' not in state.player_active['volatiles']

    print("--- Testing Trapping ---")
    # Mean Look Trap
    state = BattleState(
        player_active={'species': 'Pikachu', 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 10, 'def': 50}, 'types': ['Electric'], 'side': 'player', 'volatiles': []},
        ai_active={'species': 'Charmander', 'current_hp': 100, 'max_hp': 100, 'stats': {'atk': 80, 'def': 30, 'spd': 40}, 'types': ['Fire'], 'side': 'ai', 'volatiles': []},
        player_party=[{'species': 'Squirtle', 'species_id': 7, 'current_hp': 100, 'max_hp': 100}],
        ai_party=[]
    )
    engine.enrich_state(state)
    
    # Use Mean Look (AI uses it on Player)
    mock_calc.last_move_data['Mean Look'] = {
        'moveName': 'Mean Look', 'damage_rolls': [0], 'category': 'Status', 'type': 'Normal'
    }
    state, _ = run_turn(state, 'Move: Splash', 'Move: Mean Look')
    assert 'trapped' in state.player_active['volatiles']
    
    # Attempt switch
    state, log = run_turn(state, 'Switch: 7', 'Move: Splash')
    print(f"Trap Log: {log}")
    assert any("is trapped and can't switch" in line for line in log)
    assert state.player_active['species'] == 'Pikachu'

    print("--- Testing Partially Trapped ---")
    mock_calc.last_move_data['Bind'] = {
        'moveName': 'Bind', 'damage_rolls': [5], 'category': 'Physical', 'type': 'Normal',
        'volatileStatus': 'partiallytrapped'
    }
    state.player_active['volatiles'] = [] # Clear traps for clean test
    state, log = run_turn(state, 'Move: Splash', 'Move: Bind')
    print(f"Bind Turn Log: {log}")
    print(f"Player Volatiles: {state.player_active.get('volatiles')}")
    print(f"Player PT Turns: {state.player_active.get('partiallytrapped_turns')}")
    
    assert 'partiallytrapped' in state.player_active['volatiles']
    assert state.player_active['partiallytrapped_turns'] == 4 # Set to 5, then reduced to 4 by handle_end_of_turn
    
    # Turn End Damage
    pre_hp = state.player_active['current_hp']
    state, log = run_turn(state, 'Move: Splash', 'Move: Splash')
    print(f"Next Turn Log: {log}")
    post_hp = state.player_active['current_hp']
    print(f"Bind Damage: {pre_hp - post_hp}")
    assert pre_hp - post_hp > 0
    assert state.player_active['partiallytrapped_turns'] == 3

    print("ALL OVERHAUL TESTS PASSED")

if __name__ == "__main__":
    test_overhaul()
