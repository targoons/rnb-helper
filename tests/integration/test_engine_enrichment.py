
import sys
import os
import logging
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pkh_app.battle_engine import BattleEngine, BattleState

def test_enrichment():
    logging.basicConfig(level=logging.ERROR)
    engine = BattleEngine(MagicMock())
    
    attacker = {'species': 'Charizard', 'ability': 'Blaze', 'item': 'Choice Band', 'moves': ['Flamethrower']}
    defender = {'species': 'Blastoise', 'ability': 'Torrent', 'item': 'Leftovers'}
    state = BattleState(player_active=attacker, ai_active=defender, player_party=[], ai_party=[])
    
    # Manually call enrich (normally called in apply_turn)
    engine.enrich_state(state)
    
    print("Checking Player Active keys...")
    keys = state.player_active.keys()
    print(keys)
    
    if '_rich_ability' in keys and '_rich_item' in keys and '_rich_moves' in keys:
        print("PASS: Rich data keys present.")
        print(f"Ability Data: {state.player_active['_rich_ability'].get('name')}")
        print(f"Item Data: {state.player_active['_rich_item'].get('name')}")
    else:
        print("FAIL: Rich data keys missing.")

if __name__ == "__main__":
    test_enrichment()
