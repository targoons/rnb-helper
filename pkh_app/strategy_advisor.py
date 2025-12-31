
import os
import sys
from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.ai_scorer import AIScorer
from pkh_app.simulation import Simulation
from pkh_app import calc_client

class StrategyAdvisor:
    def __init__(self, species_names=None, move_names=None):
        self.client = calc_client
        self.species_names = species_names or {}
        self.move_names = move_names or {}
        self.engine = BattleEngine(self.client, species_names=self.species_names, move_names=self.move_names)
        self.scorer = AIScorer(self.client)
        self.sim = Simulation(self.engine, self.scorer)

    def get_species_name(self, species_id):
        return self.species_names.get(str(species_id), str(species_id))

    def normalize_mon(self, mon):
        if not mon: return {}
        new_mon = mon.copy()
        if 'species_id' in mon: 
            s_id = mon['species_id']
            name = self.get_species_name(s_id)
            new_mon['name'] = name
            new_mon['species'] = name 
        return new_mon

    def run_simulation(self, battle_state_dict):
        """
        Processes a raw battle state dictionary and returns simulation results.
        """
        player_active = self.normalize_mon(battle_state_dict.get('player_side', {}).get('active', {}))
        ai_active = self.normalize_mon(battle_state_dict.get('opponent_side', {}).get('active', {}))
        
        p_side = battle_state_dict.get('player_side', {})
        a_side = battle_state_dict.get('opponent_side', {})
        
        p_party = [self.normalize_mon(m) for m in p_side.get('party', [])]
        a_party = [self.normalize_mon(m) for m in a_side.get('party', [])]
        
        last_moves = battle_state_dict.get('last_moves', {})
        fields = battle_state_dict.get('fields', {})
        
        bs = BattleState(
            player_active=player_active,
            ai_active=ai_active,
            player_party=p_party,
            ai_party=a_party,
            last_moves=last_moves,
            fields=fields
        )
        
        return self.sim.run(bs)
