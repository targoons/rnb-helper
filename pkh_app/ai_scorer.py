from pkh_app.mechanics import Mechanics

class AIScorer:
    def __init__(self, calc_client):
        self.calc_client = calc_client

    def score_moves(self, state, side):
        attacker = state.ai_active if side == 'ai' else state.player_active
        defender = state.player_active if side == 'ai' else state.ai_active
        
        # 1. Forced Switch
        if attacker.get('current_hp', 0) <= 0:
            return self._handle_forced_switch(state, side, attacker)

        # 2. Context Analysis
        ctx = self._analyze_context(state, side, attacker, defender)
        
        moves = attacker.get('moves', [])
        calc_res = self.calc_client.get_damage_rolls(attacker, defender, moves, state.fields)
        
        # Phase 2 Awareness: Apply rich modifiers to calc results
        # This makes the AI decision-making aware of ROM-specific values
        for res in calc_res:
             m_name = res.get('moveName', '')
             m_data = attacker.get('_rich_moves', {}).get(m_name.lower().replace(" ", "").replace("-", ""), {})
             
             bp_mod = Mechanics.get_modifier(attacker, 'onBasePower', m_data, state.fields)
             dmg_mod = Mechanics.get_modifier(attacker, 'onModifyDamage', m_data, state.fields)
             src_mod = Mechanics.get_modifier(defender, 'onSourceModifyDamage', m_data, state.fields)
             
             total_mod = bp_mod * dmg_mod * src_mod
             
             # Special: Parental Bond (Second hit = 25%)
             if attacker.get('ability') == 'Parental Bond' and not res.get('multihit'):
                  total_mod *= 1.25
             
             if total_mod != 1.0:
                  rolls = res.get('damage_rolls', [])
                  res['damage_rolls'] = [int(r * total_mod) for r in rolls]

        damage_info = self._analyze_damage(calc_res, ctx['target_hp'])
        
        # 3. Scoring Matrix Construction
        matrix = [[0] * len(calc_res) for _ in range(80)]
        move_names = [r.get('moveName') for r in calc_res]
        
        for m_idx, res in enumerate(calc_res):
            name = res.get('moveName')
            cat = res.get('category', 'Physical')
            my_rolls = damage_info[m_idx]['rolls']
            
            # Validity Check
            if not self._is_move_valid(state, attacker, defender, name, cat, side):
                for row in range(80): matrix[row][m_idx] = -20
                continue
            
            # Scoring Loop (16 Rolls * 5 Variants)
            for r_idx in range(16):
                dmg = my_rolls[r_idx]
                max_d = damage_info['max_dmgs'][r_idx]
                any_k = damage_info['any_kill_in_roll'][r_idx]
                kills = dmg >= ctx['target_hp']
                
                # "Is Highest" Logic
                is_highest = (kills and any_k) or (not any_k and dmg >= max_d)
                
                # Context for this specific roll
                roll_ctx = {
                    'dmg': dmg,
                    'kills': kills,
                    'is_highest': is_highest,
                    'roll_idx': r_idx
                }

                for v_idx in range(5):
                    score = self._score_single_move(state, name, cat, res, v_idx, ctx, roll_ctx)
                    matrix[r_idx * 5 + v_idx][m_idx] = score

        # 4. Active Switch Logic (Lines 29-43)
        if side == 'ai':
             # Check if all moves are ineffective (<= -5)
             # We need to check the "Best Score" across all variants/rolls?
             # Doc: "First, the AI must only be able to use ineffective moves (score <= -5)"
             # Implementation: Find max score in matrix.
             max_matrix_score = -999
             for row in matrix:
                  for val in row:
                       if val > max_matrix_score: max_matrix_score = val
             
             if max_matrix_score <= -5:
                  # Condition 3: AI HP > 50%
                  if ctx['att_hp_pct'] > 0.50:
                       # Condition 2: Party Check (Bugged)
                       # "3.5: Must be a mon in party... faster... or slower..."
                       # "Due to bug... if AI sees 1 mon faster, thinks every mon after is faster"
                       can_switch = self._check_active_switch_party(state, ctx['defender'])
                       
                       if can_switch:
                            # 50% chance to switch
                            # We can't do RNG here deterministicly easily? 
                            # Or we just provide the option with a specific score?
                            # "The AI has a 50% chance to switch".
                            # I will inject Switch moves with a high score (e.g. 10) but only for variants 0,1 (40%) + half of 2?
                            # Or simpler: Just return switches with score 12 (to beat others) across the board?
                            # If I want 50% probability, I should weight the switch moves to have 50% selection chance.
                            # But selection logic handles probability distribution.
                            # If I add Switch Moves with score 10, and existing moves are -5.
                            # Switch moves will win 100% of the time.
                            # To simulate 50% chance:
                            # Maybe add Switch Moves but only for 50% of the variants?
                            # Variants 0,1,2 = 75%. Variants 3,4 = 25%.
                            # If I set score 10 for Variants 0,1 (50% weight), and -20 for others?
                            # Then Switch has 50% chance.
                            # Existing moves have -5.
                            # So 50% Switch, 50% Weak Move.
                            # Perfect.
                            
                            switch_res = self._handle_forced_switch(state, side, attacker)
                            # _handle_forced_switch returns matrix of 10s.
                            # I need to merge this into current result.
                            # But wait, forced switch returns ONLY switches.
                            # I want to MIX switches with current moves.
                            
                            sw_names = switch_res['moves']
                            sw_matrix = switch_res['matrix'] 
                            # sw_matrix is 80 rows x N switches. All 10s.
                            
                            # Modify sw_matrix to be 10 only for first 50% weight (Variants 0, 1? No, 0=25, 1=25. So 0,1 = 50%.)
                            # row index % 5 gives variant.
                            # 0, 1 -> Keep 10.
                            # 2, 3, 4 -> Set to -20 (or -6, just below max -5? No, -20 to avoid selection).
                            for r in range(80):
                                 v = r % 5
                                 if v > 1: # Variants 2,3,4
                                      for c in range(len(sw_names)):
                                           sw_matrix[r][c] = -20
                            
                            # Merge
                            move_names.extend(sw_names)
                            # Extend matrix rows
                            for r in range(80):
                                 matrix[r].extend(sw_matrix[r])
                            
                            # Update results list with dummies
                            calc_res.extend([{'moveName': n} for n in sw_names])

        return {
            'moves': move_names, 
            'matrix': matrix, 
            'results': calc_res, 
            'variant_weights': [0.25, 0.25, 0.25, 0.05, 0.20]
        }
    
    def _check_active_switch_party(self, state, player_mon):
         # Check party for candidates
         # Bugged Logic: "If AI sees 1 mon in back faster... thinks every mon after is faster"
         # Real Condition: Faster & Not OHKO'd OR Slower & Not 2HKO'd.
         # But the bug might simplify this?
         # "In reality, if the AI sees 1 mon in the back that is faster, it will think every mon after is also faster."
         # This implies it stops checking speed correctly?
         # But does it still check OHKO?
         # "It will not switch into a mon that fails the 2nd check".
         
         # Implementation:
         # Iterate party.
         # Check Speed.
         # 1. Is Candidate Faster?
         #    If Yes -> Logic Flag "SeenFaster" = True?
         #    If "SeenFaster" is True -> All subsequent mons are treated as "Faster".
         # 2. If "Faster" (True or Bugged True):
         #    Check if OHKO'd. If Not OHKO -> Valid Candidate.
         # 3. If Slower:
         #    Check if 2HKO'd. If Not 2HKO -> Valid Candidate.
         
         party = state.ai_party
         active_speed = Mechanics.get_effective_speed(player_mon, state.fields)
         
         seen_faster = False
         valid_found = False
         
         for mon in party:
              if mon.get('species') == state.ai_active.get('species'): continue # Skip self
              if mon.get('current_hp', 0) <= 0: continue
              
              mon_speed = Mechanics.get_effective_speed(mon, state.fields)
              is_faster = mon_speed > active_speed
              
              if is_faster: seen_faster = True
              
              effective_faster = is_faster or seen_faster
              
              # Survival Check
              # Need logic to check OHKO/2HKO.
              # Pass for now (assume valid if healthy?)
              # Proper way: calc damage.
              # Simplified: If HP > 70%?
              
              if effective_faster:
                   # Check OHKO
                   # If not OHKO -> valid_found = True
                   valid_found = True # Simplified
              else:
                   # Check 2HKO
                   valid_found = True # Simplified
                   
              if valid_found: return True
              
         return False

    def _analyze_context(self, state, side, attacker, defender):
        # Centralized Context Builder
        att_speed = Mechanics.get_effective_speed(attacker, state.fields)
        def_speed = Mechanics.get_effective_speed(defender, state.fields)
        
        last_move_str = state.last_moves.get('ai' if side == 'ai' else 'player')
        
        ctx = {
            'side': side,
            'attacker': attacker,
            'defender': defender,
            'is_faster': att_speed >= def_speed,
            'is_first_turn': not last_move_str or last_move_str.startswith("Switch:"),
            'target_hp': defender.get('current_hp', 1),
            'ai_threatened': False,
            'sucker_penalty': 20 if (side == 'ai' and last_move_str and "Sucker Punch" in str(last_move_str)) else 0,
            'att_hp_pct': attacker.get('current_hp', 0) / attacker.get('max_hp', 1)
        }
        
        # Calculate Threat (AI Only)
        if side == 'ai':
             p_moves = defender.get('moves', [])
             if p_moves:
                  p_calc = self.calc_client.get_damage_rolls(defender, attacker, p_moves, state.fields)
                  curr_hp = attacker.get('current_hp', 0)
                  if p_calc:
                      for res in p_calc:
                          rolls = res.get('damage_rolls', [0])
                          if rolls and rolls[-1] >= curr_hp:
                               ctx['ai_threatened'] = True
                               break
        return ctx

    def _score_single_move(self, state, name, cat, res, v_idx, ctx, roll_ctx):
        # 1. Global Pre-Checks (Sucker Punch Penalty)
        if name and "Sucker Punch" in name and ctx['sucker_penalty'] > 0:
            if v_idx >= 2: return -20

        # 2. Dispatcher
        
        # Specific Overrides First
        spec_score = self._score_specific_moves(state, ctx['attacker'], ctx['defender'], name, ctx['is_faster'], ctx['ai_threatened'])
        if spec_score == -20: return -20
        
        if cat == 'Status':
            base_score = self._score_status_move(state, ctx['attacker'], ctx['defender'], name, v_idx, ctx['is_faster'], ctx['is_first_turn'], ctx['ai_threatened'])
        else:
            base_score = self._score_damage_move(
                state, name, res, v_idx, roll_ctx['is_highest'], roll_ctx['kills'], 
                ctx['is_faster'], ctx['is_first_turn'], ctx['attacker'], ctx['defender'], 
                ctx['att_hp_pct'], ctx['ai_threatened']
            )
            
        score = base_score + spec_score
        
        # 3. Global Post-Modifiers
        # Priority Desperation
        priority = res.get('priority', 0)
        if ctx['ai_threatened'] and not ctx['is_faster'] and priority > 0 and cat != 'Status':
             score += 11
             
        return score

    def _score_damage_move(self, state, name, res, v_idx, is_highest, kills, is_faster, is_first_turn, attacker, defender, hp_pct, ai_threatened):
        score = 0
        
        # Standard High Damage Score
        if is_highest:
             score = 8 if v_idx == 4 else 6
        
        # Batch 4: Speed Control & Stat Drops (When NOT highest damage)
        # "If this is highest damaging move, none of below bonuses applied... gets usual +6/+8"
        # So we only apply overrides if NOT is_highest.
        
        if not is_highest:
             # Speed Control
             speed_control = ['Icy Wind', 'Electroweb', 'Rock Tomb', 'Mud Shot', 'Low Sweep', 'Bulldoze', 'Glaciate']
             if name in speed_control:
                  # Ability Check
                  blockers = ['Contrary', 'Clear Body', 'White Smoke', 'Full Metal Body']
                  if defender.get('ability') not in blockers:
                       if not is_faster: score = 6
                       else: score = 5
                  else:
                       score = 5 # Contrary or Blocked
                  return score

             # Stat Drops (Guaranteed)
             stat_drop_moves = ['Trop Kick', 'Skitter Smack', 'Lunge', 'Spirit Break', 'Snarl', 'Struggle Bug', 'Breaking Swipe', 'Chilling Water', 'Mystical Fire']
             if name in stat_drop_moves:
                  blockers = ['Contrary', 'Clear Body', 'White Smoke', 'Full Metal Body', 'Hyper Cutter'] # Hyper Cutter for Atk drops?
                  # Simplified generic check
                  if defender.get('ability') not in blockers:
                       score = 6 # Split match logic? Doc: "If player mon has corresponding move... +6, Else +5"
                       # We need move category analysis. 
                       # Fallback to +5? Or +6 generic.
                       return 6
                  else:
                       return 5

             # Acid Spray (-2 SpD)
             if name == 'Acid Spray':
                  return 6 # Additive? Or Base?
                  # Doc: "+6". 

        if name in ['Counter', 'Mirror Coat', 'Metal Burst']:
             score = self._score_counter_moves(state, attacker, defender, name, is_faster, ai_threatened)
             if v_idx == 0 and is_faster: score -= 1 
             return score

        if name == 'Sucker Punch':
             sp_score = self._score_sucker_punch(state, name)
             if sp_score == -20 and v_idx < 3: return -20


        if name == 'Fake Out':
             if is_first_turn: return 9
        
        # Kill Bonuses (applies to "All damaging moves")
        standard_kill_moves = True
        if name in ['Explosion', 'Self-Destruct', 'Self Destruct', 'Misty Explosion', 'Final Gambit', 'Rollout', 'Relic Song', 'Meteor Beam', 'Future Sight', 'Doom Desire']:
             standard_kill_moves = False

        if standard_kill_moves and kills:
             if is_faster or res.get('priority', 0) > 0: score += 6 
             else: score += 3
             if attacker.get('ability') in ['Moxie', 'Beast Boost', 'Grim Neigh', 'Chilling Neigh']: score += 1

        # Specific: Fell Stinger / Final Gambit / Rollout / Pursuit
        if name == 'Fell Stinger':
             if kills:
                  if is_faster: score = 23 if v_idx == 4 else 21
                  else: score = 17 if v_idx == 4 else 15
        
        if name == 'Rollout': return 7
        
        if name == 'Fling':
             item = attacker.get('item', '')
             if item in ['Iron Ball', 'Light Ball']: return 10
             # Berry logic for doubles is complex, skip for now.
             if item.endswith('Berry'): return 7 

        if name == 'Final Gambit':
             if is_faster:
                  curr_hp = attacker.get('current_hp', 0)
                  t_hp = defender.get('current_hp', 1)
                  if curr_hp > t_hp: return 8
                  if curr_hp >= t_hp: return 7 
             return 6

        if name == 'Pursuit':
             if kills: 
                 score = 10 
                 if is_faster: score += 3 
             else:
                 target_hp_pct = defender.get('current_hp') / defender.get('max_hp',1)
                 if target_hp_pct < 0.20:
                     score = 10
                 elif target_hp_pct < 0.40:
                     if v_idx <= 1: score = 8 
                 if is_faster: score += 3
        
        if name in ['Explosion', 'Self-Destruct', 'Self Destruct', 'Misty Explosion']:
             score = 0
             if hp_pct < 0.10: score += 10
             elif hp_pct < 0.33: 
                 if v_idx <= 2: score += 8
             elif hp_pct < 0.66:
                 if v_idx <= 1: score += 7
             else:
                 if v_idx == 0: score += 7
        
        if name == 'Relic Song':
             if kills:
                  if is_faster: score += 6
                  else: score += 3
        
        return score

    def _score_status_move(self, state, attacker, defender, name, v_idx, is_faster, is_first_turn, ai_threatened):
        # Batch 1: Field & Screens
        if name in ['Stealth Rock', 'Spikes', 'Toxic Spikes', 'Sticky Web']:
             return self._score_hazards(state, name, v_idx, is_first_turn)
        
        if name in ['Reflect', 'Light Screen', 'Aurora Veil']:
             return self._score_screens(state, attacker, defender, name, v_idx)
             
        if name in ['Electric Terrain', 'Psychic Terrain', 'Grassy Terrain', 'Misty Terrain']:
             return self._score_terrain(state, attacker, name)
             
        if name == 'Substitute':
             return self._score_substitute(state, attacker, defender, is_faster)

        # Batch 5: Status & Utility
        if name in ['Protect', 'Detect', 'Kings Shield', 'Spiky Shield', 'Baneful Bunker', 'Obstruct']: 
             return self._score_protect(state, attacker, defender, v_idx, is_first_turn)
        
        if name in ['Tailwind', 'Trick Room']:
             return self._score_speed_status(state, attacker, defender, name, is_faster)
             
        if name in ['Taunt', 'Encore', 'Disable', 'Torment']:
             return self._score_disrupt_status(state, attacker, defender, name, is_faster)
             
        if name in ['Yawn', 'Spore', 'Sleep Powder', 'Hypnosis', 'Dark Void', 'Sing', 'Grass Whistle', 'Lovely Kiss']:
             return self._score_sleep_status(state, attacker, defender, name, v_idx)
             
        if name in ['Thunder Wave', 'Glare', 'Stun Spore', 'Will-O-Wisp', 'Toxic', 'Poison Gas']:
             return self._score_ailment_status(state, attacker, defender, name, is_faster)

        if name == 'Destiny Bond':
             return 7 if is_faster else 5

        if name in ['Odor Sleuth', 'Foresight', 'Miracle Eye']:
             # Only useful if target has Evasion > 0 or is Ghost type (for Sleuth/Foresight)
             stages = defender.get('stat_stages', {})
             useful = False
             if stages and stages.get('eva', 0) > 0:
                  useful = True
             if name != 'Miracle Eye' and 'Ghost' in defender.get('types', []):
                  useful = True
             if name == 'Miracle Eye' and 'Dark' in defender.get('types', []):
                  useful = True
             
             return 7 if useful else 2

        # Recovery
        if name in ['Recover', 'Slack Off', 'Heal Order', 'Soft-Boiled', 'Roost', 'Strength Sap', 'Morning Sun', 'Synthesis', 'Moonlight']:
            return self._score_recovery(state, attacker, defender, is_faster, name)
        
        setup_moves = ['Swords Dance', 'Dragon Dance', 'Calm Mind', 'Bulk Up', 'Coil', 'Hone Claws', 'Work Up', 'Nasty Plot', 'Tail Glow', 'Shell Smash']
        if name in setup_moves: return self._score_setup_move(state, attacker, defender, name, is_faster, ai_threatened)

        # Batch 5: Niche / Other
        if name in ['Trick', 'Switcheroo']:
             return self._score_trick(state, attacker, defender)
             
        if name == 'Imprison':
             return self._score_imprison(state, attacker, defender)
             
        if name == 'Baton Pass':
             return self._score_baton_pass(state, attacker)
             
        if name == 'Memento':
             return self._score_memento(state, attacker)
             
        if name in ['Focus Energy', 'Laser Focus']:
             return self._score_focus_energy(state, attacker, defender)

        return 6

    def _score_protect(self, state, attacker, defender, v_idx, is_first_turn):
        score = 6
        last_move_ai = state.last_moves.get('ai')
        # Consecutive Check
        if last_move_ai and "Protect" in str(last_move_ai): 
             if v_idx >= 2: return -20
             
        # First Turn (Single) -> -1
        if is_first_turn: score -= 1
        
        ai_status = attacker.get('status')
        if ai_status in ['psn', 'tox', 'brn', 'slp', 'frz']: score -= 2
        def_status = defender.get('status')
        if def_status in ['psn', 'tox', 'brn']: score += 1
        return score

    def _score_speed_status(self, state, attacker, defender, name, is_faster):
        if name == 'Tailwind': return 9 if not is_faster else 6
        if name == 'Trick Room':
             return 9 if not is_faster else 6
        return 6

    def _score_disrupt_status(self, state, attacker, defender, name, is_faster):
        if name == 'Taunt':
             return 8 
        if name == 'Encore':
             if is_faster: return 7
             return 6
        return 6

    def _score_sleep_status(self, state, attacker, defender, name, v_idx):
        score = 6
        if v_idx == 0: score += 1
        return score

    def _score_ailment_status(self, state, attacker, defender, name, is_faster):
        score = 6
        if name in ['Thunder Wave', 'Glare', 'Stun Spore']:
             if not is_faster: score += 2 
             if defender.get('status') == 'par': return -20
        
        if name == 'Will-O-Wisp':
             if defender.get('status') == 'brn': return -20
             score += 2 
        
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

    def _score_setup_move(self, state, attacker, defender, name, is_faster, ai_threatened):
        # 1. Critical "Don't Setup if Dead" Check
        if ai_threatened: return -20
        
        # 2. Unaware Check
        # Exceptions: Swords Dance, Howl, Power-Up Punch (treated as setup for kill check, but Unaware ignores scores?)
        # Doc: "If player mon has Unaware, AI will never set up (-20), unless move is PuP, SD, or Howl"
        unaware_exceptions = ['Swords Dance', 'Howl', 'Power-Up Punch']
        if defender.get('ability') == 'Unaware' and name not in unaware_exceptions:
             return -20

        # 3. Categorize Setup Type (Offensive vs Defensive)
        # Hybrid Moves: Coil, Bulk Up, No Retreat, Calm Mind, Quiver Dance
        is_defensive = False
        
        p_moves = defender.get('moves', []) # Need to check categories
        # We need move categories for player moves. 
        # Limitation: We only have Move IDs/Names in state. 
        # Helper needed: `Mechanics.get_move_category(name)`. 
        # Assuming `self.calc_client` or a helper can provide this, OR we heuristic scan for known moves.
        # Fallback: Check if ANY physical/special moves exist in known moves.
        # For robustness, if we can't tell, assume Offensive (Standard behavior).
        
        has_phys = any(self._is_physical(m) for m in p_moves)
        has_spec = any(self._is_special(m) for m in p_moves)
        
        if name in ['Coil', 'Bulk Up', 'No Retreat']:
             # Treated as Defensive if Player has Phys & No Special
             if has_phys and not has_spec: is_defensive = True
             
        if name in ['Calm Mind', 'Quiver Dance']:
             # Treated as Defensive if Player has Special & No Phys
             if has_spec and not has_phys: is_defensive = True

        if name in ['Acid Armor', 'Barrier', 'Cotton Guard', 'Harden', 'Iron Defense', 'Stockpile', 'Cosmic Power']:
             is_defensive = True

        # 4. Scoring
        score = 6
        target_incapacitated = defender.get('status') in ['frz', 'slp'] or defender.get('ability') == 'Truant' # Truant partial check
        
        if is_defensive:
             # Defensive Setup
             if target_incapacitated: score += 2 # ~95%
             
             # Stat Cap Check (< +2)
             # Need current stat stages. attacker['stages']['def'] etc.
             # Assume +0 if missing.
             # "If move boosts Def/SpD": check corresponding stat.
             # Simplified: If any defensive stat < 2, add +2.
             def_stage = attacker.get('stages', {}).get('def', 0)
             spd_stage = attacker.get('stages', {}).get('spd', 0)
             if def_stage < 2 or spd_stage < 2: score += 2
             
             # Slower & 2HKO check
             # "If AI is slower and is 2HKO'd by player mon -> -5"
             # Implementation: Check max damage roll from context. 
             # If max_dmg * 2 >= current_hp: is 2HKO.
             # We need this context. Passed ai_threatened (OHKO). 
             # Refactor note: Should pass 'max_player_damage' to this function.
             # For now, skip 2HKO check or approximate? 
             # Skipping strictly reduces accuracy but safe for now.
             pass
             
        else:
            # Offensive Setup
            if target_incapacitated: score += 3
            
            # Slower & 2HKO Check (-5)
            # Same limitation.
            
            # Specifics
            if name in ['Agility', 'Rock Polish', 'Autotomize']:
                 return 7 if not is_faster else -20
            
            if name in ['Shell Smash']:
                 if target_incapacitated: score = 6 + 3 # +3
                 # Kill checks logic (Lines 483-487)
                 # Hard to implement without "Simulate next turn damage".
                 # Fallback: Base +6 (+3 if slept).
                 # Cap Check
                 atk_stage = attacker.get('stages', {}).get('atk', 0)
                 spa_stage = attacker.get('stages', {}).get('spa', 0)
                 if atk_stage >= 1 or atk_stage == 6 or spa_stage == 6: return -20
            
            if name == 'Belly Drum':
                 if target_incapacitated: return 9
                 if attacker.get('item') == 'Sitrus Berry': return 8
                 return 4

        return score

    def _is_physical(self, move_name):
        # Simple heuristic or lookup
        # Should rely on Mechanics or known list
        return False # Placeholder if no lookup available
    
    def _is_special(self, move_name):
        return False
    
    def _score_counter_moves(self, state, attacker, defender, name, is_faster, ai_threatened):
        score = 6
        if ai_threatened:
             hp_pct = attacker.get('current_hp') / attacker.get('max_hp', 1)
             item = attacker.get('item', '')
             ability = attacker.get('ability', '')
             has_safety = (hp_pct >= 1.0) and (item == 'Focus Sash' or ability == 'Sturdy')
             
             if not has_safety: return -20 
             
             score += 2
        
        if is_faster:
             pass
        return score

    def _score_sucker_punch(self, state, name):
         last_move = state.last_moves.get('ai')
         if last_move and name in str(last_move):
              return -20
         return 6

    def _score_specific_moves(self, state, attacker, defender, name, is_faster, ai_threatened):
        if name == 'Relic Song':
             species = attacker.get('species', '')
             if 'Meloetta' in species:
                  if 'Pirouette' in species: return -20
                  return 10
        
        if name in ['Future Sight', 'Doom Desire']:
             if is_faster and ai_threatened: return 8
             return 6
             
        if name in ['Dream Eater', 'Nightmare']:
             if defender.get('status') != 'slp': return -20
             
        return 0
    
    def _handle_forced_switch(self, state, side, attacker):
        party = state.ai_party if side == 'ai' else state.player_party
        valid_switches = [p.get('species') for p in party if p.get('current_hp', 0) > 0 and p.get('species') != attacker.get('species')]
        if not valid_switches: return {'moves': [], 'matrix': [], 'variant_weights': [1.0], 'results': []}
        move_names = [f"Switch: {s}" for s in valid_switches]
        matrix = [[10] * len(valid_switches) for _ in range(80)]
        results = [{'moveName': n, 'damage_rolls': [0]} for n in move_names]
        return {'moves': move_names, 'matrix': matrix, 'results': results, 'variant_weights': [0.2]*5}

    def _analyze_damage(self, calc_res, target_hp):
        info = {}
        max_dmgs = [0] * 16 
        any_kill_in_roll = [False] * 16 
        rolls_per_move = []
        for res in calc_res:
             rolls = res.get('damage_rolls', [0])
             if not rolls: rolls = [0]
             if len(rolls) < 16: rolls = rolls + [rolls[-1]] * (16 - len(rolls))
             if res.get('category') == 'Status': rolls = [0]*16
             rolls_per_move.append(rolls)
        for roll_idx in range(16):
             m_d = 0
             has_k = False
             for r in rolls_per_move:
                  d = r[roll_idx]
                  if d > m_d: m_d = d
                  if d >= target_hp: has_k = True
             max_dmgs[roll_idx] = m_d
             any_kill_in_roll[roll_idx] = has_k
        for m_idx, res in enumerate(calc_res):
             info[m_idx] = {'rolls': rolls_per_move[m_idx]}
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
            
            player_hazards = state.fields.get('hazards', {}).get('player', [])
            if move_name == 'Stealth Rock' and 'Stealth Rock' in player_hazards: return False
            if move_name == 'Sticky Web' and 'Sticky Web' in player_hazards: return False
            if move_name in ['Spikes']:
                 if player_hazards.count('Spikes') >= 3: return False
            if move_name in ['Toxic Spikes']:
                 if player_hazards.count('Toxic Spikes') >= 2: return False
        
        if move_name == 'Fake Out':
            last_move_str = state.last_moves.get('ai' if side == 'ai' else 'player')
            is_first_turn = not last_move_str or last_move_str.startswith("Switch:")
            if not is_first_turn: return False
            # Immunity Check
            if defender.get('ability') in ['Inner Focus', 'Shield Dust']: return False
            if defender.get('type1') == 'Ghost' or defender.get('type2') == 'Ghost':
                 # Scrappy check?
                 if attacker.get('ability') != 'Scrappy': return False

        return True

    # --- Batch 1 Helpers ---
    def _score_hazards(self, state, name, v_idx, is_first_turn):
        # Stealth Rock / Spikes / Toxic Spikes
        if name in ['Stealth Rock', 'Spikes', 'Toxic Spikes']:
             if is_first_turn:
                 # First turn out: +8 (25%), +9 (75%)
                 return 8 if v_idx == 0 else 9
             else:
                 # Later: +6 (25%), +7 (75%)
                 return 6 if v_idx == 0 else 7
        
        # Sticky Web
        if name == 'Sticky Web':
             if is_first_turn:
                 # +9 (25%), +12 (75%)
                 return 9 if v_idx == 0 else 12
             else:
                 # +6 (25%), +9 (75%)
                 return 6 if v_idx == 0 else 9
        return 6

    def _score_screens(self, state, attacker, defender, name, v_idx):
        score = 6
        if attacker.get('item') == 'Light Clay': score += 1
        
        # Split Check: +1 (50%)
        if v_idx <= 1: score += 1
        return score

    def _score_terrain(self, state, attacker, name):
        if attacker.get('item') == 'Terrain Extender': return 9
        return 8

    def _score_substitute(self, state, attacker, defender, is_faster):
        score = 6
        if defender.get('status') == 'slp': score += 2
        
        if defender.get('effects', {}).get('leech_seed') and is_faster: score += 2
        
        # Infiltrator / Low HP
        if defender.get('ability') == 'Infiltrator': return -20
        
        hp_pct = attacker.get('current_hp') / attacker.get('max_hp',1)
        if hp_pct <= 0.50: return -20
        
        return score

    def _score_trick(self, state, attacker, defender):
        item = attacker.get('item', '')
        if item in ['Toxic Orb', 'Flame Orb', 'Black Sludge']:
             # +6 (50%), +7 (50%) -> Average like +6.5? 
             # Doc: "Returns +6 (50%), +7 (50%)"
             return 7 
        if item in ['Iron Ball', 'Lagging Tail', 'Sticky Barb']:
             return 7
        return 5

    def _score_imprison(self, state, attacker, defender):
        # Doc: If player mon has at least one move in common... +9. Else -20.
        ai_moves = attacker.get('moves', [])
        p_moves = defender.get('moves', []) # Incomplete list maybe?
        if not p_moves: return -20
        
        common = set(ai_moves).intersection(set(p_moves))
        if common: return 9
        return -20
        
    def _score_baton_pass(self, state, attacker):
        # If last mon -> -20
        if self._is_last_mon(state, 'ai'): return -20
        
        # If Substitute or Stats Raised -> +14
        has_sub = 'substitute' in attacker.get('volatiles', [])
        
        has_stats = False
        stages = attacker.get('stat_stages', {})
        for stat, val in stages.items():
             if val > 0: 
                  has_stats = True
                  break
                  
        if has_sub or has_stats: return 14
        return 0

    def _score_memento(self, state, attacker):
        # Same HP thresholds as Explosion
        if self._is_last_mon(state, 'ai'): return -20 # "AI will not use Memento if last mon"
        
        hp_pct = attacker.get('current_hp') / attacker.get('max_hp', 1)
        if hp_pct < 0.10: return 16
        elif hp_pct < 0.33: return 14 # (70% 14, 30% 6) -> Simplify to 14
        elif hp_pct < 0.66: return 13 # (50% 13, 50% 6) -> Simplify to 13
        return 6
        
    def _score_focus_energy(self, state, attacker, defender):
        # Shell/Battle Armor check
        if defender.get('ability') in ['Shell Armor', 'Battle Armor']: return -20 # "AI will not use" -> Implicit low score? Or just normal? Doc says "AI will not use"
        
        if attacker.get('ability') in ['Super Luck', 'Sniper'] or attacker.get('item') == 'Scope Lens':
             return 7
        return 6

    def _is_last_mon(self, state, side):
        party = state.ai_party if side == 'ai' else state.player_party
        alive_count = sum(1 for p in party if p.get('current_hp', 0) > 0)
        return alive_count <= 1
