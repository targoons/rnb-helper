
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import copy

# Standard Gen 8 Type Chart
TYPE_CHART = {
    "Normal": {"Rock": 0.5, "Ghost": 0.0, "Steel": 0.5},
    "Fire": {
        "Fire": 0.5,
        "Water": 0.5,
        "Grass": 2.0,
        "Ice": 2.0,
        "Bug": 2.0,
        "Rock": 0.5,
        "Dragon": 0.5,
        "Steel": 2.0,
    },
    "Water": {
        "Fire": 2.0,
        "Water": 0.5,
        "Grass": 0.5,
        "Ground": 2.0,
        "Rock": 2.0,
        "Dragon": 0.5,
    },
    "Electric": {
        "Water": 2.0,
        "Electric": 0.5,
        "Grass": 0.5,
        "Ground": 0.0,
        "Flying": 2.0,
        "Dragon": 0.5,
    },
    "Grass": {
        "Fire": 0.5,
        "Water": 2.0,
        "Grass": 0.5,
        "Poison": 0.5,
        "Ground": 2.0,
        "Flying": 0.5,
        "Bug": 0.5,
        "Rock": 2.0,
        "Dragon": 0.5,
        "Steel": 0.5,
    },
    "Ice": {
        "Fire": 0.5,
        "Water": 0.5,
        "Grass": 2.0,
        "Ice": 0.5,
        "Ground": 2.0,
        "Flying": 2.0,
        "Dragon": 2.0,
        "Steel": 0.5,
    },
    "Fighting": {
        "Normal": 2.0,
        "Ice": 2.0,
        "Poison": 0.5,
        "Flying": 0.5,
        "Psychic": 0.5,
        "Bug": 0.5,
        "Rock": 2.0,
        "Ghost": 0.0,
        "Dark": 2.0,
        "Steel": 2.0,
        "Fairy": 0.5,
    },
    "Poison": {
        "Grass": 2.0,
        "Poison": 0.5,
        "Ground": 0.5,
        "Rock": 0.5,
        "Ghost": 0.5,
        "Steel": 0.0,
        "Fairy": 2.0,
    },
    "Ground": {
        "Fire": 2.0,
        "Electric": 2.0,
        "Grass": 0.5,
        "Poison": 2.0,
        "Flying": 0.0,
        "Bug": 0.5,
        "Rock": 2.0,
        "Steel": 2.0,
    },
    "Flying": {
        "Electric": 0.5,
        "Grass": 2.0,
        "Fighting": 2.0,
        "Bug": 2.0,
        "Rock": 0.5,
        "Steel": 0.5,
    },
    "Psychic": {
        "Fighting": 2.0,
        "Poison": 2.0,
        "Psychic": 0.5,
        "Dark": 0.0,
        "Steel": 0.5,
    },
    "Bug": {
        "Fire": 0.5,
        "Grass": 2.0,
        "Fighting": 0.5,
        "Poison": 0.5,
        "Flying": 0.5,
        "Psychic": 2.0,
        "Ghost": 0.5,
        "Dark": 2.0,
        "Steel": 0.5,
        "Fairy": 0.5,
    },
    "Rock": {
        "Fire": 2.0,
        "Ice": 2.0,
        "Fighting": 0.5,
        "Ground": 0.5,
        "Flying": 2.0,
        "Bug": 2.0,
        "Steel": 0.5,
    },
    "Ghost": {"Normal": 0.0, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5},
    "Dragon": {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
    "Dark": {"Fighting": 0.5, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Fairy": 0.5},
    "Steel": {
        "Fire": 0.5,
        "Water": 0.5,
        "Electric": 0.5,
        "Ice": 2.0,
        "Rock": 2.0,
        "Steel": 0.5,
        "Fairy": 2.0,
    },
    "Fairy": {
        "Fire": 0.5,
        "Fighting": 2.0,
        "Poison": 0.5,
        "Dragon": 2.0,
        "Dark": 2.0,
        "Steel": 0.5,
    },
}


@dataclass
class BattleState:
    player_active: Dict
    ai_active: Dict
    player_party: List[Dict]
    ai_party: List[Dict]
    last_moves: Dict = field(default_factory=lambda: {"player": None, "ai": None})
    fields: Dict = field(
        default_factory=lambda: {
            "weather": None,
            "weather_turns": 0,
            "terrain": None,
            "terrain_turns": 0,
            "screens": {
                "player": {"reflect": 0, "light_screen": 0, "aurora_veil": 0},
                "ai": {"reflect": 0, "light_screen": 0, "aurora_veil": 0},
            },
            "tailwind": {"player": 0, "ai": 0},
            "trick_room": 0,
            "hazards": {"player": [], "ai": []},
            "protected_sides": [],
        }
    )

    DANCE_MOVES = [
        "Quiver Dance",
        "Dragon Dance",
        "Swords Dance",
        "Feather Dance",
        "Petal Dance",
        "Teeter Dance",
        "Fiery Dance",
        "Revelation Dance",
        "Clangorous Soul",
        "Lunar Dance",
        "Victory Dance",
    ]

    def __post_init__(self):
        # Ensure fields has defaults if some keys are missing
        defaults = {
            "weather": None,
            "weather_turns": 0,
            "terrain": None,
            "terrain_turns": 0,
            "screens": {
                "player": {"reflect": 0, "light_screen": 0, "aurora_veil": 0},
                "ai": {"reflect": 0, "light_screen": 0, "aurora_veil": 0},
            },
            "tailwind": {"player": 0, "ai": 0},
            "trick_room": 0,
            "gravity": 0,
            "magic_room": 0,
            "wonder_room": 0,
            "hazards": {"player": [], "ai": []},
            "protected_sides": [],
        }
        if not self.fields:
            self.fields = defaults
        else:
            for k, v in defaults.items():
                if k not in self.fields:
                    self.fields[k] = v

    def deep_copy(self):
        return copy.deepcopy(self)

    def get_hash(self):
        """Returns a stable hash for the core state variables to detect cycles."""

        def get_mon_hash(m):
            v_h = tuple(sorted(m.get("volatiles", [])))
            return (
                m.get("species"),
                m.get("current_hp"),
                m.get("status"),
                tuple(sorted(m.get("stat_stages", {}).items())),
                v_h,
            )

        p_active_h = get_mon_hash(self.player_active)
        a_active_h = get_mon_hash(self.ai_active)
        p_party_h = tuple(get_mon_hash(m) for m in self.player_party)
        a_party_h = tuple(get_mon_hash(m) for m in self.ai_party)

        # Fields Hash
        f = self.fields
        screens_h = tuple(
            sorted(
                (k, tuple(sorted(v.items()))) for k, v in f.get("screens", {}).items()
            )
        )
        tailwind_h = tuple(sorted(f.get("tailwind", {}).items()))
        hazards_h = tuple(
            sorted((k, tuple(v)) for k, v in f.get("hazards", {}).items())
        )

        fields_h = (
            f.get("weather"),
            f.get("weather_turns"),
            f.get("terrain"),
            f.get("terrain_turns"),
            screens_h,
            tailwind_h,
            f.get("trick_room"),
            hazards_h,
        )

        return hash(
            (
                p_active_h,
                a_active_h,
                p_party_h,
                a_party_h,
                self.last_moves.get("player"),
                self.last_moves.get("ai"),
                fields_h,
            )
        )
