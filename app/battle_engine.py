
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import copy
import logging
from app.mechanics import Mechanics

@dataclass
class BattleState:
    player_active: Dict
    ai_active: Dict
    player_party: List[Dict]
    ai_party: List[Dict]
    last_moves: Dict = field(default_factory=lambda: {'player': None, 'ai': None})
    fields: Dict = field(default_factory=lambda: {
        'weather': None,
        'weather_turns': 0,
        'terrain': None,
        'terrain_turns': 0,
        'screens': {
            'player': {'reflect': 0, 'light_screen': 0, 'aurora_veil': 0},
            'ai': {'reflect': 0, 'light_screen': 0, 'aurora_veil': 0}
        },
        'tailwind': {'player': 0, 'ai': 0},
        'trick_room': 0,
        'hazards': {'player': [], 'ai': []}
    })
    
    def deep_copy(self):
        return copy.deepcopy(self)

    def get_hash(self):
        """Returns a stable hash for the core state variables to detect cycles."""
        def get_mon_hash(m):
            v_h = tuple(sorted(m.get('volatiles', [])))
            return (m.get('species'), m.get('current_hp'), m.get('status'), 
                    tuple(sorted(m.get('stat_stages', {}).items())), v_h)
        
        p_active_h = get_mon_hash(self.player_active)
        a_active_h = get_mon_hash(self.ai_active)
        p_party_h = tuple(get_mon_hash(m) for m in self.player_party)
        a_party_h = tuple(get_mon_hash(m) for m in self.ai_party)
        
        # Fields Hash
        f = self.fields
        screens_h = tuple(sorted((k, tuple(sorted(v.items()))) for k, v in f.get('screens', {}).items()))
        tailwind_h = tuple(sorted(f.get('tailwind', {}).items()))
        hazards_h = tuple(sorted((k, tuple(v)) for k, v in f.get('hazards', {}).items()))
        
        fields_h = (
            f.get('weather'), f.get('weather_turns'),
            f.get('terrain'), f.get('terrain_turns'),
            screens_h, tailwind_h, f.get('trick_room'), 
            hazards_h
        )
        
        return hash((p_active_h, a_active_h, p_party_h, a_party_h, 
                     self.last_moves.get('player'), self.last_moves.get('ai'),
                     fields_h))

class BattleEngine:
    def __init__(self, calc_client, species_names=None, move_names=None):
        self.calc_client = calc_client
        self.species_names = species_names or {}
        self.move_names = move_names or {}
        
    def get_move_name(self, move_id):
        return self.move_names.get(str(move_id), str(move_id))

    def get_species_name(self, s_id):
        return self.species_names.get(str(s_id), str(s_id))
        
    def get_valid_actions(self, state: BattleState, side: str) -> List[str]:
        """
        Returns a list of valid actions for the given side.
        Actions: "Move: <Name>", "Switch: <Species>"
        """
        actions = []
        active = state.player_active if side == 'player' else state.ai_active
        party = state.player_party if side == 'player' else state.ai_party
        
        # 1. Forced Switch (if fainted or pivoting)
        if active.get('current_hp', 0) <= 0 or active.get('must_switch'):
            # Must switch
            for p in party:
                if p.get('current_hp') > 0 and p.get('species') != active.get('species'):
                    actions.append(f"Switch: {p.get('species')}")
            return actions
            
        # 2. Standard Turn
        # 2a. Moves
        # 2a. Moves
        locked_move = active.get('locked_move')
        item = active.get('item', '')
        
        if active.get('status') != 'slp':
             for m in active.get('moves', []):
                 # Choice Lock Check
                 if locked_move and m != locked_move: continue
                 
                 # Assault Vest Check
                 # Need category. If not available, assume valid? Or use heuristic?
                 # Since we don't have move category here easily without lookup...
                 # We can rely on a helper or just skip AV check here if tough.
                 # StrategyAdvisor usually passes full move objects? No, just strings.
                 # Workaround: AV check requires category lookup.
                 # If we assume 'Status' moves are known... 
                 # Let's import Move data or use a hardcoded check for now?
                 # Or just skip AV validation in Sim (AI won't pick bad moves usually).
                 # But Player needs constraint.
                 # For now, implementing Choice Lock is critical. AV is bonus.
                 
                 actions.append(f"Move: {m}")
        else:
             actions.append("Move: Snooze")

        # 2b. Switches
        # Simplified: Don't allow switch if Trapped (Shadow Tag etc) - Todo
        for p in party:
            if p.get('current_hp') > 0 and p.get('species') != active.get('species'):
                 actions.append(f"Switch: {p.get('species')}")
                 
        return actions

    def apply_turn(self, state: BattleState, player_action: str, ai_action: str) -> Tuple[BattleState, List[str]]:
        """
        Simulates one ply/turn.
        """
        new_state = state.deep_copy()
        log = []
        
        # 0. Handle Forced Switches
        # If one side is fainted at start of turn (Switch Phase), we just process the switch and return.
        p_fainted = new_state.player_active.get('current_hp', 0) <= 0 or new_state.player_active.get('must_switch')
        a_fainted = new_state.ai_active.get('current_hp', 0) <= 0 or new_state.ai_active.get('must_switch')
        
        if p_fainted or a_fainted:
            if p_fainted and player_action.startswith("Switch:"):
                self.perform_switch(new_state, 'player', player_action.split(": ")[1], log)
            if a_fainted and ai_action.startswith("Switch:"):
                self.perform_switch(new_state, 'ai', ai_action.split(": ")[1], log)
            return new_state, log

        # 0.5 Init Turn Flags
        new_state.fields['protected_sides'] = []

        # 1. Determine Order
        player_speed = Mechanics.get_effective_speed(new_state.player_active, new_state.fields, side='player')
        ai_speed = Mechanics.get_effective_speed(new_state.ai_active, new_state.fields, side='ai')
        
        # Parse Priorities
        def get_prio(act):
            if act.startswith("Switch:"): return 6
            m = act.replace("Move: ", "")
            # Simplified Priority Table (Pending full metadata)
            if m in ['Protect', 'Detect', 'Kings Shield', 'Endure', 'Spiky Shield', 'Baneful Bunker']: return 4
            if m == 'Fake Out': return 3
            if m in ['Extreme Speed']: return 2
            if m in ['Aqua Jet', 'Mach Punch', 'Bullet Punch', 'Ice Shard', 'Quick Attack', 'Shadow Sneak', 'Sucker Punch', 'Vacuum Wave', 'Water Shuriken', 'Grassy Glide']: return 1 # Added Grassy Glide
            if m in ['Vital Throw', 'Circle Throw', 'Dragon Tail', 'Whirlwind', 'Roar']: return -6
            if m == 'Trick Room': return -7
            return 0
            
        p_prio = get_prio(player_action)
        a_prio = get_prio(ai_action)
        
        player_first = False
        if p_prio > a_prio: player_first = True
        elif a_prio > p_prio: player_first = False
        else:
             if new_state.fields.get('trick_room', 0) > 0:
                 player_first = player_speed <= ai_speed
             else:
                 player_first = player_speed >= ai_speed # Speed ties -> Player wins (Optimistic)
        
        first = ('player', player_action) if player_first else ('ai', ai_action)
        second = ('ai', ai_action) if player_first else ('player', player_action)
        
        # 2. Execution
        self.execute_turn_action(new_state, first[0], first[1], second[0], log)
        self.execute_turn_action(new_state, second[0], second[1], first[0], log)
             
        # 3. End Turn
        Mechanics.apply_end_turn_effects(new_state, log)
        
        # 4. Clear Turn Volatiles (Flinch)
        for p in [new_state.player_active, new_state.ai_active]:
            v = p.setdefault('volatiles', [])
            if 'flinch' in v: v.remove('flinch')
        
        return new_state, log

    def perform_switch(self, state, side, species_id, log):
        party = state.player_party if side == 'player' else state.ai_party
        target = None
        s_name = self.get_species_name(species_id)
        for p in party:
            # Match either ID or Name
            if str(p.get('species_id')) == str(species_id) or p.get('species') == s_name:
                target = p
                break
        
        if target:
            # swap current active to party and target to active
            active = state.player_active if side == 'player' else state.ai_active
            
            # Switch-Out Effects (Regenerator, Natural Cure)
            if active.get('ability') == 'Regenerator':
                heal = int(active.get('max_hp', 1) / 3)
                active['current_hp'] = min(active.get('max_hp'), active['current_hp'] + heal)
                log.append(f"  {active.get('species')} restored HP using Regenerator!")
            
            if active.get('ability') == 'Natural Cure':
                if active.get('status'):
                    active['status'] = None
                    log.append(f"  {active.get('species')} was cured by Natural Cure!")

            # Find current active in party and update its HP
            for p in party:
                if p['species'] == active['species']:
                    p['current_hp'] = active['current_hp']
                    p['stat_stages'] = active.get('stat_stages', {}).copy()
                    p['status'] = active.get('status')
                    p['stat_stages'] = active.get('stat_stages', {}).copy()
                    p['status'] = active.get('status')
                    p['protect_counter'] = 0
                    p.pop('must_switch', None)
                    p.pop('locked_move', None) # Clear choice lock
                    break
            
            # Update Active
            target_copy = target.copy()
            target_copy['protect_counter'] = 0
            
            if side == 'player': state.player_active = target_copy
            else: state.ai_active = target_copy
            
            log.append(f"[{side.upper()}] switched to {s_name}")
            
            # Apply Entry Hazards
            self.apply_switch_hazards(state, side, target_copy, log)
            
            # Apply Switch-In Abilities (Intimidate, Drizzle, etc.)
            self.apply_switch_in_abilities(state, side, target_copy, log)
        else:
            log.append(f"[{side.upper()}] tried to switch to {species_id} but failed")

    def apply_switch_in_abilities(self, state, side, mon, log):
        ability = mon.get('ability')
        if not ability: return
        
        opponent = state.ai_active if side == 'player' else state.player_active
        opp_side = 'ai' if side == 'player' else 'player'
        
        if ability == 'Intimidate':
            # Check for immunities (Clear Body, White Smoke, Hyper Cutter, Inner Focus in Gen 8, Oblivious in Gen 8, Scrappy in Gen 8)
            # Simplified check
            opp_ability = opponent.get('ability', '')
            if opp_ability in ['Clear Body', 'White Smoke', 'Hyper Cutter', 'Inner Focus', 'Oblivious', 'Scrappy', 'Full Metal Body']:
                log.append(f"  {opponent.get('species')} wasn't affected by Intimidate ({opp_ability})!")
            elif opp_ability == 'Defiant':
                stages = opponent.setdefault('stat_stages', {})
                stages['atk'] = min(6, stages.get('atk', 0) + 2)
                log.append(f"  {opponent.get('species')}'s Attack sharply rose (Defiant)!")
            elif opp_ability == 'Competitive':
                stages = opponent.setdefault('stat_stages', {})
                stages['spa'] = min(6, stages.get('spa', 0) + 2)
                log.append(f"  {opponent.get('species')}'s Sp. Atk sharply rose (Competitive)!")
            elif opp_ability == 'Mirror Armor':
                 # Bounce back
                 log.append(f"  {opponent.get('species')} bounced back Intimidate (Mirror Armor)!")
                 stages = mon.setdefault('stat_stages', {})
                 stages['atk'] = max(-6, stages.get('atk', 0) - 1)
                 log.append(f"  {mon.get('species')}'s Attack fell!")
            else:
                stages = opponent.setdefault('stat_stages', {})
                stages['atk'] = max(-6, stages.get('atk', 0) - 1)
                log.append(f"  {mon.get('species')} intimidated {opponent.get('species')}!")
                log.append(f"  {opponent.get('species')}'s Attack fell!")

        elif ability == 'Download':
            defense = opponent.get('stats', {}).get('def', 100)
            sp_def = opponent.get('stats', {}).get('spd', 100)
            stages = mon.setdefault('stat_stages', {})
            if defense < sp_def:
                stages['atk'] = min(6, stages.get('atk', 0) + 1)
                log.append(f"  {mon.get('species')} boosted Attack (Download)!")
            else:
                stages['spa'] = min(6, stages.get('spa', 0) + 1)
                log.append(f"  {mon.get('species')} boosted Sp. Atk (Download)!")

        elif ability in ['Drizzle', 'Drought', 'Sand Stream', 'Snow Warning']:
             weather_map = {
                 'Drizzle': 'Rain',
                 'Drought': 'Sun',
                 'Sand Stream': 'Sand',
                 'Snow Warning': 'Hail'
             }
             w = weather_map[ability]
             # Check Primal/Desolate logic? Ignoring for now or override.
             if state.fields.get('weather') != w:
                 state.fields['weather'] = w
                 log.append(f"  {mon.get('species')}'s {ability} changed the weather to {w}!")

        elif ability in ['Electric Surge', 'Grassy Surge', 'Misty Surge', 'Psychic Surge']:
             terrain_map = {
                 'Electric Surge': 'Electric',
                 'Grassy Surge': 'Grassy',
                 'Misty Surge': 'Misty',
                 'Psychic Surge': 'Psychic'
             }
             t = terrain_map[ability]
             if state.fields.get('terrain') != t:
                 state.fields['terrain'] = t
                 log.append(f"  {mon.get('species')}'s {ability} changed the terrain to {t}!")

    def apply_switch_hazards(self, state, side, mon, log):
        hazards = state.fields['hazards'].get(side, [])
        if not hazards: return

        # Grounded Check
        is_flying = 'Flying' in mon.get('types', [])
        has_levitate = mon.get('ability') == 'Levitate'
        has_balloon = mon.get('item') == 'Air Balloon'
        is_grounded = not (is_flying or has_levitate or has_balloon)
        if mon.get('item') == 'Iron Ball': is_grounded = True
        
        max_hp = mon.get('max_hp', 1)
        
        # 1. Stealth Rock
        if 'Stealth Rock' in hazards:
             # Type Effectiveness
             # Simplified: We need a type chart or ask calc client?
             # For now, simplistic hardcoded check or skip effectiveness?
             # We can use Mechanics helper if available, or just hardcode checking "Rock" vs types.
             # Checking `calc_client` for 1 move is expensive.
             # Let's implement basic type chart for Rock.
             factor = 1.0
             rock_eff = {
                 'Fire': 2, 'Ice': 2, 'Flying': 2, 'Bug': 2, 
                 'Water': 0.5, 'Grass': 0.5, 'Fighting': 0.5, 'Ground': 0.5, 'Steel': 0.5
             }
             for t in mon.get('types', []):
                 factor *= rock_eff.get(t, 1.0)
             
             dmg = int(max_hp * 0.125 * factor)
             if dmg > 0:
                 mon['current_hp'] -= dmg
                 log.append(f"  Pointed stones dug into {mon.get('species')}! (-{dmg})")

        # 2. Spikes
        spikes_count = hazards.count('Spikes') # Assuming list can contain duplicates? Or dict count?
        # state.fields default is list of strings. 'Spikes' usually appears once, maybe "Spikes_1"? 
        # Plan implies list of strings. Assuming multiple "Spikes" entries? 
        # Or counts handled externally?
        # Let's assume list contains "Spikes" multiple times or we just check presence.
        # Run & Bun standard: 1 layer = 1/8, 2 = 1/6, 3 = 1/4.
        # Given current state structure is likely just list of distinct strings or counts?
        # I'll check `state.fields`.
        # Assuming simple presence for now. 1 Layer.
        if is_grounded:
             num_spikes = 0
             for h in hazards: 
                 if h == 'Spikes': num_spikes += 1
             
             if num_spikes > 0:
                 frac = {1: 8, 2: 6, 3: 4}.get(num_spikes, 4 if num_spikes > 3 else 8)
                 dmg = int(max_hp / frac)
                 mon['current_hp'] -= dmg
                 log.append(f"  {mon.get('species')} was hurt by Spikes! (-{dmg})")
                 
             # 3. Sticky Web
             if 'Sticky Web' in hazards:
                 stages = mon.setdefault('stat_stages', {})
                 stages['spe'] = max(-6, stages.get('spe', 0) - 1)
                 log.append(f"  {mon.get('species')} got caught in a Sticky Web!")

             # 4. Toxic Spikes
             # Pending (Complex logic with absorbing)
             pass

    def execute_turn_action(self, state, attacker_side, action, defender_side, log):
        attacker = state.player_active if attacker_side == 'player' else state.ai_active
        defender = state.ai_active if attacker_side == 'player' else state.player_active
        
        if attacker.get('current_hp') <= 0: return # Dead can't move
        
        if action.startswith("Switch:"):
            self.perform_switch(state, attacker_side, action.split(": ")[1], log)
            return

        move_id = action.replace("Move: ", "")
        move_name = self.get_move_name(move_id)
        
        # 0. Status & Volatile Checks
        # Sleep
        status = attacker.get('status')
        if status == 'slp':
            counter = attacker.get('status_counter', 0)
            if counter > 0:
                attacker['status_counter'] = counter - 1
                log.append(f"[{attacker_side.upper()}] {attacker.get('species')} is fast asleep.")
                return
            else:
                attacker['status'] = None
                log.append(f"[{attacker_side.upper()}] {attacker.get('species')} woke up!")
        
        # Freeze
        elif status == 'frz':
            # 20% thaw chance (Simple hash-based determinism)
            if hash(move_name + str(attacker['current_hp'])) % 100 < 20: 
                attacker['status'] = None
                log.append(f"[{attacker_side.upper()}] {attacker.get('species')} thawed out!")
            elif move_name in ['Scald', 'Flare Blitz', 'Flame Wheel', 'Sacred Fire', 'Fusion Flare', 'Steam Eruption', 'Burn Up', 'Pyro Ball', 'Scorching Sands']: 
                 attacker['status'] = None
                 log.append(f"[{attacker_side.upper()}] {attacker.get('species')} thawed out by {move_name}!")
            else:
                log.append(f"[{attacker_side.upper()}] {attacker.get('species')} is frozen solid!")
                return

        # Paralysis
        elif status == 'par':
            # 25% Full Paralysis
            if hash(move_name + str(attacker['current_hp'])) % 100 < 25:
                log.append(f"[{attacker_side.upper()}] {attacker.get('species')} is paralyzed! It can't move!")
                return

        # Flinch
        volatiles = attacker.get('volatiles', [])
        if 'flinch' in volatiles:
            log.append(f"[{attacker_side.upper()}] {attacker.get('species')} flinched and couldn't move!")
            return
            
        # Confusion
        # Confusion
        if 'confusion' in volatiles:
             log.append(f"[{attacker_side.upper()}] {attacker.get('species')} is confused!")
             # Decrement Counter
             c_turns = attacker.get('confusion_turns', 0) - 1
             attacker['confusion_turns'] = c_turns
             
             if c_turns <= 0:
                 if 'confusion' in volatiles: volatiles.remove('confusion')
                 log.append(f"  {attacker.get('species')} snapped out of its confusion!")
             else:
                 # 33% Self Hit
                 if hash(move_name + str(attacker['current_hp'])) % 100 < 33:
                     log.append(f"  It hurt itself in its confusion!")
                 # Self Hit Damage (Typeless 40 BP Physical)
                 level = 100 # Approx
                 stats = attacker.get('stats', {})
                 atk = stats.get('atk', 100)
                 defi = stats.get('def', 100)
                 dmg = int(((2 * level / 5 + 2) * 40 * atk / defi) / 50 + 2)
                 attacker['current_hp'] -= dmg
                 log.append(f"  Lost {dmg} HP (Confusion)")
                 return

        # Taunt
        if 'taunt' in volatiles:
             t_turns = attacker.get('taunt_turns', 0) - 1
             attacker['taunt_turns'] = t_turns
             if t_turns <= 0:
                 if 'taunt' in volatiles: volatiles.remove('taunt')
                 log.append(f"[{attacker_side.upper()}] {attacker.get('species')} shaken off the Taunt!")
             
        if move_name:
             state.last_moves[attacker_side] = move_name
        
        # 1. Protect Logic
        if move_name in ['Protect', 'Detect', 'Kings Shield', 'Spiky Shield', 'Baneful Bunker']:
             cnt = attacker.get('protect_counter', 0)
             if cnt == 0:
                 state.fields['protected_sides'].append(attacker_side)
                 attacker['protect_counter'] = cnt + 1
                 log.append(f"[{attacker_side.upper()}] {attacker.get('species')} protected itself!")
             else:
                 attacker['protect_counter'] = 0 
                 log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name} but it failed!")
             return

        # 2. Check Protection
        if defender_side in state.fields.get('protected_sides', []):
             log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}")
             log.append(f"  {defender.get('species')} protected itself!")
             attacker['protect_counter'] = 0 
             return

        # Reset Protect Counter
        attacker['protect_counter'] = 0
        
        # 3. Immunity Check (Type & Ability)
        # We need move data (type key) which is in `move_names`? No, `move_names` is just ID->Name.
        # We rely on calc response for type mainly.
        # But we need to check BEFORE calc?
        # Construct simplified Immunity logic or rely on Calc's "desc" text to detect "Does not affect"?
        # Calc "desc" is unreliable for Status moves that don't do damage.
        # Minimal Type Logic Required.
        # Parsing move type is hard without metadata.
        # Workaround: Use `self.calc_client` to get move details (type) if possible?
        # Or assume calc handles everything?
        # Problem: Calc returns 0 damage. We assume hit.
        # If we rely on Calc Result `desc`: "It doesn't affect...".
        # Let's see `execute_turn_action` flow.
        
        dmg_res = self.calc_client.get_damage_rolls(attacker, defender, [move_name], state.fields)
        if dmg_res:
            res = dmg_res[0]
            rolls = res.get('damage_rolls', [0])
            avg_dmg = sum(rolls) / len(rolls) if rolls else 0
            damage_dealt = int(avg_dmg)
            
            # Multi-Hit Logic
            multihit = res.get('multihit')
            
            hit_count = 1
            if multihit:
                if isinstance(multihit, list): # [2, 5]
                    # Simple average or random?
                    # For sim, let's use Average or Max?
                    # Deterministic Sim: Use Average rounded up?
                    # Skill Link: 5.
                    if attacker.get('ability') == 'Skill Link': 
                        hit_count = multihit[1]
                    else:
                        # Average of [min, max]? 
                        # Gen 5+ [2,3,4,5] prob: 2(35), 3(35), 4(15), 5(15). Avg ~3.
                        # Simple 2-5: Avg ~3.1
                        # Double hit [2, 2]: 2.
                        avg_hits = sum(multihit) / len(multihit) # Poor approximation
                        # Use max hits for "worst case" analysis? Or min?
                        # Let's use 3 for 2-5 moves.
                        if multihit == [2, 5]: hit_count = 3
                        elif multihit == [2, 2]: hit_count = 2
                        else: hit_count = multihit[1] # fallback
                else:
                    hit_count = multihit # Scalar
                
                damage_dealt *= hit_count
                log.append(f"  Hit {hit_count} times!")
            
            # 1. Ability Immunities (Manual Check for Heals/Boosts)
            def_ability = defender.get('ability', '')
            move_type = res.get('type') or res.get('moveType')
            
            # Volt Absorb / Lightning Rod / Motor Drive
            if move_type == 'Electric' and def_ability in ['Volt Absorb', 'Lightning Rod', 'Motor Drive']:
                 log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}")
                 if def_ability == 'Volt Absorb':
                     heal = int(defender.get('max_hp') * 0.25)
                     defender['current_hp'] = min(defender.get('max_hp'), defender['current_hp'] + heal)
                     log.append(f"  {defender.get('species')} healed by Volt Absorb!")
                 elif def_ability == 'Motor Drive':
                     stages = defender.setdefault('stat_stages', {})
                     stages['spe'] = min(6, stages.get('spe', 0) + 1)
                     log.append(f"  {defender.get('species')}'s Speed rose (Motor Drive)!")
                 else:
                     stages = defender.setdefault('stat_stages', {})
                     stages['spa'] = min(6, stages.get('spa', 0) + 1)
                     log.append(f"  {defender.get('species')}'s Sp. Atk rose (Lightning Rod)!")
                 return

            # Water Absorb / Storm Drain / Dry Skin
            if move_type == 'Water' and def_ability in ['Water Absorb', 'Storm Drain', 'Dry Skin']:
                 log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}")
                 if def_ability in ['Water Absorb', 'Dry Skin']:
                     heal = int(defender.get('max_hp') * 0.25)
                     defender['current_hp'] = min(defender.get('max_hp'), defender['current_hp'] + heal)
                     log.append(f"  {defender.get('species')} healed by {def_ability}!")
                 else:
                     stages = defender.setdefault('stat_stages', {})
                     stages['spa'] = min(6, stages.get('spa', 0) + 1)
                     log.append(f"  {defender.get('species')}'s Sp. Atk rose (Storm Drain)!")
                 return
                 
            # Flash Fire
            if move_type == 'Fire' and def_ability == 'Flash Fire':
                 log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}")
                 log.append(f"  {defender.get('species')}'s Fire power rose (Flash Fire)!")
                 # TODO: Set Flash Fire flag
                 return
                 
            # Levitate (Ground)
            if move_type == 'Ground' and def_ability == 'Levitate':
                 log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}")
                 log.append(f"  {defender.get('species')} makes ground moves miss with Levitate!")
                 return
                 
            # 2. Check for Immunity Flag from Calc Description (Generic Type Immunity)
            desc = res.get('desc', '').lower()
            if "does not affect" in desc:
                log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}")
                log.append(f"  It doesn't affect {defender.get('species')}...")
                return

            # Apply Damage
            defender['current_hp'] -= damage_dealt
            
            hp_pct = max(0, int((defender['current_hp'] / defender['max_hp']) * 100))
            hp_str = f"{max(0, defender['current_hp'])}/{defender['max_hp']} HP ({hp_pct}%)"
            
            # Type effectiveness (simplified)
            eff_str = ""
            if "super effective" in desc:
                eff_str = " (It's super effective!)"
            elif "not very effective" in desc:
                eff_str = " (It's not very effective...)"
                
            log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}{eff_str}")
            log.append(f"  {defender.get('species')}: {hp_str} (-{damage_dealt} dmg)")
            
            if defender['current_hp'] <= 0:
                log.append(f"  {defender.get('species')} fainted!")
            
            # 5. Taunt check (before effects)
            if 'taunt' in attacker.get('volatiles', []) and res.get('category') == 'Status':
                 log.append(f"  {attacker.get('species')} can't use {move_name} after the Taunt!")
                 return

            # Apply Effects
            if defender['current_hp'] > 0:
                self.apply_move_effects(state, attacker, defender, res, damage_dealt, log)
            
            # 6. Post-Move Passive Effects
            # Life Orb Recoil
            if attacker.get('item') == 'Life Orb' and damage_dealt > 0:
                recoil = max(1, int(attacker.get('max_hp', 100) / 10))
                if attacker.get('ability') != 'Magic Guard':
                    attacker['current_hp'] -= recoil
                    log.append(f"  {attacker.get('species')} lost HP due to Life Orb (-{recoil})")
            
            # Set Choice Lock
            if attacker.get('item') in ['Choice Band', 'Choice Specs', 'Choice Scarf']:
                if not attacker.get('locked_move'):
                     attacker['locked_move'] = move_name
        else:
            log.append(f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name} (Failed)")


    def apply_move_effects(self, state: BattleState, attacker, defender, move_data, damage_dealt, log):
        attacker_side = 'player' if attacker == state.player_active else 'ai'
        defender_side = 'ai' if attacker_side == 'player' else 'player'
        
        # Recoil
        recoil = move_data.get('recoil')
        if isinstance(recoil, (list, tuple)) and len(recoil) >= 2:
            pct = recoil[0]
            source = recoil[1]
            if source == 'damage' or source == '1': # '1' is damage in some calc versions
                recoil_dmg = damage_dealt * (pct / 100)
                attacker['current_hp'] -= int(recoil_dmg)
                log.append(f"  Recoil: {int(recoil_dmg)}")
            elif source == 'max': # e.g. Steel Beam / Mind Blown
                recoil_dmg = attacker.get('max_hp') * (pct / 100)
                attacker['current_hp'] -= int(recoil_dmg)
                log.append(f"  Recoil: {int(recoil_dmg)}")

        # Drain
        drain = move_data.get('drain')
        if isinstance(drain, (list, tuple)) and len(drain) >= 2:
             pct = drain[0]
             heal = damage_dealt * (pct / 100)
             # Liquid Ooze check?
             if defender.get('ability') == 'Liquid Ooze':
                 attacker['current_hp'] -= int(heal)
                 log.append(f"  Liquid Ooze hurt attacker: {int(heal)}")
             else:
                 attacker['current_hp'] = min(attacker.get('max_hp'), attacker['current_hp'] + int(heal))
                 log.append(f"  {attacker.get('species')} drained health (+{int(heal)})")
        
        m_name = move_data.get('moveName')
        override_status = {
            'Will-O-Wisp': 'brn', 'Toxic': 'tox', 'Thunder Wave': 'par', 
            'Hypnosis': 'slp', 'Sleep Powder': 'slp', 'Spore': 'slp', 'Dark Void': 'slp', 'Sing': 'slp',
            'Poison Gas': 'psn', 'Poison Powder': 'psn', 'Stun Spore': 'par', 'Glare': 'par'
        }
        override_volatile = {
            'Confuse Ray': 'confusion', 'Supersonic': 'confusion', 'Sweet Kiss': 'confusion', 'Teeter Dance': 'confusion',
            'Swagger': 'confusion', 'Flatter': 'confusion', 'Taunt': 'taunt'
        }
        
        status = move_data.get('status')
        if not status and m_name in override_status: status = override_status[m_name]
        if status and not defender.get('status'):
            defender['status'] = status
            if status == 'slp': defender['status_counter'] = 2
            log.append(f"  {defender.get('species')} was inflicted with {status}!")

        v_status = move_data.get('volatileStatus')
        if not v_status and m_name in override_volatile: v_status = override_volatile[m_name]
        if v_status:
             v_list = defender.setdefault('volatiles', [])
             if v_status == 'flinch' and 'flinch' not in v_list:
                  v_list.append('flinch')
                  log.append(f"  {defender.get('species')} flinched!")
             elif v_status == 'confusion' and 'confusion' not in v_list:
                  v_list.append('confusion')
                  defender['confusion_turns'] = (hash(str(defender['current_hp'])) % 4) + 2
                  log.append(f"  {defender.get('species')} became confused!")
             elif v_status == 'taunt' and 'taunt' not in v_list:
                  v_list.append('taunt')
                  defender['taunt_turns'] = 3
                  log.append(f"  {defender.get('species')} fell for the Taunt!")

        # 3. Secondaries
        sec_list = move_data.get('secondaries', [])
        if not isinstance(sec_list, list): sec_list = []
        for sec in sec_list:
             chance = sec.get('chance', 100)
             if attacker.get('ability') == 'Serene Grace': chance *= 2
             if chance >= 100:
                 if sec.get('status') and not defender.get('status'):
                     defender['status'] = sec['status']
                     log.append(f"  {defender.get('species')} was inflicted with {sec['status']}!")
                 if sec.get('boosts'):
                     for stat, stage in sec['boosts'].items():
                         stages = defender.setdefault('stat_stages', {})
                         stages[stat] = max(-6, min(6, stages.get(stat, 0) + stage))
                         log.append(f"  {defender.get('species')}'s {stat} {'rose' if stage>0 else 'fell'}!")
                 if sec.get('self') and sec['self'].get('boosts'):
                     for stat, stage in sec['self']['boosts'].items():
                         stages = attacker.setdefault('stat_stages', {})
                         stages[stat] = max(-6, min(6, stages.get(stat, 0) + stage))
                         log.append(f"  {attacker.get('species')}'s {stat} {'rose' if stage>0 else 'fell'}!")
                 if sec.get('volatileStatus'):
                      v = sec['volatileStatus']
                      v_list = defender.setdefault('volatiles', [])
                      if v == 'flinch' and 'flinch' not in v_list:
                           v_list.append('flinch')
                           log.append(f"  {defender.get('species')} flinched!")
                      elif v == 'confusion' and 'confusion' not in v_list:
                           v_list.append('confusion')
                           defender['confusion_turns'] = (hash(str(defender['current_hp'])) % 4) + 2
                           log.append(f"  {defender.get('species')} became confused!")

        # 4. Self Boosts (Primary)
        self_data = move_data.get('self')
        if isinstance(self_data, dict) and self_data.get('boosts'):
             stages = attacker.setdefault('stat_stages', {})
             for stat, val in self_data['boosts'].items():
                 prev = stages.get(stat, 0)
                 stages[stat] = max(-6, min(6, prev + val))
                 change = stages[stat] - prev
                 if change != 0:
                    log.append(f"  {attacker.get('species')}'s {stat.upper()} {'sharply ' if abs(change)>=2 else ''}{'rose' if change>0 else 'fell'}!")

        # 5. Field Effects
        override_field = {
            'Rain Dance': 'Rain', 'Sunny Day': 'Sun', 'Sandstorm': 'Sandstorm', 'Hail': 'Hail',
            'Electric Terrain': 'Electric', 'Grassy Terrain': 'Grassy', 'Misty Terrain': 'Misty', 'Psychic Terrain': 'Psychic'
        }
        if m_name in override_field:
             if 'Terrain' in m_name:
                 state.fields['terrain'] = override_field[m_name]
                 state.fields['terrain_turns'] = 5
                 log.append(f"  Terrain became {override_field[m_name]}!")
             else:
                 state.fields['weather'] = override_field[m_name]
                 state.fields['weather_turns'] = 5
                 log.append(f"  Weather became {override_field[m_name]}!")
        elif m_name in ['Reflect', 'Light Screen', 'Aurora Veil']:
             screen_key = m_name.lower().replace(' ', '_')
             state.fields['screens'][attacker_side][screen_key] = 5
             log.append(f"  {m_name} started on {attacker_side.upper()} side!")
        elif m_name == 'Tailwind':
             state.fields['tailwind'][attacker_side] = 4
             log.append(f"  Tailwind started on {attacker_side.upper()} side!")
        elif m_name == 'Trick Room':
             if state.fields.get('trick_room', 0) > 0:
                 state.fields['trick_room'] = 0
                 log.append(f"  The dimensions returned to normal!")
             else:
                 state.fields['trick_room'] = 5
                 log.append(f"  Twisted the dimensions!")
        elif m_name in ['Stealth Rock', 'Spikes', 'Toxic Spikes', 'Sticky Web']:
             h_list = state.fields['hazards'][defender_side]
             if m_name == 'Spikes' and h_list.count('Spikes') < 3:
                 h_list.append('Spikes')
                 log.append(f"  Spikes set on {defender_side.upper()} side!")
             elif m_name == 'Toxic Spikes' and h_list.count('Toxic Spikes') < 2:
                 h_list.append('Toxic Spikes')
                 log.append(f"  Toxic Spikes set on {defender_side.upper()} side!")
             elif m_name not in h_list:
                 h_list.append(m_name)
                 log.append(f"  {m_name} set on {defender_side.upper()} side!")

        # 6. Pivot Moves
        if m_name in ['U-turn', 'Volt Switch', 'Flip Turn', 'Parting Shot'] and damage_dealt > 0:
             log.append(f"  {attacker.get('species')} is switching out!")
             attacker['must_switch'] = True
