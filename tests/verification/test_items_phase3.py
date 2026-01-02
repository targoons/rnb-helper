"""
Phase 3 Item Tests: Utility, Accuracy, Duration
- Utility: White Herb, Eject Button, Red Card
- Accuracy: Wide Lens
"""
import sys
import os
import json
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkh_app.battle_engine import BattleEngine
from pkh_app.mechanics import Mechanics

# --- Helpers ---

def make_mon(species, types=None, stats=None, item='No Item', ability='No Ability', moves=None, hp=None, max_hp=None, spe=None, spa=None, spd=None, atk=None, def_stat=None, side='player'):
    if stats is None: stats = {}
    if moves is None: moves = ['Splash']
    if types is None: types = ['Normal']
    
    if spe is not None: stats['spe'] = spe
    if spa is not None: stats['spa'] = spa
    if spd is not None: stats['spd'] = spd
    if atk is not None: stats['atk'] = atk
    if def_stat is not None: stats['def'] = def_stat
    
    for s in ['hp', 'atk', 'def', 'spa', 'spd', 'spe']:
        if s not in stats: stats[s] = 100
        
    return {
        'species': species,
        'types': types,
        'item': item,
        'ability': ability,
        'moves': moves,
        'stats': stats,
        'stat_stages': {'atk':0, 'def':0, 'spa':0, 'spd':0, 'spe':0, 'acc':0, 'eva':0},
        'current_hp': hp if hp is not None else (max_hp if max_hp is not None else 100),
        'max_hp': max_hp if max_hp is not None else 100,
        'volatiles': [],
        'side': side
    }

def setup_engine():
    state = type('State', (), {'fields': {}, 'player_party': [], 'ai_party': [], 'get_hash': lambda: 0})()
    engine = BattleEngine(state)
    state.fields = {'weather': None, 'terrain': None, 'weather_turns': 0}
    state.last_moves = {}
    
    if not hasattr(engine, 'rich_data'):
        engine.rich_data = {'moves': {}, 'abilities': {}, 'items': {}}
        
    # Mock items
    items_to_add = {
        'White Herb': {'name': 'White Herb'},
        'Eject Button': {'name': 'Eject Button'},
        'Red Card': {'name': 'Red Card'},
        'Wide Lens': {'name': 'Wide Lens', 'onModifyAccuracy': 1.1},
        'Scope Lens': {'name': 'Scope Lens', 'critRatio': 1},
        'Light Clay': {'name': 'Light Clay'},
        'Heat Rock': {'name': 'Heat Rock'}
    }
    for name, data in items_to_add.items():
        engine.rich_data['items'][name] = data
        
    return engine, state

# --- Tests ---

def test_utility_items():
    print("\n=== Testing Utility Items ===")
    verified = []
    
    # 1. White Herb
    print("Testing White Herb...")
    try:
        engine, state = setup_engine()
        mon = make_mon('Celebi', item='White Herb', side='player')
        
        # Method: _apply_boosts(self, mon, boosts, log, source_name=None)
        log = []
        if hasattr(engine, '_apply_boosts'):
            engine._apply_boosts(mon, {'spa': -1}, log)
            
            # White Herb logic checks after drops
            if mon['stat_stages']['spa'] == 0:
                print("PASS: White Herb restored stats")
                verified.append('White Herb')
            else:
                print(f"FAIL: Stat is {mon['stat_stages']['spa']}")
        else:
             print("SKIP: _apply_boosts not found on engine instance")
             
    except Exception as e:
        print(f"ERROR White Herb: {e}")

    # 2. Eject Button
    print("Testing Eject Button...")
    try:
        engine, state = setup_engine()
        mon = make_mon('Amoonguss', item='Eject Button', side='player')
        
        log = []
        engine.execute_post_damage_reactions(
            state=state,
            attacker=make_mon('Attacker', side='ai'),
            defender=mon,
            damage_applied=10,
            move_data={'name': 'Tackle'},
            log=log
        )
        
        if mon.get('must_switch') is True and mon['item'] is None:
            print("PASS: Eject Button forced switch")
            verified.append('Eject Button')
        else:
            print(f"FAIL: Switch {mon.get('must_switch')}, Item {mon['item']}")
    except Exception as e:
        print(f"ERROR Eject Button: {e}")

    # 3. Red Card
    print("Testing Red Card...")
    try:
        engine, state = setup_engine()
        mon = make_mon('Shedinja', item='Red Card', side='player')
        attacker = make_mon('Attacker', side='ai')
        
        log = []
        engine.execute_post_damage_reactions(
            state=state,
            attacker=attacker,
            defender=mon,
            damage_applied=10,
            move_data={'name': 'Tackle'},
            log=log
        )
        
        if attacker.get('must_switch') is True and mon['item'] is None:
            print("PASS: Red Card forced attacker switch")
            verified.append('Red Card')
        else:
            print(f"FAIL: Attacker Switch {attacker.get('must_switch')}, Item {mon['item']}")
    except Exception as e:
        print(f"ERROR Red Card: {e}")
        
    return verified

def test_accuracy_crit():
    print("\n=== Testing Acc/Crit Items ===")
    verified = []
    
    # 1. Wide Lens
    print("Testing Wide Lens...")
    try:
        engine, state = setup_engine()
        mon = make_mon('Yanmega', item='Wide Lens', side='player')
        defender = make_mon('Dummy', side='ai')
        move = {'name': 'Hypnosis', 'accuracy': 91} 
        # 91 * 1.1 = 100.1 -> 100 (Always hit)
        
        hits = 0
        trials = 50
        for _ in range(trials):
            if Mechanics.check_accuracy(mon, defender, move, state.fields):
                hits += 1
                
        if hits == trials:
            print(f"PASS: Wide Lens resulted in {hits}/{trials} hits (100%)")
            verified.append('Wide Lens')
        else:
            print(f"FAIL: Hits {hits}/{trials}")
            
    except Exception as e:
        print(f"ERROR Wide Lens: {e}")
        
    return verified

def run_phase3_tests():
    all_verified = []
    all_verified.extend(test_utility_items())
    all_verified.extend(test_accuracy_crit())
    
    if all_verified:
        try:
            from test_bulk_items import update_audit_csv
            update_audit_csv(all_verified)
        except ImportError:
            pass

if __name__ == "__main__":
    run_phase3_tests()
