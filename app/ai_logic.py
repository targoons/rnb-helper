import logging

class MoveScorer:
    def __init__(self):
        pass

    def score_moves(self, ai_active, player_active, ai_moves_calc, player_moves_calc):
        scored_moves = []
        
        # 1. State Analysis
        ai_speed = ai_active.get('stats', {}).get('spe', 0)
        player_speed = player_active.get('stats', {}).get('spe', 0)
        ai_is_faster = ai_speed >= player_speed # Speed ties -> AI faster
        
        player_hp = player_active.get('current_hp', 1)
        ai_current_hp = ai_active.get('current_hp', 1)
        
        # Check if Player kills AI (using max roll of player moves)
        player_can_kill_ai = False
        for p_move in player_moves_calc:
            rolls = p_move.get('damage_rolls', [])
            if rolls and rolls[-1] >= ai_current_hp:
                player_can_kill_ai = True
                break
                
        # 2. Find "Highest Damaging Move" threshold
        max_dmg_seen = 0
        any_move_kills = False
        
        for m in ai_moves_calc:
            if m.get('category') == 'Status': continue
            rolls = m.get('damage_rolls', [0])
            dmg = rolls[-1]
            if dmg > max_dmg_seen: max_dmg_seen = dmg
            if rolls[0] >= player_hp: any_move_kills = True
            
        # 3. Score Moves
        for move_res in ai_moves_calc:
            name = move_res.get('moveName', str(move_res.get('move')))
            category = move_res.get('category', 'Physical') # Default to damaging if unknown
            priority = move_res.get('priority', 0)
            
            damage_rolls = move_res.get('damage_rolls', [0])
            min_d = damage_rolls[0]
            max_d = damage_rolls[-1]
            
            kills = min_d >= player_hp
            
            # Base Score
            score_a = 0 # Standard
            score_b = 0 # High Roll
            
            # Check eligibility for "Highest Damaging Move" score
            is_damaging = category != 'Status'
            is_highest = False
            
            if is_damaging:
                # "If multiple moves kill, they are all considered the highest damaging move"
                if any_move_kills:
                    if kills: is_highest = True
                else:
                    if max_d >= max_dmg_seen: is_highest = True
            
            # -- Scoring Rules --
            
            # Status Moves -> Default +6
            if category == 'Status':
                score_a = 6
                score_b = 6
                
            # Damaging Moves
            elif is_highest:
                score_a = 6
                score_b = 8
                
                # Kill Bonuses
                if kills:
                    if ai_is_faster:
                        score_a += 6 # Total 12
                        score_b += 6 # Total 14
                    else:
                        score_a += 3 # Total 9
                        score_b += 3 # Total 11
            else:
                # Not Status, Not Highest -> Score 0
                score_a = 0
                score_b = 0
                
            # Priority Desperation (Matches Doc: "Damaging priority moves")
            # "If AI is dead to player mon and slower, all attacking moves with priority get +11"
            # Note: This usually implies +11 ON TOP of base.
            # But if base is 0 (weak priority)? 0 + 11 = 11.
            # If base is 6 (Strongest move)? 6 + 11 = 17.
            # If it Kills? 12 + 11 = 23.
            if is_damaging and priority > 0:
                 if not ai_is_faster and player_can_kill_ai:
                     score_a += 11
                     score_b += 11
                     
            scored_moves.append({
                'move': move_res.get('move'),
                'name': name,
                'scores': {'standard': score_a, 'high_roll': score_b},
                'damage_info': {'min': min_d, 'max': max_d}
            })
            
        return scored_moves


class SwitchPredictor:
    def __init__(self):
        pass

    def predict_switch(self, candidates, player_active, calc_client):
        """
        Evaluates potential switch-ins using the Switch Score Matrix.
        
        Args:
            candidates (list): List of opponent party pokemon (dicts).
            player_active (dict): Player's active pokemon.
            calc_client (object): Object with get_damage_rolls method.
            
        Returns:
            dict: The best candidate and the logic breakdown.
        """
        best_score = -100
        best_candidate = None
        explanations = []
        
        player_speed = player_active.get('stats', {}).get('spe', 0)
        player_hp = player_active.get('current_hp', 1)
        player_max_hp = player_active.get('max_hp', 1)

        for i, mon in enumerate(candidates):
            if mon.get('current_hp', 0) <= 0:
                continue # Skip fainted
            
            mon_speed = mon.get('stats', {}).get('spe', 0)
            mon_hp = mon.get('current_hp', 1)
            mon_max_hp = mon.get('max_hp', 1)
            
            # 1. Determine Speed
            # Tie goes to AI? For switching, usually strict > or >=. Assuming >= for consistency.
            am_fast = mon_speed >= player_speed
            
            # 2. Get Calcs
            # We need:
            # - Max damage Mon deals to Player (to check OHKO)
            # - Max damage Player deals to Mon (to check Survival)
            
            # This is synchronous and expensive if real HTTP calls. 
            # In a real app this should be batched.
            # Assuming calc_client.get_damage_rolls returns a struct including max_damage
            
            # Mon -> Player
            mon_moves = mon.get('moves', [])
            mon_atk_res = calc_client.get_damage_rolls(mon, player_active, mon_moves, {})
            
            max_dmg_to_player = 0
            if mon_atk_res:
                # Find move with highest max damage
                for res in mon_atk_res:
                    dmg = res.get('damage_rolls', [0])[-1]
                    if dmg > max_dmg_to_player:
                        max_dmg_to_player = dmg
            
            mon_kills_player = max_dmg_to_player >= player_hp
            
            # Player -> Mon
            # We need to test all Player moves against THIS candidate
            player_moves = player_active.get('moves', []) # Should be list of names
            player_atk_res = calc_client.get_damage_rolls(player_active, mon, player_moves, {})
            
            max_dmg_to_mon = 0
            if player_atk_res:
                for res in player_atk_res:
                    dmg = res.get('damage_rolls', [0])[-1]
                    if dmg > max_dmg_to_mon:
                        max_dmg_to_mon = dmg
            
            player_kills_mon = max_dmg_to_mon >= mon_hp
            
            # 3. Apply Scoring Matrix
            score = 0
            reason = "Default"
            
            # Revenge conditions need damage % comparison
            # Deals > Taken
            mon_dmg_pct = (max_dmg_to_player / player_max_hp) * 100
            player_dmg_pct = (max_dmg_to_mon / mon_max_hp) * 100
            deals_more = mon_dmg_pct > player_dmg_pct
            
            if mon_kills_player and am_fast:
                score = 5
                reason = "OHKO & Faster"
            elif mon_kills_player and not am_fast and not player_kills_mon:
                score = 4
                reason = "OHKO & Slower (Safe)"
            elif am_fast and deals_more:
                score = 3
                reason = "Revenge (Faster)"
            elif not am_fast and deals_more:
                score = 2
                reason = "Revenge (Slower)"
            elif am_fast:
                score = 1
                reason = "Faster"
            elif not am_fast and player_kills_mon:
                score = -1
                reason = "Dead on Entry"
            else:
                score = 0
                reason = "Default"
                
            explanations.append({
                'species': mon.get('species'),
                'score': score,
                'reason': reason,
                'speed': mon_speed
            })
            
            # Tie breaking: Prefer lower index (handled by > check not >=)
            # If we iterate 0..N, update if score > best_score.
            if score > best_score:
                best_score = score
                best_candidate = mon
                
        return best_candidate, explanations
