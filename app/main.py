import time
import os
import json
import sys

# Ensure root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from app.state_parser import parse_state
from app.ai_logic import MoveScorer, SwitchPredictor
from app import calc_client

STATE_FILE = os.path.join(BASE_DIR, "data", "battle_state.json")
PRED_FILE = os.path.join(BASE_DIR, "data", "predictions.txt")
MOVES_FILE = os.path.join(BASE_DIR, "data", "moves.json")
SPECIES_FILE = os.path.join(BASE_DIR, "data", "species.json")

def load_json(path):
    try:
        print(f"Loading {path}...")
        with open(path, 'r') as f:
            data = json.load(f)
            print(f"Loaded {len(data)} entries from {path}")
            return data
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return {}

MOVE_NAMES = load_json(MOVES_FILE)
SPECIES_NAMES = load_json(SPECIES_FILE)

def get_move_name(move_id):
    key = str(move_id)
    val = MOVE_NAMES.get(key)
    if not val:
        return key
    return val

def get_species_name(species_id):
    return SPECIES_NAMES.get(str(species_id), str(species_id))

def normalize_mon(mon):
    if not mon: return {}
    new_mon = mon.copy()
    if 'species_id' in mon: 
        s_id = mon['species_id']
        name = get_species_name(s_id)
        new_mon['name'] = name
        new_mon['species'] = name 
    return new_mon

def write_predictions(scored_moves, best_switch, player_active, ai_active, player_calcs, ai_calcs):
    lines = []
    
    # --- Battle Info ---
    lines.append(f"[PREDICTIONS] {time.strftime('%H:%M:%S')}")
    
    p_name = player_active.get('name', 'Player')
    a_name = ai_active.get('name', 'AI')
    
    lines.append(f"[BATTLE] {p_name} vs {a_name}")
    
    # Speed Info
    def get_eff_speed(mon):
        base = mon.get('stats', {}).get('spe', 0)
        stage = mon.get('stat_stages', {}).get('spe', 6) - 6
        multipliers = {
            -6: 2/8, -5: 2/7, -4: 2/6, -3: 2/5, -2: 2/4, -1: 2/3,
            0: 1.0,
            1: 1.5, 2: 2.0, 3: 2.5, 4: 3.0, 5: 3.5, 6: 4.0
        }
        return int(base * multipliers.get(stage, 1.0))
        
    p_spe = get_eff_speed(player_active)
    a_spe = get_eff_speed(ai_active)
    speed_text = f"Speed: {p_spe} vs {a_spe}"
    if p_spe > a_spe: speed_text += " (PLAYER FASTER)"
    elif a_spe > p_spe: speed_text += " (AI FASTER)"
    lines.append(speed_text)
    lines.append("")

    # --- Player Moves ---
    lines.append("\n[PLAYER DAMAGE]")
    ai_max_hp = ai_active.get('max_hp', 1)
    if player_calcs:
        for c in player_calcs:
            m_name = c.get('moveName') or get_move_name(c.get('move'))
            rolls = c.get('damage_rolls', [0])
            min_d, max_d = min(rolls), max(rolls)
            min_p = (min_d / ai_max_hp) * 100
            max_p = (max_d / ai_max_hp) * 100
            lines.append(f"  {m_name:15}: {min_p:4.1f}-{max_p:4.1f}%")
    else:
        lines.append("  No damage data")

    # --- AI Reasoning ---
    lines.append("\n[AI PREDICTION]")
    if scored_moves:
        sorted_moves = sorted(scored_moves, key=lambda x: x['scores']['standard'], reverse=True)
        player_max_hp = player_active.get('max_hp', 1)
        for m in sorted_moves[:5]:
            name = m.get('name') or get_move_name(m['move'])
            score = m['scores']['standard']
            
            dmg = m.get('damage_info', {})
            min_d = dmg.get('min', 0)
            max_d = dmg.get('max', 0)
            min_p = (min_d / player_max_hp) * 100
            max_p = (max_d / player_max_hp) * 100
            
            lines.append(f"  {name:15}: score {score:4} | {min_p:4.1f}-{max_p:4.1f}%")
            
    if best_switch:
         sid = best_switch.get('species_id', best_switch.get('speciesId'))
         lines.append(f"  LIKELY SWITCH: {get_species_name(sid)}")

    # Note: Strategy Advisor hint
    lines.append("\n[TIP] Run 'python3 tools/run_sim.py' for deep turn simulation.")

    content = "\n".join(lines)
    try:
        with open(PRED_FILE, 'w') as f:
            f.write(content)
    except Exception as e:
        print(f"Error writing: {e}")

def main():
    print("Pokemon Run and Bun Helper (Real-time Watcher) started.")
    print(f"Monitoring {STATE_FILE}...")
    
    last_mtime = 0
    last_state = None
    client = calc_client
    legacy_scorer = MoveScorer()
    switch_predictor = SwitchPredictor()
    
    while True:
        try:
            if os.path.exists(STATE_FILE):
                mtime = os.path.getmtime(STATE_FILE)
                if mtime > last_mtime:
                    last_mtime = mtime
                    time.sleep(0.05)
                    
                    battle_state_dict = parse_state(STATE_FILE)
                    if not battle_state_dict: continue

                    # Check if relevant state actually changed
                    if battle_state_dict == last_state:
                        continue
                    
                    last_state = battle_state_dict
                    print(f"State Updated: {time.strftime('%H:%M:%S')}")
                        
                    player_active = normalize_mon(battle_state_dict.get('player_side', {}).get('active', {}))
                    ai_active = normalize_mon(battle_state_dict.get('opponent_side', {}).get('active', {}))
                    
                    a_side = battle_state_dict.get('opponent_side', {})
                    a_party = [normalize_mon(m) for m in a_side.get('party', [])]

                    # Perform quick calc for immediate feedback
                    ai_moves = ai_active.get('moves', [])
                    player_moves = player_active.get('moves', [])
                    
                    try:
                         ai_calcs = client.get_damage_rolls(ai_active, player_active, ai_moves, {})
                    except: ai_calcs = []
                    
                    try:
                         player_calcs = client.get_damage_rolls(player_active, ai_active, player_moves, {})
                    except: player_calcs = []
                    
                    scored_moves = legacy_scorer.score_moves(ai_active, player_active, ai_calcs, [])
                    
                    best_switch = None
                    if ai_active.get('current_hp', 0) <= 0:
                         best_switch, _ = switch_predictor.predict_switch(a_party, player_active, client)
                         
                    write_predictions(scored_moves, best_switch, player_active, ai_active, player_calcs, ai_calcs)
                    
            time.sleep(0.2)
            
        except KeyboardInterrupt:
            print("Stopping...")
            break
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
