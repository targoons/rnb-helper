# Developer Handover: Phase 8 & Beyond

Welcome, Jules! This document outlines the current state of the **Pokemon Run & Bun Helper** and provides a roadmap for continuing the implementation of battle mechanics and AI alignment.

## 1. Architecture Overview

### Core Stack
- **Orchestrator (Python)**: `app/strategy_advisor.py` is the entry point. It manages the simulation loop.
- **Battle Engine**: `app/battle_engine.py` handles the logic of a single turn. It is designed to be deterministic.
- **Mechanics Utility**: `app/mechanics.py` contains static logic for speed calculations, turn-end effects, and passive modifiers.
- **Calc Service (Node.js)**: `calc_service/server.js` provides damage rolls. It wraps Smogon's `@smogon/calc`.
- **Lua Overlay**: `lua/extract_state.lua` is the link to the emulator.

### Key Data Structures
- **BattleState**: Defined in `app/battle_engine.py`. It holds the active Mons, parties, and the `fields` dictionary (Weather, Terrain, Screens, Hazards).
- **Turn Logging**: The engine returns a `log` list of strings describing every action (damage, item triggers, field changes).

---

## 2. Testing Workflow

Before pushing any changes, you **must** verify them using the simulation tool:
```bash
python3 tools/run_sim.py data/your_test_case.json
```
Refer to `data/fields_test.json` or `data/status_test.json` for examples of how to format test states.

---

## 3. Priority Tasks: Phase 8 (Consumables & Complex Mechanics)

### A. Berry Implementation (High Priority)
Berries need to be handled in `BattleEngine.execute_turn_action` (post-damage) or `Mechanics.apply_end_turn_effects`.
- **Healing Berries**: Sitrus (25% at <50% HP), Figy/Wiki/Mago/Aguav/Iapapa (1/3 at <25% HP).
- **Status Berries**: Lum (all), Pecha (poison), etc. These should trigger immediately after a status is applied in `apply_move_effects`.
- **Resist Berries**: Yache, Occa, etc. These must be passed to the `Calc Service` via the `item` field.

### B. Focus Sash & Sturdy
- Modify `execute_turn_action` to check for 1-HP survival if hit from full HP.
- Ensure the item is marked as consumed in the `state`.

### C. Advanced Abilities
Implement handlers for:
- **Transform/Imposter**: Copying stats (except HP) and moves.
- **Illusion**: Zoroark's disguise (needs to be tracked in `BattleState`).
- **Stance Change**: Aegislash Forme switching during move execution.

---

## 4. AI Heuristic Alignment

The `AIScorer` in `app/ai_scorer.py` needs to be updated to "value" the new Phase 8 mechanics:
- **Item Preservation**: AI should value keeping a Focus Sash intact.
- **Setup Synergy**: AI should recognize when a Berry (like Salac) will trigger after a certain move (like Belly Drum).

## 5. Resources
- **Reference**: `mechanics_status.md` for the current checklist of moves/abilities.
- **Roadmap**: `FULL_IMPLEMENTATION_PLAN.md` for the long-term vision.
