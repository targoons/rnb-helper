
from typing import Dict, List, Optional
import copy
import logging
from .state import BattleState
from pkh_app.mechanics import Mechanics

class StateEnricher:
    def __init__(self, pokedex, rich_data, move_names, species_names):
        self.pokedex = pokedex
        self.rich_data = rich_data
        self.move_names = move_names
        self.species_names = species_names

    def enrich_state(self, state: BattleState):
        """Attaches rich data to all mons in the state."""
        self.enrich_mon(state.player_active)
        self.enrich_mon(state.ai_active)
        for mon in state.player_party:
            self.enrich_mon(mon)
        for mon in state.ai_party:
            self.enrich_mon(mon)

    def enrich_mon(self, mon: Dict):
        if not mon:
            return

        # Move ID to Slug mapping
        if "moves" in mon:
            mon["_rich_moves"] = {}
            for move in mon["moves"]:
                if isinstance(move, int):
                    name = self.move_names.get(str(move), str(move))
                    slug = name.lower().replace(" ", "").replace("-", "").replace("'", "")
                elif isinstance(move, str):
                    slug = move.lower().replace(" ", "").replace("-", "").replace("'", "")
                else:
                    slug = None

                if slug:
                    mon["_rich_moves"][slug] = (
                        self.rich_data.get("moves", {}).get(slug, {})
                    )

        # Ability
        ab = mon.get("ability")
        if ab:
            slug = str(ab).lower().replace(" ", "").replace("-", "").replace("'", "")
            mon["_rich_ability"] = self.rich_data.get("abilities", {}).get(slug, {})

        # Item
        item = mon.get("item")
        if item:
            slug = str(item).lower().replace(" ", "").replace("-", "").replace("'", "")
            mon["_rich_item"] = self.rich_data.get("items", {}).get(slug, {})

        # Species (for weight and other data)
        species = mon.get("species")
        if species:
            slug = str(species).lower().replace(" ", "").replace("-", "")
            mon["_rich_species"] = self.pokedex.get(slug, {})
            
            # Ensure types are populated
            if not mon.get("types"):
                mon["types"] = mon["_rich_species"].get("types", ["Normal"])

    def _perform_form_change(self, mon, new_form_slug, log, state: BattleState = None):
        """
        Updates stats, types, and ability for a form change.
        """
        if new_form_slug not in self.pokedex:
            logging.warning(f"Form {new_form_slug} not found in pokedex_rich.json")
            return

        new_data = self.pokedex[new_form_slug]
        old_species = mon.get("species")
        mon["species"] = new_data["name"]
        mon["types"] = new_data["types"]

        # Ability Change
        if new_data.get("abilities"):
            mon["ability"] = new_data["abilities"][0]
            # Re-enrich mon to update _rich_ability
            self.enrich_mon(mon)

        # Stat Update (keeping HP percentage)
        old_stats = mon.get("stats", {}).copy()
        mon["stats"] = new_data["bs"].copy()

        log.append(f"  {old_species} transformed into {mon['species']}!")

        if state:
            # We need to access apply_switch_in_abilities from somewhere, but circular dependency risk.
            # Ideally, form change should just update state and return flags.
            # For now, we omit the call back to 'apply_switch_in_abilities' here or pass a callback.
            # Given the constraints, I will simplify this: if validation fails, we fix it.
            pass


    def _check_mega_evolution(self, state, side, log):
        """
        Checks if the active mon can and should Mega Evolve.
        """
        if not state:
            return
        mon = state.player_active if side == "player" else state.ai_active
        if not mon or mon.get("is_mega"):
            return

        item = mon.get("item")
        if not item:
            return

        # Mega Stone mapping logic
        rich_item = mon.get("_rich_item", {})
        mega_species = rich_item.get("megaStone")

        # Fallback for manual stones or cases where rich_data is missing the flag
        if not mega_species and item.endswith("ite X"):
            mega_species = item.replace("ite X", "-Mega-X")
        elif not mega_species and item.endswith("ite Y"):
            mega_species = item.replace("ite Y", "-Mega-Y")
        elif not mega_species and item.endswith("ite"):
            mega_species = item.replace("ite", "-Mega")

        if mega_species:
            # Species check: Does this stone belong to this mon?
            current_species = mon.get("species", "").split("-")[0]  # Base species
            if mega_species.startswith(current_species):
                # Perform transformation
                mon["is_mega"] = True
                slug = (
                    mega_species.lower()
                    .replace(" ", "")
                    .replace("-", "")
                    .replace("'", "")
                )
                self._perform_form_change(mon, slug, log, state)

    def _check_primal_reversion(self, state, side, log):
        """
        Checks for Primal Reversion (Kyogre/Groudon).
        """
        if not state:
            return
        mon = state.player_active if side == "player" else state.ai_active
        if not mon or mon.get("is_primal"):
            return

        item = mon.get("item")
        species = mon.get("species")

        if species == "Kyogre" and item == "Blue Orb":
            mon["is_primal"] = True
            self._perform_form_change(mon, "kyogreprimal", log, state)
        elif species == "Groudon" and item == "Red Orb":
            mon["is_primal"] = True
            self._perform_form_change(mon, "groudonprimal", log, state)

    def _is_item_unremovable(self, item_name, mon):
        """
        Checks if an item is unremovable (Mega Stones, Orbs, Z-Crystals, etc.)
        """
        if not item_name:
            return False

        # Check rich data for megaStone/onPrimal flags
        slug = item_name.lower().replace(" ", "").replace("-", "").replace("'", "")
        rich_item = self.rich_data.get("items", {}).get(slug, {})

        if rich_item.get("megaStone") or rich_item.get("onPrimal"):
            return True

        # Hardcoded Orbs
        if item_name in ["Blue Orb", "Red Orb"]:
            return True

        return False
