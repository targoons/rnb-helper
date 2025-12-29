
import math

class Mechanics:
    @staticmethod
    def get_effective_speed(mon, field, side=None):
        stats = mon.get('stats', {})
        base_spe = stats.get('spe', 1)
        
        if side is None:
            side = mon.get('side', 'player')
        
        # 1. Stat Stages
        stages = mon.get('stat_stages', {})
        spe_stage = stages.get('spe', 0)
        multiplier = 1.0
        if spe_stage > 0:
            multiplier = (2 + spe_stage) / 2
        elif spe_stage < 0:
            multiplier = 2 / (2 - spe_stage)
            
        spe = base_spe * multiplier
        
        # 2. Paralysis
        if mon.get('status') == 'par':
            spe = spe * 0.25
            
        # 3. Ability
        weather = field.get('weather')
        ability = mon.get('ability', '')
        if weather == 'Rain' and ability == 'Swift Swim':
            spe *= 2
        elif weather == 'Sun' and ability == 'Chlorophyll':
            spe *= 2
        elif weather == 'Sand' and ability == 'Sand Rush':
            spe *= 2
        elif weather == 'Hail' and ability == 'Slush Rush':
            spe *= 2

        # 4. Items
        item = mon.get('item', '')
        if item == 'Choice Scarf':
            spe *= 1.5
            
        # 5. Tailwind
        tailwind = field.get('tailwind', {})
        if tailwind.get(side, 0) > 0:
             spe *= 2

        return int(spe)

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

        # 1. Weather / Status / Passives
        weather = state.fields.get('weather')
        all_active = [state.player_active, state.ai_active]
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
                    
            # Items
            if item == 'Leftovers':
                if mon['current_hp'] < max_hp and mon['current_hp'] > 0:
                     heal = max(1, int(max_hp / 16))
                     mon['current_hp'] = min(max_hp, mon['current_hp'] + heal)
                     log.append(f"  {mon.get('species')} healed by Leftovers (+{heal})")
            elif item == 'Black Sludge':
                if 'Poison' in mon['types']:
                     heal = max(1, int(max_hp / 16))
                     mon['current_hp'] = min(max_hp, mon['current_hp'] + heal)
                     log.append(f"  {mon.get('species')} healed by Black Sludge (+{heal})")
                elif ability != 'Magic Guard':
                     loss = max(1, int(max_hp / 8))
                     mon['current_hp'] -= loss
                     log.append(f"  {mon.get('species')} hurt by Black Sludge (-{loss})")
                     
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
