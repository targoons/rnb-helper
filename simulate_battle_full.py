
import sys
import random
import copy
import logging
from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.ai_scorer import AIScorer
from pkh_app.simulation import Simulation
from pkh_app.mechanics import Mechanics

# Clear full_battle_log.txt on start
with open('full_battle_log.txt', 'w') as f:
    f.write("--- NEW SIMULATION START ---\n")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Global file handle for output
output_file = None

def dual_print(*args, **kwargs):
    """Print to both console and file."""
    # Remove 'file' from kwargs if present (we'll handle it ourselves)
    kwargs_console = kwargs.copy()
    kwargs_console.pop('file', None)
    
    # Print to console
    print(*args, **kwargs_console)
    
    # Print to file if open
    if output_file:
        kwargs_file = kwargs_console.copy()
        kwargs_file['file'] = output_file
        print(*args, **kwargs_file)

def create_party_with_engine(engine, is_player=True):
    # Helper to build dicts
    def make_mon(slot, name, species, ability, nature, hp_tuple, item, stats, ivs, moves):
        # Lookup types from BattleEngine Pokedex
        dex_entry = engine.pokedex.get(species.lower(), {})
        if not dex_entry:
             # Fallback if lookup fails (should not happen if pokedex is loaded)
             logging.warning(f"Species {species} not found in Pokedex!")
             types = ['Normal']
        else:
             types = dex_entry.get('types', ['Normal'])
             
        return {
            'species': species, 'name': name, 'level': 12, 'ability': ability, 'nature': nature,
            'current_hp': hp_tuple[0], 'max_hp': hp_tuple[1], 'item': item,
            'stats': {'hp':hp_tuple[1], 'atk':stats[0], 'def':stats[1], 'spa':stats[2], 'spd':stats[3], 'spe':stats[4]},
            'stat_stages': {'atk':0,'def':0,'spa':0,'spd':0,'spe':0,'acc':0,'eva':0},
            'ivs': {'hp':ivs[5], 'atk':ivs[0], 'def':ivs[1], 'spa':ivs[2], 'spd':ivs[3], 'spe':ivs[4]},
            'moves': moves,
            'types': types,
            'volatiles': []
        }
    
    p = []
    if is_player:
        # Player Team
         p.append(make_mon(1, 'Adams', 'Growlithe', 'Intimidate', 'Adamant', (38,38), 'Oran Berry', (26,18,21,19,21), (26,22,23,19,16,26), ['Flame Wheel', 'Bite', 'Covet', 'Odor Sleuth']))
         p.append(make_mon(2, 'Q.Adams', 'Rookidee', 'Keen Eye', 'Impish', (33,33), 'Oran Berry', (19,16,11,15,21), (28,19,2,14,20,18), ['Peck', 'Leer', 'Fury Attack', 'Sand Attack']))
         p.append(make_mon(3, 'Jefferson', 'Gossifleur', 'Cotton Down', 'Modest', (33,33), 'Oran Berry', (14,22,17,20,9), (12,22,18,10,21,16), ['Magical Leaf', 'Sing', 'Rapid Spin', 'Sweet Scent']))
         p.append(make_mon(4, 'Madison', 'Surskit', 'Swift Swim', 'Calm', (34,34), 'Oran Berry', (12,14,19,20,24), (16,17,19,15,30,26), ['Bubble', 'Quick Attack', 'Sweet Scent', 'Bubble Beam']))
         p.append(make_mon(5, 'Monroe', 'Zigzagoon', 'Gluttony', 'Docile', (33,33), 'Oran Berry', (15,18,12,17,20), (30,30,2,22,7,16), ['Tackle', 'Baby Doll Eyes', 'Rock Smash', 'Snarl']))
         # Zigzagoon might be Galarian in the Pokedex, we'll see what the engine returns. If standard Zigzagoon is Normal, fine.
         
         p.append(make_mon(6, 'Washington', 'Turtwig', 'Shell Armor', 'Adamant', (37,37), 'Oran Berry', (27,24,14,21,15), (31,31,6,31,29,21), ['Bite', 'Growl', 'Absorb', 'Confide']))
    else:
        # AI Team
        # 1. Machop (Fighting)
        p.append(make_mon(1, 'Champ', 'Machop', 'Guts', 'Adamant', (35,35), 'Oran Berry', (25,15,10,15,15), (31,31,31,31,31,31), ['Karate Chop', 'Leer', 'Focus Energy', 'Low Kick']))
        # 2. Geodude (Rock/Ground)
        p.append(make_mon(2, 'Rocky', 'Geodude', 'Sturdy', 'Impish', (30,30), 'Oran Berry', (22,30,10,10,10), (31,31,31,31,31,31), ['Tackle', 'Defense Curl', 'Rock Throw', 'Mud Sport']))
        # 3. Abra (Psychic)
        p.append(make_mon(3, 'Brainy', 'Abra', 'Synchronize', 'Timid', (25,25), 'Oran Berry', (10,10,30,15,30), (31,31,31,31,31,31), ['Teleport', 'Hidden Power', 'Flash', 'Charge Beam']))
        # 4. Gastly (Ghost)
        p.append(make_mon(4, 'Spook', 'Gastly', 'Levitate', 'Modest', (25,25), 'Oran Berry', (10,10,30,10,25), (31,31,31,31,31,31), ['Lick', 'Hypnosis', 'Mean Look', 'Spite']))
        # 5. Buizel (Water)
        p.append(make_mon(5, 'Jet', 'Buizel', 'Swift Swim', 'Jolly', (30,30), 'Oran Berry', (20,15,15,15,28), (31,31,31,31,31,31), ['Aqua Jet', 'Quick Attack', 'Growl', 'Water Gun']))
        # 6. Stunky (Dark/Poison)
        p.append(make_mon(6, 'Smelly', 'Stunky', 'Stench', 'Adamant', (35,35), 'Oran Berry', (22,18,10,18,20), (31,31,31,31,31,31), ['Scratch', 'Focus Energy', 'Poison Gas', 'Screech']))
    
    return p

def main():
    global output_file
    
    # Open output file
    output_file = open('battle_simulation_log.txt', 'w')
    
    dual_print("Initializing Battle Engine...")
    # calc = SimCalc() # Removed
    # BattleEngine automatically loads rich data from mechanics_rich.json AND pokedex_rich.json
    engine = BattleEngine() 
    
    scorer = AIScorer(engine)
    
    # Simulation (Beam Search) Agent
    simulation_agent = Simulation(engine, scorer)
    simulation_agent.max_depth = 4
    
    # Setup Teams using Engine Data
    player_party = create_party_with_engine(engine, is_player=True)
    ai_party = create_party_with_engine(engine, is_player=False)
    
    dual_print("\n--- BATTLE START ---")
    dual_print(f"Player Team ({len(player_party)}) vs AI Team ({len(ai_party)})")
    
    dual_print("\n=== TEAM PREVIEW ===")
    dual_print(f"{'PLAYER TEAM':<30} | {'AI TEAM':<30}")
    dual_print("-" * 65)
    for i in range(max(len(player_party), len(ai_party))):
        p_str = ""
        if i < len(player_party):
            p = player_party[i]
            p_str = f"{p['species']} (HP: {p['max_hp']})"
        
        a_str = ""
        if i < len(ai_party):
            a = ai_party[i]
            a_str = f"{a['species']} (HP: {a['max_hp']})"
            
        dual_print(f"{p_str:<30} | {a_str:<30}")
    dual_print("-" * 65)
    dual_print("\n")
    
    # Initial State
    state = BattleState(
        player_active=player_party[0], 
        ai_active=ai_party[0],      
        player_party=player_party,
        ai_party=ai_party,
        fields={'weather': None, 'terrain': None, 'hazards':{'player':[], 'ai':[]}, 'screens':{'player':{}, 'ai':{}}}
    )
    
    # Initial Entry Triggers
    init_log = []
    engine.apply_switch_in_abilities(state, 'player', state.player_active, init_log)
    engine.apply_switch_in_abilities(state, 'ai', state.ai_active, init_log)
    for line in init_log:
        dual_print(f"  {line}")

    turn = 1
    while True:
        dual_print(f"\n=== Turn {turn} ===")
        dual_print(f"Player Active: {state.player_active['name']} ({state.player_active['species']}) ({state.player_active['current_hp']}/{state.player_active['max_hp']})")
        dual_print(f"AI Active:     {state.ai_active['name']} ({state.ai_active['species']}) ({state.ai_active['current_hp']}/{state.ai_active['max_hp']})")
        
        # Win Check
        p_alive = any(m['current_hp'] > 0 for m in state.player_party)
        a_alive = any(m['current_hp'] > 0 for m in state.ai_party)
        if not p_alive:
            dual_print("AI WINS!")
            break
        if not a_alive:
            dual_print("PLAYER WINS!")
            break
            
        # Forced Switch Check
        p_fainted = state.player_active['current_hp'] <= 0
        a_fainted = state.ai_active['current_hp'] <= 0

        if p_fainted or a_fainted:
            player_action = None
            if p_fainted:
                for m in state.player_party:
                    if m['current_hp'] > 0:
                        player_action = f"Switch: {m['species']}"
                        break
            
            ai_action = None
            if a_fainted:
                for m in state.ai_party:
                    if m['current_hp'] > 0:
                        ai_action = f"Switch: {m['species']}"
                        break
            
            dual_print(f"Cleanup Action: P:{player_action} A:{ai_action}")
            state, turn_log = engine.apply_turn(state, player_action or "Move: Struggle", ai_action or "Move: Struggle")
            for line in turn_log:
                dual_print(line)
            turn += 1
            continue

        # 1. Player Decision (Random)
        dual_print(f"DEBUG: Turn={turn} Active={state.player_active['species']}")
        
        # Log Stats
        for side, mon in [('Player', state.player_active), ('AI', state.ai_active)]:
            stats = mon.get('stats', {})
            stages = mon.get('stat_stages', {})
            stat_str = []
            for s in ['atk', 'def', 'spa', 'spd', 'spe']:
                val = Mechanics.get_effective_stat(mon, s, state.fields)
                base = stats.get(s, 0)
                stage = stages.get(s, 0)
                stat_str.append(f"{s.upper()}:{val} ({base}{'+' if stage >= 0 else ''}{stage})")
            dual_print(f"  {side} Stats: {' '.join(stat_str)}")
            
            # Display status condition
            status = mon.get('status')
            if status:
                status_map = {
                    'par': 'PAR (Paralyzed)',
                    'psn': 'PSN (Poisoned)',
                    'tox': 'TOX (Badly Poisoned)',
                    'brn': 'BRN (Burned)',
                    'frz': 'FRZ (Frozen)',
                    'slp': 'SLP (Asleep)'
                }
                status_display = status_map.get(status, status.upper())
                dual_print(f"  {side} Status: {status_display}")
            
            # Display volatile status
            volatiles = mon.get('volatiles', [])
            volatile_info = []
            
            # Focus Energy / higher crit
            if 'focusenergy' in volatiles:
                volatile_info.append("FocusEnergy(+2crit)")
            
            # Confusion
            if 'confusion' in volatiles:
                confusion_turns = mon.get('confusion_turns', 0)
                volatile_info.append(f"Confused({confusion_turns}turns)")
            
            # Sleep counter
            if mon.get('status') == 'slp':
                sleep_turns = mon.get('status_counter', 0)
                volatile_info.append(f"Sleep({sleep_turns}turns)")
            
            # Substitute
            if 'substitute' in volatiles:
                sub_hp = mon.get('substitute_hp', 0)
                volatile_info.append(f"Substitute({sub_hp}HP)")
            
            # Leech Seed
            if 'leechseed' in volatiles:
                volatile_info.append("LeechSeed")
            
            # Curse (Ghost-type)
            if 'curse' in volatiles:
                volatile_info.append("Cursed")
            
            # Taunt
            if 'taunt' in volatiles:
                taunt_turns = mon.get('taunt_turns', 0)
                volatile_info.append(f"Taunted({taunt_turns}turns)")
            
            # Encore
            if 'encore' in volatiles:
                encore_turns = mon.get('encore_turns', 0)
                volatile_info.append(f"Encored({encore_turns}turns)")
            
            # Protection
            if any(v in volatiles for v in ['protect', 'detect', 'kingshield', 'banefulbunker']):
                protect_count = mon.get('protect_counter', 0)
                volatile_info.append(f"Protected(x{protect_count})")
            
            # Charged (for Charge move)
            if 'charge' in volatiles:
                volatile_info.append("Charged")
            
            # Other notable volatiles
            other_vols = [v for v in volatiles if v not in ['focusenergy', 'confusion', 'substitute', 
                         'leechseed', 'curse', 'taunt', 'encore', 'protect', 'detect', 'charge',
                         'kingshield', 'banefulbunker', 'flinch']]
            for v in other_vols:
                volatile_info.append(v.capitalize())
            
            if volatile_info:
                dual_print(f"  {side} Volatiles: {', '.join(volatile_info)}")
        
        # Random Player Action
        moves = state.player_active.get('moves', [])
        player_action = f"Move: {random.choice(moves)}"
        
        if turn == 1 and 'Leer' in moves:
            player_action = "Move: Leer"
            dual_print("DEBUG: Forced player_action to Leer")
        
        dual_print(f"Player Choice: {player_action} (Random)")
        
        # 2. AI Decision (Random)
        ai_moves = state.ai_active.get('moves', [])
        ai_action = f"Move: {random.choice(ai_moves)}"
        dual_print(f"AI Choice: {ai_action} (Random)")
        
        # 3. Apply Turn
        state, turn_log = engine.apply_turn(state, player_action, ai_action)
        for line in turn_log:
            dual_print(line)
        
        turn += 1
        if turn > 100:
             dual_print("Turn limit reached.")
             break
    
    # Print success message to both console and file before closing
    dual_print(f"\n✅ Battle log saved to: battle_simulation_log.txt")
    
    # Close output file
    if output_file:
        output_file.close()

if __name__ == "__main__":
    main()
