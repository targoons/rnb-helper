from typing import Dict, List, Optional, Tuple, Any
import logging
import json
import os
import random
import math
import copy

from pkh_app.mechanics import Mechanics
from .state import BattleState, TYPE_CHART
from .enricher import StateEnricher
from .triggers import TriggerHandler
from .damage import DamageCalculator

class BattleEngine:
    def __init__(self, calc_client=None, species_names=None, move_names=None):
        self.calc_client = calc_client
        self.species_names = species_names or {}
        self.move_names = move_names or {}

        # Load JSON Data
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        pokedex_path = os.path.join(base_dir, "data", "pokedex_rich.json")
        try:
            with open(pokedex_path, "r", encoding="utf-8") as f:
                self.pokedex = json.load(f)
        except Exception:
            logging.warning("Failed to load pokedex_rich.json")
            self.pokedex = {}

        mechanics_path = os.path.join(base_dir, "data", "mechanics_rich.json")
        try:
             with open(mechanics_path, "r", encoding="utf-8") as f:
                self.mechanics = json.load(f)
        except Exception:
             logging.warning("Failed to load mechanics_rich.json")
             self.mechanics = {}

        # rich_data is an alias for mechanics (used throughout the codebase)
        self.rich_data = self.mechanics

        # Initialize Helpers
        self.enricher = StateEnricher(self.pokedex, self.rich_data, self.move_names, self.species_names)
        self.triggers = TriggerHandler(self.enricher, self.rich_data)
        self.damage_calculator = DamageCalculator(self.calc_client, self.enricher, self.rich_data, self.move_names)

    def _ensure_types(self, mon):
        if not mon or mon.get("types"): return
        s = mon.get("name", mon.get("species"))
        if s:
             slug = s.lower().replace(" ", "").replace("-", "")
             d = self.pokedex.get(slug)
             mon["types"] = d.get("types", ["Normal"]) if d else ["Normal"]
        else:
             mon["types"] = ["Normal"]

    def get_damage_rolls(self, attacker, defender, moves, field):
        return self.damage_calculator.get_damage_rolls(attacker, defender, moves, field)

    def calc_damage_for_moves(self, attacker, defender, move_names, field_conditions=None):
        return self.damage_calculator.calc_damage_for_moves(attacker, defender, move_names, field_conditions)

    def get_state_log_lines(self, state: BattleState) -> List[str]:
        lines = []
        p = state.player_active
        a = state.ai_active
        lines.append(f"  Player Active: {p['name']} ({p['current_hp']}/{p['max_hp']} HP)")
        lines.append(f"  AI Active:     {a['name']} ({a['current_hp']}/{a['max_hp']} HP)")
        
        fields = state.fields
        field_info = []
        if fields.get("weather"):
            field_info.append(f"Weather: {fields['weather']} ({fields.get('weather_turns', 0)} turns left)")
        if fields.get("terrain"):
            field_info.append(f"Terrain: {fields['terrain']} ({fields.get('terrain_turns', 0)} turns left)")
        else:
            field_info.append("Terrain: None")
            
        for side in ["player", "ai"]:
            hazards = fields.get("hazards", {}).get(side, [])
            screens = fields.get("screens", {}).get(side, {})
            effs = []
            if "Stealth Rock" in hazards: effs.append("Stealth Rock")
            if hazards.count("Spikes"): effs.append(f"Spikes(x{hazards.count('Spikes')})")
            if hazards.count("Toxic Spikes"): effs.append(f"Toxic Spikes(x{hazards.count('Toxic Spikes')})")
            if screens.get("reflect"): effs.append("Reflect")
            if screens.get("light_screen"): effs.append("Light Screen")
            if screens.get("aurora_veil"): effs.append("Aurora Veil")
            if screens.get("tailwind"): effs.append("Tailwind")
            if effs: field_info.append(f"{side.upper()} Field: {', '.join(effs)}")
            
        if field_info: lines.append(f"  Field Effects: {' | '.join(field_info)}")
        
        for name, mon in [("Player", p), ("AI", a)]:
            stats = mon.get("stats", {})
            stages = mon.get("stat_stages", {})
            s_str = []
            for s in ["atk", "def", "spa", "spd", "spe"]:
                val = Mechanics.get_effective_stat(mon, s, state.fields)
                s_str.append(f"{s.upper()}:{val} ({stats.get(s,0)}{'+' if stages.get(s,0)>=0 else ''}{stages.get(s,0)})")
            for s in ["acc", "eva"]:
                s_str.append(f"{s.upper()}:{'+' if stages.get(s,0)>=0 else ''}{stages.get(s,0)}")
            lines.append(f"  {name} Stats: {' '.join(s_str)}")
            
            if mon.get("status"):
                lines.append(f"  {name} Status: {mon['status'].upper()}")
                
            vols = []
            if "confusion" in mon.get("volatiles", []): vols.append(f"Confused({mon.get('confusion_turns')}t)")
            if vols: lines.append(f"  {name} Volatiles: {', '.join(vols)}")
            
        return lines

    def enrich_state(self, state: BattleState):
        self.enricher.enrich_state(state)

    def enrich_mon(self, mon: Dict):
        self.enricher.enrich_mon(mon)

    def _is_ability_suppressed(self, state, mon, attacker, rich_ab):
        return self.triggers._is_ability_suppressed(state, mon, attacker, rich_ab)

    def _check_hp_triggers(self, state, mon, log):
        return self.triggers._check_hp_triggers(state, mon, log)

    def _apply_boosts(self, mon, boosts, log, source_name=None):
        return self.triggers._apply_boosts(mon, boosts, log, source_name)

    def _check_mental_herb(self, mon, log):
        return self.triggers._check_mental_herb(mon, log)

    def trigger_event(self, state, event_name, source_mon, target_mon, log, move_name=None, damage=0, context=None):
        return self.triggers.trigger_event(state, event_name, source_mon, target_mon, log, move_name, damage, context)

    def _process_trigger(self, state, trigger_mon, event_name, owner, other, log, move_name, damage, context):
        return self.triggers._process_trigger(state, trigger_mon, event_name, owner, other, log, move_name, damage, context)

    def _apply_rich_trigger(self, rich_data, owner, other, event_key, log, move_name=None, context=None):
        return self.triggers._apply_rich_trigger(rich_data, owner, other, event_key, log, move_name, context)

    def _perform_form_change(self, mon, new_form_slug, log, state=None):
        return self.enricher._perform_form_change(mon, new_form_slug, log, state)
        
    def _check_mega_evolution(self, state, side, log):
        return self.enricher._check_mega_evolution(state, side, log)

    def _check_primal_reversion(self, state, side, log):
         return self.enricher._check_primal_reversion(state, side, log)
    
    def _is_item_unremovable(self, item_name, mon):
         if mon.get("ability") == "Sticky Hold":
             return True
         return self.enricher._is_item_unremovable(item_name, mon)

    def get_move_name(self, move_id):
        return self.move_names.get(str(move_id), str(move_id))

    def get_species_name(self, s_id):
        return self.species_names.get(str(s_id), str(s_id))

    def check_immunity(self, attacker, defender, move_name):
        return self.triggers.check_immunity(attacker, defender, move_name)

    def check_prankster_immunity(self, attacker, defender, move_category):
        return self.triggers.check_prankster_immunity(attacker, defender, move_category)

    def _makes_contact(self, move_name, attacker):
        return self.triggers._makes_contact(move_name, attacker)

    def _is_sound(self, move_name):
        return self.triggers._is_sound(move_name)

    def _check_priority_block(self, attacker, defender, move_name, state):
        return self.triggers._check_priority_block(attacker, defender, move_name, state)

    def _get_modifier(self, mon, key, move_data=None, state=None, target=None):
        return self.triggers._get_modifier(mon, key, move_data, state, target)

    def get_move_priority(self, move_name, attacker, state=None):
        return self.triggers.get_move_priority(move_name, attacker, state)

    def _get_mechanic(self, key, category):
        return self.triggers._get_mechanic(key, category)

    def _check_mechanic(self, key, category, subkey):
        return self.triggers._check_mechanic(key, category, subkey)

    def get_valid_actions(self, state: BattleState, side: str) -> List[str]:
        """
        Returns a list of valid actions for the given side.
        Actions: "Move: <Name>", "Switch: <Species>"
        """
        actions = []
        active = state.player_active if side == "player" else state.ai_active
        party = state.player_party if side == "player" else state.ai_party

        # 1. Forced Switch (if fainted or pivoting)
        if active.get("current_hp", 0) <= 0 or active.get("must_switch"):
            # Must switch
            for p in party:
                if p.get("current_hp") > 0 and p.get("species") != active.get(
                    "species"
                ):
                    actions.append(f"Switch: {p.get('species')}")
            return actions

        # 2. Standard Turn
        # 2a. Moves
        locked_move = active.get("locked_move")
        rich_item = active.get("_rich_item")

        if True:  # Always allow move selection, sleep failure happens in execution
            for m in active.get("moves", []):
                # Choice Lock Check
                if locked_move and m != locked_move:
                    continue

                # Assault Vest Check
                if rich_item and rich_item.get("name") == "Assault Vest":
                    m_slug = (
                        str(m)
                        .lower()
                        .replace(" ", "")
                        .replace("-", "")
                        .replace("'", "")
                    )
                    rd = active.get("_rich_moves", {}).get(m_slug)
                    if rd and rd.get("category") == "Status":
                        continue

                actions.append(f"Move: {m}")

        # 2b. Switches
        # Simplified: Don't allow switch if Trapped (Shadow Tag etc) - Todo
        for p in party:
            if p.get("current_hp") > 0 and p.get("species") != active.get("species"):
                actions.append(f"Switch: {p.get('species')}")

        return actions

    def apply_turn(
        self, state: BattleState, player_action: str, ai_action: str
    ) -> Tuple[BattleState, List[str]]:
        """
        Simulates one ply/turn.
        """
        new_state = state.deep_copy()
        self.enrich_state(new_state)
        log = []

        # 0. Handle Forced Switches
        # If one side is fainted at start of turn (Switch Phase), we just process the switch and return.
        p_fainted = new_state.player_active.get(
            "current_hp", 0
        ) <= 0 or new_state.player_active.get("must_switch")
        a_fainted = new_state.ai_active.get(
            "current_hp", 0
        ) <= 0 or new_state.ai_active.get("must_switch")

        if p_fainted or a_fainted:
            if p_fainted and player_action.startswith("Switch:"):
                self.perform_switch(
                    new_state, "player", player_action.split(": ")[1], log
                )
            elif p_fainted and not player_action.startswith("Switch:"):
                # Forced switch needed but not provided - Perform random switch to prevent stall
                # This happens if 'U-turn' flag set but driver sent 'Move'
                valid = self.get_valid_actions(new_state, "player")
                switches = [a for a in valid if a.startswith("Switch:")]
                if switches:
                    self.perform_switch(
                        new_state, "player", switches[0].split(": ")[1], log
                    )

            if a_fainted and ai_action.startswith("Switch:"):
                self.perform_switch(new_state, "ai", ai_action.split(": ")[1], log)
            elif a_fainted and not ai_action.startswith("Switch:"):
                valid = self.get_valid_actions(new_state, "ai")
                switches = [a for a in valid if a.startswith("Switch:")]
                if switches:
                    self.perform_switch(
                        new_state, "ai", switches[0].split(": ")[1], log
                    )

            return new_state, log

        # 0.5 Init Turn Flags
        new_state.fields["protected_sides"] = []
        new_state.player_active["lost_focus"] = False  # For Focus Punch
        new_state.ai_active["lost_focus"] = False  # For Focus Punch

        # Start of Turn Effects (Quick Claw, Custap Berry, etc)
        if not player_action.startswith("Switch:"):
            Mechanics.apply_start_turn_effects(new_state.player_active, new_state, log)
        else:
            # Ensure mod is 0 for switch logic just in case
            new_state.player_active["turn_priority_mod"] = 0

        if not ai_action.startswith("Switch:"):
            Mechanics.apply_start_turn_effects(new_state.ai_active, new_state, log)
        else:
            new_state.ai_active["turn_priority_mod"] = 0

        new_state.fields["last_move_used_this_turn"] = None

        # 1. Determine Order
        player_speed = Mechanics.get_effective_speed(
            new_state.player_active, new_state.fields, side="player"
        )
        ai_speed = Mechanics.get_effective_speed(
            new_state.ai_active, new_state.fields, side="ai"
        )

        # Parse Priorities
        # Parse Priorities
        # Process move for player
        p_act = (
            player_action.replace("Move: ", "")
            if player_action.startswith("Move:")
            else None
        )
        a_act = (
            ai_action.replace("Move: ", "") if ai_action.startswith("Move:") else None
        )

        p_prio = (
            6
            if player_action.startswith("Switch:")
            else self.get_move_priority(p_act, new_state.player_active, new_state)
            + new_state.player_active.get("turn_priority_mod", 0)
        )
        a_prio = (
            6
            if ai_action.startswith("Switch:")
            else self.get_move_priority(a_act, new_state.ai_active, new_state)
            + new_state.ai_active.get("turn_priority_mod", 0)
        )

        player_first = False
        if p_prio > a_prio:
            player_first = True
        elif a_prio > p_prio:
            player_first = False
        else:
            # Equal Move Priority -> Check Turn Priority Mod (Quick Claw, etc)
            p_mod = new_state.player_active.get("turn_priority_mod", 0)
            a_mod = new_state.ai_active.get("turn_priority_mod", 0)

            if p_mod > a_mod:
                player_first = True
            elif a_mod > p_mod:
                player_first = False
            else:
                # Speed Check
                if new_state.fields.get("trick_room", 0) > 0:
                    player_first = player_speed <= ai_speed
                else:
                    player_first = (
                        player_speed >= ai_speed
                    )  # Speed ties -> Player wins (Optimistic)

        first = ("player", player_action) if player_first else ("ai", ai_action)
        second = ("ai", ai_action) if player_first else ("player", player_action)

        # 2. Execution
        # Mega Evolution Check (Start of Turn before moves)
        self._check_mega_evolution(new_state, first[0], log)
        self._check_mega_evolution(new_state, second[0], log)

        try:
            self.execute_turn_action(
                new_state, first[0], first[1], second[0], log, defender_action=second[1]
            )
            if first[1].startswith("Move: "):
                new_state.fields["last_move_used_this_turn"] = first[1].replace(
                    "Move: ", ""
                )

            self.execute_turn_action(
                new_state, second[0], second[1], first[0], log, defender_action=first[1]
            )
            if second[1].startswith("Move: "):
                new_state.fields["last_move_used_this_turn"] = second[1].replace(
                    "Move: ", ""
                )
        except Exception as e:
            import traceback

            log.append(f"CRASH: {e}")
            log.append(traceback.format_exc())
            print(f"Simulation Crashed: {e}")  # Ensure it prints to stdout too

        # 3. End Turn
        Mechanics.apply_end_turn_effects(new_state, log)
        self.handle_end_of_turn(new_state, log)

        # 4. Increment active turns and Clear Turn Volatiles (Flinch)
        for p in [new_state.player_active, new_state.ai_active]:
            if p.get("current_hp", 0) > 0:
                p["activeTurns"] = p.get("activeTurns", 0) + 1

            v = p.setdefault("volatiles", [])
            if "flinch" in v:
                v.remove("flinch")

            # SYNC BACK TO PARTY (Fixes "Zombie Switch" bug due to copy-state)
            party = (
                new_state.player_party
                if p == new_state.player_active
                else new_state.ai_party
            )
            for member in party:
                if member["species"] == p["species"]:
                    member["current_hp"] = p["current_hp"]
                    member["status"] = p.get("status")
                    # member['stat_stages'] = p.get('stat_stages', {}).copy() # Optionally sync stages
                    break

        return new_state, log

    def handle_end_of_turn(self, state: BattleState, log: List[str]):
        """
        Universal End-of-Turn handler.
        Most logic is now in Mechanics.apply_end_turn_effects.
        This remains for any engine-specific overrides or future hooks.
        """
        for side in ["player", "ai"]:
            mon = state.player_active if side == "player" else state.ai_active
            if not mon or mon.get("current_hp", 0) <= 0:
                continue

            # Clear turn flags
            mon.pop("stats_raised_this_turn", None)

    def _apply_residual(
        self, mon: dict, source_type: str, state: BattleState, log: List[str]
    ):
        rd = mon.get("_rich_ability" if source_type == "abilities" else "_rich_item")
        if not rd:
            return

        name = rd.get("name")
        max_hp = mon.get("max_hp", 100)
        volatiles = mon.get("volatiles", [])

        # 1. Healing / Damage (Black Sludge, Leftovers)
        if name == "Black Sludge":
            if "embargo" in volatiles:
                return  # Embargo blocks items
            if "Poison" in mon.get("types", []):
                if "healblock" in volatiles:
                    return
                if mon["current_hp"] < max_hp:
                    heal = max(1, int(max_hp / 16))
                    mon["current_hp"] = min(max_hp, mon["current_hp"] + heal)
                    log.append(
                        f"  {mon.get('species')} restored HP via its Black Sludge!"
                    )
            elif mon.get("ability") != "Magic Guard":
                dmg = max(1, int(max_hp / 8))
                mon["current_hp"] -= dmg
                log.append(
                    f"  {mon.get('species')} was hurt by its Black Sludge! (-{dmg})"
                )
            return

        if source_type == "items" and "embargo" in volatiles:
            return

        hr = rd.get("healRatio")
        if hr:
            if "healblock" in volatiles:
                return
            if mon["current_hp"] < max_hp:
                heal = int(max_hp * hr[0] / hr[1])
                mon["current_hp"] = min(max_hp, mon["current_hp"] + heal)
                log.append(f"  {mon.get('species')} restored HP via its {name}!")

        # 2. Boosts (e.g. Speed Boost)
        res_boosts = rd.get("boosts")
        if res_boosts:
            # Condition check for Speed Boost
            if name == "Speed Boost" and not mon.get("activeTurns", 0):
                return

            for stat, amount in res_boosts.items():
                stages = mon.setdefault("stat_stages", {})
                current = stages.get(stat, 0)
                if amount > 0 and current < 6:
                    stages[stat] = min(6, current + amount)
                    log.append(
                        f"  {mon.get('species')}'s {name} raised its {stat.upper()}!"
                    )
                elif amount < 0 and current > -6:
                    stages[stat] = max(-6, current + amount)
                    log.append(
                        f"  {mon.get('species')}'s {name} lowered its {stat.upper()}!"
                    )

    def perform_switch(self, state, side, species_id, log):
        party = state.player_party if side == "player" else state.ai_party
        target = None
        s_name = self.get_species_name(species_id)
        for p in party:
            # Match either ID or Name
            if (
                str(p.get("species_id")) == str(species_id)
                or p.get("species") == s_name
            ):
                target = p
                break

        if target:
            # swap current active to party and target to active
            active = state.player_active if side == "player" else state.ai_active

            # Switch-Out Effects (Regenerator, Natural Cure)
            if active.get("ability") == "Regenerator":
                heal = int(active.get("max_hp", 1) / 3)
                active["current_hp"] = min(
                    active.get("max_hp"), active["current_hp"] + heal
                )
                log.append(f"  {active.get('species')} restored HP using Regenerator!")

            if active.get("ability") == "Natural Cure":
                if active.get("status"):
                    active["status"] = None
                    log.append(f"  {active.get('species')} was cured by Natural Cure!")

            # Find current active in party and update its HP
            for p in party:
                if p["species"] == active["species"]:
                    p["current_hp"] = active["current_hp"]
                    p["stat_stages"] = active.get("stat_stages", {}).copy()
                    p["status"] = active.get("status")
                    p["protect_counter"] = 0
                    p.pop("must_switch", None)
                    p.pop("locked_move", None)  # Clear choice lock
                    break

            # Switch-In Logic
            target_copy = target.copy()
            target_copy["protect_counter"] = 0

            # Check Primal Reversion on Switch-In
            # Since target_copy is about to become active, we temporarily set it in state
            if side == "player":
                state.player_active = target_copy
            else:
                state.ai_active = target_copy
            self._check_primal_reversion(state, side, log)
            # Fetch enriched/transformed copy back
            target_copy = state.player_active if side == "player" else state.ai_active

            # Baton Pass Handling
            if active.get("baton_pass"):
                # Copy volatiles / stats from outgoing 'active'
                target_copy["stat_stages"] = active.get("stat_stages", {}).copy()
                # Copy specific volatiles
                kept_vols = [
                    "substitute",
                    "curse",
                    "leech_seed",
                    "confusion",
                ]  # Simplified
                active_vols = active.get("volatiles", [])
                new_vols = target_copy.get("volatiles", [])
                for v in kept_vols:
                    if v in active_vols:
                        new_vols.append(v)
                target_copy["volatiles"] = list(set(new_vols))
                log.append(f"  Stats and effects were passed to {s_name}!")

                # Helper: Clear BP flag from party member record
                for p in party:
                    if p["species"] == active["species"]:
                        p.pop("baton_pass", None)

            if side == "player":
                state.player_active = target_copy
            else:
                state.ai_active = target_copy

            log.append(f"[{side.upper()}] switched to {s_name}")

            # Apply Entry Hazards
            self.apply_switch_hazards(state, side, target_copy, log)

            # Apply Switch-In Abilities (Intimidate, Drizzle, etc.)
            self.apply_switch_in_abilities(state, side, target_copy, log)
        else:
            log.append(f"[{side.upper()}] tried to switch to {species_id} but failed")

    def apply_switch_in_abilities(self, state, side, mon, log):
        ability = mon.get("ability")
        if not ability:
            return

        opponent = state.ai_active if side == "player" else state.player_active
        opp_side = "ai" if side == "player" else "player"

        if ability == "Intimidate":
            # Check for immunities (Clear Body, White Smoke, Hyper Cutter, Inner Focus in Gen 8, Oblivious in Gen 8, Scrappy in Gen 8)
            # Simplified check
            opp_ability = opponent.get("ability", "")
            if opp_ability in [
                "Clear Body",
                "White Smoke",
                "Hyper Cutter",
                "Inner Focus",
                "Oblivious",
                "Scrappy",
                "Full Metal Body",
            ]:
                log.append(
                    f"  {opponent.get('species')} wasn't affected by Intimidate ({opp_ability})!"
                )
            elif opp_ability == "Mirror Armor":
                log.append(
                    f"  {opponent.get('species')} was unaffected by Intimidate (Mirror Armor)!"
                )
                Mechanics.apply_boosts(
                    mon, {"atk": -1}, log, source_name="Mirror Armor"
                )
            else:
                log.append(
                    f"  {mon.get('species')} intimidated {opponent.get('species')}!"
                )
                Mechanics.apply_boosts(
                    opponent, {"atk": -1}, log, source_name="Intimidate"
                )
                
                # Defiant / Competitive trigger on drop
                if opp_ability == "Defiant":
                    Mechanics.apply_boosts(opponent, {"atk": 2}, log, source_name="Defiant")
                elif opp_ability == "Competitive":
                    Mechanics.apply_boosts(opponent, {"spa": 2}, log, source_name="Competitive")

                # Adrenaline Orb Check
                # Adrenaline Orb Check
                if opponent.get("item") == "Adrenaline Orb":
                    Mechanics.apply_boosts(
                        opponent, {"spe": 1}, log, source_name="Adrenaline Orb"
                    )
                    opponent["item"] = None
                    log.append(
                        f"  {opponent.get('species')} consumed its Adrenaline Orb!"
                    )
                    if opponent.get("ability") == "Unburden":
                        opponent["unburden_active"] = True
                        log.append(f"  {opponent.get('species')} became unburdened!")

        elif ability == "Download":
            defense = opponent.get("stats", {}).get("def", 100)
            sp_def = opponent.get("stats", {}).get("spd", 100)
            if defense < sp_def:
                Mechanics.apply_boosts(mon, {"atk": 1}, log, source_name="Download")
            else:
                Mechanics.apply_boosts(mon, {"spa": 1}, log, source_name="Download")

        elif ability in ["Drizzle", "Drought", "Sand Stream", "Snow Warning"]:
            weather_map = {
                "Drizzle": "Rain",
                "Drought": "Sun",
                "Sand Stream": "Sand",
                "Snow Warning": "Hail",
            }
            w = weather_map[ability]
            # Check Primal/Desolate logic? Ignoring for now or override.
            if state.fields.get("weather") != w:
                state.fields["weather"] = w
                state.fields["weather_turns"] = 999  # Run & Bun specific: Permanent
                log.append(f"  {mon.get('species')} made it {w} with {ability}!")

        elif ability in [
            "Electric Surge",
            "Grassy Surge",
            "Misty Surge",
            "Psychic Surge",
        ]:
            terrain_map = {
                "Electric Surge": "Electric",
                "Grassy Surge": "Grassy",
                "Misty Surge": "Misty",
                "Psychic Surge": "Psychic",
            }
            t = terrain_map[ability]
            if state.fields.get("terrain") != t:
                state.fields["terrain"] = t
                state.fields["terrain_turns"] = 999  # Run & Bun specific: Permanent
                log.append(
                    f"  {mon.get('species')} created {t} Terrain with {ability}!"
                )
                # Terrain surge might trigger seeds for the opponent or allies
                for side_name in ["player", "ai"]:
                    side_mon = (
                        state.player_active
                        if side_name == "player"
                        else state.ai_active
                    )
                    if side_mon:
                        self.apply_switch_in_items(state, side_name, side_mon, log)

        elif ability == "Imposter":
            if opponent and opponent.get("current_hp", 0) > 0:
                log.append(
                    f"  {mon.get('species')} transformed into {opponent.get('species')} using Imposter!"
                )
                mon["species"] = opponent.get("species")
                mon["types"] = list(opponent.get("types", []))
                mon["moves"] = list(opponent.get("moves", []))
                # Copy stats but keep original Max HP / Current HP
                orig_hp = mon.get("current_hp")
                orig_max_hp = mon.get("max_hp")
                mon["stats"] = dict(opponent.get("stats", {}))
                mon["current_hp"] = orig_hp
                mon["max_hp"] = orig_max_hp
                mon["stat_stages"] = dict(opponent.get("stat_stages", {}))
                mon["ability"] = opponent.get("ability")
                mon["_rich_ability"] = opponent.get("_rich_ability")

        elif ability == "Anticipation":
            if opponent:
                dangerous = False
                opp_moves = opponent.get("moves", [])
                for m_id in opp_moves:
                    m_data = self._get_mechanic(m_id, "moves")
                    if not m_data or m_data.get("category") == "Status":
                        continue

                    # SE Check
                    eff = Mechanics.get_type_effectiveness_with_abilities(
                        m_data.get("type"), mon
                    )
                    if eff > 1:
                        dangerous = True
                        break

                    # OHKO / Explosion check
                    if m_data.get("ohko") or m_id in [
                        "Self-Destruct",
                        "Explosion",
                        "Final Gambit",
                    ]:
                        dangerous = True
                        break

                if dangerous:
                    log.append(f"  {mon.get('species')} shuddered with Anticipation!")

        elif ability == "Screen Cleaner":
            log.append(
                f"  {mon.get('species')} cleared the screens with Screen Cleaner!"
            )
            for s in ["player", "ai"]:
                state.fields["screens"][s]["reflect"] = 0
                state.fields["screens"][s]["light_screen"] = 0
                state.fields["screens"][s]["aurora_veil"] = 0

        elif ability == "Arena Trap":
            print(
                f"DEBUG ARENA TRAP: mon={mon.get('species')} opp={opponent.get('species')} grounded={self._is_grounded(opponent, state)}"
            )
            if opponent and self._is_grounded(opponent, state):
                log.append(
                    f"  {mon.get('species')}'s Arena Trap prevents {opponent.get('species')} from escaping!"
                )

        elif ability == "Shadow Tag":
            if opponent and opponent.get("ability") != "Shadow Tag":
                log.append(
                    f"  {mon.get('species')}'s Shadow Tag prevents {opponent.get('species')} from escaping!"
                )

        elif ability == "Magnet Pull":
            if opponent and "Steel" in opponent.get("types", []):
                log.append(
                    f"  {mon.get('species')}'s Magnet Pull prevents {opponent.get('species')} from escaping!"
                )

        elif ability == "Forecast":
            if mon.get("species") == "Castform":
                w = (state.fields.get("weather") or "").lower()
                target_form = "castform"
                if "rain" in w:
                    target_form = "castformrainy"
                elif "sun" in w or "sunny" in w:
                    target_form = "castformsunny"
                elif "hail" in w or "snow" in w:
                    target_form = "castformsnowy"

                if mon.get("species").lower().replace("-", "") != target_form:
                    print(
                        f"DEBUG: Castform changing from {mon.get('species')} to {target_form}"
                    )
                    self._perform_form_change(mon, target_form, log, state)
                    log.append(f"  Castform transformed due to Forecast!")

        elif ability == "Comatose":
            log.append(f"  {mon.get('species')} is drowsing due to Comatose!")

        elif ability == "Frisk":
            if opponent and opponent.get("item"):
                log.append(
                    f"  {mon.get('species')} frisked {opponent.get('species')} and found its {opponent.get('item')}!"
                )

        elif ability == "Forewarn":
            if opponent:
                ms = []
                for m in opponent.get("moves", []):
                    md = self._get_mechanic(m, "moves")
                    if md:
                        bp = md.get("basePower", 0)
                        if bp == 0 and md.get("ohko"):
                            bp = 150
                        ms.append((bp, md.get("name")))
                if ms:
                    ms.sort(key=lambda x: x[0], reverse=True)
                    max_bp = ms[0][0]
                    candidates = [name for b, name in ms if b == max_bp]
                    warn_move = random.choice(candidates)
                    log.append(
                        f"  {mon.get('species')}'s Forewarn alerted it to {warn_move}!"
                    )

        elif ability == "Mold Breaker":
            log.append(f"  {mon.get('species')} breaks the mold! (Mold Breaker)")

        elif ability == "Pressure":
            log.append(f"  {mon.get('species')} is exerting its Pressure!")

        elif ability == "Unnerve":
            log.append(
                f"  {mon.get('species')} makes the opposing team too nervous to eat Berries! (Unnerve)"
            )

    def apply_switch_in_items(self, state, side, mon, log):
        item_name = mon.get("item")
        if not item_name:
            return

        terrain = state.fields.get("terrain")

        # 1. Terrain Seeds
        seed_map = {
            "Electric Seed": ("Electric", "def"),
            "Grassy Seed": ("Grassy", "def"),
            "Misty Seed": ("Misty", "spd"),
            "Psychic Seed": ("Psychic", "spd"),
        }

        if item_name in seed_map:
            req_terrain, stat = seed_map[item_name]
            if terrain == req_terrain and self._is_grounded(mon, state):
                Mechanics.apply_boosts(mon, {stat: 1}, log, source_name=item_name)
                mon["item"] = None
                log.append(f"  {mon.get('species')} consumed its {item_name}!")
                if mon.get("ability") == "Unburden":
                    mon["unburden_active"] = True
                    log.append(f"  {mon.get('species')} became unburdened!")

        # 2. HP-Based Items (Berries)
        self.triggers._check_hp_triggers(state, mon, log)
        if item_name == "Room Service" and state.fields.get("trick_room", 0) > 0:
            Mechanics.apply_boosts(mon, {"spe": -1}, log, source_name=item_name)
            mon["item"] = None
            log.append(f"  {mon.get('species')} consumed its Room Service!")
            if mon.get("ability") == "Unburden":
                mon["unburden_active"] = True
                log.append(f"  {mon.get('species')} became unburdened!")

        # 2. Air Balloon Notification
        if item_name == "Air Balloon":
            log.append(
                f"  {mon.get('species')} floats in the air with its Air Balloon!"
            )

    def apply_switch_hazards(self, state, side, mon, log):
        hazards = state.fields.get("hazards", {}).get(side, [])
        if not hazards:
            return

        # Check early return for Heavy-Duty Boots
        if mon.get("item") == "Heavy-Duty Boots":
            return  # Immune to all entry hazards
        
        # Define grounding variables once for all hazard checks
        is_flying = "Flying" in mon.get("types", [])
        has_levitate = mon.get("ability") == "Levitate"
        has_balloon = mon.get("item") == "Air Balloon"
        is_grounded = not (is_flying or has_levitate or has_balloon)
        
        max_hp = mon.get("max_hp", 1)

        # 1. Stealth Rock
        if "Stealth Rock" in hazards:
            # Type Effectiveness
            # Simplified: We need a type chart or ask calc client?
            # For now, simplistic hardcoded check or skip effectiveness?
            # We can use Mechanics helper if available, or just hardcode checking "Rock" vs types.
            # Checking `calc_client` for 1 move is expensive.
            # Let's implement basic type chart for Rock.
            factor = 1.0
            rock_eff = {
                "Fire": 2,
                "Ice": 2,
                "Flying": 2,
                "Bug": 2,
                "Water": 0.5,
                "Grass": 0.5,
                "Fighting": 0.5,
                "Ground": 0.5,
                "Steel": 0.5,
            }
            for t in mon.get("types", []):
                factor *= rock_eff.get(t, 1.0)

            dmg = int(max_hp * 0.125 * factor)
            if dmg > 0:
                mon["current_hp"] -= dmg
                log.append(f"  Pointed stones dug into {mon.get('species')}! (-{dmg})")

        # 2. Spikes
        spikes_count = hazards.count(
            "Spikes"
        )  # Assuming list can contain duplicates? Or dict count?
        # state.fields default is list of strings. 'Spikes' usually appears once, maybe "Spikes_1"?
        # Plan implies list of strings. Assuming multiple "Spikes" entries?
        # Or counts handled externally?
        # I'll check `state.fields`.
        # Assuming simple presence for now. 1 Layer.
        if is_grounded:
            num_spikes = 0
            for h in hazards:
                if h == "Spikes":
                    num_spikes += 1

            if num_spikes > 0:
                frac = {1: 8, 2: 6, 3: 4}.get(num_spikes, 4 if num_spikes > 3 else 8)
                dmg = int(max_hp / frac)
                mon["current_hp"] -= dmg
                log.append(f"  {mon.get('species')} was hurt by Spikes! (-{dmg})")

            # 3. Sticky Web
            # 3. Sticky Web
            if "Sticky Web" in hazards:
                # Clear Body Check
                if mon.get("ability") in [
                    "Clear Body",
                    "White Smoke",
                    "Full Metal Body",
                ]:
                    log.append(
                        f"  {mon.get('species')} is unaffected by Sticky Web (Ability)!"
                    )
                else:
                    stages = mon.setdefault("stat_stages", {})
                    stages["spe"] = max(-6, stages.get("spe", 0) - 1)
                    log.append(f"  {mon.get('species')} got caught in a Sticky Web!")

                    if mon.get("ability") == "Defiant":
                        stages["atk"] = min(6, stages.get("atk", 0) + 2)
                        log.append(
                            f"  {mon.get('species')}'s Attack sharply rose (Defiant)!"
                        )
                    elif mon.get("ability") == "Competitive":
                        stages["spa"] = min(6, stages.get("spa", 0) + 2)
                    log.append(
                        f"  {mon.get('species')}'s Sp. Atk sharply rose (Competitive)!"
                    )

            # 4. Toxic Spikes
            if "Toxic Spikes" in hazards:
                # Poison Check (Type/Ability/Item)
                is_poison = "Poison" in mon.get("types", [])
                is_steel = "Steel" in mon.get("types", [])
                if is_flying or has_levitate or has_balloon:
                    pass  # Safe
                elif is_poison:
                    # Absorb!
                    for _ in range(hazards.count("Toxic Spikes")):
                        hazards.remove("Toxic Spikes")
                    log.append(f"  {mon.get('species')} absorbed the Toxic Spikes!")
                elif is_steel:
                    pass
                elif mon.get("ability") == "Immunity":
                    pass
                elif mon.get("status"):
                    pass  # Already status'd
                else:
                    count = hazards.count("Toxic Spikes")
                    if count >= 2:
                        mon["status"] = "tox"
                        mon["toxic_counter"] = 0
                        log.append(
                            f"  {mon.get('species')} was badly poisoned by Toxic Spikes!"
                        )
                    else:
                        mon["status"] = "psn"
                        log.append(
                            f"  {mon.get('species')} was poisoned by Toxic Spikes!"
                        )

    def _check_dancer_trigger(self, state, attacker_side, move_name, log):
        if move_name not in BattleState.DANCE_MOVES:
            return

        # Identify potential dancers (everyone except attacker)
        active_mons = []
        if attacker_side == "player":
            if state.ai_active.get("current_hp") > 0:
                active_mons.append(("ai", state.ai_active))
        else:
            if state.player_active.get("current_hp") > 0:
                active_mons.append(("player", state.player_active))

        # Double battles would check partner too, but this is 1v1

        for side, mon in active_mons:
            if mon.get("ability") == "Dancer":
                log.append(f"  {mon.get('species')}'s Dancer copied the dance!")
                # Execute the copied move immediately
                fake_action = f"Move: {move_name}"
                self._execute_turn_action_logic(
                    state, side, fake_action, attacker_side, log, check_dancer=False
                )

    def execute_turn_action(
        self, state, attacker_side, action, defender_side, log, defender_action=None
    ):
        """
        Wrapper for turn action execution to handle post-move triggers like Dancer.
        """
        self._execute_turn_action_logic(
            state, attacker_side, action, defender_side, log, defender_action
        )

        # Check Dancer Trigger if it was a move
        if action.startswith("Move: "):
            move_id = action.replace("Move: ", "")
            move_name = self.get_move_name(move_id)
            if move_name:
                self._check_dancer_trigger(state, attacker_side, move_name, log)

    def _execute_turn_action_logic(
        self,
        state,
        attacker_side,
        action,
        defender_side,
        log,
        defender_action=None,
        check_dancer=True,
    ):
        attacker = state.player_active if attacker_side == "player" else state.ai_active
        defender = state.ai_active if attacker_side == "player" else state.player_active

        # Ensure types for simulation
        self._ensure_types(attacker)
        self._ensure_types(defender)

        total_damage_dealt = 0
        damage_dealt = 0
        effectiveness = 1
        is_crit = False

        # Ensure field registry for broad-reaching abilities (Auras / Cloud Nine)
        state.fields["active_mons"] = [state.player_active, state.ai_active]

        if attacker.get("current_hp") <= 0:
            return  # Dead can't move

        # === TRUANT ABILITY CHECK ===
        # Truant causes the Pokemon to loaf every other turn
        if action.startswith("Move: ") and attacker.get('ability') == 'Truant':
            truant_loaf = attacker.get('truant_loaf', False)
            if truant_loaf:
                # Loafing this turn
                log.append(f"  {attacker.get('species')} is loafing around!")
                attacker['truant_loaf'] = False  # Next turn will attack
                return  # Skip move execution
            else:
                # Acting this turn, will loaf next turn
                attacker['truant_loaf'] = True

        # Switch Handling
        if action.startswith("Switch:"):
            # Trapping Check
            if self._is_trapped(attacker, state):
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} is trapped and can't switch!"
                )
                return
            self.perform_switch(state, attacker_side, action.split(": ")[1], log)
            return

        move_id = action.replace("Move: ", "")
        move_name = self.get_move_name(move_id)

        # 0. Status & Volatile Checks

        # Damp Check (Explosion prevention)
        if move_name in ["Explosion", "Self-Destruct", "Mind Blown", "Misty Explosion"]:
            damp_active = False
            if defender and defender.get("ability") == "Damp":
                damp_active = True
            if attacker.get("ability") == "Damp":
                damp_active = True

            if damp_active:
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} cannot use {move_name} due to dampness!"
                )
                return

        # Sleep
        status = attacker.get("status")
        if status == "slp":
            counter = attacker.get("status_counter", 0)

            # Early Bird: Decrement by 2
            decrement = 1
            if attacker.get("ability") == "Early Bird":
                decrement = 2

            attacker["status_counter"] = max(0, counter - decrement)

            if attacker["status_counter"] > 0:
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} is fast asleep."
                )
                return
            else:
                attacker["status"] = None
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} woke up!"
                )

        # Freeze
        elif status == "frz":
            # 20% thaw chance (Simple hash-based determinism)
            if hash(move_name + str(attacker["current_hp"])) % 100 < 20:
                attacker["status"] = None
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} thawed out!"
                )
            elif move_name in [
                "Scald",
                "Flare Blitz",
                "Flame Wheel",
                "Sacred Fire",
                "Fusion Flare",
                "Steam Eruption",
                "Burn Up",
                "Pyro Ball",
                "Scorching Sands",
            ]:
                attacker["status"] = None
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} thawed out by {move_name}!"
                )
            else:
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} is frozen solid!"
                )
                return
        # Paralysis
        elif status == "par":
            # 25% Full Paralysis
            if hash(move_name + str(attacker["current_hp"])) % 100 < 25:
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} is paralyzed! It can't move!"
                )
                return

        # Recharge Check
        if "mustrecharge" in attacker.get("volatiles", []):
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} must recharge!"
            )
            attacker["volatiles"].remove("mustrecharge")
            return

        # Flinch
        volatiles = attacker.get("volatiles", [])
        if "flinch" in volatiles:
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} flinched and couldn't move!"
            )
            if attacker.get("ability") == "Steadfast":
                self._apply_boosts(attacker, {"spe": 1}, log)
            return

        # Confusion
        # Confusion
        if "confusion" in volatiles:
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} is confused!"
            )
            # Decrement Counter
            c_turns = attacker.get("confusion_turns", 0) - 1
            attacker["confusion_turns"] = c_turns

            if c_turns <= 0:
                if "confusion" in volatiles:
                    volatiles.remove("confusion")
                log.append(f"  {attacker.get('species')} snapped out of its confusion!")
            else:
                # 33% Self Hit
                if hash(move_name + str(attacker["current_hp"])) % 100 < 33:
                    log.append(f"  It hurt itself in its confusion!")
                # Self Hit Damage (Typeless 40 BP Physical)
                level = 100  # Approx
                stats = attacker.get("stats", {})
                atk = stats.get("atk", 100)
                defi = stats.get("def", 100)
                dmg = int(((2 * level / 5 + 2) * 40 * atk / defi) / 50 + 2)
                attacker["current_hp"] -= dmg
                log.append(f"  Lost {dmg} HP (Confusion)")
                return

        # 0.5 Charge Check
        is_charging = attacker.get("charging")
        move_data = self._get_mechanic(move_name, "moves")
        if not move_data:
            print(f"CRITICAL ERROR: Missing move data for '{move_name}'")
            move_data = {
                "flags": {},
                "type": "Normal",
                "category": "Physical",
            }  # Fallback

        # Force Charge Move
        if is_charging and is_charging != move_name:
            move_name = is_charging
            move_data = self._get_mechanic(move_name, "moves")
            log.append(f"  {attacker.get('species')} unleashed {move_name}!")
            # Proceed with execution

        move_flags = move_data.get("flags", {})

        if move_flags.get("charge") and is_charging != move_name:
            # Check for early completion (Power Herb / weather)
            weather = state.fields.get("weather")
            fast_charge = False
            if move_name in ["Solar Beam", "Solar Blade"] and weather in [
                "Sun",
                "Sunny Day",
            ]:
                fast_charge = True

            # Power Herb
            if attacker.get("item") == "Power Herb":
                fast_charge = True
                # Consumed after move execution (below)
                attacker["_power_herb_consumed"] = True
                log.append(
                    f"  {attacker.get('species')} became fully charged due to its Power Herb!"
                )

            if not fast_charge:
                attacker["charging"] = move_name
                # Semi-invulnerability
                if move_name in ["Fly", "Bounce", "Sky Drop"]:
                    attacker.setdefault("volatiles", []).append("invulnerable_high_alt")
                    log.append(
                        f"[{attacker_side.upper()}] {attacker.get('species')} flew up high!"
                    )
                elif move_name == "Dig":
                    attacker.setdefault("volatiles", []).append(
                        "invulnerable_underground"
                    )
                    log.append(
                        f"[{attacker_side.upper()}] {attacker.get('species')} burrowed underground!"
                    )
                elif move_name == "Dive":
                    attacker.setdefault("volatiles", []).append(
                        "invulnerable_underwater"
                    )
                    log.append(
                        f"[{attacker_side.upper()}] {attacker.get('species')} hid underwater!"
                    )
                else:
                    log.append(
                        f"[{attacker_side.upper()}] {attacker.get('species')} is charging up!"
                    )
                return

        # Reset charging flag and volatiles
        if is_charging:
            attacker["charging"] = None
            vols = attacker.get("volatiles", [])
            for v in [
                "invulnerable_high_alt",
                "invulnerable_underground",
                "invulnerable_underwater",
            ]:
                if v in vols:
                    vols.remove(v)

        # 1. Taunt
        if "taunt" in volatiles:
            t_turns = attacker.get("taunt_turns", 0) - 1
            attacker["taunt_turns"] = t_turns
            if t_turns <= 0:
                if "taunt" in volatiles:
                    volatiles.remove("taunt")
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} shook off the Taunt!"
                )
            elif move_data.get("category") == "Status":
                log.append(
                    f"  {attacker.get('species')} can't use status moves due to taunt!"
                )
                return

        # 2. Encore
        if "encore" in volatiles:
            e_turns = attacker.get("encore_turns", 0) - 1
            attacker["encore_turns"] = e_turns
            if e_turns <= 0:
                if "encore" in volatiles:
                    volatiles.remove("encore")
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')}'s Encore ended!"
                )
            elif move_name != attacker.get("encore_move"):
                log.append(
                    f"  {attacker.get('species')} is forced to use {attacker.get('encore_move')} due to Encore!"
                )
                return

        # 3. Disable
        if "disable" in volatiles:
            d_turns = attacker.get("disable_turns", 0) - 1
            attacker["disable_turns"] = d_turns
            if d_turns <= 0:
                if "disable" in volatiles:
                    volatiles.remove("disable")
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')}'s Disable wore off!"
                )
            elif move_name == attacker.get("disable_move"):
                log.append(f"  {attacker.get('species')}'s {move_name} is disabled!")
                return

        # 4. Heal Block
        if "healblock" in volatiles:
            hb_turns = attacker.get("healblock_turns", 0) - 1
            attacker["healblock_turns"] = hb_turns
            if hb_turns <= 0:
                if "healblock" in volatiles:
                    volatiles.remove("healblock")
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')}'s Heal Block wore off!"
                )
            elif move_data.get("heal") or move_data.get("flags", {}).get("heal"):
                log.append(
                    f"  {attacker.get('species')} can't use healing moves due to Heal Block!"
                )
                return

        # Throat Chop Check
        if "throatchop" in volatiles:
            if move_flags.get("sound"):
                log.append(
                    f"  {attacker.get('species')} can't use sound moves due to Throat Chop!"
                )
                return

        # Torment Check
        if "torment" in volatiles:
            if move_name == attacker.get("last_move"):
                log.append(
                    f"  {attacker.get('species')} can't use the same move twice due to Torment!"
                )
                return

        # Attract Check
        if "attract" in volatiles:
            # 50% chance to fail (Deterministic hash for consistency)
            if (hash(str(attacker.get("current_hp")) + move_name) % 100) < 50:
                log.append(f"  {attacker.get('species')} is in love and can't move!")
                return

        if move_name:
            # --- PROTEAN / LIBERO ---
            if attacker.get("ability") in ["Protean", "Libero"]:
                move_data = self._get_mechanic(move_name, "moves")
                if move_data:
                    move_type = move_data.get("type")
                    if move_type and attacker.get("types") != [move_type]:
                        attacker["types"] = [move_type]
                        log.append(
                            f"  {attacker.get('species')}'s {attacker.get('ability')} changed its type to {move_type}!"
                        )

            # --- STANCE CHANGE (TRANSFORM TO BLADE) ---
            if attacker.get("ability") == "Stance Change":
                move_data = self._get_mechanic(move_name, "moves")
                if move_data and move_data.get("category") != "Status":
                    if "Shield" in attacker.get("species", ""):
                        # Swap stats
                        stats = attacker.get("stats", {})
                        stats["atk"], stats["def"] = stats["def"], stats["atk"]
                        stats["spa"], stats["spd"] = stats["spd"], stats["spa"]
                        # Change species name for identification
                        attacker["species"] = attacker["species"].replace(
                            "Shield", "Blade"
                        )
                        log.append(
                            f"  {attacker.get('species')} changed to Blade Form!"
                        )

            # Choice Lock
            rich_item = attacker.get("_rich_item")
            if rich_item and rich_item.get("isChoice"):
                if not attacker.get("locked_move"):
                    attacker["locked_move"] = move_id

            state.last_moves[attacker_side] = move_name

            # Consume Power Herb
            if attacker.get("_power_herb_consumed"):
                attacker["item"] = None
                attacker.pop("_power_herb_consumed")

        # Teleport handling - only works in wild battles to flee (Stub)
        if move_name == "Teleport":
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
            )
            log.append("  But it failed!")
            return

        # 1. Protect Logic
        protecting_moves = [
            "Protect",
            "Detect",
            "Kings Shield",
            "King's Shield",
            "Spiky Shield",
            "Baneful Bunker",
            "Defend Order",
            "Burning Bulwark",
            "Silk Trap",
            "Obstruct",
        ]
        if move_name in protecting_moves:
            # --- STANCE CHANGE (TRANSFORM TO SHIELD) ---
            if (
                move_name in ["Kings Shield", "King's Shield"]
                and attacker.get("ability") == "Stance Change"
            ):
                if "Blade" in attacker.get("species", ""):
                    stats = attacker.get("stats", {})
                    stats["atk"], stats["def"] = stats["def"], stats["atk"]
                    stats["spa"], stats["spd"] = stats["spd"], stats["spa"]
                    attacker["species"] = attacker["species"].replace("Blade", "Shield")
                    log.append(f"  {attacker.get('species')} changed to Shield Form!")

            cnt = attacker.get("protect_counter", 0)
            if cnt == 0:
                state.fields["protected_sides"].append(attacker_side)
                attacker["protect_counter"] = cnt + 1

                v = attacker.setdefault("volatiles", [])
                if move_name.lower().replace(" ", "") not in v:
                    v.append(move_name.lower().replace(" ", ""))

                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} protected itself!"
                )
            else:
                attacker["protect_counter"] = 0
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name} but it failed!"
                )
            return

        # Light Clay Logic (Duration Extension)
        if move_name in ["Reflect", "Light Screen", "Aurora Veil"]:
            duration = 5
            if attacker.get("item") == "Light Clay":
                duration = 8
                log.append(f"  Light Clay prolonged the screen's duration!")

            # Apply to field (simplified)
            slug = move_name.lower().replace(" ", "_")
            state.fields.setdefault("screens", {}).setdefault(attacker_side, {})[
                slug
            ] = duration
            log.append(f"  {move_name} raised defense!")
            return

        # 2. Check Protection
        if defender_side in state.fields.get("protected_sides", []):
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
            )
            if move_name not in [
                "Feint",
                "Hyperspace Fury",
                "Hyperspace Hole",
                "Phantom Force",
                "Shadow Force",
            ] and not (
                attacker.get("ability") == "Unseen Fist"
                and self._makes_contact(move_name, attacker)
            ):
                log.append(f"  {defender.get('species')} protected itself!")

                # Beak Blast / Burning Bulwark burn on contact
                # Check Contact Effects for Defensive Moves
                if self._makes_contact(move_name, attacker):
                    vols = defender.get("volatiles", [])

                    if "banefulbunker" in vols:
                        if (
                            attacker.get("status") is None
                            and "Poison" not in attacker.get("types", [])
                            and "Steel" not in attacker.get("types", [])
                        ):
                            attacker["status"] = "psn"
                            log.append(
                                f"  {attacker.get('species')} was poisoned by the Baneful Bunker!"
                            )

                    elif "spikyshield" in vols:
                        dmg = max(1, int(attacker.get("max_hp", 100) / 8))
                        attacker["current_hp"] = max(
                            0, attacker.get("current_hp") - dmg
                        )
                        log.append(
                            f"  {attacker.get('species')} was hurt by the Spiky Shield! (-{dmg})"
                        )

                    elif "kingsshield" in vols:
                        Mechanics.apply_boosts(
                            attacker,
                            {"atk": -2},
                            log,
                            source_name="King's Shield",
                            field=state.fields,
                        )

                    elif "obstruct" in vols:
                        Mechanics.apply_boosts(
                            attacker,
                            {"def": -2},
                            log,
                            source_name="Obstruct",
                            field=state.fields,
                        )

                    elif "silktrap" in vols:
                        Mechanics.apply_boosts(
                            attacker,
                            {"spe": -1},
                            log,
                            source_name="Silk Trap",
                            field=state.fields,
                        )

                    elif "burningbulwark" in vols:
                        if attacker.get(
                            "status"
                        ) is None and "Fire" not in attacker.get("types", []):
                            attacker["status"] = "brn"
                            log.append(
                                f"  {attacker.get('species')} was burned by the Burning Bulwark!"
                            )

                attacker["protect_counter"] = 0
                return

        # Reset Protect Counter
        attacker["protect_counter"] = 0

        # Focus Punch Check
        if move_name == "Focus Punch" and attacker.get("lost_focus"):
            log.append(f"  {attacker.get('species')} lost its focus and couldn't move!")
            return

        # 2.5 Fail Conditions (Upper Hand, Steel Roller, etc)
        if move_name == "Upper Hand":
            valid_target = False
            if defender_action and defender_action.startswith("Move: "):
                d_move = defender_action.replace("Move: ", "")
                d_prio = self.get_move_priority(d_move, defender, state)
                d_cat = self._check_mechanic(d_move, "moves", "category")
                if d_prio > 0 and d_cat != "Status":
                    valid_target = True

            if not valid_target:
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
                )
                log.append("  But it failed!")
                return

        if move_name == "Steel Roller" and not state.fields.get("terrain"):
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
            )
            log.append("  But it failed!")
            return

        if move_name == "First Impression" and attacker.get("activeTurns", 0) > 0:
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
            )
            log.append("  But it failed!")
            return

        if move_name == "Belch" and not attacker.get("ate_berry"):
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
            )
            log.append("  But it failed!")
            return

        # 2.7 Magic Bounce (Status reflection)
        is_status = move_data.get("category") == "Status"
        if is_status and defender.get("ability") == "Magic Bounce":
            log.append(f"  {defender.get('species')}'s Magic Bounce reflected {move_name}!")
            # Swap sides to reflect the move back
            attacker, defender = defender, attacker
            attacker_side, defender_side = defender_side, attacker_side

        # 3. Immunity Check (Universal)
        is_immune, imm_msg = self.check_immunity(attacker, defender, move_name)
        if is_immune:
            log.append(f"  {imm_msg}")
            return

        # 3.1 Priority Blocking (Dazzling / Queenly Majesty)
        is_blocked, block_msg = self._check_priority_block(
            attacker, defender, move_name, state
        )
        if is_blocked:
            log.append(f"  {block_msg}")
            return

        # Screen Breaking (Brick Break / Psychic Fangs)
        if move_name in ["Brick Break", "Psychic Fangs", "Raging Bull"]:
            # Screens: Reflect, Light Screen, Aurora Veil
            screen_map = {
                "reflect": "Reflect",
                "light_screen": "Light Screen",
                "aurora_veil": "Aurora Veil",
            }
            target_screens = state.fields["screens"].get(defender_side, {})

            broke_any = False
            for k in list(target_screens.keys()):
                if k in screen_map:
                    target_screens.pop(k, None)
                    log.append(
                        f"  {defender.get('species')}'s {screen_map[k]} shattered!"
                    )
                    broke_any = True

        # 3.2 Move Properties & Thresholds
        threshold = move_data.get("threshold")
        if threshold:
            if (attacker["current_hp"] / attacker.get("max_hp")) < threshold:
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
                )
                log.append(f"  But it failed!")
                return

        # 3.3 Dynamic Move Properties (Weather Ball / Terrain Pulse / Liquid Voice)
        move_type = move_data.get("type")
        move_bp = move_data.get("basePower", 0)

        # Liquid Voice: Sound moves become Water
        if attacker.get("ability") == "Liquid Voice" and (
            move_flags.get("sound") or "sound" in move_name.lower()
        ):
            move_type = "Water"

        # -ate Abilities (Normal to Type + 1.2x BP)
        att_ab = attacker.get("ability")
        if (
            move_type == "Normal"
            and move_name != "Struggle"
            and move_name != "Weather Ball"
        ):  # Weather Ball handled below
            if att_ab == "Galvanize":
                move_type = "Electric"
                if move_bp > 0:
                    move_bp = int(move_bp * 1.2)
                log.append(
                    f"  {attacker.get('species')}'s Galvanize made the move Electric!"
                )
            elif att_ab == "Pixilate":
                move_type = "Fairy"
                if move_bp > 0:
                    move_bp = int(move_bp * 1.2)
                log.append(
                    f"  {attacker.get('species')}'s Pixilate made the move Fairy!"
                )
            elif att_ab == "Refrigerate":
                move_type = "Ice"
                if move_bp > 0:
                    move_bp = int(move_bp * 1.2)
                log.append(
                    f"  {attacker.get('species')}'s Refrigerate made the move Ice!"
                )
            elif att_ab == "Aerilate":
                move_type = "Flying"
                if move_bp > 0:
                    move_bp = int(move_bp * 1.2)
                log.append(
                    f"  {attacker.get('species')}'s Aerilate made the move Flying!"
                )

        # Normalize (All moves become Normal + 1.2x BP)
        if att_ab == "Normalize" and move_name != "Struggle":
            move_type = "Normal"
            if move_bp > 0:
                move_bp = int(move_bp * 1.2)

        if move_name == "Weather Ball":
            weather = state.fields.get("weather")
            if weather in ["Sun", "Sunny Day"]:
                move_type = "Fire"
                move_bp *= 2
            elif weather in ["Rain", "Rain Dance"]:
                move_type = "Water"
                move_bp *= 2
            elif weather in ["Sand", "Sandstorm"]:
                move_type = "Rock"
                move_bp *= 2
            elif weather in ["Hail", "Snow"]:
                move_type = "Ice"
                move_bp *= 2

        elif move_name == "Terrain Pulse":
            terrain = state.fields.get("terrain")
            if terrain == "Electric":
                move_type = "Electric"
                move_bp *= 2
            elif terrain == "Grassy":
                move_type = "Grass"
                move_bp *= 2
            elif terrain == "Misty":
                move_type = "Fairy"
                move_bp *= 2
            elif terrain == "Psychic":
                move_type = "Psychic"
                move_bp *= 2

        # Weight-based moves (Low Kick, Grass Knot, Heavy Slam, Heat Crash)
        if move_name in ["Low Kick", "Grass Knot"]:
            # Get defender weight from pokedex data
            defender_weight = defender.get("_rich_species", {}).get(
                "weight", 10.0
            )  # Default 10kg if missing
            # Apply Heavy Metal / Light Metal
            def_ab = defender.get("ability")
            if def_ab == "Heavy Metal":
                defender_weight *= 2.0
            elif def_ab == "Light Metal":
                defender_weight *= 0.5
            # Low Kick / Grass Knot base power by weight (kg)
            if defender_weight < 10:
                move_bp = 20
            elif defender_weight < 25:
                move_bp = 40
            elif defender_weight < 50:
                move_bp = 60
            elif defender_weight < 100:
                move_bp = 80
            elif defender_weight < 200:
                move_bp = 100
            else:
                move_bp = 120
            # Update move_data so damage calculator uses this power
            move_data["basePower"] = move_bp

        elif move_name in ["Heavy Slam", "Heat Crash"]:
            # Get both weights
            attacker_weight = attacker.get("_rich_species", {}).get("weight", 100.0)
            defender_weight = defender.get("_rich_species", {}).get("weight", 100.0)

            # Attacker Weight Modifiers
            att_ab = attacker.get("ability")
            if att_ab == "Heavy Metal":
                attacker_weight *= 2.0
            elif att_ab == "Light Metal":
                attacker_weight *= 0.5

            # Defender Weight Modifiers
            def_ab = defender.get("ability")
            if def_ab == "Heavy Metal":
                defender_weight *= 2.0
            elif def_ab == "Light Metal":
                defender_weight *= 0.5
            weight_ratio = (
                attacker_weight / defender_weight if defender_weight > 0 else 5.0
            )
            # Base power by weight ratio
            if weight_ratio >= 5.0:
                move_bp = 120
            elif weight_ratio >= 4.0:
                move_bp = 100
            elif weight_ratio >= 3.0:
                move_bp = 80
            elif weight_ratio >= 2.0:
                move_bp = 60
            else:
                move_bp = 40
            # Update move_data so damage calculator uses this power
            move_data["basePower"] = move_bp

        # Ion Deluge (Normal -> Electric)
        if state.fields.get("ion_deluge") and move_type == "Normal":
            move_type = "Electric"

        # 3.5 Check Accuracy (Rich Data)
        acc = self._check_mechanic(move_name, "moves", "accuracy")

        # User Logic: Thunder Wave cannot miss if user is Electric
        if move_name == "Thunder Wave" and "Electric" in attacker.get("types", []):
            acc = True

        # Lock-On / Mind Reader
        if "lockon" in defender.get("volatiles", []):
            acc = True

        if acc != True:
            # Gravity Accuracy Boost (5 / 3 ~= 1.67)
            if state.fields.get("gravity", 0) > 0:
                if isinstance(acc, int):
                    acc = min(100, int(acc * 5 / 3))

            # Very simplified accuracy simulation for now
            # We assume hit unless explicit miss logic added later
            pass

        # 4. Damage Calculation
        res = {}
        damage_dealt = 0
        dmg_res = None

        move_data = self._get_mechanic(move_name, "moves")
        if not move_data:
            print(f"CRITICAL ERROR: Missing move data for '{move_name}' (2)")
            move_data = {"flags": {}, "type": "Normal", "category": "Physical"}

        is_status = move_data and move_data.get("category") == "Status"

        calc_attacker = attacker
        calc_defender = defender

        if not is_status:
            # Unaware Logic
            # If Attacker has Unaware, ignore Defender's Def/SpD stages
            # If Defender has Unaware, ignore Attacker's Atk/SpA stages

            # Check suppression
            att_rich = attacker.get("_rich_ability", {})
            def_rich = defender.get("_rich_ability", {})
            att_unaware = attacker.get(
                "ability"
            ) == "Unaware" and not self._is_ability_suppressed(
                state, attacker, defender, att_rich
            )
            def_unaware = defender.get(
                "ability"
            ) == "Unaware" and not self._is_ability_suppressed(
                state, defender, attacker, def_rich
            )

            if att_unaware:
                # Clone defender to zero out defensive stages
                calc_defender = defender.copy()
                calc_defender["stat_stages"] = defender.get("stat_stages", {}).copy()
                calc_defender["stat_stages"]["def"] = 0
                calc_defender["stat_stages"]["spd"] = 0

            if def_unaware:
                # Clone attacker to zero out offensive stages
                calc_attacker = attacker.copy()
                calc_attacker["stat_stages"] = attacker.get("stat_stages", {}).copy()
                calc_attacker["stat_stages"]["atk"] = 0
                calc_attacker["stat_stages"]["spa"] = 0

            # Thousand Arrows Bypass
            if move_name == "Thousand Arrows" and "Flying" in calc_defender.get(
                "types", []
            ):
                if calc_defender is defender:
                    calc_defender = defender.copy()
                # Strip Flying type temporarily for calc
                types = list(calc_defender.get("types", []))
                if "Flying" in types:
                    types.remove("Flying")
                calc_defender["types"] = types

            # --- Stat Overrides (Body Press, Psystrike, Foul Play) ---
            if move_data.get("useSourceDef"):
                if calc_attacker is attacker:
                    calc_attacker = attacker.copy()
                calc_attacker["stats"] = calc_attacker.get("stats", {}).copy()
                calc_attacker["stats"]["atk"] = calc_attacker["stats"].get("def", 10)
                calc_attacker["stat_stages"] = calc_attacker.get(
                    "stat_stages", {}
                ).copy()
                calc_attacker["stat_stages"]["atk"] = calc_attacker["stat_stages"].get(
                    "def", 0
                )

            if move_data.get("useTargetAtk"):
                if calc_attacker is attacker:
                    calc_attacker = attacker.copy()
                calc_attacker["stats"] = calc_attacker.get("stats", {}).copy()
                calc_attacker["stats"]["atk"] = calc_defender.get("stats", {}).get(
                    "atk", 10
                )
                calc_attacker["stat_stages"] = calc_attacker.get(
                    "stat_stages", {}
                ).copy()
                calc_attacker["stat_stages"]["atk"] = calc_defender.get(
                    "stat_stages", {}
                ).get("atk", 0)

            if move_data.get("useTargetDef"):
                if calc_defender is defender:
                    calc_defender = defender.copy()
                calc_defender["stats"] = calc_defender.get("stats", {}).copy()
                calc_defender["stats"]["spd"] = calc_defender["stats"].get("def", 10)
                calc_defender["stat_stages"] = calc_defender.get(
                    "stat_stages", {}
                ).copy()
                calc_defender["stat_stages"]["spd"] = calc_defender["stat_stages"].get(
                    "def", 0
                )

            # Knock Off Boost (1.5x if target has item)
            if (
                move_name == "Knock Off"
                and calc_defender.get("item")
                and not self._is_item_unremovable(
                    calc_defender.get("item"), calc_defender
                )
            ):
                pass

            # Leek / Stick (Farfetch'd -> Crit)
            if calc_attacker.get("item") in [
                "Leek",
                "Stick",
            ] and "Farfetch" in calc_attacker.get("species", ""):
                calc_attacker["crit_ratio"] = 2

        # Variable Power Calculations
        bp_override = Mechanics.get_variable_bp(
            move_name, attacker, defender, state.fields
        )

        # DEBUG: Log Flail BP
        if move_name in ["Flail", "Reversal"]:
            log.append(
                f"  [DEBUG] {move_name} bp_override = {bp_override} (HP: {attacker.get('current_hp')}/{attacker.get('max_hp')})"
            )

        # === SPECIAL BASE POWER OVERRIDES ===
        # (Fixed-damage moves are handled after accuracy check)

        # Speed-Based Damage - Electro Ball
        if move_name == "Electro Ball":
            attacker_spe = Mechanics.get_effective_speed(attacker, state.fields)
            defender_spe = Mechanics.get_effective_speed(defender, state.fields)
            if defender_spe > 0:
                speed_ratio = attacker_spe / defender_spe
                if speed_ratio >= 4.0:
                    bp_override = 150
                elif speed_ratio >= 3.0:
                    bp_override = 120
                elif speed_ratio >= 2.0:
                    bp_override = 80
                elif speed_ratio >= 1.0:
                    bp_override = 60
                else:
                    bp_override = 40
            else:
                bp_override = 40

        # Speed-Based Damage - Gyro Ball
        if move_name == "Gyro Ball":
            attacker_spe = Mechanics.get_effective_speed(attacker, state.fields)
            defender_spe = Mechanics.get_effective_speed(defender, state.fields)
            if attacker_spe > 0:
                bp_override = min(150, max(1, int(25 * defender_spe / attacker_spe)))
            else:
                bp_override = 1

        # HP-Based Damage  - Wring Out, Crush Grip
        if move_name in ["Wring Out", "Crush Grip"]:
            defender_hp_pct = defender.get("current_hp", 1) / max(
                1, defender.get("max_hp", 1)
            )
            bp_override = max(1, int(120 * defender_hp_pct))

        # OHKO Check
        is_ohko = move_data.get("ohko") or move_name in [
            "Fissure",
            "Guillotine",
            "Horn Drill",
            "Sheer Cold",
        ]

        # Determine Effectiveness (Early for hit logging suppression on immunity)
        # Note: We calculate full dmg later, but need effectiveness for immunity text?
        # Actually logic is later. But we need to handle efficiency.
        # Let's rely on standard flow.

        # --- PHASE 2.5: ACCURACY CHECK ---
        # We must verify hit before calculating damage rolls (or ignore rolls if miss)
        # Except if hit is guaranteed by No Guard or similar

        # Run check
        hits = Mechanics.check_accuracy(
            attacker, defender, move_data, state.fields, log
        )
        if not hits:
            # Blunder Policy
            if attacker.get("item") == "Blunder Policy":
                log.append(f"  {attacker.get('species')}'s Blunder Policy activated!")
                attacker["item"] = None
                Mechanics.apply_boosts(
                    attacker, {"spe": 2}, log, source_name="Blunder Policy"
                )

            return  # End turn action if missed

        # Fixed Damage Check (Night Shade, Seismic Toss, Dragon Rage, Psywave, etc.)
        fixed_damage = move_data.get("damage")

        # Handle Night Shade and Seismic Toss (level-based, not in move data)
        if move_name in ["Night Shade", "Seismic Toss"]:
            fixed_damage = "level"

        if fixed_damage:
            if fixed_damage == "level":
                damage_dealt = attacker.get("level", 50)
                if move_name == "Psywave":
                    # Psywave: Level * (random 0.5 to 1.5)
                    rnd = random.randint(50, 150)
                    damage_dealt = int(damage_dealt * rnd / 100)
            elif isinstance(fixed_damage, int):
                damage_dealt = fixed_damage

            # Create a dummy result for downstream logic
            dmg_res = [
                {"damage": [damage_dealt], "type_effectiveness": 1.0, "is_crit": False}
            ]
            res = dmg_res[0]

        elif is_ohko:
            dmg_res = [{"damage": [defender["max_hp"]], "type_effectiveness": 1.0}]
        else:

            # Use LOCAL damage calculation (replaces external Node.js service)
            # Pass the real attacker/defender, not calc versions (they have stats)
            from pkh_app import local_damage_calc

            # Use delegated DamageCalculator (handles calc_client vs local)
            dmg_res = self.damage_calculator.calc_damage_for_moves(
                attacker, defender, [move_name], state.fields,
                move_type_override=move_type,
                move_bp_override=move_bp
            )

        if dmg_res:
            res = dmg_res[0]
            effectiveness = res.get(
                "type_effectiveness", 1.0
            )  # Actually we use 'effectiveness' key in results from get_damage_rolls
            if "effectiveness" in res:
                effectiveness = res["effectiveness"]  # Map correctly

            # Wonder Guard Check
            if (
                defender.get("ability") == "Wonder Guard"
                and move_data.get("category") != "Status"
            ):
                # Check if move is super-effective (effectiveness >= 2)
                # Note: Some moves ignore abilities (Mold Breaker etc), but attacker ability suppression handled earlier.
                if effectiveness < 2:
                    log.append(
                        f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
                    )
                    log.append(
                        f"  It doesn't affect {defender.get('species')} (Wonder Guard)!"
                    )
                    return

            # LOGGING ACTION START
            eff_str = ""
            if res.get("is_stab"):
                eff_str += " (STAB!)"

            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}{eff_str}"
            )

            if effectiveness >= 2:
                log.append("  It's super effective!")
            elif effectiveness > 0 and effectiveness <= 0.5:
                log.append("  It's not very effective...")
            elif effectiveness == 0:
                log.append(f"  It doesn't affect {defender.get('species')}...")
                return  # Skip damage and hit count

            # Show damage range for damaging moves
            damage_rolls = res.get("damage_rolls", [])
            if (
                move_data.get("category") != "Status"
                and damage_rolls
                and len(damage_rolls) > 0
            ):
                min_dmg = min(damage_rolls)
                max_dmg = max(damage_rolls)
                if min_dmg == max_dmg:
                    log.append(f"  [Damage: {min_dmg}]")
                else:
                    log.append(f"  [Damage Range: {min_dmg}-{max_dmg}]")
            # LOGGING ACTION END

            # Context for Mechanics.py
            # Roost Check: Filter Flying type if user used Roost
            atk_types = attacker.get("types", [])
            if move_name == "Roost" or "roost" in attacker.get("volatiles", []):
                atk_types = [t for t in atk_types if t != "Flying"]

            state.fields["context"] = {
                "effectiveness": effectiveness,
                "is_grounded_target": self._is_grounded(defender, state),
                "user_moved_last": getattr(state, "user_moved_last", False),
                "target_damaged_this_turn": defender.get(
                    "took_damage_this_turn", False
                ),
                "last_move_used_this_turn": state.fields.get(
                    "last_move_used_this_turn"
                ),
                "move_name": move_name,
                "attacker_types": atk_types,
            }

            # --- Critical Hit Determination (Gen 9) ---
            # 1. Calculate Stage
            crit_stage = 0

            # Base Move Stage (Default 0, High Crit = 1)
            # API returns 1 for normal, 2 for high crit typically.
            # We normalize: stage = ratio - 1
            base_ratio = res.get("critRatio", 1) or 1
            crit_stage += max(0, int(base_ratio) - 1)

            # Focus Energy (+2)
            if "focusenergy" in attacker.get("volatiles", []):
                crit_stage += 2

            # Item Modifiers (Scope Lens, Razor Claw)
            item = attacker.get("item")
            if item in ["Scope Lens", "Razor Claw"]:
                crit_stage += 1
            elif item == "Leek" and "Farfetch" in attacker.get("species", ""):
                crit_stage += 2
            elif item == "Lucky Punch" and "Chansey" in attacker.get("species", ""):
                crit_stage += 2
            elif item == "Stick" and "Farfetch" in attacker.get(
                "species", ""
            ):  # Alias check
                crit_stage += 2

            # Ability Modifiers
            if attacker.get("ability") == "Super Luck":
                crit_stage += 1
            if attacker.get("ability") == "Merciless" and (
                defender.get("status") in ["psn", "tox"]
            ):
                crit_stage = 3  # Always Crit

            # Always Crit Moves (Frost Breath, Storm Throw, etc.)
            if move_name in [
                "Frost Breath",
                "Storm Throw",
                "Wicked Blow",
                "Surging Strikes",
                "Flower Trick",
            ] or move_data.get("alwaysCrit"):
                crit_stage = 3

            # Laser Focus
            if "laserfocus" in attacker.get("volatiles", []):
                crit_stage = 3

            # 2. Roll for Crit
            # Stages: 0=1/24 (~4.17%), 1=1/8 (12.5%), 2=1/2 (50%), 3+=100%
            CRIT_RATES = {0: 1 / 24, 1: 1 / 8, 2: 0.5, 3: 1.0}
            eff_stage = min(3, crit_stage)
            chance = CRIT_RATES.get(eff_stage, 1.0)

            # Battle Armor / Shell Armor block
            def_ability = defender.get("ability")
            if def_ability in ["Battle Armor", "Shell Armor"]:
                chance = 0
            if "lucky chant" in state.fields.get("screens", {}).get(
                defender_side, {}
            ):  # Assuming side check logic
                pass  # TODO: Access side name properly, ignoring for minimal patch

            is_crit = random.random() < chance

            # Force Crit if manually flagged (debug/testing)
            if attacker.get("crit_ratio") == 2:  # Legacy flag support
                pass  # Handled by stage logic mostly, but 'crit_ratio' in attacker meant direct override?

            res["is_crit"] = is_crit
            rolls = (
                res.get("crit_rolls", [0]) if is_crit else res.get("damage_rolls", [0])
            )
            # FIX: Pick a random roll instead of averaging
            damage_dealt = 0
            if rolls:
                damage_dealt = random.choice(rolls)

            # Phase 2: Apply Rich Data Modifiers (onBasePower, onModifyDamage)
            # SKIP if OHKO
            # NOTE: These are already applied in local_damage_calc.py. Removing to prevent double counting.
            # if not is_ohko:
            #      bp_mod = self._get_modifier(attacker, 'onBasePower', move_data, state, target=defender)
            #      dmg_mod = self._get_modifier(attacker, 'onModifyDamage', move_data, state, target=defender)
            #      src_mod = self._get_modifier(defender, 'onSourceModifyDamage', move_data, state, target=attacker)
            #
            #      total_mod = bp_mod * dmg_mod * src_mod
            # else:
            #      total_mod = 1.0

            total_mod = 1.0

            # Glaive Rush (Target takes 2x damage next turn)
            if "glaiverush" in defender.get("volatiles", []):
                total_mod *= 2

            # Tar Shot (Fire weakness)
            if "tarshot" in defender.get("volatiles", []) and move_type == "Fire":
                total_mod *= 2

            # King's Rock / Razor Fang (Post Hit Flinch)
            # King's Rock / Razor Fang (Post Hit Flinch)
            # Apply only if damage > 0 and user moved first
            if damage_dealt > 0:
                if attacker.get("item") in ["King's Rock", "Kings Rock", "Razor Fang"]:
                    if random.random() < 0.1:
                        defender.setdefault("volatiles", []).append("flinch")
                        log.append(f"  {defender.get('species')} flinched!")

            # Minimize (Double damage from specific moves)
            if "minimize" in defender.get("volatiles", []):
                min_moves = [
                    "Stomp",
                    "Steamroller",
                    "Body Slam",
                    "Flying Press",
                    "Dragon Rush",
                    "Heat Crash",
                    "Heavy Slam",
                ]
                if move_name in min_moves:
                    total_mod *= 2

            # Type-Boosting Items (46 items + 16 Arceus Plates = 62 total)
            item_name = attacker.get("item")
            if item_name:
                TYPE_BOOST_ITEMS = {
                    "Silk Scarf": "Normal",
                    "Black Belt": "Fighting",
                    "Fist Plate": "Fighting",
                    "Sharp Beak": "Flying",
                    "Sky Plate": "Flying",
                    "Poison Barb": "Poison",
                    "Toxic Plate": "Poison",
                    "Soft Sand": "Ground",
                    "Earth Plate": "Ground",
                    "Hard Stone": "Rock",
                    "Stone Plate": "Rock",
                    "Silver Powder": "Bug",
                    "Insect Plate": "Bug",
                    "Spell Tag": "Ghost",
                    "Spooky Plate": "Ghost",
                    "Metal Coat": "Steel",
                    "Iron Plate": "Steel",
                    "Charcoal": "Fire",
                    "Flame Plate": "Fire",
                    "Mystic Water": "Water",
                    "Splash Plate": "Water",
                    "Miracle Seed": "Grass",
                    "Meadow Plate": "Grass",
                    "Magnet": "Electric",
                    "Zap Plate": "Electric",
                    "Twisted Spoon": "Psychic",
                    "Mind Plate": "Psychic",
                    "Never-Melt Ice": "Ice",
                    "Icicle Plate": "Ice",
                    "Dragon Fang": "Dragon",
                    "Draco Plate": "Dragon",
                    "Black Glasses": "Dark",
                    "Dread Plate": "Dark",
                    "Pixie Plate": "Fairy",
                    "Sea Incense": "Water",
                    "Rose Incense": "Grass",
                    "Rock Incense": "Rock",
                    "Odd Incense": "Psychic",
                    "Wave Incense": "Water",
                    "Full Incense": "Normal",
                }

                POKEMON_SPECIFIC_ORBS = {
                    "Adamant Orb": (["Dragon", "Steel"], "Dialga"),
                    "Lustrous Orb": (["Water", "Dragon"], "Palkia"),
                    "Griseous Orb": (["Ghost", "Dragon"], "Giratina"),
                }
                # Type-Boosting Items: Handled by Mechanics (onBasePower)
                # Legacy block removed to prevent double counting.

                if "Gem" in item_name:
                    gem_type = item_name.replace(" Gem", "")
                    if gem_type == move_type or (
                        item_name == "Normal Gem" and move_type == "Normal"
                    ):
                        # Multiplier handled by Mechanics (onBasePower)
                        attacker["item"] = None
                        log.append(f"  The {item_name} strengthened the move!")

                elif item_name in POKEMON_SPECIFIC_ORBS:
                    boosted_types, required_pokemon = POKEMON_SPECIFIC_ORBS[item_name]
                    # Multiplier handled by Mechanics if item data is correct.
                    # Assuming Logic is in Mechanics.
                    pass

            # Type-Resist Berries
            defender_item = defender.get("item")
            if defender_item and effectiveness > 1.0:
                TYPE_RESIST_BERRIES = {
                    "Occa Berry": "Fire",
                    "Passho Berry": "Water",
                    "Wacan Berry": "Electric",
                    "Rindo Berry": "Grass",
                    "Yache Berry": "Ice",
                    "Chople Berry": "Fighting",
                    "Kebia Berry": "Poison",
                    "Shuca Berry": "Ground",
                    "Coba Berry": "Flying",
                    "Payapa Berry": "Psychic",
                    "Tanga Berry": "Bug",
                    "Charti Berry": "Rock",
                    "Kasib Berry": "Ghost",
                    "Haban Berry": "Dragon",
                    "Colbur Berry": "Dark",
                    "Babiri Berry": "Steel",
                    "Roseli Berry": "Fairy",
                    "Chilan Berry": "Normal",
                }
                if (
                    defender_item in TYPE_RESIST_BERRIES
                    and move_type == TYPE_RESIST_BERRIES[defender_item]
                ):
                    # Multiplier handled by Mechanics (onSourceModifyDamage)
                    defender["item"] = None
                    log.append(
                        f"  {defender.get('species')}'s {defender_item} weakened the attack!"
                    )

            # Category Boosters
            if item_name:
                pass  # Muscle Band handled by Mechanics

                if (
                    item_name == "Wise Glasses"
                    and move_data.get("category") == "Special"
                ):
                    pass  # total_mod *= 1.1 - Handled in Mechanics
                elif item_name == "Punching Glove":
                    if "punch" in move_name.lower() or move_name in [
                        "Mach Punch",
                        "Bullet Punch",
                        "Ice Punch",
                        "Fire Punch",
                        "Thunder Punch",
                    ]:
                        pass  # total_mod *= 1.1 - Handled in Mechanics

            # if bp_override is not None:
            #      original_bp = move_data.get('basePower') or 1
            #      total_mod *= (bp_override / original_bp)

            # --- PHASE 2.7: DAMAGE MODIFIERS ---
            weather = state.fields.get("weather")
            if weather == "Rain":
                if move_type == "Water":
                    total_mod *= 1.5
                    log.append("  The Rain strengthened the Water move!")
                elif move_type == "Fire":
                    total_mod *= 0.5
                    log.append("  The Rain weakened the Fire move!")
            elif weather == "Sun":
                if move_type == "Fire":
                    total_mod *= 1.5
                    log.append("  The Sunlight strengthened the Fire move!")
                elif move_type == "Water":
                    total_mod *= 0.5
                    log.append("  The Sunlight weakened the Water move!")

            terrain = state.fields.get("terrain")
            is_grounded_attacker = self._is_grounded(attacker, state)
            is_grounded_defender = self._is_grounded(defender, state)
            if (
                terrain == "Electric"
                and is_grounded_attacker
                and move_type == "Electric"
            ):
                total_mod *= 1.3
                log.append("  The Electric Terrain strengthened the move!")
            elif terrain == "Grassy" and is_grounded_attacker and move_type == "Grass":
                total_mod *= 1.3
                log.append("  The Grassy Terrain strengthened the move!")
            elif (
                terrain == "Psychic" and is_grounded_attacker and move_type == "Psychic"
            ):
                total_mod *= 1.3
                log.append("  The Psychic Terrain strengthened the move!")
            elif terrain == "Misty" and is_grounded_defender and move_type == "Dragon":
                total_mod *= 0.5
                log.append("  The Misty Terrain weakened the Dragon move!")

            if not is_crit and attacker.get("ability") != "Infiltrator":
                screens = state.fields.get("screens", {}).get(defender_side, {})
                if screens.get("aurora_veil", 0) > 0:
                    total_mod *= 0.5
                    log.append(
                        f"  {defender.get('species')}'s Aurora Veil weakened the physical/special attack!"
                    )
                elif (
                    move_data.get("category") == "Physical"
                    and screens.get("reflect", 0) > 0
                ):
                    total_mod *= 0.5
                    log.append(
                        f"  {defender.get('species')}'s Reflect weakened the physical attack!"
                    )
                elif (
                    move_data.get("category") == "Special"
                    and screens.get("light_screen", 0) > 0
                ):
                    total_mod *= 0.5
                    log.append(
                        f"  {defender.get('species')}'s Light Screen weakened the special attack!"
                    )

            if total_mod != 1.0:
                damage_dealt = int(damage_dealt * total_mod)

            if (
                move_name == "Counter"
                and attacker.get("last_dmg_received_cat") == "Physical"
            ):
                damage_dealt = attacker.get("last_dmg_received", 0) * 2
            elif (
                move_name == "Mirror Coat"
                and attacker.get("last_dmg_received_cat") == "Special"
            ):
                damage_dealt = attacker.get("last_dmg_received", 0) * 2
            elif move_name in ["Super Fang", "Nature's Madness"]:
                damage_dealt = int(defender["current_hp"] / 2)
            elif move_name == "Endeavor":
                if attacker["current_hp"] < defender["current_hp"]:
                    damage_dealt = defender["current_hp"] - attacker["current_hp"]
                else:
                    damage_dealt = 0

        if is_status or dmg_res:

            # Multi-Hit Logic (Universal)
            # Check rich data first
            rich_multihit = self._check_mechanic(move_name, "moves", "multihit")

            # Check for effectiveness type immunity again?
            # If effectiveness was 0, we returned earlier. So safe.

            hit_count = 1
            if rich_multihit:
                if isinstance(rich_multihit, (list, tuple)) and len(rich_multihit) >= 2:
                    # Range [min, max]
                    mn, mx = rich_multihit[0], rich_multihit[1]
                    if attacker.get("ability") == "Skill Link":
                        hit_count = mx
                    elif mx == 5:  # Standard 2-5 hit distribution
                        # 2: 35%, 3: 35%, 4: 15%, 5: 15%
                        r = random.random()
                        if r < 0.35:
                            hit_count = 2
                        elif r < 0.70:
                            hit_count = 3
                        elif r < 0.85:
                            hit_count = 4
                        else:
                            hit_count = 5
                    else:
                        hit_count = random.randint(mn, mx)
                else:
                    # Fixed number (e.g. Double Kick = 2)
                    hit_count = int(rich_multihit)

                damage_dealt *= hit_count

            # Survival Check (False Swipe / Endure)
            if (
                move_data.get("survival") or "endure" in defender.get("volatiles", [])
            ) and damage_dealt >= defender["current_hp"]:
                if defender["current_hp"] > 0:
                    damage_dealt = max(0, defender["current_hp"] - 1)
                    log.append(f"  {defender.get('species')} endured the hit!")

            # 1. Check for Immunities (Ability-based)
            def_rich_ab = defender.get("_rich_ability", {})
            move_flags = move_data.get("flags", {})

            is_suppressed = self._is_ability_suppressed(
                state, defender, attacker, def_rich_ab
            )

            # Prankster Immunity
            if self.check_prankster_immunity(attacker, defender, res.get("category")):
                log.append(
                    f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name}"
                )
                log.append(
                    f"  It doesn't affect {defender.get('species')} (Prankster Immunity)!"
                )
                return

            if not is_suppressed:
                def_ability = def_rich_ab.get("name")

                # Volt Absorb / Lightning Rod
                if move_type == "Electric" and def_ability in [
                    "Volt Absorb",
                    "Lightning Rod",
                    "Motor Drive",
                ]:
                    if def_ability == "Volt Absorb":
                        heal = int(defender.get("max_hp") * 0.25)
                        defender["current_hp"] = min(
                            defender.get("max_hp"), defender["current_hp"] + heal
                        )
                        log.append(
                            f"  {defender.get('species')} healed by Volt Absorb!"
                        )
                    elif def_ability == "Motor Drive":
                        Mechanics.apply_boosts(
                            defender, {"spe": 1}, log, source_name="Motor Drive"
                        )
                    else:
                        Mechanics.apply_boosts(
                            defender, {"spa": 1}, log, source_name=def_ability
                        )
                    return

                # Water Absorb / Storm Drain / Dry Skin
                if move_type == "Water" and def_ability in [
                    "Water Absorb",
                    "Storm Drain",
                    "Dry Skin",
                ]:
                    if def_ability in ["Water Absorb", "Dry Skin"]:
                        heal = int(defender.get("max_hp") * 0.25)
                        defender["current_hp"] = min(
                            defender.get("max_hp"), defender["current_hp"] + heal
                        )
                        log.append(
                            f"  {defender.get('species')} healed by {def_ability}!"
                        )
                    else:
                        Mechanics.apply_boosts(
                            defender, {"spa": 1}, log, source_name=def_ability
                        )
                    return

                # Sap Sipper
                if move_type == "Grass" and def_ability == "Sap Sipper":
                    Mechanics.apply_boosts(
                        defender, {"atk": 1}, log, source_name="Sap Sipper"
                    )
                    return

                # Flash Fire
                if move_type == "Fire" and def_ability == "Flash Fire":
                    log.append(f"  {defender.get('species')}'s Fire power rose!")
                    defender["flash_fire"] = True
                    return

                # Levitate
                if move_type == "Ground" and def_ability == "Levitate":
                    log.append(
                        f"  {defender.get('species')} avoided the move with Levitate!"
                    )
                    return

                # Soundproof
                if move_flags.get("sound") and def_ability == "Soundproof":
                    log.append(f"  {defender.get('species')} is immune to sound moves!")
                    return

                # Bulletproof
                if move_flags.get("bullet") and def_ability == "Bulletproof":
                    log.append(
                        f"  {defender.get('species')} is immune to ball/bomb moves!"
                    )
                    return

            # 2. Check for Immunity Flag from Calc Description (Generic Type Immunity)
            desc = res.get("desc", "").lower()
            if "does not affect" in desc:
                log.append(f"  It doesn't affect {defender.get('species')}...")
                return

            # Apply Damage & On-Hit Effects (Phase 3 Convergence)

            # Context for triggers
            effectiveness = 1
            if "super effective" in desc:
                effectiveness = 2
            elif "not very effective" in desc:
                effectiveness = 0.5
            is_crit = res.get("is_crit", False)
            if is_status:
                is_crit = False
            if is_crit:
                log.append("  Critical hit!")
                if attacker.get("ability") == "Merciless":
                    log.append(
                        f"  {attacker.get('species')}'s Merciless ensured a critical hit!"
                    )
            context = {
                "is_crit": is_crit,
                "effectiveness": effectiveness,
                "category": move_data.get("category"),
            }

            actual_hits = 0
            total_damage_dealt = 0

            # Store HP before hit for Innards Out
            defender["_hp_before_hit"] = defender.get("current_hp", 0)

            # Loop for Hits (Multi-hit support)
            for h in range(hit_count):
                if defender["current_hp"] <= 0:
                    break

                hit_dmg = damage_dealt // hit_count
                if h == hit_count - 1:  # Last hit takes remainder
                    hit_dmg = damage_dealt - total_damage_dealt

                rich_item = defender.get("_rich_item", {})
                rich_ab = defender.get("_rich_ability", {})
                item_survive = False
                ab_survive = False

                # Focus Sash / Sturdy Check (Only on first hit at full HP)
                survived_with_1hp = False

                # Disguise Logic (Gen 8+)
                if defender.get("ability") == "Disguise" and defender.get(
                    "is_disguised", True
                ):
                    log.append(f"  Its disguise served it as a decoy!")
                    defender["is_disguised"] = False
                    # Bust damage (1/8 HP)
                    bust_dmg = max(1, int(defender.get("max_hp", 100) / 8))
                    defender["current_hp"] = max(0, defender["current_hp"] - bust_dmg)
                    log.append(f"  {defender.get('species')}'s disguise busted!")

                    damage_dealt = 0
                    hit_dmg = 0
                    continue

                if h == 0:
                    # Full HP checks (Sash / Sturdy)
                    if defender["current_hp"] == defender.get("max_hp"):
                        item_survive = rich_item and rich_item.get("survival")
                        # Ability survival (Sturdy) check with suppression
                        ab_s = rich_ab and rich_ab.get("survival")
                        # Hotfix: Pressure erroneously has survival=True in some datasets?
                        if rich_ab and rich_ab.get("name") == "Pressure":
                            ab_s = False

                        if ab_s and not self._is_ability_suppressed(
                            state, defender, attacker, rich_ab
                        ):
                            ab_survive = True

                        if (item_survive or ab_survive) and hit_dmg >= defender[
                            "current_hp"
                        ]:
                            survived_with_1hp = True

                    # Focus Band (10% chance - always active regardless of HP)
                    if (
                        defender.get("item") == "Focus Band"
                        and hit_dmg >= defender["current_hp"]
                    ):
                        if random.random() < 0.10:
                            survived_with_1hp = True
                            # Focus Band does NOT consume, so item_survive should remain False for consumption logic
                            log.append(
                                f"  {defender.get('species')} hung on using its Focus Band!"
                            )

                # Sturdy (Always active in Gen 5+? No, Sturdy is Full HP in older, sturdy always in new?
                # In Gen 5+, Sturdy works if FULL HP. So h=0 check is correct for Sturdy.)

                # Consume Sash (if triggered)
                # My previous logic relied on 'item_survive' being True to consume.
                # And 'ab_survive' to log ability.
                # I need to ensure variables align for the check below.

                # Logic below line 1880 checks 'item_survive or ab_survive'.
                # If I set survived_with_1hp inside h=0 block, I should synchronize.

                # Simplification:
                # If survived_with_1hp is True, we enforce 1HP.
                # Usage of item_survive below drives consumption.

                # Re-aligning logic to match existing structure 1882+ w.r.t consumption.

                if survived_with_1hp:
                    hit_dmg = defender["current_hp"] - 1
                    source = "Focus Band"
                    if item_survive:
                        source = rich_item.get("name", "Focus Sash")
                    elif ab_survive:
                        source = rich_ab.get("name", "Sturdy")

                    # Log if not already logged (Focus Band logged itself earlier?)
                    # Actually, simplistic:
                    if source != "Focus Band":  # Band logged itself
                        log.append(
                            f"  {defender.get('species')} hung on using its {source}!"
                        )

                    if item_survive:
                        defender["item"] = None
                        if rich_ab and rich_ab.get("name") == "Unburden":
                            defender["unburden_active"] = True
                            log.append(
                                f"  {defender.get('species')} became unburdened!"
                            )

                # Substitute Redirection
                vols = defender.get("volatiles", [])
                is_sound = move_flags.get("sound") or "sound" in move_name.lower()
                is_infiltrator = attacker.get("ability") == "Infiltrator"
                if (
                    "substitute" in vols
                    and not (is_sound or is_infiltrator)
                    and hit_dmg > 0
                ):
                    sub_hp = defender.get("substitute_hp", 0)
                    actual_dmg = min(hit_dmg, sub_hp)
                    defender["substitute_hp"] = sub_hp - actual_dmg
                    log.append(
                        f"  The substitute took damage for {defender.get('species')}!"
                    )

                    if defender["substitute_hp"] <= 0:
                        vols.remove("substitute")
                        log.append(f"  {defender.get('species')}'s substitute faded!")

                    total_damage_dealt += actual_dmg
                    actual_hits += 1
                    continue  # Skip HP reduction for this hit

                defender["current_hp"] -= hit_dmg
                total_damage_dealt += hit_dmg
                actual_hits += 1

                # On-Hit Reactions per hit (Rocky Helmet, Rough Skin, etc)
                if hit_dmg > 0 or (not is_status and defender.get("ability") == "Ice Face"):
                    # Air Balloon Pop
                    if defender.get("item") == "Air Balloon":
                        defender["item"] = None
                        log.append(f"  {defender.get('species')}'s Air Balloon popped!")

                    self.trigger_event(
                        state,
                        "onDamagingHit",
                        attacker,
                        defender,
                        log,
                        move_name,
                        hit_dmg,
                        context,
                    )

                    # Illusion Break
                    if defender.get("ability") == "Illusion" and defender.get(
                        "is_disguised"
                    ):
                        defender["is_disguised"] = False
                        log.append(f"  {defender.get('species')}'s illusion wore off!")

                    # Knock Off Item Removal
                    if move_name == "Knock Off" and defender.get("item"):
                        item = defender["item"]
                        if not self._is_item_unremovable(item, defender):
                            defender["item"] = None
                            defender["_rich_item"] = None
                            log.append(
                                f"  {defender.get('species')} knocked off {defender.get('species')}'s {item}!"
                            )

            # Magician (Steal item on hit if attacker has none)
            if (
                attacker.get("ability") == "Magician"
                and not attacker.get("item")
                and defender.get("item")
            ):
                if total_damage_dealt > 0:
                    item = defender.get("item")
                    if not self._is_item_unremovable(item, defender):
                        attacker["item"] = item
                        attacker["_rich_item"] = defender.get("_rich_item")
                        defender["item"] = None
                        defender["_rich_item"] = None
                        log.append(
                            f"  {attacker.get('species')} stole {defender.get('species')}'s {item} with Magician!"
                        )

            if hit_count > 1:
                log.append(f"  Hit {actual_hits} times!")

            hp_pct = max(0, int((defender["current_hp"] / defender["max_hp"]) * 100))
            hp_str = (
                f"{max(0, defender['current_hp'])}/{defender['max_hp']} HP ({hp_pct}%)"
            )

            # Log HP and Damage Summary
            log.append(
                f"  {defender.get('species')}: {hp_str} (-{total_damage_dealt} dmg)"
            )

            # HP Threshold Triggers (Berries, Berserk)
            self._check_hp_triggers(state, defender, log)
            self._check_hp_triggers(state, attacker, log)

            # Destiny Bond Trigger Check
            if defender.get("current_hp") <= 0:
                if "destiny_bond" in defender.get("volatiles", []):
                    log.append(
                        f"  {defender.get('species')} took its attacker down with it! (Destiny Bond)"
                    )
                    attacker["current_hp"] = 0
                    log.append(f"  {attacker.get('species')} fainted!")

                # Aftermath
                if defender.get("ability") == "Aftermath":
                    contact = self._makes_contact(move_name, attacker)
                    # print(f"DEBUG: Aftermath check. DefHP={defender.get('current_hp')} Ab={defender.get('ability')} Contact={contact}")
                    if contact:
                        dmg = attacker.get("max_hp", 100) // 4
                        attacker["current_hp"] = max(0, attacker["current_hp"] - dmg)
                        log.append(
                            f"  {attacker.get('species')} was hurt by {defender.get('species')}'s Aftermath! (-{dmg})"
                        )

                # Innards Out
                if defender.get("ability") == "Innards Out":
                    dmg = defender.get("_hp_before_hit", 0)
                    attacker["current_hp"] = max(0, attacker["current_hp"] - dmg)
                    log.append(
                        f"  {attacker.get('species')} was hurt by {defender.get('species')}'s Innards Out! (-{dmg})"
                    )

            # --- PARENTAL BOND (Second Hit for single-hit moves) ---
            if (
                attacker.get("ability") == "Parental Bond"
                and total_damage_dealt > 0
                and defender["current_hp"] > 0
            ):
                if hit_count == 1 and not res.get("isCharge"):
                    # Second hit dmg = 25% (Phase 3 generic handling)
                    second_hit_dmg = total_damage_dealt // 4
                    if second_hit_dmg > 0:
                        defender["current_hp"] = max(
                            0, defender["current_hp"] - second_hit_dmg
                        )
                        log.append(
                            f"  The parent and child are attacking together! ({second_hit_dmg} damage)"
                        )
                        self.trigger_event(
                            state,
                            "onDamagingHit",
                            attacker,
                            defender,
                            log,
                            move_name,
                            second_hit_dmg,
                            context,
                        )

            # --- THROAT SPRAY ---
            if attacker.get("item") == "Throat Spray":
                is_sound = (
                    move_data.get("flags", {}).get("sound")
                    or "sound" in move_name.lower()
                )
                if is_sound:
                    Mechanics.apply_boosts(
                        attacker, {"spa": 1}, log, source_name="Throat Spray"
                    )
                    attacker["item"] = None
                    log.append(f"  {attacker.get('species')} used its Throat Spray!")
                    if attacker.get("ability") == "Unburden":
                        attacker["unburden_active"] = True
                        log.append(f"  {attacker.get('species')} became unburdened!")

            # Move Secondary Effects (Phase 3 generic handling) - Handled in apply_move_effects
            pass

            # Move Secondary Effects (Phase 3 generic handling) - Handled below in consolidated apply_move_effects
            pass

            # 3. Field Effects (Weather / Terrain / Side Conditions)
            mw = move_data.get("weather")
            if mw:
                w_map = {
                    "sunnyday": "Sun",
                    "raindance": "Rain",
                    "sandstorm": "Sand",
                    "hail": "Hail",
                    "snow": "Snow",
                    "snowscape": "Hail",
                }
                final_w = w_map.get(mw, mw)
                state.fields["weather"] = final_w

                # Weather Extenders
                turns = 5
                item = attacker.get("item")
                if (
                    (final_w == "Sun" and item == "Heat Rock")
                    or (final_w == "Rain" and item == "Damp Rock")
                    or (final_w == "Sand" and item == "Smooth Rock")
                    or (final_w == "Hail" and item == "Icy Rock")
                    or (final_w == "Snow" and item == "Icy Rock")
                ):
                    turns = 8

                state.fields["weather_turns"] = turns
                log.append(f"  The weather became {final_w}!")

            # --- More Specific Status Moves ---
            if move_name == "Rest":
                if attacker.get("current_hp") == attacker.get("max_hp"):
                    log.append(f"  {attacker.get('species')} is already fully healthy!")
                else:
                    attacker["status"] = "slp"
                    attacker["sleep_turns"] = 2
                    attacker["current_hp"] = attacker.get("max_hp")
                    log.append(f"  {attacker.get('species')} slept and became healthy!")

            elif move_name in ["Moonlight", "Morning Sun", "Synthesis"]:
                weather = state.fields.get("weather")
                factor = 0.5
                if weather == "Sun":
                    factor = 0.66
                elif weather in ["Rain", "Sand", "Hail", "Snow"]:
                    factor = 0.25

                heal_amt = int(attacker.get("max_hp", 100) * factor)
                attacker["current_hp"] = min(
                    attacker.get("max_hp"), attacker["current_hp"] + heal_amt
                )
                log.append(f"  {attacker.get('species')} regained health!")

            elif move_name in ["Aromatherapy", "Heal Bell"]:
                side_party = (
                    state.player_party if attacker_side == "player" else state.ai_party
                )
                # Assuming side_party handles active mon too if it's in the list
                for m in side_party:
                    if m.get("status"):
                        m["status"] = None
                        log.append(f"  {m.get('species')} was cured!")
                log.append(f"  A bell chimed!")

            elif move_name == "Refresh":
                if attacker.get("status"):
                    attacker["status"] = None
                    log.append(f"  {attacker.get('species')} refreshed its status!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Pain Split":
                # Substitute Check
                v_list = defender.get("volatiles", [])
                if "substitute" in v_list and not (
                    move_flags.get("sound") or attacker.get("ability") == "Infiltrator"
                ):
                    log.append(
                        f"  But it failed due to {defender.get('species')}'s substitute!"
                    )
                else:
                    avg = (attacker.get("current_hp") + defender.get("current_hp")) // 2
                    attacker["current_hp"] = min(attacker.get("max_hp"), avg)
                    defender["current_hp"] = min(defender.get("max_hp"), avg)
                    log.append(f"  The battlers shared their pain!")

            elif move_name == "Perish Song":
                for mon in [state.player_active, state.ai_active]:
                    v = mon.setdefault("volatiles", [])
                    if "perish3" not in v:
                        v.append("perish3")
                        log.append(
                            f"  {mon.get('species')}'s perish count will fall in 3 turns."
                        )

            elif move_name == "Magnet Rise":
                v = attacker.setdefault("volatiles", [])
                if "magnetrise" not in v:
                    v.append("magnetrise")
                    attacker["magnet_rise_turns"] = 5
                    log.append(
                        f"  {attacker.get('species')} levitated with electromagnetism!"
                    )

            elif move_name == "Focus Energy":
                v = attacker.setdefault("volatiles", [])
                if "focusenergy" not in v:
                    v.append("focusenergy")
                    log.append(f"  {attacker.get('species')} is getting pumped!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Dragon Cheer":
                v = attacker.setdefault("volatiles", [])
                if "dragoncheer" not in v:
                    v.append("dragoncheer")
                    log.append(f"  {attacker.get('species')} cheered its allies!")

            elif move_name == "Imprison":
                v = attacker.setdefault("volatiles", [])
                if "imprison" not in v:
                    v.append("imprison")
                    log.append(
                        f"  {attacker.get('species')} sealed the opponent's moves!"
                    )

            elif move_name == "No Retreat":
                if "trapped" not in attacker.get("volatiles", []):
                    Mechanics.apply_boosts(
                        attacker,
                        {"atk": 1, "def": 1, "spa": 1, "spd": 1, "spe": 1},
                        log,
                        source_name="No Retreat",
                        field=state.fields,
                    )
                    attacker.setdefault("volatiles", []).append("trapped")
                    log.append(f"  {attacker.get('species')} has no retreat!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Fairy Lock":
                state.fields["fairy_lock"] = 1
                log.append("  No one can escape now!")

            elif move_name == "Venom Drench":
                if defender.get("status") in ["psn", "tox"]:
                    Mechanics.apply_boosts(
                        defender,
                        {"atk": -1, "spa": -1, "spe": -1},
                        log,
                        source_name="Venom Drench",
                        field=state.fields,
                    )
                else:
                    log.append("  But it failed!")

            elif move_name == "Acupressure":
                stats = ["atk", "def", "spa", "spd", "spe", "acc", "eva"]
                stat = random.choice(stats)
                Mechanics.apply_boosts(
                    defender,
                    {stat: 2},
                    log,
                    source_name="Acupressure",
                    field=state.fields,
                )

            elif move_name in ["Roar", "Whirlwind", "Dragon Tail", "Circle Throw"]:
                # Phazing Logic
                # Check for immunities (Suction Cups / Ingrain)
                if defender.get(
                    "ability"
                ) == "Suction Cups" or "ingrain" in defender.get("volatiles", []):
                    log.append(
                        f"  {defender.get('species')} anchors itself with {defender.get('ability') or 'Ingrain'}!"
                    )
                elif move_name in [
                    "Dragon Tail",
                    "Circle Throw",
                ] and "substitute" in defender.get("volatiles", []):
                    # Damaging phazing moves fail to switch if hitting a substitute
                    log.append("  The attack was absorbed by the substitute!")
                else:
                    # Check available switch-ins
                    target_party = (
                        state.player_party
                        if defender_side == "player"
                        else state.ai_party
                    )
                    # Valid: HP > 0 and not active
                    valid_targets = [
                        p
                        for p in target_party
                        if p.get("current_hp") > 0
                        and p.get("species") != defender.get("species")
                    ]

                    if not valid_targets:
                        log.append("  But it failed!")
                    else:
                        # Pick random target
                        switch_mon = random.choice(valid_targets)
                        s_name = switch_mon.get("species")
                        log.append(f"  {defender.get('species')} was blown away!")
                        self.perform_switch(state, defender_side, s_name, log)

            elif move_name == "Heal Pulse":
                heal_amt = int(defender.get("max_hp", 100) * 0.5)
                defender["current_hp"] = min(
                    defender.get("max_hp"), defender["current_hp"] + heal_amt
                )
                log.append(f"  {defender.get('species')} regained health!")

            elif move_name == "Shore Up":
                weather = state.fields.get("weather")
                factor = 0.5
                if weather == "Sand":
                    factor = 0.66
                elif weather in ["Sun", "Rain", "Hail", "Snow"]:
                    factor = 0.25  # Shore Up reduces in non-sand weather?
                # Actually Shore Up is 2/3 in Sand, 1/2 otherwise. It does NOT decrease in other weather usually?
                # Bulbapedia: "restores 1/2 max HP. In Sandstorm, restores 2/3."
                # Let's stick to BULBAPEDIA: 1/2 normally, 2/3 in Sand.
                if weather != "Sand":
                    factor = 0.5

                heal_amt = int(attacker.get("max_hp", 100) * factor)
                attacker["current_hp"] = min(
                    attacker.get("max_hp"), attacker["current_hp"] + heal_amt
                )
                log.append(f"  {attacker.get('species')} shored up its defenses!")

            elif move_name == "Substitute":
                vols = attacker.setdefault("volatiles", [])
                cost = attacker.get("max_hp", 100) // 4
                if "substitute" in vols:
                    log.append(f"  {attacker.get('species')} already has a substitute!")
                elif attacker.get("current_hp", 0) <= cost:
                    log.append(
                        f"  {attacker.get('species')} is too weak to make a substitute!"
                    )
                else:
                    attacker["current_hp"] -= cost
                    if "substitute" not in vols:
                        vols.append("substitute")
                    attacker["substitute_hp"] = cost
                    log.append(
                        f"  {attacker.get('species')} put in a substitute! (-{cost} HP)"
                    )

            elif move_name == "Nature's Madness" or move_name == "Super Fang":
                dmg = max(1, defender.get("current_hp") // 2)
                # Substitute Redirection
                v_list = defender.get("volatiles", [])
                if "substitute" in v_list and not (
                    move_flags.get("sound") or attacker.get("ability") == "Infiltrator"
                ):
                    sub_hp = defender.get("substitute_hp", 0)
                    actual_dmg = min(dmg, sub_hp)
                    defender["substitute_hp"] = sub_hp - actual_dmg
                    log.append(
                        f"  The substitute took damage for {defender.get('species')}!"
                    )
                    if defender["substitute_hp"] <= 0:
                        v_list.remove("substitute")
                        log.append(f"  {defender.get('species')}'s substitute faded!")
                else:
                    defender["current_hp"] -= dmg
                log.append(f"  {defender.get('species')} lost {dmg} HP! (Half HP)")

            elif move_name == "Final Gambit":
                dmg = attacker.get("current_hp", 0)
                attacker["current_hp"] = 0
                # Substitute Redirection
                v_list = defender.get("volatiles", [])
                if "substitute" in v_list and not (
                    move_flags.get("sound") or attacker.get("ability") == "Infiltrator"
                ):
                    sub_hp = defender.get("substitute_hp", 0)
                    actual_dmg = min(dmg, sub_hp)
                    defender["substitute_hp"] = sub_hp - actual_dmg
                    log.append(
                        f"  The substitute took damage for {defender.get('species')}!"
                    )
                    if defender["substitute_hp"] <= 0:
                        v_list.remove("substitute")
                        log.append(f"  {defender.get('species')}'s substitute faded!")
                else:
                    defender["current_hp"] = max(0, defender.get("current_hp") - dmg)
                log.append(
                    f"  {attacker.get('species')} sacrificed itself to deal {dmg} damage!"
                )

            elif move_name == "Splash":
                log.append("  But nothing happened!")

            elif move_name in ["Soak", "Magic Powder"]:
                # Change type stub
                new_type = "Water" if move_name == "Soak" else "Psychic"
                defender["types"] = [new_type]
                log.append(
                    f"  {defender.get('species')} transformed into the {new_type} type!"
                )

            elif move_name == "Forest's Curse":
                if "Grass" not in defender.get("types", []):
                    defender.setdefault("types", []).append("Grass")
                    log.append(f"  Grass type was added to {defender.get('species')}!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Trick-or-Treat":
                if "Ghost" not in defender.get("types", []):
                    defender.setdefault("types", []).append("Ghost")
                    log.append(f"  Ghost type was added to {defender.get('species')}!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Sparkling Aria":
                if defender.get("status") == "brn":
                    defender["status"] = None
                    log.append(f"  {defender.get('species')}'s burn was healed!")

            elif move_name == "Burning Jealousy":
                if defender.get("stats_raised_this_turn"):
                    if defender.get("status") is None:
                        defender["status"] = "brn"
                        log.append(
                            f"  {defender.get('species')} was burned for its ambition!"
                        )

            elif move_name == "Plasma Fists":
                state.fields["ion_deluge"] = 1
                log.append("  A deluge of ions covers the battlefield!")

            elif move_name == "Throat Chop":
                v = defender.setdefault("volatiles", [])
                if "throatchop" not in v:
                    v.append("throatchop")
                    log.append(f"  {defender.get('species')} can't use sound moves!")

            elif move_name == "Thousand Arrows":
                if "smackdown" not in defender.get("volatiles", []):
                    defender.setdefault("volatiles", []).append("smackdown")
                    log.append(
                        f"  {defender.get('species')} was knocked to the ground!"
                    )

            elif move_name in ["Healing Wish", "Lunar Dance"]:
                attacker["current_hp"] = 0
                state.fields[f"{attacker_side}_wish"] = move_name
                log.append(f"  {attacker.get('species')} sacrificed itself!")

            elif move_name in ["Metronome", "Assist", "Copycat", "Sleep Talk"]:
                # Random Move Logic (Simplified)
                # 1. Metronome: Pick any move
                if move_name == "Metronome":
                    # Retrieve all valid move names
                    all_moves = list(self.rich_data.get("moves", {}).keys())
                    # Filter restricted moves (Metronome, Assist, etc.) and Max Moves (isMax)
                    restricted = [
                        "Metronome",
                        "Assist",
                        "Copycat",
                        "Sleep Talk",
                        "Nature Power",
                        "Struggle",
                        "Protect",
                        "Detect",
                        "Endure",
                        "Follow Me",
                        "Rage Powder",
                        "Helping Hand",
                        "Trick",
                        "Switcheroo",
                        "Thief",
                        "Covet",
                        "Bestow",
                        "Snatch",
                        "King's Shield",
                        "Baneful Bunker",
                        "Spiky Shield",
                        "Obstruct",
                        "Destiny Bond",
                        "Counter",
                        "Mirror Coat",
                        "Feint",
                        "Focus Punch",
                        "Transform",
                        "Mimic",
                        "Sketch",
                    ]

                    valid_moves = []
                    moves_dict = self.rich_data.get("moves", {})
                    for m_key in all_moves:
                        if m_key not in restricted:
                            m_data = moves_dict[m_key]
                            # Filter Max Moves (isMax check)
                            if (
                                not m_data.get("isMax")
                                and not m_data.get("isZ")
                                and m_data.get("name") not in restricted
                            ):
                                valid_moves.append(m_key)

                    if valid_moves:
                        rand_move = random.choice(valid_moves)
                        log.append(f"  Waggling a finger... used {rand_move}!")
                        self.execute_turn_action(
                            state,
                            attacker_side,
                            f"Move: {rand_move}",
                            defender_side,
                            log,
                        )
                    else:
                        log.append("  But it failed!")

                # 2. Sleep Talk
                elif move_name == "Sleep Talk":
                    if attacker.get("status") != "slp":
                        log.append("  But it failed!")
                    else:
                        known_moves = attacker.get("moves", [])
                        # Filter Sleep Talk and invalid moves
                        valid_moves = [m for m in known_moves if m != "Sleep Talk"]
                        # Should filter Charge/etc? For now simplified.
                        if valid_moves:
                            rand_move = random.choice(valid_moves)
                            log.append(
                                f"  {attacker.get('species')} used {rand_move} while asleep!"
                            )
                            self.execute_turn_action(
                                state,
                                attacker_side,
                                f"Move: {rand_move}",
                                defender_side,
                                log,
                            )
                        else:
                            log.append("  But it failed!")

                # 3. Copycat (Use last move globally)
                elif move_name == "Copycat":
                    last_move = state.fields.get(
                        "last_move_used_this_turn"
                    )  # Need to track this field properly!
                    # Currently field tracks 'last_move_used_this_turn' in apply_move.
                    # Ideally we need 'last_move_used_GLOBAL'.
                    # Assuming state.fields['last_move_used'] exists or we use 'last_move_used_this_turn' if it happened?
                    # Stub fallback if not tracked explicitly across turns.
                    # We'll use state.fields.get('last_move_global') if we implement tracking, else fail.
                    # Let's use 'last_move_used_this_turn' as best effort, or fail.
                    l_move = state.fields.get("last_move_global")
                    if l_move and l_move != "Copycat":
                        log.append(f"  {attacker.get('species')} copied {l_move}!")
                        self.execute_turn_action(
                            state, attacker_side, f"Move: {l_move}", defender_side, log
                        )
                    else:
                        log.append("  But it failed!")

                # 4. Assist (Random from party)
                elif move_name == "Assist":
                    party = (
                        state.player_party
                        if attacker_side == "player"
                        else state.ai_party
                    )
                    valid_moves = []
                    restricted = [
                        "Assist",
                        "Metronome",
                        "Copycat",
                        "Sleep Talk",
                        "Struggle",
                        "Protect",
                        "Detect",
                        "Endure",
                        "Destiny Bond",
                        "Way of the Peal",
                        "Dragon Cheer",
                    ]  # incomplete list
                    for p in party:
                        if p["species"] == attacker["species"]:
                            continue  # Don't use self
                        for m in p.get("moves", []):
                            if m not in restricted:
                                valid_moves.append(m)

                    if valid_moves:
                        rand_move = random.choice(valid_moves)
                        log.append(
                            f"  {attacker.get('species')} used {rand_move} via Assist!"
                        )
                        self.execute_turn_action(
                            state,
                            attacker_side,
                            f"Move: {rand_move}",
                            defender_side,
                            log,
                        )
                    else:
                        log.append("  But it failed!")

            elif move_name == "Nature Power":
                terrain = state.fields.get("terrain")
                target_move = "Tri Attack"
                if terrain == "Electric":
                    target_move = "Thunderbolt"
                elif terrain == "Grassy":
                    target_move = "Energy Ball"
                elif terrain == "Misty":
                    target_move = "Moonblast"
                elif terrain == "Psychic":
                    target_move = "Psychic"

                log.append(f"  Nature Power turned into {target_move}!")
                self.execute_turn_action(
                    state, attacker_side, f"Move: {target_move}", defender_side, log
                )

            elif move_name in [
                "Role Play",
                "Skill Swap",
                "Gastro Acid",
            ]:  # Entrainment/SimpleBeam/WorrySeed removed from here
                if move_name == "Role Play":
                    # Copy target ability
                    t_ab = defender.get("ability")
                    if t_ab and t_ab not in [
                        "Wonder Guard",
                        "Multitype",
                        "Stance Change",
                        "Schooling",
                        "Comatose",
                        "Shields Down",
                        "Disguise",
                        "RKS System",
                        "Battle Bond",
                        "Power Construct",
                        "Ice Face",
                        "Gulp Missile",
                        "Receiver",
                        "Power of Alchemy",
                        "Trace",
                        "Forecast",
                        "Flower Gift",
                    ]:
                        attacker["ability"] = t_ab
                        attacker["_rich_ability"] = defender.get("_rich_ability")
                        log.append(f"  {attacker.get('species')} copied {t_ab}!")
                    else:
                        log.append("  But it failed!")

                elif move_name == "Skill Swap":
                    # Swap abilities
                    a_ab = attacker.get("ability")
                    t_ab = defender.get("ability")
                    # Validation (Simplified lists)
                    invalid = [
                        "Wonder Guard",
                        "Multitype",
                        "Illusion",
                        "Stance Change",
                        "Schooling",
                        "Comatose",
                        "Shields Down",
                        "Disguise",
                        "RKS System",
                        "Battle Bond",
                        "Power Construct",
                        "Ice Face",
                        "Gulp Missile",
                        "Neutralizing Gas",
                    ]
                    if a_ab not in invalid and t_ab not in invalid:
                        attacker["ability"] = t_ab
                        defender["ability"] = a_ab
                        # Update rich
                        tmp = attacker.get("_rich_ability")
                        attacker["_rich_ability"] = defender.get("_rich_ability")
                        defender["_rich_ability"] = tmp
                        log.append(
                            f"  {attacker.get('species')} swapped abilities with {defender.get('species')}!"
                        )
                    else:
                        log.append("  But it failed!")

                elif move_name == "Gastro Acid":
                    v = defender.setdefault("volatiles", [])
                    if "gastroacid" not in v:
                        v.append("gastroacid")
                        log.append(
                            f"  {defender.get('species')}'s ability was suppressed!"
                        )
                    else:
                        log.append("  But it failed!")

            elif move_name == "Attract":
                if (
                    defender.get("gender") == "Unknown"
                    or attacker.get("gender") == "Unknown"
                    or defender.get("gender") == attacker.get("gender")
                ):
                    log.append("  But it failed!")
                elif defender.get("ability") == "Oblivious":
                    log.append(
                        f"  {defender.get('species')}'s Oblivious prevents attraction!"
                    )
                elif self._is_protected_by_aroma_veil(defender, log):
                    pass
                else:
                    v = defender.setdefault("volatiles", [])
                    if "infatuation" not in v:
                        v.append("infatuation")
                        log.append(f"  {defender.get('species')} fell in love!")
                    else:
                        log.append("  But it failed!")

            elif move_name in ["Natural Gift"]:
                # Consumes berry to deal damage
                item = attacker.get("item")
                rich_item = attacker.get("_rich_item", {})

                # Natural Gift Berry Table (Gen 8 simplified)
                # Map Berry -> (Type, Power)
                # We can use a small hardcoded map or heuristics.
                # Heuristic: 'cheri': Fire, 'chesto': Water, 'pecha': Electric...
                # Or just generic "It's a berry" check.
                # Let's use a partial map for common berries + generic fallback.

                berry_map = {
                    "Cheri Berry": ("Fire", 80),
                    "Chesto Berry": ("Water", 80),
                    "Pecha Berry": ("Electric", 80),
                    "Rawst Berry": ("Grass", 80),
                    "Aspear Berry": ("Ice", 80),
                    "Leppa Berry": ("Fighting", 80),
                    "Oran Berry": ("Poison", 80),
                    "Persim Berry": ("Ground", 80),
                    "Lum Berry": ("Flying", 80),
                    "Sitrus Berry": ("Psychic", 80),
                    "Figy Berry": ("Bug", 80),
                    "Wiki Berry": ("Rock", 80),
                    "Mago Berry": ("Ghost", 80),
                    "Aguav Berry": ("Dragon", 80),
                    "Iapapa Berry": ("Dark", 80),
                    "Liechi Berry": ("Grass", 100),
                    "Ganlon Berry": ("Ice", 100),
                    "Salac Berry": ("Fighting", 100),
                    "Petaya Berry": ("Poison", 100),
                    "Apicot Berry": ("Ground", 100),
                    "Lansat Berry": ("Flying", 100),
                    "Starf Berry": ("Psychic", 100),
                    "Enigma Berry": ("Bug", 100),
                    "Micle Berry": ("Rock", 100),
                    "Custap Berry": ("Ghost", 100),
                    "Jaboca Berry": ("Dragon", 100),
                    "Rowap Berry": ("Dark", 100),
                    "Roseli Berry": ("Fairy", 80),
                    "Kee Berry": ("Fairy", 100),
                    "Maranga Berry": ("Dark", 100),
                }

                # Logic
                b_data = berry_map.get(rich_item.get("name"))
                if b_data:
                    t, p = b_data

                    # Create Temp Move
                    t_move = res.copy()  # res is currently Natural Gift data
                    t_move["type"] = t
                    t_move["basePower"] = p
                    t_move["category"] = "Physical"

                    # Consume Item
                    attacker["item"] = None
                    attacker["_rich_item"] = None

                    log.append(
                        f"  {attacker.get('species')} used Natural Gift via {rich_item.get('name')}!"
                    )

                    # Execute Damage (Simplified: We don't have a clean recursive 'execute_move' logic that takes custom data
                    # without full refactor. We will manually calc damage here or use trigger.)
                    # We'll rely on a basic calc for this specific move to ensure effect.

                    # Fetch stats
                    atk = Mechanics.get_effective_stat(attacker, "atk", state.fields)
                    defense = Mechanics.get_effective_stat(
                        defender, "def", state.fields
                    )
                    val = int(
                        (((2 * 100 / 5 + 2) * p * atk / defense) / 50 + 2) * 1
                    )  # simplified

                    defender["current_hp"] = max(0, defender["current_hp"] - val)
                    log.append(f"  It dealt {val} damage (Type: {t})!")

                    self.trigger_event(
                        state,
                        "onDamagingHit",
                        attacker,
                        defender,
                        log,
                        move_name,
                        val,
                        {"effectiveness": 1},
                    )

                else:
                    log.append("  But it failed!")

            elif move_name == "Mirror Move":
                # Use opponent's last move
                opp_last = state.last_moves.get(defender_side)
                if opp_last and opp_last != "Mirror Move":
                    log.append(f"  {attacker.get('species')} mirrored {opp_last}!")
                    # Recursion
                    self.execute_turn_action(
                        state, attacker_side, f"Move: {opp_last}", defender_side, log
                    )
                else:
                    log.append("  But it failed!")

            elif move_name == "Conversion 2":
                # Change to type resisting opponent's last move
                opp_last = state.last_moves.get(defender_side)
                if opp_last:
                    m_data = self._get_mechanic(opp_last, "moves")
                    m_type = m_data.get("type")
                    if m_type:
                        # Find resistance
                        # Simplified table
                        resist_map = {
                            "Normal": "Ghost",
                            "Fire": "Water",
                            "Water": "Grass",
                            "Electric": "Ground",
                            "Grass": "Fire",
                            "Ice": "Fire",
                            "Fighting": "Ghost",
                            "Poison": "Ground",
                            "Ground": "Flying",
                            "Flying": "Electric",
                            "Psychic": "Dark",
                            "Bug": "Flying",
                            "Rock": "Fighting",
                            "Ghost": "Normal",
                            "Dragon": "Fairy",
                            "Dark": "Fighting",
                            "Steel": "Fire",
                            "Fairy": "Poison",
                        }
                        new_type = resist_map.get(m_type, "Normal")
                        attacker["types"] = [new_type]
                        log.append(
                            f"  {attacker.get('species')} transformed into the {new_type} type to resist {m_type}!"
                        )
                    else:
                        log.append("  But it failed!")
                else:
                    log.append("  But it failed!")

            elif move_name in ["Quash", "After You"]:
                # Singles: No effect
                log.append("  But it failed! (No effect in Singles)")
            elif move_name in ["Gravity", "Magic Room", "Wonder Room"]:
                state.fields[move_name.lower().replace(" ", "_")] = 5
                log.append(f"  {move_name} twisted the dimensions!")

            elif move_name in ["Fire Pledge", "Water Pledge", "Grass Pledge"]:
                log.append(
                    f"  {attacker.get('species')} is waiting for its ally... (Singles Stub)"
                )

            elif move_name == "Beat Up":
                # Full Party Logic
                party = (
                    state.player_party
                    if attacker["side"] == "player"
                    else state.ai_party
                )
                total_damage = 0
                hits = 0

                for member in party:
                    if member.get("current_hp", 0) > 0 and not member.get("status"):
                        p_data = Mechanics.get_mon_data(member.get("species", ""))
                        base_atk = p_data.get("baseStats", {}).get("atk", 100)
                        bp = (base_atk // 10) + 5

                        # Manual Damage Calc Call (Simulation)
                        # We approximate damage using a simplified formula here because
                        # calling 'calc_client' recursively for sub-hits is tricky without a dedicated method.
                        # Formula: (((2*L/5+2)*BP*A/D)/50 + 2) * Modifiers
                        level = attacker.get("level", 100)
                        # Attacker Stat: Use MEMBER'S base atk? No, Beat Up uses USER'S Atk stat stages but MEMBER'S Base Atk for BP.
                        # Actually, Beat Up (Gen 5+) uses "The user's Attack stat and the target's Defense stat".
                        # The BASE POWER depends on party member.

                        # So we need to use the User's ATK stat (with stages).
                        atk = Mechanics.get_effective_stat(
                            attacker, "atk", state.fields
                        )
                        defense = Mechanics.get_effective_stat(
                            defender, "def", state.fields
                        )

                        dmg = int((((2 * level / 5 + 2) * bp * atk / defense) / 50 + 2))

                        # Apply to target
                        defender["current_hp"] = max(0, defender["current_hp"] - dmg)
                        total_damage += dmg
                        hits += 1
                        log.append(f"  Strike from {member.get('species')}! (-{dmg})")

                        if defender["current_hp"] <= 0:
                            break

                if hits == 0:
                    log.append("  But it failed!")
                else:
                    log.append(f"  Beat Up dealt {total_damage} damage total!")

            elif move_name == "Psycho Shift":
                # Validation
                status = attacker.get("status")
                if status and not defender.get("status"):
                    if not self._is_status_immune(state, defender, status, attacker):
                        defender["status"] = status
                        attacker["status"] = None
                        log.append(
                            f"  {attacker.get('species')} moved its {status} to {defender.get('species')}!"
                        )
                    else:
                        log.append("  It doesn't affect the opposing Pokemon...")
                else:
                    log.append("  But it failed!")

            elif move_name == "Reflect Type":
                # User copies target types
                t_types = defender.get("types", [])
                if t_types:
                    attacker["types"] = list(t_types)
                    log.append(
                        f"  {attacker.get('species')} became the same type as {defender.get('species')}!"
                    )
                else:
                    log.append("  But it failed!")

            elif move_name in ["Power Split", "Guard Split"]:
                # Average stats
                stats_to_split = (
                    ["atk", "spa"] if move_name == "Power Split" else ["def", "spd"]
                )
                for s in stats_to_split:
                    # Get raw stats (before stages)
                    u_val = attacker.get("stats", {}).get(s, 100)
                    t_val = defender.get("stats", {}).get(s, 100)
                    avg = (u_val + t_val) // 2
                    attacker["stats"][s] = avg
                    defender["stats"][s] = avg

                log.append(
                    f"  {attacker.get('species')} shared its power with the target!"
                )

            elif move_name == "Psych Up":
                # Copy stages
                if defender.get("stat_stages"):
                    attacker["stat_stages"] = defender["stat_stages"].copy()
                    log.append(f"  {attacker.get('species')} copied the stat changes!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Bestow":
                # Give item
                item = attacker.get("item")
                if item and not defender.get("item"):
                    defender["item"] = item
                    attacker["item"] = None
                    defender["_rich_item"] = attacker.get("_rich_item")  # Hack
                    log.append(f"  {attacker.get('species')} bestowed its {item}!")
                else:
                    log.append("  But it failed!")
                # Simplified: Just deals damage if no ally

            elif move_name == "Fling":
                item = attacker.get("item")
                if item:
                    attacker["item"] = None
                    log.append(f"  {attacker.get('species')} flung its {item}!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Camouflage":
                terrain = state.fields.get("terrain")
                new_type = "Normal"
                if terrain == "Electric":
                    new_type = "Electric"
                elif terrain == "Grassy":
                    new_type = "Grass"
                elif terrain == "Misty":
                    new_type = "Fairy"
                elif terrain == "Psychic":
                    new_type = "Psychic"

                attacker["types"] = [new_type]
                log.append(
                    f"  {attacker.get('species')} transformed into the {new_type} type!"
                )

            elif move_name == "Conversion":
                # Change to type of first move
                moves = attacker.get("moves", [])
                if moves:
                    # We need the type of the first move.
                    # We don't have full move objects here, just names usually?
                    # Or 'moves' dict?
                    first_move = moves[0]
                    # 'moves' is usually a list of strings (names) or dicts.
                    # Based on structure seen elsewhere: attacker['moves'] = defender['moves'].copy() -> list logic.
                    # Let's assume list of names.
                    if isinstance(first_move, dict):
                        first_move = first_move.get("name")

                    m_data = self._get_mechanic(first_move, "moves")
                    t = m_data.get("type")
                    if t:
                        attacker["types"] = [t]
                        log.append(
                            f"  {attacker.get('species')} transformed into the {t} type!"
                        )
                    else:
                        log.append("  But it failed!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Metal Burst":
                # 1.5x damage taken this turn
                taken = attacker.get("last_dmg_received", 0)
                # Metal Burst doesn't care about category (unlike Counter/Mirror Coat)
                if taken > 0 and attacker.get("took_damage_this_turn"):
                    dmg = int(taken * 1.5)
                    defender["current_hp"] = max(0, defender["current_hp"] - dmg)
                    log.append(
                        f"  {attacker.get('species')} retaliated with Metal Burst! (-{dmg})"
                    )
                    self.trigger_event(
                        state,
                        "onDamagingHit",
                        attacker,
                        defender,
                        log,
                        move_name,
                        dmg,
                        {"effectiveness": 1},
                    )
                else:
                    log.append("  But it failed!")

            # Conversion 2, Mirror Move, Natural Gift: Removed (Too complex for simple logic)

            # Quash/After You removed.

            if move_name == "Baton Pass":
                # The stat boosts remain on the Pokémon
                # The switch itself will be handled by the must_switch flag
                log.append(
                    f"  {attacker_side.upper()} side is preparing to pass boosts..."
                )
                # Set switch flag to trigger switch in apply_turn
                attacker["must_switch"] = True

            elif move_name == "Recycle":
                item = attacker.get("last_item")
                if item and not attacker.get("item"):
                    attacker["item"] = item
                    log.append(f"  {attacker.get('species')} found one {item}!")
                else:
                    log.append("  But it failed!")

            elif move_name == "Haze":
                # Reset all stat stages for both Pokemon
                attacker.setdefault("stat_stages", {}).clear()
                defender.setdefault("stat_stages", {}).clear()
                log.append("  All stat changes were eliminated!")

            elif move_name == "Safeguard":
                sc = state.fields.setdefault("screens", {})
                side_sc = sc.setdefault(attacker_side, {})
                side_sc["safeguard"] = 5
                log.append(f"  {attacker_side.upper()} side is protected by a veil!")

            elif move_name == "Spite":
                log.append("  But it failed!")

            elif move_name == "Attract":
                v = defender.setdefault("volatiles", [])
                if "attract" not in v:
                    v.append("attract")
                    log.append(f"  {defender.get('species')} fell in love!")
                    self._check_mental_herb(defender, log)

            elif move_name == "Revival Blessing":
                log.append(f"  {attacker.get('species')} is attempting a revival!")

            elif move_name in [
                "Helping Hand",
                "Follow Me",
                "Rage Powder",
                "Ally Switch",
            ]:
                log.append(f"  {move_name} is only effective in Double Battles.")

            # High-Priority Simple Moves
            elif move_name == "Obstruct":
                # Similar to King's Shield but lowers Defense by 2
                v = attacker.setdefault("volatiles", [])
                if "obstruct" not in v:
                    v.append("obstruct")
                    log.append(f"  {attacker.get('species')} obstructed the attack!")

            elif move_name in ["Foresight", "Odor Sleuth", "Miracle Eye"]:
                v = defender.setdefault("volatiles", [])
                key = "miracleeye" if move_name == "Miracle Eye" else "foresight"
                if key not in v:
                    v.append("foresight")
                    log.append(
                        f"  {attacker.get('species')} identified {defender.get('species')}!"
                    )

            elif move_name == "Miracle Eye":
                v = defender.setdefault("volatiles", [])
                if "miracleeye" not in v:
                    v.append("miracleeye")
                    log.append(
                        f"  {attacker.get('species')} identified {defender.get('species')}!"
                    )

            elif move_name == "Embargo":
                v = defender.setdefault("volatiles", [])
                if "embargo" not in v:
                    v.append("embargo")
                    defender["embargo_turns"] = 5
                    log.append(f"  {defender.get('species')} can't use items!")

            elif move_name == "Heal Block":
                if self._is_protected_by_aroma_veil(defender, log):
                    pass
                else:
                    v = defender.setdefault("volatiles", [])
                    if "healblock" not in v:
                        v.append("healblock")
                        defender["heal_block_turns"] = 5
                        log.append(f"  {defender.get('species')} can't heal!")

            elif move_name == "Laser Focus":
                v = attacker.setdefault("volatiles", [])
                if "laserfocus" not in v:
                    v.append("laserfocus")
                    log.append(f"  {attacker.get('species')} concentrated intensely!")

            elif move_name == "Power Shift":
                atk = attacker.get("stats", {}).get("atk", 1)
                df = attacker.get("stats", {}).get("def", 1)
                attacker.setdefault("stats", {})["atk"] = df
                attacker["stats"]["def"] = atk
                log.append(
                    f"  {attacker.get('species')} swapped its offensive and defensive stats!"
                )

            elif move_name == "Nightmare":
                if defender.get("status") == "slp":
                    v = defender.setdefault("volatiles", [])
                    if "nightmare" not in v:
                        v.append("nightmare")
                        log.append(
                            f"  {defender.get('species')} began having a nightmare!"
                        )
                else:
                    log.append("  But it failed!")

            elif move_name == "Lucky Chant":
                sc = state.fields.setdefault("screens", {})
                side_sc = sc.setdefault(attacker_side, {})
                side_sc["luckychant"] = 5
                log.append(
                    f"  {attacker_side.upper()} side is protected by Lucky Chant!"
                )

            elif move_name == "Octolock":
                v = defender.setdefault("volatiles", [])
                if "octolock" not in v:
                    v.append("octolock")
                    v.append("trapped")
                    log.append(f"  {defender.get('species')} can't escape!")

            # Medium-Priority Interaction Moves
            elif move_name == "Electrify":
                v = defender.setdefault("volatiles", [])
                if "electrify" not in v:
                    v.append("electrify")
                    log.append(
                        f"  {defender.get('species')}'s moves became Electric-type!"
                    )

            elif move_name == "Ion Deluge":
                state.fields["ion_deluge"] = True
                log.append("  A deluge of ions showers the battlefield!")

            elif move_name == "Powder":
                v = defender.setdefault("volatiles", [])
                if "powder" not in v:
                    v.append("powder")
                    log.append(f"  {defender.get('species')} is covered in powder!")

            elif move_name == "Telekinesis":
                v = defender.setdefault("volatiles", [])
                if "telekinesis" not in v:
                    v.append("telekinesis")
                    defender["telekinesis_turns"] = 3
                    log.append(f"  {defender.get('species')} was hurled into the air!")

            elif move_name == "Crafty Shield":
                sc = state.fields.setdefault("screens", {})
                side_sc = sc.setdefault(attacker_side, {})
                side_sc["craftyshield"] = 1
                log.append(
                    f"  {attacker_side.upper()} side is protected by Crafty Shield!"
                )

            elif move_name == "Mat Block":
                # Only works on first turn
                if state.fields.get("turn", 1) == 1:
                    sc = state.fields.setdefault("screens", {})
                    side_sc = sc.setdefault(attacker_side, {})
                    side_sc["matblock"] = 1
                    log.append(
                        f"  {attacker_side.upper()} side is protected by Mat Block!"
                    )
                else:
                    log.append("  But it failed!")

            elif move_name == "Snatch":
                v = attacker.setdefault("volatiles", [])
                if "snatch" not in v:
                    v.append("snatch")
                    log.append(
                        f"  {attacker.get('species')} waits for a beneficial move!"
                    )

            elif move_name == "Rage":
                v = attacker.setdefault("volatiles", [])
                if "rage" not in v:
                    v.append("rage")
                    log.append(f"  {attacker.get('species')} is enraged!")

            elif move_name == "Pursuit":
                # Pursuit logic handled in damage calculation
                pass

            # Low-Priority Complex Moves (Simplified)
            elif move_name == "Bide":
                v = attacker.setdefault("volatiles", [])
                if "bide" not in v:
                    v.append("bide")
                    attacker["bide_turns"] = 2
                    attacker["bide_damage"] = 0
                    log.append(f"  {attacker.get('species')} is storing energy!")

            elif move_name == "Me First":
                # Simplified: Just log, actual copying logic would be complex
                log.append(f"  {attacker.get('species')} tried to use Me First!")

            elif move_name == "Magic Coat":
                v = attacker.setdefault("volatiles", [])
                if "magiccoat" not in v:
                    v.append("magiccoat")
                    log.append(
                        f"  {attacker.get('species')} shrouded itself with Magic Coat!"
                    )

            elif move_name == "Shell Trap":
                v = attacker.setdefault("volatiles", [])
                if "shelltrap" not in v:
                    v.append("shelltrap")
                    log.append(f"  {attacker.get('species')} set a shell trap!")

            # G-Max Moves (Dynamax not in scope - mark as utility)
            elif move_name in [
                "G-Max Cannonade",
                "G-Max Vine Lash",
                "G-Max Wildfire",
                "G-Max Volcalith",
                "G-Max Chi Strike",
                "G-Max Steelsurge",
            ]:
                log.append(
                    f"  {move_name} requires Dynamax (not implemented in singles)."
                )

            # Deprecated Sport Moves
            elif move_name in ["Mud Sport", "Water Sport"]:
                log.append("  But it failed!")

            # Final 3 Moves for 100% Coverage
            elif move_name == "Grudge":
                v = attacker.setdefault("volatiles", [])
                if "grudge" not in v:
                    v.append("grudge")
                    log.append(
                        f"  {attacker.get('species')} wants the foe to bear a grudge!"
                    )

            elif move_name == "Max Guard":
                # Dynamax protection move
                v = attacker.setdefault("volatiles", [])
                if "maxguard" not in v:
                    v.append("maxguard")
                    log.append(
                        f"  {attacker.get('species')} protected itself with Max Guard!"
                    )

            elif move_name == "Spotlight":
                v = defender.setdefault("volatiles", [])
                if "spotlight" not in v:
                    v.append("spotlight")
                    log.append(
                        f"  {defender.get('species')} became the center of attention!"
                    )

            elif move_name == "Worry Seed":
                # Changes ability to Insomnia
                if defender.get("ability") not in [
                    "Insomnia",
                    "Truant",
                    "Multitype",
                    "Stance Change",
                    "Schooling",
                    "Comatose",
                    "Shields Down",
                    "Disguise",
                    "RKS System",
                    "Battle Bond",
                    "Power Construct",
                    "Ice Face",
                    "Gulp Missile",
                ]:
                    defender["ability"] = "Insomnia"
                    # Update rich ability
                    defender["_rich_ability"] = self._get_mechanic(
                        "Insomnia", "abilities"
                    )
                    log.append(f"  {defender.get('species')} acquired Insomnia!")
                else:
                    log.append(f"  But it failed!")

            elif move_name == "Simple Beam":
                # Changes ability to Simple
                if defender.get("ability") not in [
                    "Simple",
                    "Truant",
                    "Multitype",
                    "Stance Change",
                    "Schooling",
                    "Comatose",
                    "Shields Down",
                    "Disguise",
                    "RKS System",
                    "Battle Bond",
                    "Power Construct",
                    "Ice Face",
                    "Gulp Missile",
                ]:
                    defender["ability"] = "Simple"
                    defender["_rich_ability"] = self._get_mechanic(
                        "Simple", "abilities"
                    )
                    log.append(f"  {defender.get('species')} acquired Simple!")
                else:
                    log.append(f"  But it failed!")

            elif move_name == "Entrainment":
                # Changes ability to User's
                target_ab = attacker.get("ability")
                if defender.get("ability") not in [
                    "Truant",
                    "Multitype",
                    "Stance Change",
                    "Schooling",
                    "Comatose",
                    "Shields Down",
                    "Disguise",
                    "RKS System",
                    "Battle Bond",
                    "Power Construct",
                    "Ice Face",
                    "Gulp Missile",
                ] and target_ab not in [
                    "Trace",
                    "Forecast",
                    "Flower Gift",
                    "Zen Mode",
                    "Illusion",
                    "Imposter",
                    "Power of Alchemy",
                    "Receiver",
                    "Disguise",
                    "Power Construct",
                    "Battle Bond",
                    "RKS System",
                    "Comatose",
                    "Shields Down",
                    "Schooling",
                    "Stance Change",
                    "Multitype",
                    "Gulp Missile",
                    "Ice Face",
                ]:
                    defender["ability"] = target_ab
                    defender["_rich_ability"] = attacker.get("_rich_ability")
                    log.append(f"  {defender.get('species')} acquired {target_ab}!")
                else:
                    log.append(f"  But it failed!")

            elif move_name == "Lock-On":
                v = defender.setdefault("volatiles", [])
                if "lockon" not in v:
                    v.append("lockon")
                    log.append(
                        f"  {attacker.get('species')} locked on to {defender.get('species')}!"
                    )

            elif move_name == "Mist":
                sc = state.fields.setdefault("screens", {})
                side_sc = sc.setdefault(attacker_side, {})
                side_sc["mist"] = 5
                log.append(f"  {attacker_side.upper()} side is protected by Mist!")

            elif move_name == "Quick Guard":
                sc = state.fields.setdefault("screens", {})
                side_sc = sc.setdefault(attacker_side, {})
                side_sc["quickguard"] = 1
                log.append(
                    f"  {attacker_side.upper()} side is protected by Quick Guard!"
                )

            elif move_name == "Wide Guard":
                sc = state.fields.setdefault("screens", {})
                side_sc = sc.setdefault(attacker_side, {})
                side_sc["wideguard"] = 1
                log.append(
                    f"  {attacker_side.upper()} side is protected by Wide Guard!"
                )

            elif move_name == "Wish":
                state.fields["wish_hp"] = int(attacker.get("max_hp") / 2)
                state.fields["wish_turns"] = 2
                log.append(f"  {attacker.get('species')} made a wish!")

            elif move_name == "Chilly Reception":
                state.fields["weather"] = "Snow"
                state.fields["weather_turns"] = 5
                log.append(f"  {attacker.get('species')} prepared a chilly reception!")
                # Switch logic handled by move execution usually, but we'll flag it
                attacker["should_switch"] = True

            elif move_name == "Power Trick":
                atk = attacker.get("stats", {}).get("atk", 1)
                df = attacker.get("stats", {}).get("def", 1)
                attacker.setdefault("stats", {})["atk"] = df
                attacker["stats"]["def"] = atk
                log.append(
                    f"  {attacker.get('species')} swapped its Attack and Defense!"
                )

            # Defense Curl and Minimize are now handled by the data-driven apply_move_effects
            pass

            # --- Specific Move Logic (Stockpile / Trump Card) ---
            if move_name == "Trump Card":
                pp = attacker.get("_pp_trumpcard", 5)
                attacker["_pp_trumpcard"] = max(0, pp - 1)

            elif move_name == "Stockpile":
                layers = attacker.get("stockpile_layers", 0)
                if layers < 3:
                    attacker["stockpile_layers"] = layers + 1
                    # Explicitly apply boosts since they are in JS code, not data keys
                    Mechanics.apply_boosts(
                        attacker,
                        {"def": 1, "spd": 1},
                        log,
                        source_name="Stockpile",
                        field=state.fields,
                    )
                else:
                    log.append(f"  But it failed (Max Stockpile reached)!")

            elif move_name == "Swallow":
                layers = attacker.get("stockpile_layers", 0)
                if layers > 0:
                    heal_map = {1: 0.25, 2: 0.5, 3: 1.0}
                    heal = int(attacker.get("max_hp") * heal_map[layers])
                    attacker["current_hp"] = min(
                        attacker.get("max_hp"), attacker["current_hp"] + heal
                    )
                    log.append(
                        f"  {attacker.get('species')} swallowed the stockpile and restored HP!"
                    )
                    # Reset
                    Mechanics.apply_boosts(
                        attacker,
                        {"def": -layers, "spd": -layers},
                        log,
                        source_name="Swallow",
                        field=state.fields,
                    )
                    attacker["stockpile_layers"] = 0
                else:
                    log.append(f"  But it failed (No stockpile layers)!")

            elif move_name == "Spit Up":
                layers = attacker.get("stockpile_layers", 0)
                if layers > 0:
                    Mechanics.apply_boosts(
                        attacker,
                        {"def": -layers, "spd": -layers},
                        log,
                        source_name="Spit Up",
                        field=state.fields,
                    )
                    attacker["stockpile_layers"] = 0
                else:
                    log.append(f"  But it failed (No stockpile layers)!")

            mt = move_data.get("terrain")
            if mt:
                t_map = {
                    "electricterrain": "Electric",
                    "grassyterrain": "Grassy",
                    "mistyterrain": "Misty",
                    "psychicterrain": "Psychic",
                }
                final_t = t_map.get(mt, mt)
                state.fields["terrain"] = final_t
                state.fields["terrain_turns"] = 5
                log.append(f"  The terrain became {final_t}!")

            msc = move_data.get("sideCondition")
            if msc:
                # Side conditions like Screens, Spikes are usually on the opponent's side
                # or Tailwind on own side.
                is_hazard = msc in ["spikes", "toxicspikes", "stealthrock", "stickyweb"]
                if is_hazard:
                    opp_side = "ai" if attacker_side == "player" else "player"
                    hazards = state.fields.setdefault("hazards", {}).setdefault(
                        opp_side, []
                    )

                    h_map = {
                        "spikes": "Spikes",
                        "toxicspikes": "Toxic Spikes",
                        "stealthrock": "Stealth Rock",
                        "stickyweb": "Sticky Web",
                    }
                    h_name = h_map.get(msc, msc.title())
                    hazards.append(h_name)
                    log.append(f"  Set {h_name} on {opp_side} side!")
                else:
                    side_to_apply = attacker_side
                    if msc in ["reflect", "lightscreen", "auroraveil"]:
                        side_to_apply = attacker_side

                    sc = state.fields.setdefault("screens", {}).setdefault(
                        side_to_apply, {}
                    )
                    sc_key = msc.lower().replace("_", "").replace(" ", "")
                    if "reflect" in sc_key:
                        sc["reflect"] = 5
                    elif "lightscreen" in sc_key:
                        sc["light_screen"] = 5
                    elif "auroraveil" in sc_key:
                        sc["aurora_veil"] = 5
                    elif "tailwind" in sc_key:
                        state.fields.setdefault("tailwind", {})[attacker_side] = 4
                    log.append(f"  Applied side condition: {msc}")

            mpw = move_data.get("pseudoWeather")
            if mpw:
                if mpw == "trickroom":
                    # 5 turns normally
                    state.fields["trick_room"] = 5
                    log.append(f"  {attacker.get('species')} twisted the dimensions!")
                elif mpw == "magicroom":
                    state.fields["magic_room"] = 5
                    log.append(
                        f"  It created a bizarre area in which held items hold no effect!"
                    )
                elif mpw == "wonderroom":
                    state.fields["wonder_room"] = 5
                    log.append(
                        f"  It created a bizarre area in which Defense and Sp. Def stats are swapped!"
                    )
                elif mpw == "gravity":
                    state.fields["gravity"] = 5
                    log.append(f"  Gravity intensified!")

            # Special Hardcoded cases for unique logic
            if move_name == "Belly Drum":
                if attacker.get("current_hp") > attacker.get("max_hp") / 2:
                    attacker["current_hp"] -= int(attacker.get("max_hp") / 2)
                    attacker.setdefault("stat_stages", {})["atk"] = 6
                    log.append(
                        f"  {attacker.get('species')} cut its own HP and maximized Attack!"
                    )

            if move_name == "Yawn":
                if "yawn" not in defender.get("volatiles", []):
                    defender.setdefault("volatiles", []).append("yawn")
                    log.append(f"  {defender.get('species')} grew drowsy!")

            # Batch 11: Status & Volatiles
            if move_name in ["Haze", "Clear Smog"]:
                # Reset Stats for ALL
                # Haze resets everyone. Clear Smog just target.
                if move_name == "Haze":
                    for mon in [state.player_active, state.ai_active]:
                        mon["stat_stages"] = {}
                    log.append(f"  All stat changes were reset!")
                else:
                    defender["stat_stages"] = {}
                    log.append(
                        f"  {defender.get('species')}'s stat changes were eliminated!"
                    )

            if move_name == "Taunt":
                if self._is_protected_by_aroma_veil(defender, log):
                    pass
                else:
                    defender.setdefault("volatiles", []).append("taunt")
                    defender["taunt_turns"] = (
                        4  # 3 turns effectively? Sim uses 4 and decrements?
                    )
                    log.append(f"  {defender.get('species')} fell for the Taunt!")
                self._check_mental_herb(defender, log)

            if move_name == "Encore":
                last = state.last_moves.get(defender_side)  # Check defender's last move
                if last:
                    if self._is_protected_by_aroma_veil(defender, log):
                        pass
                    else:
                        defender["volatiles"].append("encore")
                        defender["encore_move"] = last
                        defender["encore_turns"] = 4
                        log.append(f"  {defender.get('species')} received an encore!")
                    self._check_mental_herb(defender, log)
                else:
                    log.append(f"  But it failed!")

            if move_name == "Disable":
                last = state.last_moves.get(defender_side)
                if last:
                    if self._is_protected_by_aroma_veil(defender, log):
                        pass
                    else:
                        defender["volatiles"].append("disable")
                        defender["disable_move"] = last
                        defender["disable_turns"] = 4
                        log.append(
                            f"  {defender.get('species')}'s {last} was disabled!"
                        )
                    self._check_mental_herb(defender, log)
                else:
                    log.append(f"  But it failed!")

            if move_name == "Destiny Bond":
                attacker.setdefault("volatiles", []).append("destiny_bond")
                log.append(
                    f"  {attacker.get('species')} is hoping to take its attacker down with it!"
                )

            # Batch 9: Items
            if move_name == "Knock Off":
                # Remove Item (Simplified: No sticky hold check yet)
                item = defender.get("item")
                if item and not self._is_item_unremovable(item, defender):
                    log.append(
                        f"  {defender.get('species')} had its {item} knocked off!"
                    )
                    defender["item"] = None

            if move_name in ["Trick", "Switcheroo"]:
                # Swap check (Sticky Hold etc)
                i1 = attacker.get("item")
                i2 = defender.get("item")
                can_swap = (
                    defender.get("ability") != "Sticky Hold"
                    and attacker.get("ability") != "Sticky Hold"
                )
                if (
                    can_swap
                    and not self._is_item_unremovable(i1, attacker)
                    and not self._is_item_unremovable(i2, defender)
                ):
                    attacker["item"] = i2
                    defender["item"] = i1
                    log.append(
                        f"  {attacker.get('species')} switched items with its target!"
                    )

            # Batch 10: Switch/Pivot
            # Note: Teleport removed - it only works to flee wild battles, not trainer battles
            if move_name in ["U-turn", "Volt Switch", "Flip Turn", "Parting Shot"]:
                # Force Switch for Attacker
                attacker["must_switch"] = True

            if move_name == "Baton Pass":
                attacker["must_switch"] = True
                attacker["baton_pass"] = (
                    True  # Flag to preserve stats logic in perform_switch
                )

            if move_name == "Parting Shot":
                # Drop stats
                stages = defender.setdefault("stat_stages", {})
                stages["atk"] = max(-6, stages.get("atk", 0) - 1)
                stages["spa"] = max(-6, stages.get("spa", 0) - 1)
                log.append(f"  {defender.get('species')}'s Atk/SpA fell!")

            if move_name == "Curse":
                if "Ghost" in attacker.get("types", []):
                    # apply curse volatile
                    vols = defender.setdefault("volatiles", [])
                    if "curse" not in vols:
                        vols.append("curse")
                        log.append(
                            f"  {attacker.get('species')} cursed {defender.get('species')}!"
                        )
                    # cost 50% HP
                    cost = int(attacker.get("max_hp") * 0.5)
                    attacker["current_hp"] = max(0, attacker["current_hp"] - cost)
                    log.append(
                        f"  {attacker.get('species')} cut its own HP to lay a curse! (-{cost})"
                    )
                else:
                    # Standard Curse: -1 Spe, +1 Atk, +1 Def
                    stages = attacker.setdefault("stat_stages", {})
                    stages["spe"] = max(-6, stages.get("spe", 0) - 1)
                    stages["atk"] = min(6, stages.get("atk", 0) + 1)
                    stages["def"] = min(6, stages.get("def", 0) + 1)
                    log.append(
                        f"  {attacker.get('species')}'s Speed fell! Its Attack and Defense rose!"
                    )

            if move_name == "Transform":
                # Copy Species, Types, Stats (except HP), Stat Stages, Ability, Moves
                attacker["species"] = defender.get("species")
                attacker["types"] = defender.get("types", []).copy()
                attacker["stats"] = defender.get("stats", {}).copy()
                attacker["stat_stages"] = defender.get("stat_stages", {}).copy()
                attacker["ability"] = defender.get("ability")
                attacker["moves"] = defender.get("moves", []).copy()
                # Re-enrich to get the new ability's data
                self.enrich_state(state)
                log.append(
                    f"  {attacker.get('species')} transformed into {defender.get('species')}!"
                )

            if move_name == "Memento":
                # Faint User
                attacker["current_hp"] = 0
                log.append(f"  {attacker.get('species')} fainted!")
                # Drop Target Stats
                stages = defender.setdefault("stat_stages", {})
                stages["atk"] = max(-6, stages.get("atk", 0) - 2)
                stages["spa"] = max(-6, stages.get("spa", 0) - 2)
                log.append(f"  {defender.get('species')}'s Atk/SpA falls harshly!")

            if defender["current_hp"] <= 0:
                log.append(f"  {defender.get('species')} fainted!")

                # KO Abilities
                att_ability = attacker.get("ability")
                if att_ability in ["Moxie", "Chilling Neigh", "As One (Glastrier)"]:
                    stages = attacker.setdefault("stat_stages", {})
                    stages["atk"] = min(6, stages.get("atk", 0) + 1)
                    log.append(
                        f"  {attacker.get('species')}'s Attack rose ({att_ability})!"
                    )
                elif att_ability in ["Grim Neigh", "Soul-Heart", "As One (Spectrier)"]:
                    stages = attacker.setdefault("stat_stages", {})
                    stages["spa"] = min(6, stages.get("spa", 0) + 1)
                    log.append(
                        f"  {attacker.get('species')}'s Sp. Atk rose ({att_ability})!"
                    )
                elif att_ability == "Beast Boost":
                    stats = attacker.get("stats", {})
                    best_stat = "atk"
                    best_val = 0
                    for s_key in ["atk", "def", "spa", "spd", "spe"]:
                        if stats.get(s_key, 0) > best_val:
                            best_val = stats[s_key]
                            best_stat = s_key
                    stages = attacker.setdefault("stat_stages", {})
                    stages[best_stat] = min(6, stages.get(best_stat, 0) + 1)
                    log.append(
                        f"  {attacker.get('species')}'s {best_stat} rose (Beast Boost)!"
                    )

            if attacker["current_hp"] <= 0:
                # Note: Memento/Explosion log fainting themselves, but we should ensure abilities trigger.
                # If attacker fainted from recoil/life orb, it's not logged elsewhere yet (except Memento).
                # To avoid double logging, we could check if already handled.
                # But let's just handle abilities.
                def_ability = defender.get("ability")
                if def_ability in ["Grim Neigh", "Soul-Heart"]:
                    stages = defender.setdefault("stat_stages", {})
                    stages["spa"] = min(6, stages.get("spa", 0) + 1)
                    log.append(
                        f"  {defender.get('species')}'s Sp. Atk rose ({def_ability})!"
                    )

            # Field Effects (Rapid Spin, Defog, Brick Break)
            if move_name in ["Rapid Spin", "Mortal Spin"]:
                u_side = "player" if attacker_side == "player" else "ai"
                state.fields["hazards"][u_side] = []
                v_list = [
                    "leech_seed",
                    "bind",
                    "magma_storm",
                    "sand_tomb",
                    "whirlpool",
                    "infestation",
                ]
                for v in v_list:
                    if v in attacker.get("volatiles", []):
                        attacker["volatiles"].remove(v)
                log.append(f"  {attacker.get('species')} blew away hazards!")

            if move_name == "Defog":
                state.fields["hazards"]["player"] = []
                state.fields["hazards"]["ai"] = []
                state.fields["terrain"] = None
                state.fields["terrain_turns"] = 0
                for s in ["player", "ai"]:
                    state.fields["screens"][s] = {
                        "reflect": 0,
                        "light_screen": 0,
                        "aurora_veil": 0,
                    }
                log.append(f"  {attacker.get('species')} blew away the field effects!")

            if move_name in ["Brick Break", "Psychic Fangs"]:
                opp_side = "ai" if attacker_side == "player" else "player"
                sc = state.fields["screens"][opp_side]
                if (
                    sc.get("reflect", 0) > 0
                    or sc.get("light_screen", 0) > 0
                    or sc.get("aurora_veil", 0) > 0
                ):
                    sc["reflect"] = 0
                    sc["light_screen"] = 0
                    sc["aurora_veil"] = 0
                    log.append(f"  The screens were shattered!")

            # Charge / Recharge Logic (Hyper Beam, Solar Beam etc) - Todo

            # --- PARENTAL BOND (Second Hit) logic is already handled in the main hit loop ---
            pass

            # Apply Effects
            if defender["current_hp"] > 0:
                # Update last damage flags for Counter/Mirror Coat/Assurance
                defender["last_dmg_received"] = damage_dealt
                defender["last_dmg_received_cat"] = move_data.get("category")
                defender["took_damage_this_turn"] = True

                # Focus Punch / Beak Blast logic
                if (
                    "focuspunch" in defender.get("volatiles", [])
                    and move_data.get("category") != "Status"
                ):
                    defender["lost_focus"] = True

                if "beakblast" in defender.get("volatiles", []) and move_flags.get(
                    "contact"
                ):
                    if not defender.get("status"):
                        attacker["status"] = "brn"
                        log.append(
                            f"  {attacker.get('species')} was burned by Beak Blast!"
                        )

                if "burningbulwark" in defender.get("volatiles", []) and move_flags.get(
                    "contact"
                ):
                    if not defender.get("status"):
                        attacker["status"] = "brn"
                        log.append(
                            f"  {attacker.get('species')} was burned by Burning Bulwark!"
                        )

                self.apply_move_effects(
                    state,
                    attacker,
                    defender,
                    res,
                    total_damage_dealt,
                    move_name,
                    log,
                    is_crit,
                    effectiveness,
                )

                # 5. Handle Recharge Flag
                if res.get("flags", {}).get("recharge"):
                    attacker.setdefault("volatiles", []).append("mustrecharge")

            # 6. Post-Move Passive Effects
            # Set Choice Lock
            if attacker.get("item") in ["Choice Band", "Choice Specs", "Choice Scarf"]:
                if not attacker.get("locked_move"):
                    attacker["locked_move"] = move_name
        else:
            log.append(
                f"[{attacker_side.upper()}] {attacker.get('species')} used {move_name} (Failed)"
            )

    def _is_status_immune(self, state, mon, status, attacker, log=None):
        ab_rich = mon.get("_rich_ability", {})
        if self._is_ability_suppressed(state, mon, attacker, ab_rich):
            return False

        name = ab_rich.get("name")
        if name == "Comatose":
            if log is not None:
                log.append(
                    f"  {mon.get('species')} is immune to status due to Comatose!"
                )
            return True
        if status == "brn" and name == "Water Veil":
            if log is not None:
                log.append(f"  {mon.get('species')}'s Water Veil prevents burns!")
            return True
        if status == "par" and name == "Limber":
            if log is not None:
                log.append(f"  {mon.get('species')}'s Limber prevents paralysis!")
            return True
        if status == "slp" and name in ["Insomnia", "Vital Spirit"]:
            if log is not None:
                log.append(f"  {mon.get('species')}'s {name} prevents sleep!")
            return True
        if status in ["psn", "tox"] and name in ["Immunity", "Pastel Veil"]:
            if log is not None:
                log.append(f"  {mon.get('species')}'s {name} prevents poisoning!")
            return True
        if status == "frz" and name == "Magma Armor":
            if log is not None:
                log.append(f"  {mon.get('species')}'s Magma Armor prevents freezing!")
            return True
        if status == "confusion" and name == "Own Tempo":
            if log is not None:
                log.append(f"  {mon.get('species')}'s Own Tempo prevents confusion!")
            return True
        if status == "taunt" and name == "Oblivious":
            if log is not None:
                log.append(f"  {mon.get('species')}'s Oblivious prevents taunting!")
            return True
        if status == "flinch" and name == "Inner Focus":
            if log is not None:
                log.append(f"  {mon.get('species')}'s Inner Focus prevents flinching!")
            return True

        # Leaf Guard (Prevents status in Sun)
        if name == "Leaf Guard":
            weather = state.fields.get("weather")
            if weather in ["Sun", "Sunny Day"]:
                if log is not None:
                    log.append(
                        f"  {mon.get('species')} is protected by Leaf Guard in the sun!"
                    )
                return True

        # Type Immunities
        mon_types = mon.get("types", [])
        if status == "brn" and "Fire" in mon_types:
            return True
        if status in ["psn", "tox"] and ("Poison" in mon_types or "Steel" in mon_types):
            if attacker and attacker.get("ability") == "Corrosion":
                if log is not None:
                    log.append(
                        f"  {attacker.get('species')}'s Corrosion allows it to poison {mon.get('species')}!"
                    )
                pass
            else:
                return True
        if status == "par" and "Electric" in mon_types:
            return True

        return False

    def apply_move_effects(
        self,
        state: BattleState,
        attacker,
        defender,
        move_data,
        damage_dealt,
        move_name,
        log,
        is_crit=False,
        effectiveness=1,
    ):
        if not move_data:
            return
        context = {
            "is_crit": is_crit,
            "effectiveness": effectiveness,
            "category": move_data.get("category"),
        }

        attacker_side = "player" if attacker == state.player_active else "ai"
        defender_side = "ai" if attacker_side == "player" else "player"

        # Ensure we have rich data (caller sometimes passes minimal dict or result object)
        if move_name:
            rich_m = self._get_mechanic(move_name, "moves")
            if rich_m:
                # Merge rich data into move_data (keeping any overrides in move_data)
                move_data = {**rich_m, **move_data}

        # Determine target for primary effects (target: self vs target: normal)
        # Determine target for primary effects (target: self vs target: normal)
        # Most primary boosts/status from status moves use the 'target' field.
        target_val = move_data.get("target")
        if move_name == "Acupressure":
            target_val = "self"  # Force self-target

        target_mon = attacker if target_val == "self" else defender

        move_flags = move_data.get("flags", {})

        # Normalize secondaries
        secondaries = []
        raw_secs = move_data.get("secondaries")
        if raw_secs and isinstance(raw_secs, list):
            secondaries.extend(raw_secs)

        raw_sec = move_data.get("secondary")
        if raw_sec:
            if isinstance(raw_sec, list):
                secondaries.extend(raw_sec)
            elif isinstance(raw_sec, dict):
                secondaries.append(raw_sec)

        if not secondaries:
            secondaries = None

        # Shield Dust (Blocks secondary effects of damaging moves)
        if (
            defender.get("ability") == "Shield Dust"
            and move_data.get("category") != "Status"
        ):
            secondaries = None

        sheer_force_suppresses = (
            attacker.get("ability") == "Sheer Force" and secondaries is not None
        )

        # 1. Recoil
        if move_name == "Struggle":
            recoil_dmg = max(1, int(attacker.get("max_hp", 1) / 4))
            attacker["current_hp"] = max(0, attacker.get("current_hp") - recoil_dmg)
            log.append(
                f"  {attacker.get('species')} took recoil damage! (-{recoil_dmg})"
            )

        # Recoil damage from move data
        recoil = move_data.get("recoil")
        if isinstance(recoil, (list, tuple)) and len(recoil) >= 2:
            # Rock Head prevents recoil damage
            if attacker.get("ability") != "Rock Head":
                recoil_dmg = int(damage_dealt * recoil[0] / recoil[1])
                attacker["current_hp"] -= recoil_dmg
                log.append(
                    f"  {attacker.get('species')} took recoil damage (-{recoil_dmg})"
                )

        # 5. Items (Life Orb / Shell Bell) - Moved here to interact with Sheer Force
        # Life Orb: 10% recoil unless Sheer Force active AND move had secondary effects
        if attacker.get("item") == "Life Orb" and damage_dealt > 0:
            if not sheer_force_suppresses and attacker.get("ability") != "Magic Guard":
                loss = max(1, int(attacker.get("max_hp", 100) / 10))
                attacker["current_hp"] -= loss
                log.append(
                    f"  {attacker.get('species')} lost HP due to Life Orb (-{loss})"
                )

        if attacker.get("item") == "Shell Bell" and damage_dealt > 0:
            heal = int(damage_dealt / 8)  # Use damage_dealt from the main hit
            attacker["current_hp"] = min(
                attacker.get("max_hp"), attacker["current_hp"] + heal
            )
            log.append(f"  {attacker.get('species')} healed via Shell Bell! (+{heal})")

        # 2. Drain
        drain = move_data.get("drain")
        if isinstance(drain, (list, tuple)) and len(drain) >= 2:
            heal_amt = int(damage_dealt * drain[0] / drain[1])
            if defender.get("ability") == "Liquid Ooze":
                attacker["current_hp"] -= heal_amt
                log.append(f"  Liquid Ooze hurt {attacker.get('species')}!")
            else:
                if attacker.get("item") == "Big Root":
                    heal_amt = int(heal_amt * 1.3)
                if defender.get("ability") == "Liquid Ooze":
                    attacker["current_hp"] = max(0, attacker["current_hp"] - heal_amt)
                    log.append(
                        f"  {attacker.get('species')}'s health was sucked away by Liquid Ooze (-{heal_amt})!"
                    )
                else:
                    attacker["current_hp"] = min(
                        attacker.get("max_hp"), attacker["current_hp"] + heal_amt
                    )
                    log.append(
                        f"  {attacker.get('species')} drained health (+{heal_amt})"
                    )

        # 3. Main Move Status
        status = move_data.get("status")
        target_vols = defender.get("volatiles", [])
        behind_sub = "substitute" in target_vols
        move_bypasses_sub = (
            move_flags.get("bypasssub")
            or move_flags.get("sound")
            or attacker.get("ability") == "Infiltrator"
        )

        if status and not target_mon.get("status"):
            # Self-targeting status moves (like Rest) bypass defender's substitute
            is_self = target_mon == attacker
            if not is_self and behind_sub and not move_bypasses_sub:
                log.append(
                    f"  {defender.get('species')}'s substitute blocked the status!"
                )
            elif not self._is_status_immune(
                state, target_mon, status, attacker, log=log
            ):
                target_mon["status"] = status
                if status == "slp":
                    target_mon["status_counter"] = 2
                log.append(
                    f"  {target_mon.get('species')} was inflicted with {status}!"
                )
                self._check_status_triggers(state, target_mon, log)
            else:
                log.append(f"  {target_mon.get('species')} is immune to {status}!")

        v_status = move_data.get("volatileStatus")
        if move_name == "Heal Block":
            v_status = "healblock"  # Force it incase data missing
        if v_status:
            is_self = target_mon == attacker
            if not is_self and behind_sub and not move_bypasses_sub:
                log.append(
                    f"  {defender.get('species')}'s substitute blocked the effect!"
                )
            elif not self._is_status_immune(
                state, target_mon, v_status, attacker, log=log
            ):
                v_list = target_mon.setdefault("volatiles", [])
                if v_status not in v_list:
                    v_list.append(v_status)
                    if v_status == "partiallytrapped":
                        target_mon["partiallytrapped_turns"] = 5
                    if v_status == "confusion":
                        target_mon["confusion_turns"] = 3
                    if v_status == "taunt":
                        target_mon["taunt_turns"] = 3
                    if v_status == "healblock":
                        target_mon["healblock_turns"] = 5

                    log.append(f"  {target_mon.get('species')} became {v_status}!")

                    # Synchronize Check (Primary)
                    if (
                        v_status in ["psn", "tox", "brn", "par"]
                        and target_mon.get("ability") == "Synchronize"
                    ):
                        if attacker and not self._is_status_immune(
                            state, attacker, v_status, target_mon
                        ):
                            attacker["status"] = v_status
                            log.append(
                                f"  {target_mon.get('species')}'s Synchronize passed the status back!"
                            )

                    if v_status in [
                        "confusion",
                        "taunt",
                        "encore",
                        "disable",
                        "infatuation",
                    ]:
                        self._check_status_triggers(state, target_mon, log)
                        self._check_mental_herb(target_mon, log)
            else:
                log.append(f"  {target_mon.get('species')} is immune to {v_status}!")

        # 4. Trapping Moves (Mean Look, Block, Spider Web)
        if move_name in ["Mean Look", "Block", "Spider Web"]:
            v_list = defender.setdefault("volatiles", [])
            if "trapped" not in v_list:
                v_list.append("trapped")
                log.append(f"  {defender.get('species')} can no longer escape!")

        # Color Change (Type change on hit)
        if (
            damage_dealt > 0
            and move_data
            and defender.get("ability") == "Color Change"
            and move_data.get("category") != "Status"
        ):
            m_type = move_data.get("type")
            if m_type and m_type not in defender.get("types", []):
                defender["types"] = [m_type]
                log.append(
                    f"  {defender.get('species')} transformed into the {m_type} type!"
                )

        if damage_dealt > 0:
            # Magician Check
            if (
                attacker.get("ability") == "Magician"
                and not attacker.get("item")
                and defender.get("item")
            ):
                it = defender.get("item")
                attacker["item"] = it
                defender["item"] = None
                self.enrich_mon(attacker)
                self.enrich_mon(defender)
                log.append(
                    f"  {attacker.get('species')} stole {defender.get('species')}'s {it} with Magician!"
                )

            # Innards Out Check (if defender fainted)
            if (
                defender.get("current_hp") <= 0
                and defender.get("ability") == "Innards Out"
            ):
                loss = defender.get("_hp_before_hit", 0)
                attacker["current_hp"] = max(0, attacker["current_hp"] - loss)
                log.append(
                    f"  {defender.get('species')} dealt damage with Innards Out (-{loss})!"
                )

        # 3. Secondaries (Chance-based)
        secondaries = move_data.get("secondaries")

        # Stench (10% Flinch on damaging moves)
        if (
            attacker.get("ability") == "Stench"
            and move_data.get("category") != "Status"
        ):
            if not secondaries:
                secondaries = []
            has_flinch = any(
                s.get("volatileStatus") == "flinch"
                for s in secondaries
                if isinstance(s, dict)
            )
            if not has_flinch:
                secondaries.append({"chance": 10, "volatileStatus": "flinch"})
        if not secondaries and move_data.get("secondary"):
            secondaries = [move_data["secondary"]]

        if secondaries and defender["current_hp"] > 0:
            # Sheer Force Suppression
            if attacker.get("ability") == "Sheer Force":
                return

            # Serene Grace check
            chance_mult = 2 if attacker.get("ability") == "Serene Grace" else 1

            for sec in secondaries:
                if not isinstance(sec, dict):
                    continue
                chance = sec.get("chance", 100) / 100
                if random.random() < (chance * chance_mult):
                    if behind_sub and not move_bypasses_sub:
                        # Secondaries are blocked by substitute unless bypassed
                        # Special case: Self-targeting secondaries (like stat boosts) are NOT blocked.
                        # But this loop handles secondaries applied to target usually.
                        pass
                    else:
                        # Apply Status from secondary
                        s = sec.get("status")
                        if s and not defender.get("status"):
                            if not self._is_status_immune(state, defender, s, attacker):
                                defender["status"] = s
                                log.append(
                                    f"  Secondary Effect: {defender.get('species')} was {s}ed!"
                                )

                                # Synchronize Check (Secondary)
                                if (
                                    s in ["psn", "tox", "brn", "par"]
                                    and defender.get("ability") == "Synchronize"
                                ):
                                    if attacker and not self._is_status_immune(
                                        state, attacker, s, defender
                                    ):
                                        attacker["status"] = s
                                        log.append(
                                            f"  {defender.get('species')}'s Synchronize passed the status back!"
                                        )

                        # Apply Volatile from secondary
                        vs = sec.get("volatileStatus") or sec.get("volatiles")
                        if vs:
                            if not self._is_status_immune(
                                state, defender, vs, attacker
                            ):
                                v_list = defender.setdefault("volatiles", [])
                                if vs not in v_list:
                                    v_list.append(vs)
                                    log.append(
                                        f"  Secondary Effect: {defender.get('species')} became {vs}ed!"
                                    )

                        # Apply Boosts from secondary
                        b = sec.get("boosts")
                        if b:
                            # Special case: Fell Stinger only boosts if target was KO'd
                            if move_name == "Fell Stinger":
                                if defender.get("current_hp", 1) > 0:
                                    # Target survived, no boost
                                    continue

                            target = attacker if sec.get("self") else defender
                            # If targeting defender, it's blocked. If targeting self, it's not.
                            if (
                                target == defender
                                and behind_sub
                                and not move_bypasses_sub
                            ):
                                log.append(
                                    f"  Secondary Effect: {defender.get('species')}'s substitute blocked the stat drops!"
                                )
                            else:
                                self._apply_boosts(target, b, log)

        # 4. Primary Boosts (for Status moves)
        p_boosts = move_data.get("boosts")
        if p_boosts:
            is_self = target_mon == attacker
            if not is_self and behind_sub and not move_bypasses_sub:
                log.append(
                    f"  {defender.get('species')}'s substitute blocked the stat drops!"
                )
            else:
                self._apply_boosts(target_mon, p_boosts, log)

        s_data = move_data.get("self")
        if isinstance(s_data, dict):
            s_boosts = s_data.get("boosts")
            if s_boosts:
                self._apply_boosts(attacker, s_boosts, log)
        # If secondaries is a dict (single), wrap it?
        # Smogon TS data: secondaries: null | [...] | { ... }?
        # Raw data has 'secondary: { ... }' or 'secondaries: [ ... ]'?
        # I need to check if I am missing `secondary` key in parser or if I should look for both.
        # For now, let's assume I might have missed 'secondary' key in parser.
        # But `Close Combat`'s `self` worked.

        # Let's fix parser later if Thunderbolt fails.
        # Proceed with logic assuming lists.

        # 5. Field Effects (Awareness Expansion)
        m_data = self._get_mechanic(move_name, "moves")
        if m_data:
            # Weather
            weather = m_data.get("weather")
            if weather:
                state.fields["weather"] = weather
                state.fields["weather_turns"] = 999
                log.append(f"  The weather became {weather}!")

            # Terrain
            terrain = m_data.get("terrain")
            if terrain:
                state.fields["terrain"] = terrain
                turns = 5
                if attacker.get("item") == "Terrain Extender":
                    turns = 8
                state.fields["terrain_turns"] = turns
                log.append(f"  {terrain} Terrain covered the field!")

            # Side Conditions (Screens, Tailwind, etc)
            sc = m_data.get("sideCondition")
            if sc:
                # Hazards
                if sc in ["spikes", "toxicspikes", "stealthrock", "stickyweb"]:
                    h_name = {
                        "spikes": "Spikes",
                        "toxicspikes": "Toxic Spikes",
                        "stealthrock": "Stealth Rock",
                        "stickyweb": "Sticky Web",
                    }.get(sc, sc)
                    state.fields["hazards"][defender_side].append(h_name)
                    log.append(
                        f"  {h_name} were laid on the {defender_side.upper()} side!"
                    )
                # Screens
                elif sc in ["reflect", "lightscreen", "auroraveil"]:
                    screen_key = {
                        "reflect": "reflect",
                        "lightscreen": "light_screen",
                        "auroraveil": "aurora_veil",
                    }.get(sc)
                    state.fields["screens"][attacker_side][screen_key] = 999
                    log.append(
                        f"  {sc.title()} protected the {attacker_side.upper()} side!"
                    )
                # Tailwind
                elif sc == "tailwind":
                    state.fields["tailwind"][attacker_side] = 4
                    log.append(
                        f"  Tailwind blew behind the {attacker_side.upper()} side!"
                    )

            # PseudoWeather (Trick Room, etc)
            pw = m_data.get("pseudoWeather")
            if pw == "trickroom":
                state.fields["trick_room"] = 5
                log.append("  Dimensions were twisted (Trick Room)!")

        # 6. Contact & Properties

        # Universal Contact Logic
        if damage_dealt > 0 and self._makes_contact(move_name, attacker):
            def_ab_name = defender.get("ability")
            def_itemove_name = self._check_mechanic(
                defender.get("item"), "items", "name"
            )

        # Universal Contact Logic (handled by trigger_event for reactive effects)
        pass

        if damage_dealt > 0:
            # Specific triggers for Move Properties
            if is_crit:
                self.trigger_event(
                    state, "onCrit", attacker, defender, log, move_name, damage_dealt
                )

        # 7. Field Overrides
        override_field = {
            "Electric Terrain": "Electric",
            "Grassy Terrain": "Grassy",
            "Misty Terrain": "Misty",
            "Psychic Terrain": "Psychic",
            "Sunny Day": "Sun",
            "Rain Dance": "Rain",
            "Sandstorm": "Sand",
            "Hail": "Hail",
            "Snow": "Snow",
        }

        if move_name in override_field:
            if "Terrain" in move_name:
                state.fields["terrain"] = override_field[move_name]
                state.fields["terrain_turns"] = 5
                log.append(f"  Terrain became {override_field[move_name]}!")
            else:
                state.fields["weather"] = override_field[move_name]
                state.fields["weather_turns"] = 5
                log.append(f"  Weather became {override_field[move_name]}!")
        elif move_name in ["Reflect", "Light Screen", "Aurora Veil"]:
            screen_key = move_name.lower().replace(" ", "_")
            state.fields["screens"][attacker_side][screen_key] = 5
            log.append(f"  {move_name} started on {attacker_side.upper()} side!")
        elif move_name == "Tailwind":
            state.fields["tailwind"][attacker_side] = 4
            log.append(f"  Tailwind started on {attacker_side.upper()} side!")
        elif move_name == "Trick Room":
            if state.fields.get("trick_room", 0) > 0:
                state.fields["trick_room"] = 0
                log.append(f"  The dimensions returned to normal!")
            else:
                state.fields["trick_room"] = 5
                log.append(f"  Twisted the dimensions!")
        elif move_name in ["Stealth Rock", "Spikes", "Toxic Spikes", "Sticky Web"]:
            h_list = state.fields["hazards"][defender_side]
            if move_name == "Spikes" and h_list.count("Spikes") < 3:
                h_list.append("Spikes")
                log.append(f"  Spikes set on {defender_side.upper()} side!")
            elif move_name == "Toxic Spikes" and h_list.count("Toxic Spikes") < 2:
                h_list.append("Toxic Spikes")
                log.append(f"  Toxic Spikes set on {defender_side.upper()} side!")
            elif move_name not in h_list:
                h_list.append(move_name)
                log.append(f"  {move_name} set on {defender_side.upper()} side!")

        # 6. Pivot Moves
        if (
            move_name in ["U-turn", "Volt Switch", "Flip Turn", "Parting Shot"]
            and damage_dealt > 0
        ):
            log.append(f"  {attacker.get('species')} is switching out!")
            attacker["must_switch"] = True

    def enrich_state(self, state: BattleState):
        """
        Attaches rich data objects directly to the Pokemon state dictionaries
        for faster access during simulation.
        """
        mons = [state.player_active, state.ai_active]
        mons.extend(state.player_party)
        mons.extend(state.ai_party)

        for mon in mons:
            if not mon:
                continue

            # Ability
            ab_name = mon.get("ability")
            if ab_name and isinstance(ab_name, str):
                key = ab_name.lower().replace(" ", "").replace("-", "").replace("'", "")
                mon["_rich_ability"] = self.rich_data["abilities"].get(key)

            # Item
            itemove_name = mon.get("item")
            if itemove_name and isinstance(itemove_name, str):
                key = (
                    itemove_name.lower()
                    .replace(" ", "")
                    .replace("-", "")
                    .replace("'", "")
                )
                mon["_rich_item"] = self.rich_data["items"].get(key)

            # Moves
            if "moves" in mon:
                rich_moves = {}
                for m in mon["moves"]:
                    if isinstance(m, str):
                        key = (
                            m.lower().replace(" ", "").replace("-", "").replace("'", "")
                        )
                        rd = self.rich_data["moves"].get(key)
                        if rd:
                            rich_moves[m] = rd
                mon["_rich_moves"] = rich_moves

    def _get_mechanic(self, source_name, source_type):
        """
        Helper to get the rich data object for a move, ability, or item.
        source_type: 'moves', 'abilities', 'items'
        """
        if not source_name:
            return None
        key = (
            str(source_name).lower().replace(" ", "").replace("-", "").replace("'", "")
        )
        return self.rich_data.get(source_type, {}).get(key)

    def _check_mechanic(self, source, source_type, key):
        """
        Check if a specific flag/property exists in the rich data.
        Returns the value if found, None (or False) otherwise.

        'source' can be the name (str) OR the Pokemon object (dict) if we want to look up its ability/item.
        Actually, existing calls pass names (e.g. move_name).
        To leverage fast path, we need to pass the enriched object or look it up differently.

        Refactoring Plan:
        If 'source' is a Pokemon object (dict), we assume we want its Ability or Item data?
        Ambiguous. source_type must tell us.

        If source_type == 'abilities' and source is dict: return source.get('_rich_ability', {}).get(key)
        If source_type == 'items' and source is dict: return source.get('_rich_item', {}).get(key)
        """
        # Fast Path for Enriched Objects
        if isinstance(source, dict):
            if source_type == "abilities":
                rd = source.get("_rich_ability")
                if rd:
                    return rd.get(key)
            elif source_type == "items":
                rd = source.get("_rich_item")
                if rd:
                    return rd.get(key)

        # Standard Lookup (String Name)
        source_name = source
        if isinstance(source, dict):
            # If dict passed but no rich data (or mismatched type), fallback to getting name string
            if source_type == "abilities":
                source_name = source.get("ability")
            elif source_type == "items":
                source_name = source.get("item")
            else:
                source_name = source.get("name")  # Generic?

        # DEBUG
        # print(f"DEBUG check_mechanic: SourceType={source_type} SourceName={source_name} Key={key}")

        data = self._get_mechanic(source_name, source_type)
        if data:
            return data.get(key)
        return None

    def _check_status_triggers(self, state, mon, log):
        item = mon.get("item")
        if not item or mon.get("ability") == "Klutz":
            return

        cured = False
        if item == "Lum Berry" and mon.get("status"):
            log.append(
                f"  {mon.get('species')} ate its Lum Berry and cured its status!"
            )
            mon["status"] = None
            cured = True
        elif item == "Persim Berry" and "confusion" in mon.get("volatiles", []):
            log.append(
                f"  {mon.get('species')} ate its Persim Berry and snapped out of confusion!"
            )
            mon["volatiles"].remove("confusion")
            cured = True
        elif item == "Mental Herb":
            # Natural Gift or other status cure? Herb usually handles mental.
            # Status cure berries usually handle standard.
            pass

        # Generic status berries (Aspear, Cheri, Chesto, Pecha, Rawst)
        berry_map = {
            "Cheri Berry": "par",
            "Chesto Berry": "slp",
            "Pecha Berry": "psn",
            "Rawst Berry": "brn",
            "Aspear Berry": "frz",
        }
        if item in berry_map and mon.get("status") == berry_map[item]:
            log.append(f"  {mon.get('species')} ate its {item} and cured its status!")
            mon["status"] = None
            cured = True

        if cured:
            mon["item"] = None
            if mon.get("ability") == "Cheek Pouch":
                heal_amt = mon.get("max_hp", 0) // 3
                mon["current_hp"] = min(
                    mon.get("max_hp", 0), mon.get("current_hp", 0) + heal_amt
                )
                log.append(
                    f"  {mon.get('species')}'s Cheek Pouch restored HP! (+{heal_amt})"
                )

            if mon.get("ability") == "Unburden":
                mon["unburden_active"] = True
                log.append(f"  {mon.get('species')} became unburdened!")

    def _is_protected_by_aroma_veil(self, mon, log=None):
        if mon.get("ability") == "Aroma Veil":
            if log:
                log.append(f"  {mon.get('species')} is protected by Aroma Veil!")
            return True
        return False

    def _check_mental_herb(self, mon, log):
        if mon.get("item") == "Mental Herb":
            vols = mon.get("volatiles", [])
            mental_vols = [
                "taunt",
                "encore",
                "disable",
                "infatuation",
                "healblock",
                "torment",
            ]
            triggered = False
            for v in mental_vols:
                if v in vols:
                    vols.remove(v)
                    triggered = True

            if triggered:
                log.append(
                    f"  {mon.get('species')} used its Mental Herb to cure mental effects!"
                )
                mon["item"] = None
                if mon.get("ability") == "Unburden":
                    mon["unburden_active"] = True
                    log.append(f"  {mon.get('species')} became unburdened!")

    def _check_hp_triggers(self, state, mon, log):
        """
        Checks for HP-based triggers like berries or abilities.
        """
        if not mon or mon.get("current_hp", 0) <= 0:
            return

        item_name = mon.get("item")
        ability_name = mon.get("ability")
        max_hp = mon.get("max_hp", 1)
        current_hp = mon.get("current_hp", 0)
        hp_ratio = current_hp / max_hp

        # Emergency Exit / Wimp Out
        if ability_name in ["Emergency Exit", "Wimp Out"] and hp_ratio <= 0.5:
            if not mon.get("_emergency_exit_triggered"):
                mon["_emergency_exit_triggered"] = True
                log.append(
                    f"  {mon.get('species')}'s {ability_name} triggered! It wants to switch out!"
                )
                mon["must_switch"] = True

        has_gluttony = ability_name == "Gluttony"

        # Berries and Berry Juice
        if item_name and ability_name != "Klutz":
            # Unnerve Check
            opponent = (
                state.ai_active if mon == state.player_active else state.player_active
            )
            if opponent and opponent.get("ability") in [
                "Unnerve",
                "As One (Glastrier)",
                "As One (Spectrier)",
            ]:
                pass  # Unnerve blocks berries
            else:
                # Eat Berry
                consumed = False
                heal_pct = 0
                rich_item = mon.get("_rich_item", {})
                if rich_item.get("isBerry"):
                    # This return here would prevent any berry from being eaten if Unnerve is NOT active.
                    # Assuming the intent was to proceed with berry checks if Unnerve is not active.
                    # The original code had a 'return' if Unnerve was active and it was a berry.
                    # This new structure implies that if it's a berry and Unnerve is NOT active, we should process it.
                    # I will remove this 'return' to allow the berry processing below to occur.
                    pass  # Allow berry processing if not unnerved
                else:
                    # If it's not a berry, but it's an item (like Berry Juice), proceed.
                    # The original code had a check for Berry Juice outside the rich_item.get('isBerry') block.
                    pass

            if hp_ratio <= 0.5 or (hp_ratio <= 0.25 and has_gluttony):
                # 1. Berry Juice (Heals 20 HP) - No Gluttony boost needed logic-wise, usually standard
                if item_name == "Berry Juice":
                    heal_amt = 20
                    if current_hp < max_hp:
                        mon["current_hp"] = min(max_hp, current_hp + heal_amt)
                        mon["item"] = None
                        log.append(
                            f"  {mon.get('species')} restored health using its Berry Juice!"
                        )
                        return

                # 2. Berries
                if "Berry" in item_name:
                    # Parse rich data triggers?
                    # Simplified hardcoded map for common berries
                    # Simplified hardcoded map for common berries
                    heal_pct = 0
                    heal_amt = 0
                    if item_name == "Oran Berry":
                        heal_amt = 10
                    elif item_name == "Sitrus Berry":
                        heal_pct = 0.25

                    if heal_pct > 0:
                        heal_amt = int(max_hp * heal_pct)

                    if heal_amt > 0:
                        if ability_name == "Ripen":
                            heal_amt *= 2  # Ripen doubles healing
                        if current_hp < max_hp:
                            mon["current_hp"] = min(max_hp, current_hp + heal_amt)
                            mon["item"] = None
                            mon["_last_consumed_item"] = item_name
                            log.append(
                                f"  {mon.get('species')} ate its {item_name} (+{heal_amt})!"
                            )

                            if ability_name == "Cheek Pouch":
                                cp_heal = max_hp // 3
                                mon["current_hp"] = min(
                                    max_hp, mon["current_hp"] + cp_heal
                                )
                                log.append(
                                    f"  {mon.get('species')}'s Cheek Pouch restored HP! (+{cp_heal})"
                                )

                            if ability_name == "Unburden":
                                mon["unburden_active"] = True
                                log.append(f"  {mon.get('species')} became unburdened!")
                                return
                    elif item_name in [
                        "Figy Berry",
                        "Wiki Berry",
                        "Mago Berry",
                        "Aguav Berry",
                        "Iapapa Berry",
                    ]:
                        # Pinch Berries (Gen 7+ heal 1/3, confuse if wrong nature)
                        # Simplified: just heal 1/3, no confusion check for now
                        heal_amt = int(max_hp / 3)
                        if ability_name == "Ripen":
                            heal_amt *= 2  # Ripen doubles healing
                        if current_hp < max_hp:
                            mon["current_hp"] = min(max_hp, current_hp + heal_amt)
                            mon["item"] = None
                            mon["_last_consumed_item"] = item_name
                            log.append(
                                f"  {mon.get('species')} ate its {item_name} (+{heal_amt})!"
                            )

                            if ability_name == "Cheek Pouch":
                                cp_heal = max_hp // 3
                                mon["current_hp"] = min(
                                    max_hp, mon["current_hp"] + cp_heal
                                )
                                log.append(
                                    f"  {mon.get('species')}'s Cheek Pouch restored HP! (+{cp_heal})"
                                )

                            if ability_name == "Unburden":
                                mon["unburden_active"] = True
                                log.append(f"  {mon.get('species')} became unburdened!")
                            return
                    elif item_name == "Salac Berry" and hp_ratio <= 0.25:
                        # Speed boost
                        val = 2 if ability_name == "Ripen" else 1
                        Mechanics.apply_boosts(
                            mon, {"spe": val}, log, source_name=item_name
                        )
                        mon["item"] = None
                        mon["_last_consumed_item"] = item_name
                        log.append(f"  {mon.get('species')} ate its {item_name}!")
                        if ability_name == "Unburden":
                            mon["unburden_active"] = True
                            log.append(f"  {mon.get('species')} became unburdened!")
                        return
                    elif item_name == "Liechi Berry" and hp_ratio <= 0.25:
                        val = 2 if ability_name == "Ripen" else 1
                        Mechanics.apply_boosts(
                            mon, {"atk": val}, log, source_name=item_name
                        )
                        mon["item"] = None
                        mon["_last_consumed_item"] = item_name
                        log.append(f"  {mon.get('species')} ate its {item_name}!")
                        if ability_name == "Unburden":
                            mon["unburden_active"] = True
                        return
                    elif item_name == "Ganlon Berry" and hp_ratio <= 0.25:
                        val = 2 if ability_name == "Ripen" else 1
                        Mechanics.apply_boosts(
                            mon, {"def": val}, log, source_name=item_name
                        )
                        mon["item"] = None
                        mon["_last_consumed_item"] = item_name
                        log.append(f"  {mon.get('species')} ate its {item_name}!")
                        if ability_name == "Unburden":
                            mon["unburden_active"] = True
                        return
                    elif item_name == "Apicot Berry" and hp_ratio <= 0.25:
                        val = 2 if ability_name == "Ripen" else 1
                        Mechanics.apply_boosts(
                            mon, {"spd": val}, log, source_name=item_name
                        )
                        mon["item"] = None
                        mon["_last_consumed_item"] = item_name
                        log.append(f"  {mon.get('species')} ate its {item_name}!")
                        if ability_name == "Unburden":
                            mon["unburden_active"] = True
                        return
                    elif item_name == "Petaya Berry" and hp_ratio <= 0.25:
                        val = 2 if ability_name == "Ripen" else 1
                        Mechanics.apply_boosts(
                            mon, {"spa": val}, log, source_name=item_name
                        )
                        mon["item"] = None
                        mon["_last_consumed_item"] = item_name
                        log.append(f"  {mon.get('species')} ate its {item_name}!")
                        if ability_name == "Unburden":
                            mon["unburden_active"] = True
                        return
                    elif item_name == "Starf Berry" and hp_ratio <= 0.25:
                        # Random stat +2
                        stats = ["atk", "def", "spa", "spd", "spe"]
                        stat = random.choice(stats)
                        val = 4 if ability_name == "Ripen" else 2
                        Mechanics.apply_boosts(
                            mon, {stat: val}, log, source_name=item_name
                        )
                        mon["item"] = None
                        mon["_last_consumed_item"] = item_name
                        log.append(f"  {mon.get('species')} ate its {item_name}!")
                        if ability_name == "Unburden":
                            mon["unburden_active"] = True
                        return
        # Abilities
        if ability_name == "Torrent" and hp_ratio <= 0.33:
            if not mon.get("torrent_active"):
                mon["torrent_active"] = True
                log.append(f"  {mon.get('species')}'s Torrent activated!")
        elif ability_name == "Blaze" and hp_ratio <= 0.33:
            if not mon.get("blaze_active"):
                mon["blaze_active"] = True
                log.append(f"  {mon.get('species')}'s Blaze activated!")
        elif ability_name == "Overgrow" and hp_ratio <= 0.33:
            if not mon.get("overgrow_active"):
                mon["overgrow_active"] = True
                log.append(f"  {mon.get('species')}'s Overgrow activated!")
        elif ability_name == "Swarm" and hp_ratio <= 0.33:
            if not mon.get("swarm_active"):
                mon["swarm_active"] = True
                log.append(f"  {mon.get('species')}'s Swarm activated!")
        elif ability_name == "Defiant" and mon.get("stat_stages", {}).get("atk", 0) < 6:
            # This is typically triggered by stat drops from opponent, not HP.
            # But if it's a general HP trigger check, it might be here.
            # For now, assuming it's not HP-based.
            pass
        elif (
            ability_name == "Berserk"
            and hp_ratio <= 0.5
            and not mon.get("berserk_active")
        ):
            # Berserk activates when HP drops to 50% or below
            # Need to check if it dropped *to* or *below* from *above*
            # This check is usually done in onDamagingHit, not here.
            # For simplicity, if it's below 50% and not active, activate.
            mon["berserk_active"] = True
            Mechanics.apply_boosts(mon, {"spa": 1}, log, source_name="Berserk")
            log.append(f"  {mon.get('species')}'s Berserk activated!")

    def execute_post_damage_reactions(
        self, state, attacker, defender, damage_applied, move_data, log
    ):
        """
        Handles reaction abilities, items, and berries after damage is dealt.
        """
        if defender.get("current_hp", 0) <= 0:
            return

        rich_ab = defender.get("_rich_ability")
        rich_item = defender.get("_rich_item")

        # 1. Damaging Hit Reactions (Stamina, Justified, Water Compaction, Berserk)
        if damage_applied > 0:
            if rich_ab:
                # Type-specific triggers (Justified: Dark, Water Compaction: Water)
                t_type = rich_ab.get("triggerType")
                move_type = move_data.get("type")

                if t_type and move_type == t_type:
                    boosts = rich_ab.get("boosts")
                    if boosts:
                        Mechanics.apply_boosts(
                            defender, boosts, log, f"{rich_ab['name']} ability"
                        )

                # General onDamagingHit (Stamina)
                elif rich_ab.get("onDamagingHit"):
                    boosts = rich_ab.get("boosts")
                    if boosts:
                        Mechanics.apply_boosts(
                            defender, boosts, log, f"{rich_ab['name']} ability"
                        )

                # Threshold-based (Berserk)
                threshold = rich_ab.get("threshold")
                if threshold:
                    hp_before = defender["current_hp"] + damage_applied
                    hp_now = defender["current_hp"]
                    max_hp = defender.get("max_hp", 1)
                    if hp_now <= max_hp * threshold < hp_before:
                        boosts = rich_ab.get("boosts")
                        if boosts:
                            Mechanics.apply_boosts(
                                defender, boosts, log, f"{rich_ab['name']} ability"
                            )

            # Critical Hit Triggers (Anger Point)
            if rich_ab and rich_ab.get("onCrit") and move_data.get("crit"):
                boosts = rich_ab.get("boosts")
                if boosts:
                    Mechanics.apply_boosts(
                        defender, boosts, log, f"{rich_ab['name']} ability"
                    )

        # 2. Berries (HP/Status)
        itemove_name = defender.get("item")
        if rich_item and rich_item.get("isBerry"):
            max_hp = defender.get("max_hp", 1)
            hp_now = defender["current_hp"]

            # HP Recovery Berries (Sitrus, Oran)
            heal = rich_item.get("healRatio")
            if heal:
                # Trigger threshold (Usually 0.5 for Sitrus in R&B)
                th = rich_item.get("threshold", 0.5)
                # Gluttony check
                if rich_ab and rich_ab.get("name") == "Gluttony":
                    th = 0.5

                if hp_now <= max_hp * th:
                    num, den = heal[0], heal[1]
                    heal_amt = int(max_hp * num / den)
                    defender["current_hp"] = min(
                        max_hp, defender["current_hp"] + heal_amt
                    )
                    log.append(
                        f"  {defender.get('species')} ate its {itemove_name} (+{heal_amt})!"
                    )
                    defender["item"] = None
                    
                    # Cheek Pouch
                    if rich_ab and rich_ab.get("name") == "Cheek Pouch":
                        cp_amt = int(max_hp / 3)
                        defender["current_hp"] = min(max_hp, defender["current_hp"] + cp_amt)
                        log.append(f"  {defender.get('species')}'s Cheek Pouch restored specific HP (+{cp_amt})!")
                    
                    # Unburden check
                    if rich_ab and rich_ab.get("name") == "Unburden":
                        defender["unburden_active"] = True
                        log.append(f"  {defender.get('species')} became unburdened!")

        # 3. Item-based Reactions (Red Card, Eject Button)
        if damage_applied > 0:
            if itemove_name == "Red Card":
                log.append(f"  {defender.get('species')} showed its Red Card!")
                attacker["must_switch"] = True
                defender["item"] = None
            elif itemove_name == "Eject Button":
                log.append(f"  {defender.get('species')} used its Eject Button!")
                defender["must_switch"] = True
                defender["item"] = None

    def _is_grounded(self, mon, state):
        is_flying = "Flying" in mon.get("types", [])
        has_levitate = mon.get("ability") == "Levitate"
        has_balloon = mon.get("item") == "Air Balloon"
        is_grounded = not (is_flying or has_levitate or has_balloon)

        # Iron Ball or Gravity grounds the user
        if mon.get("item") == "Iron Ball":
            is_grounded = True
        if state.fields.get("gravity", 0) > 0:
            is_grounded = True

        # Ingrain / Smack Down
        vols = mon.get("volatiles", [])
        if "ingrain" in vols or "smackdown" in vols or "thousandarrows" in vols:
            is_grounded = True

        return is_grounded

    def _is_trapped(self, mon, state):
        # Shed Shell -> Never blocked
        if mon.get("item") == "Shed Shell":
            return False

        # Ghost types cannot be trapped (Gen 6+)
        if "Ghost" in mon.get("types", []):
            return False

        # Check volatiles
        volatiles = mon.get("volatiles", [])
        trapping_volatiles = [
            "meanlook",
            "block",
            "spiderweb",
            "trapped",
            "partiallytrapped",
            "ingrain",
            "jawlock",
            "octolock",
        ]
        for v in trapping_volatiles:
            if v in volatiles:
                return True

        # Check opponent ability
        side = "player" if mon == state.player_active else "ai"
        opponent = state.ai_active if side == "player" else state.player_active
        opp_ab = opponent.get("ability")

        # Shadow Tag prevents non-Shadow Tag pokemon from switching
        if opp_ab == "Shadow Tag" and mon.get("ability") != "Shadow Tag":
            return True
        # Arena Trap affects grounded pokemon
        if opp_ab == "Arena Trap" and self._is_grounded(mon, state):
            return True
        # Magnet Pull affects Steel types
        if opp_ab == "Magnet Pull" and "Steel" in mon.get("types", []):
            return True

        return False
