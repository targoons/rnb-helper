# Run and Bun AI Helper 🤖🔥

A real-time battle analysis and decision-support tool for the **Pokémon Emerald Run and Bun** romhack. This project integrates directly with the mGBA emulator to extract game state and provides advanced AI-driven move recommendations using a custom-built probabilistic battle engine.

## 🚀 Key Features

### 📡 Real-time ROM Integration

- **mGBA Lua Interface**: Automatically exports active battle state, opponent team data, and player party info.
- **Run and Bun Sync**: custom mappings for items, moves, and species IDs specifically tuned for the RnB environment.

### 🧠 Probabilistic AI Scorer

- **World Simulation**: Evaluates every move across 16 damage rolls and multiple AI behavior variants.
- **Strategic Evaluation**: Accounts for priority, type-effectiveness, stat stages, held items, and field conditions (weather, terrain, hazards).
- **Speed Bracket Analysis**: Real-time calculation of speed tiers, including Choice Scarf and ability modifiers.

### ⚔️ Modular Battle Engine

A high-fidelity implementation of modern Pokémon mechanics (Gen 1-9) designed for analysis:

- **Modular Architecture**: Separate handlers for damage calculation, primary/secondary triggers, and field state.
- **Complex Abilities**: Full support for 150+ abilities including mechanics like *Disguise*, *Truant*, *Poison Heal*, and *Libero*.
- **Entry Hazards & Field Effects**: Precise handling of *Stealth Rock*, *Sticky Web*, *Trick Room*, etc.

### 🧪 Comprehensive Test Suite

- **300+ Verified Tests**: Including unit tests for moves, integration tests for complex engine interactions, and an audit system for move/ability correctness.
- **Verification Reports**: Automated generation of mechanics status and audit summaries.

---

## 📁 Project Structure

```text
rnb_helper/
├── pkh_app/                    # Python Application Logic
│   ├── battle_engine/          # Modular Battle Simulation Engine
│   │   ├── damage.py           # HP/Damage calculation logic
│   │   ├── triggers.py         # Ability & Item trigger system
│   │   └── state.py            # Battle state management
│   ├── ai_scorer.py            # Probabilistic move evaluation logic
│   ├── local_damage_calc.py    # Local fallback damage engine
│   └── main.py                 # Application entry point/loop
├── lua/                        # Emulator Scripts
│   └── extract_state.lua       # mGBA script for state extraction
├── data/                       # Config & Mappings
│   ├── item_ids.json           # RnB specific Item ID mappings
│   └── verified_moves.json     # Audit-verified move data
└── tests/                      # Testing Environment
    ├── verification/           # Engine correctness tests
    └── features/               # Advanced mechanic benchmarks
```

---

## 🛠️ Setup Instructions

### Prerequisites

- **Emulator**: [mGBA](https://mgba.io/) (0.10.x recommended)
- **Python**: 3.9+

### 1. Application Setup

```bash
git clone https://github.com/targoons/rnb-helper.git
cd rnb-helper
pip install -r requirements.txt
```

### 2. Emulator Integration

1. Open **Pokémon Emerald Run and Bun** in mGBA.
2. Go to `Tools` -> `Scripting`.
3. Load `lua/extract_state.lua`.
4. Ensure your workspace has a `data/` directory for state sharing.

---

## 🎮 Usage

Start the main analysis loop:

```bash
python3 pkh_app/main.py
```

The tool will monitor the game state and output real-time analysis to the console, including:

- **Best Move Recommendation** with probability of winning the turn.
- **Damage Ranges** for all current moves.
- **Speed Ties/Brackets** for the current matchup.
- **Opponent Team Stats** discovered via engine simulation.

---

## 🧪 Running Tests

Validate the engine's mechanics:

```bash
# Run all verification tests
pytest tests/verification

# Run full engine audit
python3 tools/audit_engine.py
```

---

## 📜 Acknowledgments

- **Run and Bun Team**: For the incredible ROM hack.
- **Bulbapedia/Smogon**: For comprehensive mechanics documentation.

---
**Disclaimer**: This project is an unofficial tool and is not affiliated with Nintendo, Game Freak, or the Pokémon Company.
