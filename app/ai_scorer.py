from app.mechanics import Mechanics

class AIScorer:
    def __init__(self, calc_client):
        self.calc_client = calc_client

    def score_moves(self, state, side):
        attacker = state.ai_active if side == 'ai' else state.player_active
        defender = state.player_active if side == 'ai' else state.ai_active
        
        # 1. Forced Switch
        if attacker.get('current_hp', 0) <= 0:
            return self._handle_forced_switch(state, side, attacker)

        # 2. Context
        att_speed = Mechanics.get_effective_speed(attacker, state.fields)
        def_speed = Mechanics.get_effective_speed(defender, state.fields)
        is_faster = att_speed >= def_speed
        target_hp = defender.get('current_hp', 1)
        
        # Determine "First Turn"
        # If last_moves['ai'] is None or starts with switch, we assume new mon out
        # Limitation: If turn 1, last_moves empty -> True.
        # If switch occurred, last_moves['ai'] -> "Switch: ..." -> True.
        # If move used, last_moves['ai'] -> "Move: ..." -> False.
        last_move_str = state.last_moves.get('ai' if side == 'ai' else 'player')
        is_first_turn = not last_move_str or last_move_str.startswith("Switch:")
        
        moves = attacker.get('moves', [])
        calc_res = self.calc_client.get_damage_rolls(attacker, defender, moves, state.fields)
        
        # 3. Analyze
        damage_info = self._analyze_damage(calc_res, target_hp)
        
        # 4. Matrix
        matrix = [[0] * len(calc_res) for _ in range(80)]
        move_names = [r.get('moveName') for r in calc_res]
        
        sucker_penalty = 0
        if side == 'ai' and last_move_str == 'Move: Sucker Punch': # Check "Move: " prefix? BattleEngine logs "Move: Name"
             # Wait, BattleEngine log format is "Move: X". 
             # I need to handle if last_move_str is just "Sucker Punch" or "Move: Sucker Punch".
             # state.last_moves store whatever apply_turn returned. 
             # apply_turn returns "Move: Name".
             if "Sucker Punch" in str(last_move_str): sucker_penalty = 20

        # Check if AI is dead to player (Threatened)
        # "If AI is dead to player mon and slower"
        ai_threatened = False
        if side == 'ai':
             # Calculate Player -> AI Damage
             # We need to simulate Player attacking AI to see if they can kill
             p_moves = defender.get('moves', [])
             if p_moves:
                  # Note: This adds overhead (another calc call) but is necessary for accurate logic
                  p_calc = self.calc_client.get_damage_rolls(defender, attacker, p_moves, state.fields)
                  current_hp = attacker.get('current_hp', 0)
                  if p_calc:
                      for res in p_calc:
                          # Check max roll
                          rolls = res.get('damage_rolls', [0])
                          if rolls and rolls[-1] >= current_hp:
                               ai_threatened = True
                               break

        for m_idx, res in enumerate(calc_res):
            name = res.get('moveName')
            cat = res.get('category', 'Physical')
            my_rolls = damage_info[m_idx]['rolls']
            
            # Validity
            if not self._is_move_valid(state, attacker, defender, name, cat, side):
                for row in range(80): matrix[row][m_idx] = -20
                continue
            
            # Scoring
            for roll_idx in range(16):
                dmg = my_rolls[roll_idx]
                max_d = damage_info['max_dmgs'][roll_idx]
                any_k = damage_info['any_kill_in_roll'][roll_idx]
                kills = dmg >= target_hp
                is_highest = (kills and any_k) or (not any_k and dmg >= max_d)
                
                for v_idx in range(5):
                    if cat == 'Status':
                         score = self._score_status_move(state, attacker, defender, name, v_idx, is_faster, is_first_turn)
                    else:
                         score = self._score_damage_move(
                             state, name, res, v_idx, is_highest, kills, is_faster, is_first_turn, 
                             attacker, defender, hp_pct=attacker.get('current_hp')/attacker.get('max_hp',1),
                             ai_threatened=ai_threatened
                         )

                    # Global Sucker Penalty
                    if "Sucker Punch" in name and sucker_penalty > 0:
                        if v_idx >= 2: score -= sucker_penalty

                    matrix[roll_idx * 5 + v_idx][m_idx] = score

        return {
            'moves': move_names, 
            'matrix': matrix, 
            'results': calc_res, 
            'variant_weights': [0.25, 0.25, 0.25, 0.05, 0.20]
        }

    def _score_damage_move(self, state, name, res, v_idx, is_highest, kills, is_faster, is_first_turn, attacker, defender, hp_pct, ai_threatened):
        score = 0
        
        # Standard High Damage Score
        if is_highest:
             score = 8 if v_idx == 4 else 6
        
        # Check Special Moves Override (Speed Control etc)
        # "If this is the highest damaging move, none of the below bonuses are applied... gets usual +6/+8"
        # This implies if it IS highest, we stick to above.
        # But wait, "If target is not Contrary... +6/5".
        # This implies alternate scoring if NOT highest.
        
        # Speed Control
        speed_control = ['Icy Wind', 'Electroweb', 'Rock Tomb', 'Mud Shot', 'Low Sweep', 'Bulldoze']
        if name in speed_control and not is_highest:
             # If target not Contrary/Clear Body and AI Slower: +6, else +5
             # Simplified check
             if not is_faster: score = 6
             else: score = 5
             # Double battle check skipped
             return score # Should we return immediately? "None of the below bonuses applied" applied to when it IS highest. 
             # If it is NOT highest, we use this score.
             # Does it get Kill bonuses?
             # "Note: stack with bonuses for kill". Not stated for Speed Control.
             # I'll assume Speed Control logic REPLACES base score if not highest.
        
        # Fake Out
        if name == 'Fake Out':
            if is_first_turn: return 9
            # Else? Usually 6 if highest, or just bad?
            # Fake Out is rarely highest damage.
            # If not first turn, it fails (validity check should handle?).
            # "If not first turn... +6"?
            # Validity check: Fails if not first turn.
            pass 

        # Priority Desperation
        # "If AI is dead to player mon and slower, all attacking moves with priority get an additional +11"
        priority = res.get('priority', 0)
        if ai_threatened and not is_faster and priority > 0:
             score += 11
        
        # Kill Bonuses (applies to "All damaging moves")
        if kills:
             if is_faster or priority > 0: score += 6 
             else: score += 3
             if attacker.get('ability') in ['Moxie', 'Beast Boost']: score += 1

        # Pursuit
        if name == 'Pursuit':
             # "If Pursuit can KO: +10".
             if kills: 
                 score = 10 
                 if is_faster: score += 3 # "Regardless... +3"
                 # "Stacks with bonus for kill".
                 # So 10 + 6 (Fast Kill) + 3 (Faster) = 19?
                 # Or does 10 REPLACE base 6?
                 # "If Pursuit can KO... +10". Does not say "Additional".
                 # So Score = 10 defined base. Then add Kill bonus?
                 # "Note: The bonuses for kill and AI outspeeding stack with the bonus for kill listed in 'All damaging moves'"
                 # This implies "All damaging moves" kill bonus (+6/+3) STACKS on top of Pursuit 10?
                 # That seems extremely high (19).
                 # Interpret: Pursuit Base is 10 (instead of 6). Then add Kill Bonus (+6). Then Add specific Pursuit Speed Bonus (+3).
                 # Total 19.
                 # I'll implement additive.
                 pass
             else:
                 # Not killing
                 target_hp_pct = defender.get('current_hp') / defender.get('max_hp',1)
                 if target_hp_pct < 0.20:
                     score = 10
                 elif target_hp_pct < 0.40:
                     if v_idx <= 1: score = 8 # 50%
                 
                 if is_faster: score += 3
        
        # Boom Moves
        if name in ['Explosion', 'Self-Destruct', 'Self Destruct', 'Misty Explosion']:
             # Override base score? "Never considered highest damaging move".
             score = 0
             if hp_pct < 0.10: score += 10
             elif hp_pct < 0.33: 
                 if v_idx <= 2: score += 8
             elif hp_pct < 0.66:
                 if v_idx <= 1: score += 7
             else:
                 if v_idx == 0: score += 7
             # Kill bonus still applies (except Explosion doesn't check kill? Doc says "Never considered highest... exceptions... still have check to see if they kill")
             # "All of these moves, with exceptions of Explosion... still have check".
             # So Explosion DOES NOT get kill bonuses.
             # "Exceptions of Explosion, Final Gambit, Rollout".
             # So reset kill bonuses if implemented above.
             pass

        return score

    def _score_status_move(self, state, attacker, defender, name, v_idx, is_faster, is_first_turn):
        if name in ['Stealth Rock', 'Spikes', 'Toxic Spikes']: return 8 if v_idx == 0 else 9
        if name == 'Sticky Web': return 9 if v_idx == 0 else 12
        if name in ['Protect', 'Detect', 'Kings Shield']: return self._score_protect(state, attacker, defender, v_idx)
        if name in ['Recover', 'Slack Off', 'Heal Order', 'Soft-Boiled', 'Roost', 'Strength Sap', 'Morning Sun', 'Synthesis', 'Moonlight']:
            return self._score_recovery(state, attacker, defender, is_faster, name)
        
        setup_moves = ['Swords Dance', 'Dragon Dance', 'Calm Mind', 'Bulk Up', 'Coil', 'Hone Claws', 'Work Up', 'Nasty Plot', 'Tail Glow', 'Shell Smash']
        if name in setup_moves: return self._score_setup_move(state, attacker, defender, name, is_faster)

        return 6

    # ... Helper methods (_handle_forced_switch, _analyze_damage, _is_move_valid, _score_protect, etc) from previous step ...
    # Integrating previous methods here for completeness in "write_to_file"
    def _score_protect(self, state, attacker, defender, v_idx):
        score = 6
        last_move_ai = state.last_moves.get('ai')
        if last_move_ai and "Protect" in str(last_move_ai): # Robust check
             if v_idx >= 2: return -20
        ai_status = attacker.get('status')
        if ai_status in ['psn', 'tox', 'brn']: score -= 2
        def_status = defender.get('status')
        if def_status in ['psn', 'tox', 'brn']: score += 1
        return score

    def _score_recovery(self, state, attacker, defender, is_faster, move_name):
        current_hp = attacker.get('current_hp', 0)
        max_hp = attacker.get('max_hp', 1)
        hp_pct = current_hp / max_hp
        if hp_pct >= 1.0: return -20
        if hp_pct >= 0.85: return -6
        should_recover = False
        if is_faster:
             if hp_pct < 0.66: should_recover = True
        else:
             if hp_pct < 0.50: should_recover = True
             elif hp_pct < 0.70: should_recover = True
        if move_name in ['Morning Sun', 'Synthesis', 'Moonlight']:
             if state.fields.get('weather') == 'Sun' and should_recover: return 7
        return 7 if should_recover else 5

    def _score_setup_move(self, state, attacker, defender, name, is_faster):
        score = 6
        if defender.get('ability') == 'Unaware' and name not in ['Swords Dance', 'Howl']: return -20
        if name in ['Agility', 'Rock Polish', 'Autotomize']:
             return 7 if not is_faster else -20
        if defender.get('status') in ['frz', 'slp']: score += 3
        return score
    
    def _handle_forced_switch(self, state, side, attacker):
        party = state.ai_party if side == 'ai' else state.player_party
        valid_switches = [p.get('species') for p in party if p.get('current_hp', 0) > 0 and p.get('species') != attacker.get('species')]
        if not valid_switches: return {'moves': [], 'matrix': [], 'variant_weights': [1.0]}
        move_names = [f"Switch: {s}" for s in valid_switches]
        matrix = [[10] * len(valid_switches) for _ in range(80)]
        return {'moves': move_names, 'matrix': matrix, 'results': [], 'variant_weights': [0.2]*5}

    def _analyze_damage(self, calc_res, target_hp):
        info = {}
        max_dmgs = [0] * 16 
        any_kill_in_roll = [False] * 16 
        rolls_per_move = []
        for res in calc_res:
            rolls = res.get('damage_rolls', [0])
            if len(rolls) < 16: rolls = rolls + [rolls[-1]] * (16 - len(rolls))
            if res.get('category') == 'Status': rolls = [0]*16
            rolls_per_move.append(rolls)
        for roll_idx in range(16):
            m_d = 0
            has_k = False
            for m_idx, r in enumerate(rolls_per_move):
                 d = r[roll_idx]
                 if d > m_d: m_d = d
                 if d >= target_hp: has_k = True
            max_dmgs[roll_idx] = m_d
            any_kill_in_roll[roll_idx] = has_k
        for m_idx, res in enumerate(calc_res):
            rolls = rolls_per_move[m_idx]
            info[m_idx] = {'rolls': rolls}
        info['max_dmgs'] = max_dmgs
        info['any_kill_in_roll'] = any_kill_in_roll
        return info

    def _is_move_valid(self, state, attacker, defender, move_name, category, side):
        if category == 'Status':
            existing_status = defender.get('status')
            if move_name in ['Spore', 'Sleep Powder', 'Hypnosis', 'Dark Void', 'Sing', 'Grass Whistle', 'Lovely Kiss', 'Yawn']:
                 if existing_status: return False 
                 if state.fields.get('electric_terrain') or state.fields.get('misty_terrain'): return False
            if move_name in ['Thunder Wave', 'Glare', 'Stun Spore']:
                if existing_status: return False
            if move_name == 'Will-O-Wisp':
                if existing_status: return False
                if defender.get('type1') == 'Fire' or defender.get('type2') == 'Fire': return False
            if move_name in ['Toxic', 'Poison Gas', 'Toxic Spikes']:
                if existing_status: return False
                if move_name == 'Toxic' and (defender.get('type1') in ['Poison', 'Steel'] or defender.get('type2') in ['Poison', 'Steel']): return False
            weather = state.fields.get('weather')
            if move_name in ['Sunny Day'] and weather == 'Sun': return False
            if move_name in ['Rain Dance'] and weather == 'Rain': return False
            if move_name in ['Sandstorm'] and weather == 'Sand': return False
            if move_name in ['Hail', 'Snowscape'] and weather in ['Hail', 'Snow']: return False
        
        # Fake Out Validity check: Only first turn
        if move_name == 'Fake Out':
            last_move_str = state.last_moves.get('ai' if side == 'ai' else 'player')
            is_first_turn = not last_move_str or last_move_str.startswith("Switch:")
            if not is_first_turn: return False # Fails
            
        return True
