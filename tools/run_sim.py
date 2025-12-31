import os
import sys
import json
import argparse
import re
import math

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from pkh_app.strategy_advisor import StrategyAdvisor
from pkh_app.state_parser import parse_state

def main():
    parser = argparse.ArgumentParser(description="Run Pokemon Battle Simulation on a state file.")
    parser.add_argument("file", help="Path to the battle_state.json file")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        return

    # Load metadata for names
    moves_path = os.path.join(BASE_DIR, "data", "moves.json")
    species_path = os.path.join(BASE_DIR, "data", "species.json")
    
    def load_json(path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    move_names = load_json(moves_path)
    species_names = load_json(species_path)

    print(f"Analyzing state: {args.file}...")
    states_data = parse_state(args.file)
    if not states_data:
        print("Error: Could not parse state file.")
        return

    # Handle single state or list of states
    if isinstance(states_data, dict) and 'player_side' in states_data:
        test_cases = [{"name": "Single State", "state": states_data}]
    elif isinstance(states_data, list):
        test_cases = states_data
    else:
        # Assume it's a single state with top-level player_active etc?
        # Better to just wrap it.
        test_cases = [{"name": "Legacy State", "state": states_data}]

    advisor = StrategyAdvisor(species_names, move_names)
    
    for case in test_cases:
        name = case.get('name', 'Unnamed Test')
        state_dict = case.get('state', case)
        
        print(f"\n>>> RUNNING TEST: {name}")
        print("Running Simulation (Iterative Deepening, Max Depth 20)...")
        
        try:
            result = advisor.run_simulation(state_dict)
        except Exception as e:
            import traceback
            traceback.print_exc()
            result = {"error": str(e)}

        if "error" in result:
            print(f"Simulation Error: {result['error']}")
            continue
        def format_action(act):
            if not act: return "None"
            if act.startswith("Move: "):
                m_id = act.split(": ")[1]
                return f"Move: {move_names.get(str(m_id), m_id)}"
            if act.startswith("Switch: "):
                s_id = act.split(": ")[1]
                return f"Switch: {species_names.get(str(s_id), s_id)}"
            return act

        best = result.get('best_action', 'None')
        paths = result.get('paths', {})
        depth = result.get('final_depth', 0)
        status = result.get('status', 'Unknown')

        print("\n" + "="*30)
        print("      STRATEGY ADVISOR")
        print("="*30)
        print(f"DEPTH REACHED : {depth} turns ({status})")
        print(f"RECOMMENDATION: {format_action(best)}")
        print("-" * 30)
        print("Analysis (Higher is better):")
        scores = result.get('scores', {})
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        for act, score in sorted_scores:
            marker = ">>" if act == best else "  "
            print(f" {marker} {format_action(act):<25} : {score:.1f}")
            
            # Show top lines for this action
            if act in paths:
                # Merge identical paths
                merged_branches = {}
                for branch in paths[act]:
                    raw_turns = branch['path']
                    clean_turns = []
                    for turn in raw_turns:
                        clean_lines = []
                        for line in turn:
                            cl = line
                            # BattleEngine now logs with names directly, so cl is already clean
                            clean_lines.append(cl)
                        clean_turns.append(tuple(clean_lines))
                    
                    path_tuple = tuple(clean_turns)
                    merged_branches[path_tuple] = merged_branches.get(path_tuple, 0) + branch['prob']
                
                # Sort by probability
                sorted_branches = sorted(merged_branches.items(), key=lambda x: x[1], reverse=True)
                for path_turns, prob in sorted_branches:
                    if prob < 0.01: continue
                    print(f"    {'Probability':<11}: {int(prob * 100)}%")
                    
                    for t_idx, turn_lines in enumerate(path_turns):
                        turn_num = t_idx + 1
                        is_last_turn = (t_idx == len(path_turns) - 1)
                        
                        for l_idx, line in enumerate(turn_lines):
                             is_last_line = is_last_turn and (l_idx == len(turn_lines) - 1)
                             if l_idx == 0:
                                 connector = "└── " if is_last_line else "├── "
                                 print(f"    {connector}T{turn_num}: {line}")
                             else:
                                 # AI move or secondary effect
                                 indent = "    └── " if is_last_line else "    │   "
                                 print(f"{indent}{line}")
                print()
        print("="*30)

if __name__ == "__main__":
    main()
