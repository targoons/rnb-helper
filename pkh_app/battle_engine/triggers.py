
from typing import Dict, List, Optional
import random
import logging
from .state import BattleState
from pkh_app.mechanics import Mechanics

class TriggerHandler:
    def __init__(self, enricher, rich_data):
        self.enricher = enricher
        self.rich_data = rich_data

    def trigger_event(
        self,
        state: BattleState,
        event_name,
        source_mon,
        target_mon,
        log,
        move_name=None,
        damage=0,
        context=None,
    ):
        """
        Processes a reactive event (e.g., onDamagingHit, onDamage) for both sides.
        """
        if context is None:
            context = {}

        # 1. Source (Attacker/Active side) - Abilities
        self._process_trigger(
            state,
            source_mon,
            event_name,
            source_mon,
            target_mon,
            log,
            move_name,
            damage,
            context,
        )
        # 2. Target (Defender/Reactive side) - Abilities
        self._process_trigger(
            state,
            target_mon,
            event_name,
            target_mon,
            source_mon,
            log,
            move_name,
            damage,
            context,
        )

    def _process_trigger(
        self,
        state,
        trigger_mon,
        event_name,
        owner,
        other,
        log,
        move_name,
        damage,
        context,
    ):
        # 1. Ability Logic
        ab_rich = trigger_mon.get("_rich_ability", {})
        if ab_rich and not self._is_ability_suppressed(
            state, trigger_mon, other, ab_rich
        ):
            self._apply_rich_trigger(
                ab_rich, owner, other, event_name, log, move_name, context, state
            )

        # 2. Item
        self._apply_rich_trigger(
            trigger_mon.get("_rich_item", {}),
            owner,
            other,
            event_name,
            log,
            move_name,
            context,
            state
        )

    def _is_ability_suppressed(self, state, mon, attacker, rich_ab):
        if not rich_ab:
            return True
        if "gastroacid" in mon.get("volatiles", []):
            return True

        # Neutralizing Gas
        all_active = [state.player_active, state.ai_active]
        for m in all_active:
            if (
                m.get("ability") == "Neutralizing Gas"
                and rich_ab.get("name") != "Neutralizing Gas"
            ):
                return True

        # Mold Breaker
        if attacker and attacker != mon:
            att_ab = attacker.get("ability", "")
            if att_ab in ["Mold Breaker", "Teravolt", "Turboblaze"]:
                if rich_ab.get("flags", {}).get("breakable"):
                    return True
        return False

    def _apply_rich_trigger(
        self, rich_data, owner, other, event_key, log, move_name=None, context=None, state=None
    ):
        if not rich_data:
            return
        if context is None:
            context = {}
        
        move_data = None
        if move_name:
            slug = move_name.lower().replace(" ", "").replace("-", "").replace("'", "")
            move_data = self._get_mechanic(slug, "moves")

        trigger = rich_data.get(event_key)
        name = rich_data.get("name", "Unknown")

        if not trigger:
            # Hardcoded fallbacks for incomplete JSON
            if event_key == "onDamagingHit" and name in [
                "Color Change",
                "Wandering Spirit",
                "Effect Spore",
                "Cute Charm",
                "Cursed Body",
                "Sturdy",
                "Static",
                "Rough Skin",
                "Iron Barbs",
                "Rocky Helmet",
                "Ice Face",
                "Cotton Down",
                "Pickpocket",
                "Poison Touch",
                "Poison Point",
                "Flame Body",
                "Cute Charm",
                "Steam Engine",
                "Water Compaction",
            ]:
                trigger = True
            else:
                return

        # Super Effective required?
        if name in ["Weakness Policy", "Enigma Berry"]:
            if context.get("effectiveness", 1) <= 1:
                return

        # Critical Hit required?
        if event_key == "onCrit" or name == "Anger Point":
            if not context.get("is_crit"):
                return

        # Check Contact requirement for certain triggers
        if event_key == "onDamagingHit":
            # Some triggers only fire on contact (Rough Skin, Rocky Helmet)
            # We need a way to know if this mechanic requires contact.
            # Usually 'onDamagingHit' combined with certain flags or just known mechanics.
            if name in [
                "Rough Skin",
                "Iron Barbs",
                "Rocky Helmet",
                "Static",
                "Flame Body",
                "Poison Point",
                "Effect Spore",
                "Cute Charm",
                "Pickpocket",
            ]:
                if not self._makes_contact(move_name, other):  # 'other' is the attacker
                    return

            if name == "Ice Face" and event_key == "onDamagingHit":
                if context and context.get("category") == "Physical":
                    if owner.get("species", "").strip() == "Eiscue":
                        self.enricher._perform_form_change(owner, "eiscuenoice", log, state)
                        log.append(f"  Eiscue's Ice Face deactivated!")



        # Data might be in sibling keys if trigger is boolean, or inside trigger if it's a dict
        src = trigger if isinstance(trigger, dict) else rich_data

        # 1. Boosts
        if "boosts" in src and name != "Cotton Down":
            stages = owner.setdefault("stat_stages", {})
            for stat, val in src["boosts"].items():
                # Maximize for Anger Point
                if val == 12:
                    val = 12  # will be capped at 6 anyway or handled specially

                prev = stages.get(stat, 0)
                stages[stat] = max(-6, min(6, prev + val))
                if stages[stat] != prev:
                    term = "rose" if val > 0 else "fell"
                    log.append(
                        f"  {owner.get('species')}'s {stat.upper()} {'sharply ' if abs(val)>=2 else ''}{term} (Trigger: {name})!"
                    )

        # 1.5. Cotton Down (Specific)
        if name == "Cotton Down":
            # Cotton Down lowers stats of ALL other Pokemon.
            Mechanics.apply_boosts(other, {"spe": -1}, log, source_name="Cotton Down")

        # 2. Damage to Other (Rough Skin, Iron Barbs, Rocky Helmet)
        # Using healRatio or specific damage logic
        if name in ["Rough Skin", "Iron Barbs", "Rocky Helmet"]:
            ratio = 8 if "Skin" in name or "Barbs" in name else 6
            dmg = int(other.get("max_hp") / ratio)
            other["current_hp"] = max(0, other["current_hp"] - dmg)
            log.append(f"  {other.get('species')} was hurt by {name} (-{dmg})!")

        # 3. Status Effects (Static, Flame Body, Effect Spore)
        status_map = {"Static": "par", "Flame Body": "brn", "Poison Point": "psn"}
        if name in status_map and not other.get("status"):
            r = random.random()
            print(f"DEBUG: Checking {name} for {other.get('species')}. Random: {r}")
            if r < 0.3:
                other["status"] = status_map[name]
                log.append(f"  {other.get('species')} was affected by {name}!")

        if name == "Effect Spore" and other.get("status") == None:
            if random.random() < 0.3:
                # 1/3 each for PSN, PAR, SLP
                roll = random.random()
                if roll < 0.33:
                    other["status"] = "psn"
                elif roll < 0.66:
                    other["status"] = "par"
                else:
                    other["status"] = "slp"
                log.append(f"  {other.get('species')} was affected by Effect Spore!")

        if name == "Poison Touch" and other.get("status") == None:
            if self._makes_contact(move_name, owner):  # owner attacked 'other'
                if random.random() < 0.3:
                    other["status"] = "psn"
                    log.append(
                        f"  {other.get('species')} was poisoned by Poison Touch!"
                    )

        if name == "Cute Charm" and other.get("status") == None:
            if random.random() < 0.3:
                # Simplified infatuation as a volatile
                vols = other.setdefault("volatiles", [])
                if "attract" not in vols:
                    vols.append("attract")
                    log.append(
                        f"  {other.get('species')} fell in love with Cute Charm!"
                    )

        if name == "Pickpocket" and not owner.get("item") and other.get("item"):
            if self._makes_contact(move_name, other):  # other attacked owner
                it = other.get("item")
                owner["item"] = it
                other["item"] = None
                self.enricher.enrich_mon(owner)
                self.enricher.enrich_mon(other)
                log.append(
                    f"  {owner.get('species')} stole {other.get('species')}'s {it} with Pickpocket!"
                )

        if name == "Color Change" and move_name:
            slug = move_name.lower().replace(" ", "").replace("-", "").replace("'", "")
            move_data = self._get_mechanic(slug, "moves")
            if move_data:
                move_type = move_data.get("type")
                if move_type and move_type not in owner.get("types", []):
                    owner["types"] = [move_type]
                    log.append(
                        f"  {owner.get('species')}'s Color Change made it {move_type} type!"
                    )

        if name == "Gooey" or name == "Tangling Hair":
            if self._makes_contact(move_name, other):
                Mechanics.apply_boosts(other, {"spe": -1}, log, source_name=name)

        if name == "Cursed Body":
            if random.random() < 0.3:
                # Aroma Veil Check
                if self._is_protected_by_aroma_veil(other, log):
                    pass
                else:
                    # Disable move
                    vols = other.setdefault("volatiles", [])
                    if "disable" not in vols:
                        vols.append("disable")
                        other["disable_move"] = move_name
                        other["disable_turns"] = 4
                        log.append(
                            f"  {other.get('species')}'s {move_name} was disabled by Cursed Body!"
                        )

        if name == "Stamina":
            Mechanics.apply_boosts(owner, {"def": 1}, log, source_name="Stamina")

        if name == "Justified" and move_data and move_data.get("type") == "Dark":
            Mechanics.apply_boosts(owner, {"atk": 1}, log, source_name="Justified")

        if (
            name == "Rattled"
            and move_data
            and move_data.get("type") in ["Dark", "Bug", "Ghost"]
        ):
            Mechanics.apply_boosts(owner, {"spe": 1}, log, source_name="Rattled")
        if (
            name == "Steam Engine"
            and move_data
            and move_data.get("type") in ["Fire", "Water"]
        ):
            Mechanics.apply_boosts(owner, {"spe": 6}, log, source_name="Steam Engine")

        if (
            name == "Weak Armor"
            and move_data
            and move_data.get("category") == "Physical"
        ):
            Mechanics.apply_boosts(
                owner, {"def": -1, "spe": 2}, log, source_name="Weak Armor"
            )

        if name == "Mummy":
            if self._makes_contact(move_name, other):
                if other.get("ability") != "Mummy":
                    other["ability"] = "Mummy"
                    other["_rich_ability"] = rich_data
                    log.append(f"  {other.get('species')}'s ability became Mummy!")

        if name == "Wandering Spirit":
            if self._makes_contact(move_name, other):
                # Swap abilities
                owner_ab = owner.get("ability")
                other_ab = other.get("ability")
                owner["ability"], other["ability"] = other_ab, owner_ab
                owner["_rich_ability"], other["_rich_ability"] = other.get(
                    "_rich_ability"
                ), owner.get("_rich_ability")
                log.append(
                    f"  {owner.get('species')} and {other.get('species')} swapped abilities!"
                )

        if name == "Sand Spit":
            if state:
                state.fields["weather"] = "Sandstorm"
                state.fields["weather_turns"] = 5
                log.append(f"  {owner.get('species')}'s Sand Spit whipped up a sandstorm!")

        if name == "Water Compaction" and move_data and move_data.get("type") == "Water":
            Mechanics.apply_boosts(
                owner, {"def": 2}, log, source_name="Water Compaction"
            )

        if name == "Perish Body":
            if self._makes_contact(move_name, other):
                vols = owner.setdefault("volatiles", [])
                other_vols = other.setdefault("volatiles", [])
                if (
                    "perish3" not in vols
                    and "perish2" not in vols
                    and "perish1" not in vols
                ):
                    vols.append("perish3")
                    other_vols.append("perish3")
                    log.append(f"  Both Pokemon will faint in 3 turns! (Perish Body)")

        if name == "Poison Touch" and event_key == "onDamagingHit":
            if self._makes_contact(move_name, owner):
                if other.get("status") == None and random.random() < 0.3:
                    other["status"] = "psn"
                    log.append(
                        f"  {other.get('species')} was poisoned by {owner.get('species')}'s Poison Touch!"
                    )

        if name == "Pickpocket" and event_key == "onDamagingHit":
            if self._makes_contact(move_name, owner):
                # Steal item if owner has none and attacker has one
                if not owner.get("item") and other.get("item"):
                    # Check sticky hold (need access to engine or pass check? simplified check here or assume engine handles?
                    # Trigger handlers usually don't have full engine access easily unless passed.
                    # But wait, this modifies state directly.
                    # Let's check common logic. Usually straightforward.
                    should_steal = True
                    # Simple Sticky Hold check if 'other' is dict
                    if other.get("ability") == "Sticky Hold":
                         should_steal = False
                    
                    if should_steal:
                         item = other["item"]
                         owner["item"] = item
                         owner["_rich_item"] = other.get("_rich_item")
                         other["item"] = None
                         other["_rich_item"] = None
                         log.append(f"  {owner.get('species')} stole {other.get('species')}'s {item} with Pickpocket!")

        # 4. Survival (Sturdy, Focus Sash)
        if "survival" in src or name == "Sturdy":
            if owner.get("current_hp") <= 0:
                owner["current_hp"] = 1
                log.append(f"  {owner.get('species')} endured the hit! (Trigger: {name})")


    def check_immunity(self, attacker, defender, move_name):
        # 1. Type Immunity (handled in calc_Client mostly, but good to double check)
        # 2. Ability Immunity
        def_rich_ab = defender.get("_rich_ability", {})
        def_ability_name = def_rich_ab.get("name")
        
        # Mold Breaker check
        if attacker and attacker != defender:
             att_ab = attacker.get("ability", "")
             if att_ab in ["Mold Breaker", "Teravolt", "Turboblaze"]:
                  if def_rich_ab.get("flags", {}).get("breakable"):
                       return False, "" # Not immune

        # Get move type
        slug = ""
        if move_name:
             slug = move_name.lower().replace(" ", "").replace("-", "").replace("'", "")
        m_data = self._get_mechanic(slug, "moves")
        move_type = m_data.get("type", "Normal") if m_data else "Normal"
        


        # Flash Fire
        if move_type == "Fire" and def_ability_name == "Flash Fire":
             # Need to pass log? check_immunity signature is (attacker, defender, move_name)
             # It does NOT take log.
             # So we cannot append to log here easily.
             # However, check_immunity returns (bool, msg). BattleEngine appends msg to log.
             # For side effects like "Fire power rose", we might need to include that in the msg or handle it silently?
             # But we also need to set flags/boosts.
             defender["flash_fire"] = True
             return True, f"{defender.get('species')}'s Fire power rose (Flash Fire)!"

        # Sap Sipper
        if move_type == "Grass" and def_ability_name == "Sap Sipper":
             defender.setdefault("stat_stages", {})["atk"] = min(6, defender.get("stat_stages", {}).get("atk", 0) + 1)
             return True, f"{defender.get('species')}'s Attack rose (Sap Sipper)!"

        # Storm Drain / Water Absorb / Dry Skin (Water Immunity)
        if move_type == "Water":
             if def_ability_name == "Storm Drain":
                 defender.setdefault("stat_stages", {})["spa"] = min(6, defender.get("stat_stages", {}).get("spa", 0) + 1)
                 return True, f"{defender.get('species')}'s Sp. Atk rose (Storm Drain)!"
             if def_ability_name == "Water Absorb" or def_ability_name == "Dry Skin":
                 heal = int(defender.get("max_hp", 100) * 0.25)
                 defender["current_hp"] = min(defender.get("max_hp", 100), defender.get("current_hp", 0) + heal)
                 return True, f"{defender.get('species')} healed by {def_ability_name}!"

        # Volt Absorb / Lightning Rod / Motor Drive
        if move_type == "Electric":
             if def_ability_name == "Volt Absorb":
                 heal = int(defender.get("max_hp", 100) * 0.25)
                 defender["current_hp"] = min(defender.get("max_hp", 100), defender.get("current_hp", 0) + heal)
                 return True, f"{defender.get('species')} healed by Volt Absorb!"
             if def_ability_name == "Motor Drive":
                 defender.setdefault("stat_stages", {})["spe"] = min(6, defender.get("stat_stages", {}).get("spe", 0) + 1)
                 return True, f"{defender.get('species')}'s Speed rose (Motor Drive)!"
             if def_ability_name == "Lightning Rod":
                 defender.setdefault("stat_stages", {})["spa"] = min(6, defender.get("stat_stages", {}).get("spa", 0) + 1)
                 return True, f"{defender.get('species')}'s Sp. Atk rose (Lightning Rod)!"

        if move_type == "Ground" and def_ability_name == "Levitate": 
             return True, f"{defender.get('species')} avoided the move with Levitate!"

        # Soundproof
        if self._is_sound(move_name) and def_ability_name == "Soundproof":
            return True, f"{defender.get('species')}'s Soundproof blocks the move!"

        # Bulletproof
        flags = self._check_mechanic(move_name, "moves", "flags") or {}
        if flags.get("bullet") and def_ability_name == "Bulletproof":
            return True, f"{defender.get('species')}'s Bulletproof blocks the move!"

        # Safety Goggles & Overcoat (Powder Moves)
        if defender.get("item") == "Safety Goggles" or def_ability_name == "Overcoat":
            if flags.get("powder") or "Spore" in move_name or "Powder" in move_name:
                source = (
                    "Safety Goggles"
                    if defender.get("item") == "Safety Goggles"
                    else "Overcoat"
                )
                return True, f"{defender.get('species')}'s {source} blocks the move!"

        # Telepathy (Blocks damaging moves from allies)
        if def_ability_name == "Telepathy":
            if attacker.get("side") == defender.get("side"):
                m_data = self._get_mechanic(move_name, "moves")
                if m_data and m_data.get("category") != "Status":
                    return (
                        True,
                        f"{defender.get('species')}'s Telepathy blocks the move from its ally!",
                    )

        # 3. Semi-Invulnerability
        vols = defender.get("volatiles", [])
        if "invulnerable_high_alt" in vols:
            if move_name not in [
                "Thunder",
                "Hurricane",
                "Sky Uppercut",
                "Smack Down",
                "Gust",
                "Twister",
            ]:
                return True, f"{defender.get('species')} is high up in the air!"
        if "invulnerable_underground" in vols:
            if move_name not in ["Earthquake", "Magnitude"]:
                return True, f"{defender.get('species')} is underground!"
        if "invulnerable_underwater" in vols:
            if move_name not in ["Surf", "Whirlpool"]:
                return True, f"{defender.get('species')} is underwater!"

        return False, None

    def check_prankster_immunity(self, attacker, defender, move_category):
        if move_category == "Status" and attacker.get("ability") == "Prankster":
            if "Dark" in defender.get("types", []):
                return True
        return False

    def _is_sound(self, move_name):
        flags = self._check_mechanic(move_name, "moves", "flags")
        return flags.get("sound") if flags else False

    def _check_priority_block(self, attacker, defender, move_name, state):
        def_rich_ab = defender.get("_rich_ability", {})
        def_ability_name = def_rich_ab.get("name") or defender.get("ability")

        if def_ability_name in ["Dazzling", "Queenly Majesty", "Armor Tail"]:
            # Check move priority
            priority = self.get_move_priority(move_name, attacker, state)
            if priority > 0:
                return (
                    True,
                    f"{defender.get('species')}'s {def_ability_name} blocks the move!",
                )
        return False, None

    def _get_modifier(self, mon, key, move_data=None, state=None, target=None):
        return Mechanics.get_modifier(
            mon, key, move_data, state.fields if state else None, target
        )

    def get_move_priority(self, move_name, attacker, state=None):
        if not move_name:
            return 0

        # 1. Base Priority
        base = self._check_mechanic(move_name, "moves", "priority")
        if base is None:
            base = 0
        else:
            base = int(base)

        # 2. Ability Modifiers
        rich_ab = attacker.get("_rich_ability", {})
        ab_priority = rich_ab.get("onModifyPriority")
        ability_name = rich_ab.get("name")

        # Fallback for missing JSON keys in Phase 4
        if ab_priority is None:
            if ability_name == "Prankster":
                ab_priority = 1
            elif ability_name == "Gale Wings":
                ab_priority = 1
            elif ability_name == "Triage":
                ab_priority = 3

        if ab_priority:
            # Special logic for conditional priority
            if ability_name == "Prankster":
                cat = self._check_mechanic(move_name, "moves", "category")
                if cat == "Status":
                    base += ab_priority
            elif ability_name == "Gale Wings":
                m_type = self._check_mechanic(move_name, "moves", "type")
                if m_type == "Flying" and attacker.get("current_hp") == attacker.get(
                    "max_hp"
                ):
                    base += ab_priority
            elif ability_name == "Triage":
                # Check for heal/drain flags or properties
                m_data = self._check_mechanic(move_name, "moves", "all")
                if m_data and (
                    m_data.get("heal")
                    or m_data.get("drain")
                    or (m_data.get("flags", {}).get("heal"))
                ):
                    base += ab_priority
            else:
                base += ab_priority  # Generic fallback

        # Item Priority Modifications
        item = attacker.get("item")
        if item == "Full Incense" or item == "Lagging Tail":
            # Move last in bracket -> -0.1 priority (effectively)
            base -= 0.1
        elif item == "Quick Claw":
            # 20% chance to move first in bracket -> +0.1 priority
            # Deterministic hash for "randomness"
            if (
                hash(
                    str(attacker.get("current_hp"))
                    + move_name
                    + str(getattr(state, "turns", 0))
                )
                % 100
            ) < 20:
                base += 0.5

        # Grassy Glide
        if move_name == "Grassy Glide":
            # Need shared state or field check?
            if state:
                if state.fields.get("terrain") == "Grassy":
                    base = 1

        return base

    def _get_mechanic(self, key, category):
        # Helper to access rich data safely
        return self.rich_data.get(category, {}).get(key, {}) if key else {}

    def _check_mechanic(self, key, category, subkey):
        data = self._get_mechanic(key.lower().replace(" ", "").replace("-", "").replace("'", "") if key else None, category)
        if data:
            return data.get(subkey)
        return None

    def _is_protected_by_aroma_veil(self, mon, log):
         # Placeholder from original file logic
         return False

    def _check_hp_triggers(self, state, mon, log):
        """
        Checks for HP-based triggers like Berries, Berserk, etc.
        """
        if mon["current_hp"] <= 0:
            return

        max_hp = mon.get("max_hp", 100)
        hp_pct = mon["current_hp"] / max_hp

        # 1. Berries
        rich_item = mon.get("_rich_item", {})
        if rich_item.get("isBerry") and mon.get("ability") != "Klutz":
            # Standard trigger is 50% for Sitrus/Oran, 25% for others
            threshold = (
                0.5 if rich_item.get("name") in ["Sitrus Berry", "Oran Berry"] else 0.25
            )
            if mon.get("ability") == "Gluttony":
                threshold = 0.5

            if hp_pct <= threshold:
                logging.info(
                    f"DEBUG BERRY: {mon.get('species')} HP:{mon['current_hp']}/{max_hp} ({hp_pct:.2f}) Thr:{threshold}"
                )
                itemove_name = rich_item.get("name")
                # Heal Ratio
                hr = rich_item.get("healRatio")
                if hr:
                    heal_amt = int(max_hp * hr[0] / hr[1])
                    mon["current_hp"] = min(max_hp, mon["current_hp"] + heal_amt)
                    log.append(
                        f"  {mon.get('species')} ate its {itemove_name} (+{heal_amt})! (Gluttony active)"
                        if mon.get("ability") == "Gluttony"
                        else f"  {mon.get('species')} ate its {itemove_name} (+{heal_amt})!"
                    )
                    mon["item"] = None
                # Stat Boosts (Pinch Berries)
                boosts = rich_item.get("boosts")
                if boosts:
                    log.append(f"  {mon.get('species')} ate its {itemove_name}!")
                    self._apply_boosts(mon, boosts, log)
                    mon["item"] = None

                if mon["item"] is None:  # Consumed
                    if mon.get("ability") == "Unburden":
                        mon["unburden_active"] = True
                        log.append(f"  {mon.get('species')} became unburdened!")

        # 2. Abilities (Berserk)
        ab_rich = mon.get("_rich_ability", {})
        if ab_rich.get("name") == "Berserk" and hp_pct <= 0.5:
            # Berserk triggers when dropping below 50%
            # We need to track if it triggered THIS move.
            # Simplified: If not boosted yet
            stages = mon.setdefault("stat_stages", {})
            if stages.get("spa", 0) < 6:
                stages["spa"] += 1
                log.append(f"  {mon.get('species')}'s Sp. Atk rose (Berserk)!")

    def _apply_boosts(self, mon, boosts, log, source_name=None):
        dropped = any(v < 0 for v in boosts.values())
        Mechanics.apply_boosts(mon, boosts, log, source_name=source_name)

        # White Herb Check
        if dropped and mon.get("item") == "White Herb":
            restored = False
            stages = mon.get("stat_stages", {})
            for s in ["atk", "def", "spa", "spd", "spe", "acc", "eva"]:
                if stages.get(s, 0) < 0:
                    stages[s] = 0
                    restored = True

            if restored:
                mon["item"] = None
                log.append(
                    f"  {mon.get('species')} returned its stats to normal using its White Herb!"
                )

        # Eject Pack
        if dropped and mon.get("item") == "Eject Pack":
            mon["must_switch"] = True
            mon["item"] = None
            log.append(f"  {mon.get('species')} used its Eject Pack!")

    def _check_mental_herb(self, mon, log):
        if mon.get("item") == "Mental Herb":
            cured = []
            volatiles = mon.get("volatiles", [])
            for v in ["taunt", "encore", "torment", "attract", "disable", "healblock"]:
                if v in volatiles:
                    volatiles.remove(v)
                    cured.append(v)

            if cured:
                mon["item"] = None
                log.append(
                    f"  {mon.get('species')} cured its status using its Mental Herb!"
                )

    def _makes_contact(self, move_name, attacker):
        """
        Determines if a move makes contact, accounting for abilities (Long Reach) and items.
        """
        if not move_name:
             return False
             
        flags = self._check_mechanic(move_name, "moves", "flags")
        if not flags or not flags.get("contact"):
             # print(f"DEBUG: makes_contact failed for {move_name}. Flags: {flags}")
             return False
             
        # Abilities that block contact
        if attacker.get("ability") == "Long Reach":
             return False
             
        # Items that block contact effects (Protective Pads) - technically Contact still happens but effects are blocked.
        # But for 'Trigger' logic (Rough Skin, etc.), we usually treat it as 'no contact' for the purpose of the trigger.
        if attacker.get("item") == "Protective Pads":
             return False
             
        return True
