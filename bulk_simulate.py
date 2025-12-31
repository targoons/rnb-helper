import random
import logging
import sys
import copy

from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.ai_scorer import AIScorer
from pkh_app.simulation import Simulation
from pkh_app.mechanics import Mechanics

# Configure logging to stay quiet for console, we will write to files manually
logging.basicConfig(level=logging.ERROR)

def generate_random_team(engine, size=6):
    """Generates a random team of Pokemon (Lvl 50, perfect IVs, neutral nature)."""
    team = []
    
    # Get all valid species keys from pokedex
    all_species = list(engine.pokedex.keys())
    
    # Get all valid moves from rich_data
    moves_data = getattr(engine, 'rich_data', {}).get('moves', {})
    valid_moves = []
    for k, v in moves_data.items():
         # Filter Max Moves and Z-Moves
         if not v.get('isMax') and not v.get('isZ'):
             valid_moves.append(v.get('name', k))
             
    if not valid_moves:
         valid_moves = ['Tackle', 'Growl', 'Pound', 'Scratch']

    for i in range(size):
        species_key = random.choice(all_species)
        dex_entry = engine.pokedex[species_key]
        name = dex_entry.get('name', species_key.title()).strip()
        types = dex_entry.get('types', ['Normal'])
        
        # Base Stats
        bs_raw = dex_entry.get('bs', {})
        base_stats = {
            'hp': bs_raw.get('hp', 50),
            'atk': bs_raw.get('at', 50),
            'def': bs_raw.get('df', 50),
            'spa': bs_raw.get('sa', 50),
            'spd': bs_raw.get('sd', 50),
            'spe': bs_raw.get('sp', 50)
        }
        
        level = 50
        iv = 31
        ev = 0
        
        # HP Calculation
        if 'Shedinja' in name:
             calc_hp = 1
        else:
             calc_hp = int((2 * base_stats['hp'] + iv + (ev//4)) * level / 100) + level + 10
        
        stats = {}
        for s in ['atk', 'def', 'spa', 'spd', 'spe']:
             base = base_stats[s]
             val = int( ((2 * base + iv + (ev//4)) * level / 100 + 5) * 1.0 )
             stats[s] = val
        stats['hp'] = calc_hp
        
        num_moves = 4
        my_moves = random.sample(valid_moves, min(len(valid_moves), num_moves))
        
        abilities_raw = dex_entry.get('abilities', [])
        ability = 'Pressure'
        if isinstance(abilities_raw, list) and abilities_raw:
             ability = random.choice(abilities_raw)
        elif isinstance(abilities_raw, dict):
             ability = random.choice(list(abilities_raw.values()))
            
        mon = {
            'species': name,
            'name': name,
            'level': level,
            'ability': ability,
            'nature': 'Hardy',
            'current_hp': calc_hp,
            'max_hp': calc_hp,
            'item': 'Oran Berry',
            'stats': stats,
            'stat_stages': {'atk':0,'def':0,'spa':0,'spd':0,'spe':0,'acc':0,'eva':0},
            'ivs': {'hp':iv, 'atk':iv, 'def':iv, 'spa':iv, 'spd':iv, 'spe':iv},
            'moves': my_moves,
            'types': types,
            'volatiles': []
        }
        team.append(mon)
        
    return team

def run_simulation(sim_id, engine, scorer):
    filename = f"sim_log_{sim_id}.txt"
    print(f"Starting Simulation {sim_id} -> {filename}")
    
    with open(filename, 'w') as f:
        def dual_print(*args, **kwargs):
            # Print to file only
            kwargs_file = kwargs.copy()
            kwargs_file['file'] = f
            print(*args, **kwargs_file)

        player_party = generate_random_team(engine)
        ai_party = generate_random_team(engine)

        dual_print(f"--- BATTLE {sim_id} START ---")
        dual_print(f"Player: {[m['species'] for m in player_party]}")
        dual_print(f"AI:     {[m['species'] for m in ai_party]}")
        
        state = BattleState(
            player_active=player_party[0], 
            ai_active=ai_party[0],      
            player_party=player_party,
            ai_party=ai_party,
            fields={'weather': None, 'terrain': None, 'hazards':{'player':[], 'ai':[]}, 'screens':{'player':{}, 'ai':{}}}
        )

        # Init logs
        init_log = []
        engine.apply_switch_in_abilities(state, 'player', state.player_active, init_log)
        engine.apply_switch_in_abilities(state, 'ai', state.ai_active, init_log)
        for line in init_log:
            dual_print(f"  {line}")

        turn = 1
        max_turns = 30 
        
        while turn <= max_turns:
            dual_print(f"\n=== Turn {turn} ===")
            
            # --- Detailed Logging via Engine Helper ---
            log_lines = engine.get_state_log_lines(state)
            for line in log_lines:
                 dual_print(line)
            # ------------------------------------------

            p_alive = any(m['current_hp'] > 0 for m in state.player_party)
            a_alive = any(m['current_hp'] > 0 for m in state.ai_party)
            if not p_alive:
                dual_print("AI WINS!")
                break
            if not a_alive:
                dual_print("PLAYER WINS!")
                break
                
            p_fainted = state.player_active['current_hp'] <= 0
            a_fainted = state.ai_active['current_hp'] <= 0

            if p_fainted or a_fainted:
                state, turn_log = engine.apply_turn(state, "Move: Struggle", "Move: Struggle") 
                
                clean_log = []
                if p_fainted:
                    for m in state.player_party:
                        if m['current_hp'] > 0:
                            state.player_active = m
                            clean_log.append(f"Player switched to {m['species']}!")
                            break
                if a_fainted:
                    for m in state.ai_party:
                        if m['current_hp'] > 0:
                            state.ai_active = m
                            clean_log.append(f"AI switched to {m['species']}!")
                            break
                            
                for l in clean_log: dual_print(l)
                p_alive = any(m['current_hp'] > 0 for m in state.player_party)
                a_alive = any(m['current_hp'] > 0 for m in state.ai_party)
                if not p_alive or not a_alive: continue
                continue

            # Random moves
            p_move_name = random.choice(state.player_active['moves'])
            a_move_name = random.choice(state.ai_active['moves'])
            
            dual_print(f"Player Choice: Move: {p_move_name} (Random)")
            dual_print(f"AI Choice: Move: {a_move_name} (Random)")
            
            state, turn_log = engine.apply_turn(state, f"Move: {p_move_name}", f"Move: {a_move_name}")
            for line in turn_log:
                dual_print(line)
            
            turn += 1

def main():
    engine = BattleEngine()
    scorer = AIScorer(engine)
    
    for i in range(1, 11):
        try:
            run_simulation(i, engine, scorer)
        except Exception as e:
            print(f"Simulation {i} Crashed: {e}")
            with open(f"sim_log_{i}.txt", 'a') as f:
                f.write(f"\nCRASH: {e}")

if __name__ == "__main__":
    main()
