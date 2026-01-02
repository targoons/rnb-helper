
import sys
import os
# Ensure root is in path
sys.path.append(os.getcwd())

from pkh_app.state_parser import parse_state
from pkh_app.battle_engine import BattleState
from pkh_app.ai_scorer import AIScorer
from app import calc_client

def normalize_mon(mon):
    # Simplified norm for test
    return mon

def main():
    path = "data/battle_state.json"
    if len(sys.argv) > 1: path = sys.argv[1]
    
    print(f"Testing Prediction on {path}...")
    state_dict = parse_state(path)
    if not state_dict:
        print("Failed to parse state.")
        return

    player_active = state_dict.get('player_side', {}).get('active', {})
    ai_active = state_dict.get('opponent_side', {}).get('active', {})
    
    # Ensure moves are present for AI Scorer threat check
    # If using mocked data make sure player_active has moves
    
    bs = BattleState(
        player_active=player_active,
        ai_active=ai_active,
        player_party=state_dict.get('player_side', {}).get('party', []),
        ai_party=state_dict.get('opponent_side', {}).get('party', []),
        last_moves=state_dict.get('last_moves', {}),
        fields=state_dict.get('fields', {})
    )
    
    scorer = AIScorer(calc_client)
    res = scorer.score_moves(bs, 'ai')
    
    move_names = res['moves']
    matrix = res['matrix']
    weights = res['variant_weights']
    
    print("\nResults:")
    for i, m in enumerate(move_names):
        # Calculate Weighted Avg
        total = 0
        for r in range(16):
            for v in range(5):
                 w = weights[v] * (1/16)
                 s = matrix[r*5 + v][i]
                 total += s * w
        
        print(f"Move: {m}, weighted_score: {total:.2f}")

if __name__ == "__main__":
    main()
