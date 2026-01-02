
import pytest
from pkh_app.battle_engine import BattleEngine

def setup_engine():
    # Mock Mechanics
    class MockCalc:
        def get_damage_rolls(self, *args, **kwargs):
            return [{'damage': [10], 'flags': {}}]

    engine = BattleEngine(MockCalc())
    # Mock get_mechanic to return basic move data
    engine._get_mechanic = lambda name, type: {
        'name': name, 'accuracy': 100, 'category': 'Physical', 'target': 'normal', 
        'flags': {}, 'secondary': None, 'basePower': 75, 'type': 'Fighting'
    }
    return engine

def setup_state_with_screens():
    state = type('State', (), {})()
    
    # Initialize fields with screens present on AI side
    state.fields = {
        'weather': None, 'terrain': None, 'pseudoweathers': {}, 
        'screens': {
            'player': {'reflect': 0, 'light_screen': 0, 'aurora_veil': 0}, 
            'ai': {'reflect': 5, 'light_screen': 5, 'aurora_veil': 0}
        }, 
        'protected_sides': [],
        'last_move_used_this_turn': None, 'trick_room': 0, 'gravity': 0, 'magic_room': 0, 'wonder_room': 0,
        'hazards': {'player': [], 'ai': []}, 'weather_turns': 0, 'terrain_turns': 0, 'tailwind': {'player': 0, 'ai': 0}
    }
    state.last_moves = {'player': None, 'ai': None}
    
    # Active Mons
    state.player_active = {'species': 'Charizard', 'side': 'player', 'current_hp': 100, 'max_hp': 100, 'moves': [], 'volatiles': [], 'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100}, 'stat_stages': {'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0, 'acc': 0, 'eva': 0}}
    state.ai_active = {'species': 'Blastoise', 'side': 'ai', 'current_hp': 100, 'max_hp': 100, 'moves': [], 'volatiles': [], 'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100}, 'stat_stages': {'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0, 'acc': 0, 'eva': 0}}
    state.player_party = [state.player_active]
    state.ai_party = [state.ai_active]
    state.log = []
    
    # Deep copy mock
    state.deep_copy = lambda: state
    
    return state

def test_brick_break_shatters_screens():
    engine = setup_engine()
    state = setup_state_with_screens()
    
    # Verify setup
    assert 'reflect' in state.fields['screens']['ai']
    assert 'light_screen' in state.fields['screens']['ai']
    
    # Execute Brick Break (Player -> AI)
    # Brick Break removes screens from default target (AI)
    engine.execute_turn_action(state, 'player', "Move: Brick Break", 'ai', state.log)
    
    # Assert screens are gone from AI side
    assert 'reflect' not in state.fields['screens']['ai']
    assert 'light_screen' not in state.fields['screens']['ai']
    found_shatter = any("Blastoise's Reflect shattered!" in line for line in state.log) or \
                    any("Blastoise's Light Screen shattered!" in line for line in state.log) or \
                    any("The screens were shattered!" in line for line in state.log)
    assert found_shatter, f"Log did not contain shatter message. Log: {state.log}"

def test_psychic_fangs_shatters_screens():
    engine = setup_engine()
    state = setup_state_with_screens()
    
    # Verify setup
    assert 'reflect' in state.fields['screens']['ai']
    
    # Execute Psychic Fangs
    engine.execute_turn_action(state, 'player', "Move: Psychic Fangs", 'ai', state.log)
    
    # Assert screens are gone
    assert 'reflect' not in state.fields['screens']['ai']
    assert 'light_screen' not in state.fields['screens']['ai']
