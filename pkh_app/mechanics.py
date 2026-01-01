
import math

class Mechanics:
    @staticmethod
    def get_effective_stat(mon, stat_name, field=None):
        """
        Calculates effective stat including stages, rich data modifiers, and field effects.
        """
        # 0. Wonder Room Swap
        if field and field.get('wonder_room', 0) > 0:
             if stat_name == 'def': stat_name = 'spd'
             elif stat_name == 'spd': stat_name = 'def'

        base = mon.get('stats', {}).get(stat_name, 1)
        
        # 1. Stat Stages
        stages = mon.get('stat_stages', {})
        stage = stages.get(stat_name, 0)
        
        if stat_name in ['acc', 'eva', 'accuracy', 'evasion']:
             acc_mult = [3, 4, 5, 6, 7, 8, 9]
             if stage >= 0: multiplier = acc_mult[min(6, stage)] / 3.0
             else: multiplier = 3.0 / acc_mult[min(6, abs(stage))]
        else:
             if stage >= 0: multiplier = (2 + stage) / 2.0
             else: multiplier = 2.0 / (2 - stage)
             
        val = base * multiplier
        
        # 2. Rich Data Modifiers
        # Abilities
        rich_ab = mon.get('_rich_ability', {})
        ab_name = rich_ab.get('name')
        
        # Generic onModifyStat logic (Casing matches rich_data: Atk, Def, SpA, SpD, Spe)
        stat_keys = {'atk': 'Atk', 'def': 'Def', 'spa': 'SpA', 'spd': 'SpD', 'spe': 'Spe'}
        key = f"onModify{stat_keys.get(stat_name, stat_name.capitalize())}"
        ab_mod = rich_ab.get(key)
        if isinstance(ab_mod, (int, float)):
            # Guts, Quick Feet, Marvel Scale, Flare/Toxic Boost are handled conditionally below
            conditional_ab = ['Guts', 'Quick Feet', 'Marvel Scale', 'Flare Boost', 'Toxic Boost']
            if ab_name not in conditional_ab:
                val *= ab_mod
        
        # Hardcoded Fallbacks for Stat Multipliers (Huge Power, etc.)
        if ab_name == 'Huge Power' or ab_name == 'Pure Power':
            if stat_name == 'atk': val *= 2
        elif ab_name == 'Gorilla Tactics':
            if stat_name == 'atk': val *= 1.5
        elif ab_name == 'Fur Coat':
            if stat_name == 'def': val *= 2
        elif ab_name == 'Hustle':
            if stat_name == 'atk': val *= 1.5
            
        # Hardcoded Conditional Ability Speed Buffs (Rain Dance, etc)
        if stat_name == 'spe':
            weather = field.get('weather') if field else None
            if weather in ['Rain', 'Rain Dance'] and ab_name == 'Swift Swim': val *= 2
            if weather in ['Sun', 'Sunny Day'] and ab_name == 'Chlorophyll': val *= 2
            if weather in ['Sandstorm', 'Sand'] and ab_name == 'Sand Rush': val *= 2
            if weather in ['Hail', 'Snow'] and ab_name == 'Slush Rush': val *= 2
            terrain = field.get('terrain') if field else None
            if terrain == 'Electric' and ab_name == 'Surge Surfer': val *= 2
            if ab_name == 'Unburden' and mon.get('unburden_active'): val *= 2
            if ab_name == 'Quick Feet' and mon.get('status'): val *= 1.5

        # Items
        if not field or field.get('magic_room', 0) <= 0:
             rich_item = mon.get('_rich_item', {})
             item_mod = rich_item.get(key)
             if isinstance(item_mod, (int, float)):
                 val *= item_mod
             else:
                 # Fallback for common speed items if rich data missing/failed
                 item_name = mon.get('item', '')
                 if stat_name == 'spe':
                     if item_name == 'Iron Ball' or item_name == 'Macho Brace' or 'Power' in str(item_name):
                         val *= 0.5
                     elif item_name == 'Choice Scarf':
                         val *= 1.5
                 elif stat_name == 'atk' and item_name == 'Choice Band':
                     val *= 1.5
                 elif stat_name == 'spa' and item_name == 'Choice Specs':
                     val *= 1.5
                 elif stat_name == 'spd' and item_name == 'Assault Vest':
                     val *= 1.5

        
        # 3. Conditional Rich Modifiers (Ailment-based)
        status = mon.get('status')
        if status:
             # Abilities that trigger on ANY status
             if ab_name == 'Guts' and stat_name == 'atk': val *= 1.5
             if ab_name == 'Quick Feet' and stat_name == 'spe': val *= 1.5
             if ab_name == 'Marvel Scale' and stat_name == 'def': val *= 1.5
             # Abilities that trigger on specific status
             if ab_name == 'Flare Boost' and stat_name == 'spa' and status == 'brn': val *= 1.5
             if ab_name == 'Toxic Boost' and stat_name == 'atk' and status in ['psn', 'tox']: val *= 1.5
        
        # 4. Status Effects (Side Effects)
        status = mon.get('status')
        if status == 'brn' and stat_name == 'atk' and ab_name != 'Guts':
             val *= 0.5
        # if status == 'par' and stat_name == 'spe' and ab_name != 'Quick Feet':
        #      val *= 0.5 # Handled in Post-Modifiers as 0.25
        
        # 4. Ally Modifiers (Awareness Expansion)
        if field and field.get('allies'):
             side = mon.get('side')
             ally = field['allies'].get(side)
             if ally:
                  ally_rich_ab = ally.get('_rich_ability', {})
                  ally_key = f"onAlly{key}" # e.g. onAllyModifyAtk
                  ally_mod = ally_rich_ab.get(ally_key)
                  if isinstance(ally_mod, (int, float)):
                       # Check condition (e.g. Flower Gift needs Sun)
                       ally_ab_name = ally_rich_ab.get('name')
                       if ally_ab_name == 'Flower Gift':
                            if field.get('weather') not in ['Sun', 'Sunny Day']: 
                                 ally_mod = 1.0
                       val *= ally_mod
                   
                  # Minus / Plus (Generic 1.5x if ally has Minus/Plus)
                  if (ab_name in ['Minus', 'Plus']) and stat_name == 'spa':
                       if ally_rich_ab.get('name') in ['Minus', 'Plus']:
                            val *= 1.5
                
        # Hardcoded Speed Drop for Weight Items (if rich data misses them)
        if stat_name == 'spe':
            item_name = mon.get('item', '')
            if item_name in ['Iron Ball', 'Macho Brace', 'Power Bracer', 'Power Belt', 'Power Lens', 'Power Band', 'Power Anklet', 'Power Weight']:
                val *= 0.5
        
        # 3. Special Post-Modifiers (Tailwind, Paralysis)
        if stat_name == 'spe':
            # Paralysis (Run & Bun)
            if mon.get('status') == 'par' and (not rich_ab or rich_ab.get('name') != 'Quick Feet'):
                 val *= 0.25
            # Tailwind
            if field and field.get('tailwind'):
                 side = mon.get('side')
                 if side and field['tailwind'].get(side, 0) > 0:
                      val *= 2

        return int(val)

    @staticmethod
    def check_accuracy(attacker, defender, move_data, field, log=None):
        """
        Determines if a move hits using Gen 8 mechanics.
        Returns True (Hit) or False (Miss).
        """
        move_acc = move_data.get('accuracy')
        
        # 0. Always Hit Moves
        if move_acc is None or move_acc is True:
             return True

        # No Guard
        if attacker.get('ability') == 'No Guard' or defender.get('ability') == 'No Guard':
             return True

        # Wonder Skin (Status moves > 50% acc become 50% base)
        if defender.get('ability') == 'Wonder Skin' and move_data.get('category') == 'Status' and move_acc > 50:
             move_acc = 50
        # 1. Accuracy Stage (Attacker)
        acc_stage = attacker.get('stat_stages', {}).get('acc', 0)
        acc_mult = [3/3, 4/3, 5/3, 6/3, 7/3, 8/3, 9/3]
        if acc_stage >= 0:
             acc_mod = acc_mult[min(6, acc_stage)]
        else:
             acc_mod = 3 / (3 + abs(acc_stage)) # 3/4, 3/5...
             
        # 2. Evasion Stage (Defender)
        eva_stage = defender.get('stat_stages', {}).get('eva', 0)
        # Apply strict rules: (Acc - Eva) is usually how it's done for stages combined?
        # Actually standard formula is: Mods * AccStage * (1/EvaStage) ?
        # No, Gen 3+ uses strict table lookups on (Acc - Eva).
        # We'll stick to independent modifiers for simplicity or combined stage.
        # Standard: Stage = AccStage - EvaStage. Cap at +6/-6.
        
        # Ignore Evasion if Forewarn/Keen Eye? (Keen Eye ignores drops in Acc, not Eva raises? No, ignores Eva raises)
        # Let's simplify:
        combined_stage = acc_stage - eva_stage
        combined_stage = max(-6, min(6, combined_stage))
        
        stage_mults = {
            -6: 3/9, -5: 3/8, -4: 3/7, -3: 3/6, -2: 3/5, -1: 3/4,
             0: 3/3,
             1: 4/3, 2: 5/3, 3: 6/3, 4: 7/3, 5: 8/3, 6: 9/3
        }
        mod = stage_mults.get(combined_stage, 1.0)
        
        # 3. Item Modifiers
        # Attacker
        item = attacker.get('item', '')
        if item == 'Wide Lens': mod *= 1.1
        if item == 'Zoom Lens' and field.get('context', {}).get('user_moved_last'): mod *= 1.2
        
        # Defender
        def_item = defender.get('item', '')
        if def_item == 'Bright Powder' or def_item == 'Lax Incense': mod *= 0.9
        
        # 4. Ability Modifiers
        # Hustle (Applied to modifier)
        ab_name = attacker.get('_rich_ability', {}).get('name') or attacker.get('ability')
        if ab_name == 'Hustle' and move_data.get('category') == 'Physical':
             mod *= 0.8

        if attacker.get('ability') == 'Compound Eyes': mod *= 1.3
        if defender.get('ability') == 'Sand Veil' and field.get('weather') in ['Sand', 'Sandstorm']: mod *= 0.8
        if defender.get('ability') == 'Snow Cloak' and field.get('weather') in ['Hail', 'Snow']: mod *= 0.8
        if defender.get('ability') == 'Tangled Feet' and defender.get('confused'): mod *= 0.5
        
        # Victory Star (1.1x accuracy for user)
        if attacker.get('ability') == 'Victory Star': mod *= 1.1
        
        # 5. Field
        # Gravity (1.67x accuracy)
        if field.get('gravity'): mod *= 5/3
        
        # Calculate Final Accuracy
        final_acc = move_acc * mod
        
        # OHKO Moves? (Handled mostly by 'accuracy': True or specific logic, but if they have 30, we handle it)
        # OHKO moves ignore stages.
        if move_data.get('ohko'):
             final_acc = move_acc # Raw 30 usually.
             # Level difference logic?
             # Run & Bun simplification: 30% flat for now.
             
        # Roll
        # Standard: r = random(0..99). If r < final_acc, Hit.
        import random
        hit = random.random() * 100 < final_acc
        
        if not hit and log is not None:
             log.append(f"  {attacker.get('species')} used {move_data.get('name')} but missed!")
             
        return hit

    @staticmethod
    def _is_status_immune(state, mon, status, attacker=None, log=None):
        # 0. Uproar check for Sleep
        if status == 'slp':
             # Check if anyone is making an Uproar
             for p in [state.player_active, state.ai_active]:
                  if 'uproar' in p.get('volatiles', []):
                       if log: log.append(f"  But everyone is too loud to sleep! (Uproar)")
                       return True
             if mon.get('ability') == 'Sweet Veil':
                  if log: log.append(f"  {mon.get('species')} is protected by Sweet Veil!")
                  return True

        # Safeguard Check
        sc = state.fields.get('screens', {})
        side = mon.get('side', 'player') # Usually set in get_effective_speed or similar
        if sc.get(side, {}).get('safeguard', 0) > 0:
             if log: log.append(f"  {mon.get('species')} is protected by Safeguard!")
             return True

        if mon.get('ability') == 'Overcoat' and status == 'slp': # Simplified
             return True

    @staticmethod
    def get_effective_speed(mon, field, side=None):
        # Compatibility wrapper for existing calls
        if side: mon['side'] = side # Temporary inject for tailwind check
        val = Mechanics.get_effective_stat(mon, 'spe', field)
        
        # Simple Quick Powder Check (Ditto -> 2x Speed)
        # Note: Usually this is in get_effective_stat modifiers, but we inject here for simplicity.
        if mon.get('item') == 'Quick Powder' and 'Ditto' in mon.get('species', ''):
             # Transformed check usually applies (Quick Powder fails if transformed).
             # Assuming 'transformed' flag or species change handled elsewhere.
             # If species is still Ditto, it applies.
             val *= 2
             
        return val

    @staticmethod
    def get_mon_data(species_name):
        """
        Retrieves base stats (and type) for a species from pokedex_rich.json
        """
        # We need to cache this or load it efficiently. For now, load on demand (slow but works).
        # Better: BattleEngine should pass this context. 
        # But this method is static.
        # Let's assume the caller handles caching or we do a simple file read.
        import json
        import os
        try:
             # Locate pokedex_rich.json relative to this file
             path = os.path.join(os.path.dirname(__file__), '../data/pokedex_rich.json')
             with open(path, 'r') as f:
                  dex = json.load(f)
             
             # Normalize key
             key = species_name.lower().replace(" ", "").replace("-", "").replace(".", "").replace("'", "")
             # Handle forms crudely if needed, but standard normalization handles most
             return dex.get(key, {})
        except Exception:
             return {}


    @staticmethod
    def apply_end_turn_effects(state, log):
        # 0. Decrement Field Effects
        f = state.fields
        
        # Weather
        if f.get('weather'):
            turns = f.get('weather_turns', 0) - 1
            f['weather_turns'] = turns
            if turns <= 0:
                log.append(f"The {f['weather']} subsided.")
                f['weather'] = None
        
        # Terrain
        if f.get('terrain'):
            turns = f.get('terrain_turns', 0) - 1
            f['terrain_turns'] = turns
            if turns <= 0:
                log.append(f"The {f['terrain']} terrain wore off.")
                f['terrain'] = None

        # Tailwind
        tw = f.get('tailwind', {})
        for side in ['player', 'ai']:
            if tw.get(side, 0) > 0:
                tw[side] -= 1
                if tw[side] <= 0:
                    log.append(f"The Tailwind behind {side.upper()} side petered out.")

        # Screens
        sc = f.get('screens', {})
        for side in ['player', 'ai']:
            side_screens = sc.get(side, {})
            for screen in list(side_screens.keys()):
                if side_screens[screen] > 0:
                    side_screens[screen] -= 1
                    if side_screens[screen] <= 0:
                        log.append(f"{screen.replace('_', ' ').title()} wore off on {side.upper()} side.")

        # Trick Room
        if f.get('trick_room', 0) > 0:
            f['trick_room'] -= 1
            if f['trick_room'] <= 0:
                log.append("The dimensions returned to normal.")

        # Rooms & Gravity
        for k, msg in [('magic_room', "The magic room subsided."), 
                         ('wonder_room', "The wonder room subsided."), 
                         ('gravity', "Gravity returned to normal.")]:
             if f.get(k, 0) > 0:
                  f[k] -= 1
                  if f[k] <= 0:
                       log.append(msg)
        
        # Ion Deluge (Immediate clear)
        if f.pop('ion_deluge', None):
             log.append("The deluge of ions subsided.")
        
        # 0.4 Wish
        if f.get('wish_turns', 0) > 0:
             f['wish_turns'] -= 1
             if f['wish_turns'] <= 0:
                  for side in ['player', 'ai']:
                       mon = state.player_active if side == 'player' else state.ai_active
                       if mon and mon.get('current_hp', 0) > 0:
                            heal = f.get('wish_hp', 0)
                            mon['current_hp'] = min(mon.get('max_hp'), mon['current_hp'] + heal)
                            log.append(f"  {mon.get('species')}'s wish came true! (+{heal})")
                  f['wish_hp'] = 0

        # 1. Weather / Status / Passives
        weather = state.fields.get('weather')
        all_active = [state.player_active, state.ai_active]
        
        # 1.0 Status Orbs (Flame Orb, Toxic Orb) - Inflict status at end of turn
        for mon in all_active:
            if not mon or mon.get('current_hp', 0) <= 0:
                continue
            
            item = mon.get('item')
            if item == 'Flame Orb' and not mon.get('status'):
                mon['status'] = 'brn'
                mon['item'] = None  # Consume
                log.append(f"  {mon.get('species')} was burned by its Flame Orb!")
            elif item == 'Toxic Orb' and not mon.get('status'):
                mon['status'] = 'tox'
                mon['toxic_counter'] = 1
                mon['item'] = None  # Consume
                log.append(f"  {mon.get('species')} was badly poisoned by its Toxic Orb!")
        
        for mon in all_active:
            if not mon or mon.get('current_hp', 0) <= 0:
                continue
                
            # 1.1 Status Residuals (Burn/Poison) - Handled in second loop (lines 498+) for better Ability support (Poison Heal/Heatproof)
            # Removed duplicate block here.


            # 1.2 Volatile Residuals (Leech Seed, Aqua Ring, Ingrain)
            vols = mon.get('volatiles', [])
            if 'leechseed' in vols and mon.get('ability') != 'Magic Guard':
                 dmg = int(mon.get('max_hp', 100) / 8)
                 mon['current_hp'] = max(0, mon['current_hp'] - dmg)
                 log.append(f"  {mon.get('species')} was hurt by Leech Seed! (-{dmg})")
                 # Heal other mon
                 other = state.ai_active if mon == state.player_active else state.player_active
                 if other and other['current_hp'] > 0:
                      other['current_hp'] = min(other.get('max_hp'), other['current_hp'] + dmg)
                      log.append(f"  {other.get('species')} regained HP via Leech Seed!")
                      
            # 1.25 Uproar (Sleep prevention)
            uproar_active = False
            for p in all_active:
                 if 'uproar' in p.get('volatiles', []): uproar_active = True
                 
            if 'aquaring' in vols:
                 heal = int(mon.get('max_hp', 100) / 16)
                 mon['current_hp'] = min(mon.get('max_hp'), mon['current_hp'] + heal)
                 log.append(f"  A veil of water restored {mon.get('species')}'s HP!")
                 
            if 'ingrain' in vols:
                 heal = int(mon.get('max_hp', 100) / 16)
                 mon['current_hp'] = min(mon.get('max_hp'), mon['current_hp'] + heal)
                 log.append(f"  {mon.get('species')} restored HP via its roots!")

            if 'partiallytrapped' in vols and mon.get('current_hp', 0) > 0 and mon.get('ability') != 'Magic Guard':
                 dmg = int(mon.get('max_hp', 100) / 8)
                 mon['current_hp'] = max(0, mon['current_hp'] - dmg)
                 log.append(f"  {mon.get('species')} is hurt by the trap! (-{dmg})")

            # 1.3 Delayed States (Yawn, Perish Song)
            # Simplified: We just note they exist for now.
            if 'yawn' in vols:
                 mon.setdefault('yawn_turns', 2)
                 mon['yawn_turns'] -= 1
                 if mon['yawn_turns'] <= 0:
                      mon['status'] = 'slp'
                      mon['status_counter'] = 2
                      vols.remove('yawn')
                      log.append(f"  {mon.get('species')} fell asleep!")
                      
            if 'perish3' in vols:
                 vols.remove('perish3')
                 vols.append('perish2')
                 log.append(f"  {mon.get('species')}'s perish count fell to 2.")
            elif 'perish2' in vols:
                 vols.remove('perish2')
                 vols.append('perish1')
                 log.append(f"  {mon.get('species')}'s perish count fell to 1.")
            elif 'perish1' in vols:
                 vols.remove('perish1')
                 mon['current_hp'] = 0
                 log.append(f"  {mon.get('species')}'s perish count fell to 0! It fainted!")

            # 1.4 Salt Cure / Syrup Bomb
            if 'saltcure' in vols and mon.get('ability') != 'Magic Guard':
                 # 1/4 if Water/Steel, 1/8 otherwise
                 is_water_steel = 'Water' in mon.get('types', []) or 'Steel' in mon.get('types', [])
                 dmg_ratio = 4 if is_water_steel else 8
                 dmg = max(1, int(mon.get('max_hp', 100) / dmg_ratio))
                 mon['current_hp'] = max(0, mon['current_hp'] - dmg)
                 log.append(f"  {mon.get('species')} is being salt cured! (-{dmg})")
                 
            if 'syrupbomb' in vols:
                 # Reduce Speed each turn
                 Mechanics.apply_boosts(mon, {'spe': -1}, log, source_name='Syrup Bomb')
                 
            if 'magnetrise' in vols:
                 mon['magnet_rise_turns'] = mon.get('magnet_rise_turns', 5) - 1
                 if mon['magnet_rise_turns'] <= 0:
                      vols.remove('magnetrise')
                      log.append(f"  {mon.get('species')}'s Magnet Rise wore off.")
            
            # Nightmare damage
            if 'nightmare' in vols and mon.get('status') == 'slp':
                 dmg = int(mon.get('max_hp', 100) / 4)
                 mon['current_hp'] = max(0, mon['current_hp'] - dmg)
                 log.append(f"  {mon.get('species')} is locked in a nightmare! (-{dmg})")
            
            # Embargo/Heal Block timers
            if 'embargo' in vols:
                 mon['embargo_turns'] = mon.get('embargo_turns', 5) - 1
                 if mon['embargo_turns'] <= 0:
                      vols.remove('embargo')
                      log.append(f"  {mon.get('species')} can use items again!")
            
            if 'healblock' in vols:
                 mon['heal_block_turns'] = mon.get('heal_block_turns', 5) - 1
                 if mon['heal_block_turns'] <= 0:
                      vols.remove('healblock')
                      log.append(f"  {mon.get('species')}'s Heal Block wore off!")
            
            # Octolock stat drops
            if 'octolock' in vols:
                 Mechanics.apply_boosts(mon, {'def': -1, 'spd': -1}, log, source_name='Octolock', field=state.fields)
            
            # Telekinesis timer
            if 'telekinesis' in vols:
                 mon['telekinesis_turns'] = mon.get('telekinesis_turns', 3) - 1
                 if mon['telekinesis_turns'] <= 0:
                      vols.remove('telekinesis')
                      log.append(f"  {mon.get('species')} was freed from telekinesis!")
             
        for mon in all_active:
            if mon.get('current_hp') <= 0: continue
            
            ability = mon.get('ability', '')
            item = mon.get('item', '')
            max_hp = mon.get('max_hp', 100)
            
            # Weather Damage
            if weather in ['Sandstorm', 'Sand']:
                if 'Ground' not in mon['types'] and 'Rock' not in mon['types'] and 'Steel' not in mon['types']:
                    if ability not in ['Sand Force', 'Sand Rush', 'Sand Veil', 'Magic Guard', 'Overcoat']:
                        loss = max(1, int(max_hp / 16))
                        mon['current_hp'] -= loss
                        log.append(f"  {mon.get('species')} buffeted by Sand (-{loss})")
                        
            elif weather == 'Hail':
                if 'Ice' not in mon['types']:
                     if ability not in ['Ice Body', 'Snow Cloak', 'Magic Guard', 'Overcoat']:
                        loss = max(1, int(max_hp / 16))
                        mon['current_hp'] -= loss
                        log.append(f"  {mon.get('species')} buffeted by Hail (-{loss})")
            
            # Status Damage
            status = mon.get('status')
            if status == 'psn':
                loss = max(1, int(max_hp / 8))
                if ability == 'Poison Heal':
                    mon['current_hp'] = min(max_hp, mon['current_hp'] + loss)
                    log.append(f"  {mon.get('species')} healed by Poison Heal (+{loss})")
                elif ability != 'Magic Guard':
                    mon['current_hp'] -= loss
                    log.append(f"  {mon.get('species')} hurt by poison (-{loss})")
            elif status == 'tox':
                # Simplified Toxic: increase counter
                cnt = mon.get('toxic_counter', 0) + 1
                mon['toxic_counter'] = cnt
                loss = max(1, int(max_hp * cnt / 16))
                if ability == 'Poison Heal':
                    mon['current_hp'] = min(max_hp, mon['current_hp'] + max(1, int(max_hp / 8)))
                elif ability != 'Magic Guard':
                    mon['current_hp'] -= loss
                    log.append(f"  {mon.get('species')} hurt by Toxic (-{loss})")
            elif status == 'brn':
                loss = max(1, int(max_hp / 16))
                if ability == 'Heatproof': loss = int(loss / 2)
                if ability != 'Magic Guard':
                    mon['current_hp'] -= loss
                    log.append(f"  {mon.get('species')} hurt by Burn (-{loss})")
                    
            # 1b. Generic Residuals (Abilities & Items)
            # Ability Residual
            ab_rich = mon.get('_rich_ability', {})
            hr = ab_rich.get('healRatio')
            if hr and isinstance(hr, (list, tuple)) and len(hr) >= 2:
                factor = hr[0] / hr[1]
                # Check for specific conditions
                if ability == 'Poison Heal':
                    if mon.get('status') not in ['psn', 'tox']: factor = 0
                elif ability == 'Solar Power' and weather not in ['Sun', 'Sunny Day']: factor = 0
                elif ability == 'Dry Skin' and weather not in ['Rain', 'Rain Dance']: factor = 0
                elif ability == 'Disguise': factor = 0
                elif ability in ['Volt Absorb', 'Water Absorb', 'Flash Fire', 'Lightning Rod', 'Motor Drive', 'Sap Sipper', 'Storm Drain']: factor = 0
                
                if factor != 0:
                    delta = int(max_hp * factor)
                    is_dmg = ability in ['Solar Power', 'Dry Skin'] and weather in ['Sun', 'Sunny Day']
                    
                    if is_dmg:
                         mon['current_hp'] -= delta
                         log.append(f"  {mon.get('species')} hurt by {ability} (-{delta})")
                    else:
                         old_hp = mon['current_hp']
                         mon['current_hp'] = min(max_hp, mon['current_hp'] + delta)
                         if mon['current_hp'] > old_hp:
                             log.append(f"  {mon.get('species')} restored HP (+{delta})")

            # Item Residual
            it_rich = mon.get('_rich_item')
            it_hr = it_rich.get('healRatio') if it_rich else None
            if it_hr and isinstance(it_hr, (list, tuple)) and len(it_hr) >= 2:
                factor = it_hr[0] / it_hr[1]
                if item == 'Black Sludge' and 'Poison' not in mon.get('types', []):
                     loss = int(max_hp / 8)
                     mon['current_hp'] -= loss
                     log.append(f"  {mon.get('species')} hurt by Black Sludge (-{loss})")
                elif item == 'Sticky Barb':
                     loss = int(max_hp / 8)
                     mon['current_hp'] -= loss
                     log.append(f"  {mon.get('species')} hurt by Sticky Barb (-{loss})")
                else:
                     heal = int(max_hp * factor)
                     old_hp = mon['current_hp']
                     mon['current_hp'] = min(max_hp, mon['current_hp'] + heal)
                     if mon['current_hp'] > old_hp:
                         log.append(f"  {mon.get('species')} healed by {item} (+{heal})")
                     
            # Ability
            if ability == 'Speed Boost':
                stages = mon.setdefault('stat_stages', {})
                current_spe = stages.get('spe', 0)
                if current_spe < 6:
                    stages['spe'] = current_spe + 1
                    log.append(f"  {mon.get('species')} Speed Boost!")
            elif ability == 'Shed Skin':
                if mon.get('status') and hash(str(state.get_hash())) % 100 < 30:
                    mon['status'] = None
                    log.append(f"  {mon.get('species')} Shed Skin!")
            elif ability == 'Hydration' and weather in ['Rain', 'Rain Dance']:
                if mon.get('status'):
                     mon['status'] = None
                     log.append(f"  {mon.get('species')} Hydration cured its status!")
            elif ability == 'Rain Dish' and weather in ['Rain', 'Rain Dance']:
                heal = max(1, int(max_hp / 16))
                old_hp = mon['current_hp']
                mon['current_hp'] = min(max_hp, mon['current_hp'] + heal)
                if mon['current_hp'] > old_hp:
                     log.append(f"  {mon.get('species')} healed by Rain Dish (+{heal})")
            elif ability == 'Bad Dreams':
                 # Find opponent
                 opponent = state.ai_active if mon == state.player_active else state.player_active
                 if opponent.get('current_hp') > 0 and opponent.get('status') == 'slp':
                      if opponent.get('ability') != 'Magic Guard':
                           loss = max(1, int(opponent.get('max_hp', 100) / 8))
                           opponent['current_hp'] -= loss
                           log.append(f"  {opponent.get('species')} is tormented by Bad Dreams (-{loss})")
            elif ability == 'Moody':
                 stats = ['atk', 'def', 'spa', 'spd', 'spe', 'acc', 'eva']
                 idx = hash(str(state.get_hash()) + 'moody' + str(mon.get('species'))) 
                 up = stats[idx % len(stats)]
                 down = stats[(idx + 1) % len(stats)] # Simple deterministic different choice
                 
                 stages = mon.setdefault('stat_stages', {})
                 curr_up = stages.get(up, 0)
                 if curr_up < 6:
                      stages[up] = min(6, curr_up + 2)
                      log.append(f"  {mon.get('species')}'s {up} rose sharply!")
                 
                 curr_down = stages.get(down, 0)
                 if curr_down > -6:
                      stages[down] = max(-6, curr_down - 1)
                      log.append(f"  {mon.get('species')}'s {down} fell!")
                 last_item = mon.get('_last_consumed_item')
                 if not mon.get('item') and last_item:
                      chance = 100 if weather in ['Sun', 'Sunny Day'] else 50
                      if hash(str(state.get_hash()) + 'harvest' + mon.get('species')) % 100 < chance:
                           mon['item'] = last_item
                           mon['_last_consumed_item'] = None
                           log.append(f"  {mon.get('species')} harvested one {last_item}!")
            elif ability == 'Hunger Switch':
                 if mon.get('species') == 'Morpeko':
                      mon['species'] = 'Morpeko-Hangry'
                      log.append(f"  {mon.get('species')} changed to Hangry Mode!")
                 elif mon.get('species') == 'Morpeko-Hangry':
                      mon['species'] = 'Morpeko'
                      log.append(f"  {mon.get('species')} changed to Full Belly Mode!")
            # Early Bird usually affects sleep turns decremented in start_turn not end_turn.
            # But if status counter is handled here? No, Sleep counter checked in execute_turn.
            # We can leave Early Bird for now or implement a passive reduction?
            # Implemented in execute_turn usually.
            
            # Leech Seed
            if 'leech_seed' in mon.get('volatiles', []):
                drain = max(1, int(max_hp / 8))
                if ability != 'Magic Guard':
                    mon['current_hp'] -= drain
                    log.append(f"  {mon.get('species')} sapped by Leech Seed (-{drain})")
                    opponent = state.ai_active if mon == state.player_active else state.player_active
                    if opponent.get('current_hp') > 0:
                        opponent['current_hp'] = min(opponent.get('max_hp'), opponent['current_hp'] + drain)
            
            # Grassy Terrain
            terrain = state.fields.get('terrain')
            if terrain == 'Grassy' and mon.get('current_hp') > 0:
                 is_flying = 'Flying' in mon.get('types', [])
                 has_levitate = ability == 'Levitate'
                 if not is_flying and not has_levitate and item != 'Air Balloon':
                      heal = max(1, int(max_hp / 16))
                      mon['current_hp'] = min(max_hp, mon['current_hp'] + heal)
                      log.append(f"  {mon.get('species')} healed by Grassy Terrain (+{heal})")

    @staticmethod
    def apply_start_turn_effects(mon, state, log):
        mon['turn_priority_mod'] = 0
        ability = mon.get('ability', '')
        item = mon.get('item', '')

        # 0. Apply Negative Priority First (Stall / Lagging Tail)
        # If both Stall and Lagging Tail are present, it remains -1.
        if ability == 'Stall' or item in ['Lagging Tail', 'Full Incense']:
            mon['turn_priority_mod'] = -1

        # 1. Quick Claw
        if item == 'Quick Claw':
            if hash(str(state.get_hash()) + 'qc' + mon.get('species', '')) % 100 < 20:
                mon['turn_priority_mod'] = 1
                log.append(f"  Quick Claw let {mon.get('species')} move first!")

        # 2. Quick Draw
        # Independent check. If both Quick Claw and Quick Draw proc, it's still just priority +1.
        # But we want to give chance for both to fire (though effect is same).
        # We only log if it affects the outcome? Or log both?
        # Standard behavior: If Quick Claw fires, we don't necessarily check Quick Draw?
        # Actually, they are independent events.
        # If Quick Claw activates, we are already +1.
        # If Quick Draw activates, we are +1.
        # We check both to allow probability stacking (approx 44% total chance).
        if ability == 'Quick Draw':
            if hash(str(state.get_hash()) + 'qd' + mon.get('species', '')) % 100 < 30:
                mon['turn_priority_mod'] = 1
                log.append(f"  Quick Draw let {mon.get('species')} move first!")

        # 3. Custap Berry
        if item == 'Custap Berry':
            threshold = 0.25
            if ability == 'Gluttony': threshold = 0.5
            if mon.get('current_hp') <= mon.get('max_hp', 1) * threshold:
                mon['turn_priority_mod'] = 1
                mon['item'] = None
                log.append(f"  {mon.get('species')}'s Custap Berry activated!")
                log.append(f"  Custap Berry let {mon.get('species')} move first!")
    @staticmethod
    def apply_boosts(mon, boosts, log, source_name=None, field=None):
        """
        Applies a boosts dictionary (e.g. {'atk': 1, 'def': -1}) to a mon.
        """
        if not boosts: return
        
        # 0. Mist Check (If field provided and stats are being lowered)
        if field:
             sc = field.get('screens', {})
             side = mon.get('side')
             if sc.get(side, {}).get('mist', 0) > 0:
                  any_drop = any(v < 0 for v in boosts.values())
                  if any_drop:
                       log.append(f"  {mon.get('species')} is protected by Mist!")
                       # Filter out drops
                       boosts = {k: v for k, v in boosts.items() if v >= 0}
        
        # Contrary check
        rich_ab = mon.get('_rich_ability')
        is_contrary = rich_ab and rich_ab.get('name') == 'Contrary'
        
        stages = mon.setdefault('stat_stages', {})
        source_str = f" from {source_name}" if source_name else ""
        
        for stat, amount in boosts.items():
            if is_contrary:
                amount = -amount
            
            # Stat Drop Prevention (Big Pecks, Keen Eye, Clear Body, etc.)
            # Note: Technically these shouldn't block self-inflicted drops (e.g. Close Combat), 
            # but without source context, we assume protection.
            # Contrary turns drops into raises, so we check amount < 0 AFTER logic.
            # However, Contrary + Big Pecks: Move lowers Def -> Contrary Raises Def -> Big Pecks ignores (positive).
            # Move raises Def -> Contrary Lowers Def -> Big Pecks protects? 
            # (Gen 5+: Mold Breaker can bypass, but we assume standard).
            # Actually, self-inflicted drops via Contrary are usually NOT protected by these abilities.
            # But standard checks usually filter out 'self' source before calling this or use a flag.
            
            if amount < 0:
                 ab = mon.get('ability')
                 if ab == 'Big Pecks' and stat == 'def':
                      log.append(f"  {mon.get('species')}'s Big Pecks prevents defense loss!")
                      continue
                 if ab == 'Keen Eye' and stat in ['acc', 'accuracy']: # 'acc' is internal key
                      log.append(f"  {mon.get('species')}'s Keen Eye prevents accuracy loss!")
                      continue
                 if ab in ['Clear Body', 'White Smoke', 'Full Metal Body'] and stat not in ['accuracy', 'evasion']: # Usually protects all stats
                      log.append(f"  {mon.get('species')}'s {ab} prevents stat loss!")
                      continue
                 if ab == 'Hyper Cutter' and stat == 'atk':
                      log.append(f"  {mon.get('species')}'s Hyper Cutter prevents attack loss!")
                      continue
                
            current = stages.get(stat, 0)
            # Cap at -6/+6
            new_stage = max(-6, min(6, current + amount))
            if new_stage != current:
                stages[stat] = new_stage
                diff = new_stage - current
                direction = "rose" if diff > 0 else "fell"
                severity = ""
                if abs(diff) == 2: severity = " sharply"
                elif abs(diff) >= 3: severity = " drastically"
                
                log.append(f"  {mon.get('species')}'s {stat.upper()} {direction} to {new_stage}{severity}{source_str}!")
            elif amount > 0 and current == 6:
                log.append(f"  {mon.get('species')}'s {stat.upper()} won't go any higher!")
            elif amount < 0 and current == -6:
                log.append(f"  {mon.get('species')}'s {stat.upper()} won't go any lower!")



    @staticmethod
    def get_modifier(mon, key, move_data=None, field=None, target=None):
        """
        Generic modifier retriever for onBasePower, onModifyDamage, etc.
        """
        mod = 1.0
        # print("DEBUG: get_modifier called for loop", getattr(source, "name", "Unknown"), getattr(target, "name", "Unknown"), move_name, loop_name)

        
        # 1. Move itself (Phase 3 Convergence)
        if move_data:
             move_val = move_data.get(key)
             if isinstance(move_val, (int, float)):
                  if Mechanics.test_modifier_condition(move_data, mon, move_data, field, target):
                       mod *= move_val
        
        # Context extraction
        context = field.get('context', {}) if field else {}
        user_moved_last = context.get('user_moved_last', False)
        
        # 2. Ability
        rich_ab = mon.get('_rich_ability', {})
        val = rich_ab.get(key)
        
        # Special Case: Technician (check 'onBasePower' logic internally or here)
        # However, mechanics.json defines 'Technician' with a static float.
        # We rely on test_modifier_condition to gate it.
        
        if val is not None and isinstance(val, (int, float)):
             if Mechanics.test_modifier_condition(rich_ab, mon, move_data, field, target):
                  mod *= val
                  
        # Special Case: Analytic (needs context)
        if rich_ab.get('name') == 'Analytic' and user_moved_last and key == 'onBasePower':
             # Analytic isn't always fully defined in rich data with a conditional
             # So we hardcode the 1.3x check if data is missing or generic
             if not val: mod *= 1.3

        # Sand Force Fallback (Data often missing explicit modifier)
        if key == 'onBasePower' and rich_ab.get('name') == 'Sand Force':
             # Note: test_modifier_condition handles Weather/Type checks
             cond = Mechanics.test_modifier_condition(rich_ab, mon, move_data, field, target)
             if cond:
                  mod *= 1.3

        # Special Case: Sheer Force (needs context for secondary check)
        # Usually handled via test_modifier_condition if properly defined, 
        # but let's ensure it checks the move's secondary property.
        
        # Item
        it = mon.get('_rich_item')
        if it and mon.get('ability') != 'Klutz':
             val = it.get(key)
             if val is not None and isinstance(val, (int, float)):
                  if Mechanics.test_modifier_condition(it, mon, move_data, field, target):
                       mod *= val

        
        # 3. Ally Modifiers (Phase 2 Awareness)
        if field and field.get('allies'):
             side = mon.get('side')
             ally = field['allies'].get(side)
             if ally:
                  ally_rich_ab = ally.get('_rich_ability', {})
                  ally_key = f"onAlly{key}" # e.g. onAllyBasePower if key='onBasePower'
                  # Special case: onAllyBasePower matches onBasePower
                  if key == 'onBasePower': ally_mod = ally_rich_ab.get('onAllyBasePower')
                  else: ally_mod = ally_rich_ab.get(ally_key)
                  
                  if isinstance(ally_mod, (int, float)):
                       if Mechanics.test_modifier_condition(ally_rich_ab, ally, move_data, field, target):
                            mod *= ally_mod
        
        # 4. Global Aura Modifiers (Phase 5)
        if field:
             # Check for Air Lock / Cloud Nine (Negate all aura/weather modifiers)
             # This is a bit complex as it should affect test_modifier_condition.
             # For now, we handle Auras specifically.
             
             # aura_break_active = ... (Check player/ai/allies)
             aura_break = False
             for p in field.get('active_mons', []):
                  if p.get('ability') == 'Aura Break': aura_break = True
             
             m_type = move_data.get('type') if move_data else None
             if m_type == 'Dark':
                  for p in field.get('active_mons', []):
                       if p.get('ability') == 'Dark Aura':
                            mod *= 0.75 if aura_break else 1.33
                            break
             if m_type == 'Fairy':
                  for p in field.get('active_mons', []):
                       if p.get('ability') == 'Fairy Aura':
                            mod *= 0.75 if aura_break else 1.33
                            break
                            
        # 5. Fixed Defensive Modifiers (Filter / Solid Rock / Multiscale)
        if key == 'onSourceModifyDamage':
             # Filter / Solid Rock (SE only)
             if context.get('effectiveness', 1) > 1:
                  if rich_ab.get('name') in ['Filter', 'Solid Rock', 'Prism Armor']:
                       mod *= 0.75
             
             # Multiscale / Shadow Shield (Full HP)
             if mon.get('current_hp') == mon.get('max_hp') and mon.get('max_hp', 0) > 0:
                  if rich_ab.get('name') in ['Multiscale', 'Shadow Shield']:
                       mod *= 0.5
              
              # Fluffy (Contact -> 0.5x, Fire -> 2.0x)
             if rich_ab.get('name') == 'Fluffy':
                  flags = move_data.get('flags', {}) if move_data else {}
                  if flags.get('contact'):
                       mod *= 0.5
                  if move_data.get('type') == 'Fire':
                       mod *= 2.0
             
             # Thick Fat (Fire/Ice -> 0.5x)
             if rich_ab.get('name') == 'Thick Fat':
                  if move_data.get('type') in ['Fire', 'Ice']:
                       mod *= 0.5
                       
             # Dry Skin (Fire -> 1.25x)
             if rich_ab.get('name') == 'Dry Skin':
                  if move_data.get('type') == 'Fire':
                       mod *= 1.25
                  
        return mod

    @staticmethod
    def test_modifier_condition(rich_data, mon, move_data, field, target=None):
        if not move_data: return True
        name = rich_data.get('name')
        
        # 1. triggerType matching (Fighting, Dark, etc for Plates/Incenses)
        trigger_type = rich_data.get('triggerType')
        if trigger_type and move_data.get('type') != trigger_type:
            # Special case for Thick Fat (usually handles both Fire and Ice)
            if name == 'Thick Fat' and move_data.get('type') == 'Fire':
                pass # Allow Fire
            elif name == 'Thick Fat' and move_data.get('type') == 'Ice':
                pass # Allow Ice
            # Special Case: Sand Force (Has triggerType='Rock' but works for Ground/Steel too)
            elif name == 'Sand Force':
                 pass
            else:
                return False
            
        # Category Checks for specific abilities
        move_category = move_data.get('category', 'Physical')
        if name == 'Ice Scales' and move_category != 'Special': return False
        
        # 2. Flag-based matching
        flags = move_data.get('flags', {})
        name = rich_data.get('name')
        
        if name == 'Strong Jaw' and not flags.get('bite'): return False
        if name == 'Iron Fist' and not flags.get('punch'): return False
        if name == 'Sharpness' and not flags.get('slicing'): return False
        if name == 'Mega Launcher' and not flags.get('pulse'): return False
        if name == 'Punk Rock' and not flags.get('sound'): return False
        if name == 'Reckless' and not (flags.get('recoil') or move_data.get('recoil')): return False
        if name == 'Tough Claws' and not flags.get('contact'): return False
        
        # 3. Technician logic
        if name == 'Technician' and move_data.get('basePower', 0) > 60:
            return False
            
        # 4. Status Checks
        if name == 'Guts' and not mon.get('status'): return False
        if name == 'Marvel Scale' and not mon.get('status'): return False
        if name == 'Toxic Boost' and not (mon.get('status') in ['psn', 'tox']): return False
        if name == 'Flare Boost' and not (mon.get('status') == 'brn'): return False
        
        # Facade check
        if name == 'Facade':
             if not mon.get('status'): return False
        
        # 5. Weather Checks
        weather = field.get('weather') if field else None
        
        # Cloud Nine / Air Lock Negation
        if weather:
             weather_negated = False
             for p in field.get('active_mons', []):
                  if p.get('ability') in ['Cloud Nine', 'Air Lock']:
                       weather_negated = True
                       break
             if weather_negated: weather = None

        if name == 'Sand Force':
             if weather not in ['Sand', 'Sandstorm']: return False
             if move_data.get('type') not in ['Rock', 'Ground', 'Steel']: return False
        if name == 'Solar Power' and weather not in ['Sun', 'Sunny Day']: return False
        if name == 'Flower Gift':
             if weather not in ['Sun', 'Sunny Day']: return False
             # Only Atk/SpD usually, but we check if the key matches.
        
        # 6. HP Thresholds
        curr_hp = mon.get('current_hp', 1)
        max_hp = mon.get('max_hp', 1)
        hp_ratio = curr_hp / max_hp
        
        if name == 'Defeatist' and hp_ratio > 0.5: return False
        if name == 'Overgrow' and (hp_ratio > 1/3 or move_data.get('type') != 'Grass'): return False
        if name == 'Blaze' and (hp_ratio > 1/3 or move_data.get('type') != 'Fire'): return False
        if name == 'Torrent' and (hp_ratio > 1/3 or move_data.get('type') != 'Water'): return False
        if name == 'Swarm' and (hp_ratio > 1/3 or move_data.get('type') != 'Bug'): return False
        
        # 7. Type-based Power
        if name == 'Water Bubble' and move_data.get('type') != 'Water': return False
        if name == 'Transistor' and move_data.get('type') != 'Electric': return False
        if name == "Dragon's Maw" and move_data.get('type') != 'Dragon': return False
        if name in ['Steelworker', 'Steely Spirit'] and move_data.get('type') != 'Steel': return False
        if name == "Dragon's Gale" and move_data.get('type') != 'Dragon': return False
        
        # 8. Sheer Force logic
        if name == 'Sheer Force':
             # Active if move has secondary effects
             has_secondary = bool(move_data.get('secondary') or move_data.get('secondaries'))
             if not has_secondary: return False
             
        # 9. Item specific conditional logic
        context = field.get('context', {}) if field else {}
        species = mon.get('species', '')
        
        if name == 'Expert Belt':
             if context.get('effectiveness', 1) <= 1: return False
             
        if name == 'Tinted Lens':
             if context.get('effectiveness', 1) >= 1: return False
             
        if name == 'Light Ball':
             if 'Pikachu' not in species: return False
        
        if name == 'Thick Club':
             if not any(s in species for s in ['Cubone', 'Marowak']): return False
             
        if name in ['Deep Sea Tooth', 'Deep Sea Scale']:
             if 'Clamperl' not in species: return False
             
        if name == 'Soul Dew':
             if not any(s in species for s in ['Latios', 'Latias']): return False
             
        if name == 'Muscle Band':
             if move_data.get('category') != 'Physical': return False
        
        if name == 'Wise Glasses':
             if move_data.get('category') != 'Special': return False
             
        if 'Memory' in name:
             # Silvally Memories (e.g., 'Fire Memory' -> 'Fire')
             mem_type = name.replace(' Memory', '')
             if move_data.get('type') != mem_type: return False
             
        if 'Gem' in name:
             # Type Gems (e.g., 'Fire Gem' -> 1.3x or 1.5x damage for Fire moves)
             # NOTE: In R&B they are often 1.3x. Rich data should have the value.
             gem_type = name.replace(' Gem', '')
             if move_data.get('type') != gem_type: return False

        if name == 'Eviolite':
             nfes = ['Porygon2', 'Chansey', 'Doublade', 'Gligar', 'Scyther', 'Rhydon', 'Dusclops', 'Type: Null', 'Slowpoke', 'Onix', 'Magneton', 'Golbat', 'Piloswine', 'Misdreavus', 'Murkrow', 'Tangela', 'Roselia', 'Seadra', 'Electabuzz', 'Magmar', 'Togetic', 'Clefairy', 'Combusken', 'Marshtomp', 'Grovyle']
             if species not in nfes and 'Galarian' not in species: return False

        # 10. Move-specific Conditions (Expanding Force, Rising Voltage, etc)
        terrain = field.get('terrain') if field else None
        context = field.get('context', {}) if field else {}
        
        if name == 'Expanding Force':
             return terrain == 'Psychic Terrain'
        if name == 'Rising Voltage':
             # If target is grounded in Electric Terrain, BP doubles.
             # Note: Rising Voltage BP double is handled in its onBasePower if we set it.
             # If BP is already doubled in data, we just return Terrain check.
             return terrain == 'Electric Terrain' and context.get('is_grounded_target', True)
        if name == 'Misty Explosion':
             return terrain == 'Misty Terrain'
        if name in ['Collision Course', 'Electro Drift']:
             return context.get('effectiveness', 1) > 1
        
        if name == 'Lash Out':
             return mon.get('stats_lowered_this_turn', False)
        
        if name == 'Assurance':
             return context.get('target_damaged_this_turn', False)
        
        if name in ['Venoshock', 'Hex', 'Barb Barrage']:
             if target and target.get('status'):
                  if name == 'Venoshock' and target.get('status') in ['psn', 'tox']: return True
                  if name == 'Hex': return True # Any status
                  if name == 'Barb Barrage' and target.get('status') in ['psn', 'tox']: return True
             return False

        if name == 'Brine':
             if target and target.get('current_hp', 1) / target.get('max_hp', 1) <= 0.5:
                  return True
             return False
        
        if name == 'Payback':
             # BP doubles if target moved first
             return context.get('user_moved_last', False)

        if name in ['Bolt Beak', 'Fishious Rend']:
             # Double power if user moves before target
             moved_last = context.get('user_moved_last', False)
             return not moved_last
             
        if name in ['Revenge', 'Avalanche']:
             return mon.get('took_damage_this_turn', False)
             
        if name == 'Retaliate':
             return field.get('ally_fainted_last_turn', False)

        # New Move Conditions
        if name == 'Fickle Beam':
             # 30% chance for double power (Deterministic hash for consistency)
             return (hash(str(mon.get('current_hp')) + context.get('move_name', '')) % 100) < 30
             
        if name == 'Grav Apple':
             return field.get('gravity', 0) > 0
             
        if name == 'Psyblade':
             return field.get('terrain') == 'Psychic'

        if name in ['Fusion Bolt', 'Fusion Flare']:
             # Double if previous move was the counterpart
             last_move = context.get('last_move_used_this_turn')
             counterpart = 'Fusion Flare' if name == 'Fusion Bolt' else 'Fusion Bolt'
             return last_move == counterpart

        if name == 'Barb Barrage':
             return defender.get('status') is not None
             
        if name == 'Knock Off':
             if target and target.get('item'):
                  # Basic check. Assume removable if present for now (simplification)
                  return True
        
        if 'Berry' in name and name != 'Custap Berry':
             # Type-Resist Berries
             TYPE_RESIST_BERRIES = {
                  'Occa Berry': 'Fire', 'Passho Berry': 'Water', 'Wacan Berry': 'Electric',
                  'Rindo Berry': 'Grass', 'Yache Berry': 'Ice', 'Chople Berry': 'Fighting',
                  'Kebia Berry': 'Poison', 'Shuca Berry': 'Ground', 'Coba Berry': 'Flying',
                  'Payapa Berry': 'Psychic', 'Tanga Berry': 'Bug', 'Charti Berry': 'Rock',
                  'Kasib Berry': 'Ghost', 'Haban Berry': 'Dragon', 'Colbur Berry': 'Dark',
                  'Babiri Berry': 'Steel', 'Roseli Berry': 'Fairy', 'Chilan Berry': 'Normal'
             }
             if name in TYPE_RESIST_BERRIES:
                  if context.get('effectiveness', 1) > 1 and move_data.get('type') == TYPE_RESIST_BERRIES[name]:
                       return True
                  if name == 'Chilan Berry' and move_data.get('type') == 'Normal':
                       return True # Chilan Berry (Normal) works on neutral hit? Usually checks type match.
                  return False
        
        return True

    @staticmethod
    def get_stab_multiplier(attacker, move_type):
         ab_name = attacker.get('ability') or attacker.get('_rich_ability', {}).get('name')
         if ab_name == 'Adaptability':
              return 2.0
         return 1.5

    @staticmethod
    def get_type_effectiveness_with_abilities(move_type, defender, attacker=None):
         from pkh_app.local_damage_calc import get_type_effectiveness
         def_types = defender.get('types', ['Normal'])
         effectiveness = get_type_effectiveness(move_type, def_types)

         if attacker:
              ab_name = attacker.get('ability') or attacker.get('_rich_ability', {}).get('name')
              # Scrappy / Mind's Eye bypass for Ghost immunity
              if effectiveness == 0 and move_type in ['Normal', 'Fighting']:
                   if ab_name in ['Scrappy', "Mind's Eye"]:
                        # Calculate effectiveness treating Ghost as neutral (1.0)
                        effectiveness = get_type_effectiveness(move_type, [t for t in def_types if t != 'Ghost'])
         
         return effectiveness

    @staticmethod
    def get_variable_bp(move_name, attacker, defender, field=None):
        """
        Calculates dynamic Base Power for moves like Gyro Ball, Low Kick, etc.
        """
        # 1. Stat-based
        if move_name == 'Stored Power' or move_name == 'Power Trip':
             # 20 + 20 * sum(positive stages)
             total_boosts = 0
             for s, v in attacker.get('stat_stages', {}).items():
                  if v > 0 and s not in ['accuracy', 'evasion']: total_boosts += v
             return 20 + (20 * total_boosts)

        if move_name == 'Punishment':
             # 60 + 20 * sum(positive stages of target). Max 200.
             total_boosts = 0
             for s, v in defender.get('stat_stages', {}).items():
                  if v > 0 and s not in ['accuracy', 'evasion']: total_boosts += v
             return min(200, 60 + (20 * total_boosts))

        # 2. Speed-based
        if move_name == 'Gyro Ball':
             user_spe = Mechanics.get_effective_stat(attacker, 'spe', field)
             target_spe = Mechanics.get_effective_stat(defender, 'spe', field)
             if user_spe == 0: return 1
             bp = min(150, (25 * target_spe) / user_spe)
             return int(bp)
             
        if move_name == 'Electro Ball':
             user_spe = Mechanics.get_effective_stat(attacker, 'spe', field)
             target_spe = Mechanics.get_effective_stat(defender, 'spe', field)
             if target_spe == 0: return 150
             ratio = user_spe / target_spe
             if ratio >= 4: return 150
             if ratio >= 3: return 120
             if ratio >= 2: return 80
             if ratio >= 1: return 60
             return 40

        # 3. Weight-based
        # We assume weight is in kg. Default to 10kg if missing.
        user_weight = attacker.get('weightkg', 10.0)
        target_weight = defender.get('weightkg', 10.0)
        
        if move_name in ['Low Kick', 'Grass Knot']:
             w = target_weight
             if w < 10: return 20
             if w < 25: return 40
             if w < 50: return 60
             if w < 100: return 80
             if w < 200: return 100
             return 120
             
        if move_name in ['Heavy Slam', 'Heat Crash']:
             ratio = user_weight / target_weight
             if ratio > 5: return 120
             if ratio > 4: return 100
             if ratio > 3: return 80
             if ratio > 2: return 60
             return 40
             
        # 4. Item-based
        if move_name == 'Acrobatics':
             if not attacker.get('item'): return 110
             return 55

        # 6. HP-based (User)
        if move_name in ['Water Spout', 'Eruption', 'Dragon Energy']:
             curr = attacker.get('current_hp', 1)
             mx = attacker.get('max_hp', 1)
             return max(1, int(150 * (curr / mx)))
             
        if move_name in ['Reversal', 'Flail']:
             curr = attacker.get('current_hp', 1)
             mx = attacker.get('max_hp', 1)
             ratio = (curr * 48) // mx
             # Gen 5+ values
             if ratio <= 1: return 200
             if ratio <= 4: return 150
             if ratio <= 9: return 100
             if ratio <= 16: return 80
             if ratio <= 32: return 40
             return 20

        # 7. HP-based (Target)
        if move_name in ['Crush Grip', 'Wring Out']:
             curr = defender.get('current_hp', 1)
             mx = defender.get('max_hp', 1)
             # BP = 1 + 120 * (HP / MaxHP)
             return max(1, int(120 * (curr / mx)))

        # 8. Sequence-based (Simplified)
        if move_name in ['Rollout', 'Ice Ball', 'Fury Cutter', 'Echoed Voice']:
             # Use a generic 'move_count' tracker if present
             cnt = attacker.get(f'_cnt_{move_name}', 0)
             bp_map = {
                  'Rollout': [30, 60, 120, 240, 480],
                  'Ice Ball': [30, 60, 120, 240, 480],
                  'Fury Cutter': [40, 80, 160],
                  'Echoed Voice': [40, 80, 120, 160, 200]
             }
             steps = bp_map.get(move_name, [40])
             idx = min(len(steps)-1, cnt)
             return steps[idx]

        if move_name in ['Rollout', 'Ice Ball']:
             # Double if user already started the sequence
             # Also double if Defense Curl was used
             layers = attacker.get('move_sequence_count', 0)
             bp = 30 * (2 ** layers)
             if 'defensecurl' in attacker.get('volatiles', []):
                  bp *= 2
             return min(bp, 480) # Max 5 turns or capped
             
        if move_name == 'Trump Card':
             # BP: 5-200. Depends on remaining PP. Assume we track a simulated countdown.
             pp = attacker.get('_pp_trumpcard', 5)
             bp_map = {5: 40, 4: 50, 3: 60, 2: 80, 1: 200, 0: 200}
             return bp_map.get(pp, 40)
        if move_name == 'Spit Up':
             layers = attacker.get('stockpile_layers', 0)
             return layers * 100

    @staticmethod
    def get_stab_multiplier(attacker, move_type):
         ab_name = attacker.get('ability') or attacker.get('_rich_ability', {}).get('name')
         if ab_name == 'Adaptability':
              return 2.0
         return 1.5

    @staticmethod
    def get_type_effectiveness_with_abilities(move_type, defender, attacker=None):
         from pkh_app.local_damage_calc import get_type_effectiveness
         def_types = defender.get('types', ['Normal'])
         effectiveness = get_type_effectiveness(move_type, def_types)

         if attacker:
              ab_name = attacker.get('ability') or attacker.get('_rich_ability', {}).get('name')
              # Scrappy / Mind's Eye bypass for Ghost immunity
              if effectiveness == 0 and move_type in ['Normal', 'Fighting']:
                   if ab_name in ['Scrappy', "Mind's Eye"]:
                        # Calculate effectiveness treating Ghost as neutral (1.0)
                        effectiveness = get_type_effectiveness(move_type, [t for t in def_types if t != 'Ghost'])
         
         return effectiveness
