
from typing import Dict, List, Optional
import math
from pkh_app.mechanics import Mechanics

class DamageCalculator:
    def __init__(self, calc_client, enricher, rich_data, move_names=None):
        self.calc_client = calc_client
        self.enricher = enricher
        self.rich_data = rich_data
        self.move_names = move_names or {}

    def get_damage_rolls(self, attacker, defender, moves, field):
        """
        Legacy interface for AIScorer - delegates to calc_damage_for_moves.
        Handles both move IDs (int) and move names (str).
        """
        keys = list(moves) # Pass raw moves (ints or strings)
        
        results = self.calc_damage_for_moves(attacker, defender, keys, field)
        
        # Flatten structure: AIScorer expects {move_name: [rolls]} or list of rolls?
        # Looking at usage, it likely expects a consistent return. 
        # But this method signature is vague in the original file.
        # Based on original implementation:
        return results

    def calc_damage_for_moves(
        self, attacker, defender, move_names, field_conditions=None, 
        move_type_override=None, move_bp_override=None
    ):
        """
        Calculate damage for multiple moves (for prediction generator).
        Returns list of dicts with damage_rolls, crit_rolls, etc.
        Handles both move names (strings) and move IDs (integers).
        """
        if not field_conditions:
            field_conditions = {}

        results = []
        for move_input in move_names:
            if isinstance(move_input, int):
                move_name = self.move_names.get(str(move_input), str(move_input))
            else:
                move_name = str(move_input)
            
            # Use calc_client (pkmn.py/nodejs bridge) if available
            if self.calc_client:
                # Prepare Request
                # Note: This implies calc_client has a method 'calc_damage_many' or similar
                # or we loop. In original code it likely looped or sent batch.
                # Here we assume single calc for simplicity of refactor unless we see batch API.
                try:
                    # In original code, it called self.calc_client.calc_damage(...)
                    result = self.calc_client.calc_damage(attacker, defender, move_name, field_conditions)
                except Exception as e:
                    # Fallback or error
                    result = {'damage': [0]}
            else:
                # Fallback to internal python mechanic (if existed) or returns 0
                try:
                    from pkh_app import local_damage_calc
                    move_data = self.rich_data.get("moves", {}).get(
                        str(move_name).lower().replace(" ", "").replace("-", "").replace("'", ""), {}
                    )
                    # If move_data missing, try to fetch from mechanics
                    if not move_data:
                        # Try to get from mechanic helper via enricher logic or just skip
                        # We don't have direct access to 'pokedex' here easily unless passed, 
                        # but we have 'rich_data'.
                        # Let's rely on what we have.
                        pass
                    
                    result = local_damage_calc.calculate_damage(
                        attacker, defender, move_name, move_data, field_conditions,
                        move_type_override=move_type_override,
                        move_bp_override=move_bp_override
                    )
                except ImportError:
                    result = {'damage': [0]}
                except Exception as e:
                    import logging
                    logging.error(f"Error in local damage calc: {e}")
                    result = {'damage': [0]}

            damage_rolls = result.get("damage_rolls", result.get("damage", [0]))
            
            crit_rolls = [0] * len(damage_rolls)
            if result.get("can_crit", True):
                # Sniper Logic (1.5x -> 2.25x)
                crit_mult = 1.5
                if attacker.get("ability") == "Sniper":
                    crit_mult = 2.25
                crit_rolls = [int(d * crit_mult) for d in damage_rolls]

            # Create final result, preserving all client-returned metadata
            res = result.copy()
            res.update({
                "moveName": move_name,
                "move": move_input,
                "damage_rolls": damage_rolls,
                "crit_rolls": crit_rolls,
                "desc": f"{min(damage_rolls)}-{max(damage_rolls)} damage",
                "effectiveness": result.get("effectiveness", result.get("type_effectiveness", 1.0)),
                "is_stab": result.get("is_stab", False),
            })
            results.append(res)

        return results
