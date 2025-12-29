# Full Implementation Plan: Pokemon Run & Bun Helper

This document provides a comprehensive roadmap of the development status for the Helper Tool, categorized by sub-systems and implementation phases.

## Status Summary

- **Core Infrastructure**: 100% Complete
- **AI Heuristic Modeling**: 90% Complete
- **Battle Mechanics (Simulation)**: 85% Complete
- **UI/UX (Lua Overlay)**: 95% Complete

---

## 1. Core Infrastructure (COMPLETED)

- **Phase 1: Foundation**: Set up Python/Node/Lua bridges and basic communication protocols.
- **Phase 2: Data Extraction**: Robust Lua scripts for extracting party stats, move IDs, and field states.
- **Phase 3: Calc Service**: High-fidelity damage calculation microservice using `@smogon/calc`.
- **Phase 4: Simulation Framework**: Beam search with expectimax path merging and iterative deepening (up to 20 turns).

---

## 2. Battle Mechanics Implementation

### Completed (Phases 1-7)
- [x] **Core Systems**: Protect/Detect, Type Immunities, Switch logic.
- [x] **Passive Effects**: End-of-turn weather/status damage, Leftovers/Black Sludge healing.
- [x] **Switch Interactions**: Intimidate, Drizzle, Drought (Switch-in), Regenerator (Switch-out).
- [x] **Pivoting**: U-turn, Volt Switch, Flip Turn, Parting Shot.
- [x] **Stat Modifiers**: Choice Items (Locking logic), Life Orb, Huge Power, Guts.
- [x] **Move Nuances**: Recoil, Drain, Multi-hit (Skill Link).
- [x] **Status Conditions**: Sleep (counters), Paralysis (Speed drop), Burn, Toxic (scaling).
- [x] **Volatile Status**: Confusion (self-hit logic), Flinch, Taunt (turn tracking).
- [x] **Field Effects**: Setting Weather/Terrain, Screens (Reflect/Light Screen/Aurora Veil).
- [x] **Speed Control**: Tailwind (doubling), Trick Room (speed inversion).
- [x] **Hazard Logic**: Stealth Rock, Spikes (stacking), Toxic Spikes, Sticky Web.

### Remaining (Phase 8+)
- [ ] **Consumables**: Berries (Sitrus, Lum, Resist), Focus Sash, White Herb.
- [ ] **Complex Abilities**: Transform/Imposter, Illusion, Stance Change.
- [ ] **Additional Move Nuances**: Accuracy/Evasion formulas, Critical hit ratios.
- [ ] **Field Prevention**: Safeguard, Misty Terrain status prevention.

---

## 3. AI Heuristic Alignment

### Completed
- [x] **Modular Scoring**: Dispatcher-based scoring for different move categories.
- [x] **Global Validity**: Preventing redundant status/hazards/weather.
- [x] **Recovery Logic**: Threshold-based healing evaluation.
- [x] **Setup Logic**: Evaluating offensive/defensive boosts vs KO threats.
- [x] **Utility Attacks**: Fake Out, Sucker Punch, Pursuit (logic for AI usage).
- [x] **Boom/Suicide**: Explosion/Healing Wish scoring.

### Remaining
- [ ] **Precise Switch Heuristics**: Fine-tuning when the AI decides to switch vs stay in.
- [ ] **History Tracking**: Improving Sucker Punch prediction based on historical patterns.

---

## 4. Verification Plan

- [x] **Unit Testing**: Automated JSON test cases for Immunities, Status, and Fields.
- [x] **Simulation Stress Tests**: 20-depth runs on complex board states.
- [ ] **Live Verification**: Comparing tool predictions with actual in-game AI behavior in specific boss fights.

---

## 5. Future Roadmap

- **Multi-Trainer Support**: Pre-loading teams for specific trainers (Gym Leaders, E4).
- **Route Tracking**: Integrating encounter data for the ROM hack.
- **Web Dashboard**: An optional secondary interface for detailed path analysis.
