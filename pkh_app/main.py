import time
import os
import json
import sys

# Ensure root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from pkh_app.state_parser import parse_state
from pkh_app.ai_logic import SwitchPredictor
from pkh_app.ai_scorer import AIScorer
from pkh_app.battle_engine import BattleState
from pkh_app import calc_client

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

    return new_mon

def normalize_mon(mon):
    if not mon: return {}
    new_mon = mon.copy()
    if 'species_id' in mon: 
        s_id = mon['species_id']
        name = get_species_name(s_id)
        new_mon['name'] = name
        new_mon['species'] = name 
    return new_mon

def patch_active_from_party(active, party):
    if not active or not party: return active
    for p_mon in party:
        if p_mon.get('species_id') == active.get('species_id'):
            # Sync item (Party data is more reliable than shifted battle memory)
            p_item = p_mon.get('item')
            if p_item:
                active['item'] = p_item
            
            # Sync nature
            p_nature = p_mon.get('nature')
            if p_nature:
                active['nature'] = p_nature

            # Sync ability
            p_ability = p_mon.get('ability')
            if p_ability:
                active['ability'] = p_ability
            
            # Sync IVs
            if p_mon.get('ivs'):
                active['ivs'] = p_mon['ivs']
            break
    return active

def write_predictions(scored_moves, best_switch, player_active, ai_active, player_calcs, ai_calcs):
    lines = []
    
    # --- Battle Info ---
    lines.append(f"[AI ANALYSIS] {time.strftime('%H:%M:%S')}")
    
    p_name = player_active.get('name', 'Player')
    a_name = ai_active.get('name', 'AI')
    
    lines.append(f"[BATTLE] {p_name} vs {a_name}")
    
    def format_mon_status(mon, name):
        curr = mon.get('current_hp', 0)
        mhp = mon.get('max_hp', 0)
        
        # Stats
        stages = mon.get('stat_stages', {})
        stat_strs = []
        for stat, raw_stage in stages.items():
            # Internal stages are 0-12, with 6 being neutral.
            stage = raw_stage - 6
            if stage != 0:
                sign = "+" if stage > 0 else ""
                stat_strs.append(f"{stat.capitalize()}{sign}{stage}")
        
        stat_info = f" ({', '.join(stat_strs)})" if stat_strs else ""
        return f"{name}: {curr}/{mhp} HP{stat_info}"

    lines.append(format_mon_status(player_active, p_name))
    lines.append(format_mon_status(ai_active, a_name))
    
    # Speed Info
    def get_eff_speed(mon):
        base = mon.get('stats', {}).get('spe', 0)
        stage = mon.get('stat_stages', {}).get('spe', 6) - 6
        multipliers = {
            -6: 2/8, -5: 2/7, -4: 2/6, -3: 2/5, -2: 2/4, -1: 2/3,
            0: 1.0,
            1: 1.5, 2: 2.0, 3: 2.5, 4: 3.0, 5: 3.5, 6: 4.0
        }
        val = base * multipliers.get(stage, 1.0)
        
        # Item Multipliers
        item = mon.get('item', '')
        if item == 'Iron Ball' or item == 'Macho Brace' or 'Power' in str(item):
            val *= 0.5
        elif item == 'Choice Scarf':
            val *= 1.5
            
        return int(val)
        
    p_spe = get_eff_speed(player_active)
    a_spe = get_eff_speed(ai_active)
    speed_text = f"Speed: {p_spe} vs {a_spe}"
    if p_spe > a_spe: speed_text += " (PLAYER FASTER)"
    elif a_spe > p_spe: speed_text += " (AI FASTER)"
    lines.append(speed_text)
    lines.append("")

    # --- Player Moves ---
    # --- Player Moves ---
    lines.append("\n[PLAYER DAMAGE]")
    ai_max_hp = ai_active.get('max_hp', 1)
    
    if player_calcs:
        try:
            for c in player_calcs:
                m_name = c.get('moveName') or get_move_name(c.get('move'))
                rolls = c.get('damage_rolls', [0])
                desc = c.get('desc', '')
                
                # Extract KO info (e.g. "guaranteed 2HKO")
                ko_info = ""
                if '--' in desc:
                    parts = desc.split('--')
                    if len(parts) > 1:
                        ko_info = parts[1].strip()
                
                if not rolls:
                    lines.append(f"  {m_name:15}: -- (No rolls)")
                    continue
                    
                min_d, max_d = min(rolls), max(rolls)
                min_p = (min_d / ai_max_hp) * 100
                max_p = (max_d / ai_max_hp) * 100
                
                line = f"  {m_name:15}: {min_p:4.1f}-{max_p:4.1f}% ({min_d}-{max_d})"
                if ko_info:
                    line += f"  {ko_info}"
                lines.append(line)
        except Exception as e:
            lines.append(f"  Error calculating damage: {e}")
    else:
        lines.append("  No damage data available")

    # --- AI Reasoning ---
    lines.append("\n[AI PREDICTION]")
    if scored_moves:
        player_max_hp = player_active.get('max_hp', 1)
        
        # AIScorer returns dict with 'moves', 'matrix', 'results', 'variant_weights'
        move_names = scored_moves['moves']
        matrix = scored_moves['matrix']
        weights = scored_moves['variant_weights']
        results = scored_moves['results']
        
        display_list = []
        
        num_moves = len(move_names)
        move_probs = [0.0] * num_moves
        move_avg_scores = [0.0] * num_moves
        
        move_probs = [0.0] * num_moves
        move_score_dists = [{} for _ in range(num_moves)]
        
        # 1. Analyze Scores & Calculate Selection Probability
        for r_idx in range(16):
            for v_idx in range(5):
                weight = weights[v_idx] * (1/16)
                
                # Get all scores for this world
                scores_in_world = []
                for m_idx in range(num_moves):
                    s = matrix[r_idx * 5 + v_idx][m_idx]
                    scores_in_world.append(s)
                    
                    # Track score distribution
                    s_rnd = round(s, 1)
                    move_score_dists[m_idx][s_rnd] = move_score_dists[m_idx].get(s_rnd, 0.0) + weight

                # Find max score (Winner)
                max_s = max(scores_in_world)
                
                # Identify winners and distribute probability
                winners = [i for i, s in enumerate(scores_in_world) if s == max_s]
                prob_share = weight / len(winners)
                for w_idx in winners:
                    move_probs[w_idx] += prob_share

        display_list = []
        for m_idx in range(num_moves):
            prob_pct = move_probs[m_idx] * 100
            
            # Format Score Distribution String
            dist_list = sorted(move_score_dists[m_idx].items(), key=lambda x: x[0])
            dist_strs = []
            for s, w in dist_list:
                if w >= 0.01: # Filter tiny negligible weights
                    dist_strs.append(f"{s}({w*100:.0f}%)")
            score_str = ", ".join(dist_strs)
            
            # Get Min/Max Damage from result
            res = results[m_idx]
            rolls = res.get('damage_rolls', [0])
            if not rolls: rolls = [0]
            min_d, max_d = min(rolls), max(rolls)
            
            # Get Crit
            crit_rolls = res.get('crit_rolls', [0])
            if not crit_rolls: crit_rolls = [0]
            min_cd, max_cd = min(crit_rolls), max(crit_rolls)
            
            min_p = (min_d / player_max_hp) * 100
            max_p = (max_d / player_max_hp) * 100
            min_cp = (min_cd / player_max_hp) * 100
            max_cp = (max_cd / player_max_hp) * 100
            
            # Extract KO info
            desc = res.get('desc', '')
            ko_info = ""
            if '--' in desc:
                parts = desc.split('--')
                if len(parts) > 1:
                    ko_info = parts[1].strip()
            
            display_list.append({
                'name': move_names[m_idx],
                'score_str': score_str,
                'prob': prob_pct,
                'min_p': min_p,
                'max_p': max_p,
                'min_d': min_d,
                'max_d': max_d,
                'min_cp': min_cp,
                'max_cp': max_cp,
                'min_cd': min_cd,
                'max_cd': max_cd,
                'ko_info': ko_info
            })
            
        # Sort by Probability
        display_list.sort(key=lambda x: x['prob'], reverse=True)
            
        for item in display_list[:5]:
            # Format: "Move : Score(Prob) -> Sel: % | Dmg% (Dmg) KO [Crit: Dmg% (Dmg)]"
            ko_str = f" {item['ko_info']}" if item['ko_info'] else ""
            lines.append(f"  {item['name']:15}: {item['score_str']:20} -> Sel: {item['prob']:3.0f}% | {item['min_p']:4.1f}-{item['max_p']:4.1f}% ({item['min_d']}-{item['max_d']}){ko_str} [Crit: {item['min_cp']:4.1f}-{item['max_cp']:4.1f}% ({item['min_cd']}-{item['max_cd']})]")
            
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
    client = calc_client
    scorer = AIScorer(client)
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
                    
                    p_side = battle_state_dict.get('player_side', {})
                    p_party = [normalize_mon(m) for m in p_side.get('party', [])]
                    a_side = battle_state_dict.get('opponent_side', {})
                    a_party = [normalize_mon(m) for m in a_side.get('party', [])]

                    # Apply Party Patch
                    player_active = patch_active_from_party(player_active, p_party)
                    ai_active = patch_active_from_party(ai_active, a_party)

                    # Perform quick calc for immediate feedback
                    ai_moves = ai_active.get('moves', [])
                    player_moves = player_active.get('moves', [])
                    
                    try:
                         ai_calcs = client.get_damage_rolls(ai_active, player_active, ai_moves, {})
                    except: ai_calcs = []
                    
                    try:
                         player_calcs = client.get_damage_rolls(player_active, ai_active, player_moves, {})
                    except: player_calcs = []
                    
                    try:
                         player_calcs = client.get_damage_rolls(player_active, ai_active, player_moves, {})
                    except: player_calcs = []
                    
                    # Create BattleState for AIScorer
                    p_party_list = [normalize_mon(m) for m in battle_state_dict.get('player_side', {}).get('party', [])]
                    a_party_list = [normalize_mon(m) for m in battle_state_dict.get('opponent_side', {}).get('party', [])]
                    
                    bs = BattleState(
                        player_active=player_active,
                        ai_active=ai_active,
                        player_party=p_party_list,
                        ai_party=a_party_list,
                        last_moves=battle_state_dict.get('last_moves', {}),
                        fields=battle_state_dict.get('fields', {})
                    )
                    
                    scored_moves = scorer.score_moves(bs, 'ai')
                    
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
