# Pokemon Red/Blue Battle Simulator

A comprehensive Pokemon battle simulator for Pokemon Red & Blue that accurately implements Generation 1-9 mechanics with rich move data, ability interactions, and AI-driven decision making.

## Features

### Core Battle System

- **Accurate Damage Calculation**: Implements Pokemon damage formula with STAB, type effectiveness, critical hits, and stat modifications
- **Rich Move Mechanics**: 950+ moves with proper handling of secondary effects, priority, accuracy, and special interactions
- **Ability System**: 300+ abilities with conditional modifiers and battle interactions
- **Item Effects**: 580+ items including held items, berries, and battle items
- **Status Conditions**: Sleep, Paralysis, Burn, Freeze, Poison, Toxic, and Confusion
- **Stat Stage Modifiers**: Full implementation of ±6 stage system with proper capping and display

### Battle Simulation

- **Turn-by-Turn Execution**: Complete battle flow with proper move ordering by priority and speed
- **AI Decision Making**: Strategic move selection with damage prediction and type advantage calculation
- **Iterative Deepening Search**: Simulation-based AI that evaluates multiple turns ahead
- **Damage Range Display**: Shows min-max possible damage before moves execute
- **Battle Log Export**: Complete history saved to file with stats, damage, and all effects

### Advanced Mechanics

- **Weather & Terrain**: Rain, Sun, Sand, Hail, Electric Terrain, Grassy Terrain, etc.
- **Entry Hazards**: Stealth Rock, Spikes, Toxic Spikes, Sticky Web
- **Screen Effects**: Reflect, Light Screen, Aurora Veil
- **Substitute**: Damage blocking and interaction handling
- **Form Changes**: Stance Change (Aegislash), Weather Forms, etc.
- **Multi-Hit Moves**: Fury Attack, Double Slap, etc. with proper hit counting
- **Pivot Moves**: U-turn, Volt Switch, Flip Turn (Teleport correctly fails in trainer battles)

## Project Structure

```
pokemon_rnb_helper/
├── pkh_app/                    # Main application code
│   ├── battle_engine.py        # Core battle logic and move execution
│   ├── mechanics.py            # Stat calculations, boosts, and passive effects
│   ├── simulation.py           # AI simulation with iterative deepening
│   ├── ai_scorer.py            # Move evaluation and scoring
│   └── calc_client.py          # Damage calculation interface
├── data/                       # Game data
│   ├── mechanics_rich.json     # Move/ability/item data (950+ moves, 300+ abilities)
│   ├── pokedex_rich.json       # Pokemon species data
│   └── test_cases/             # Test scenarios for verification
├── calc_service/               # Damage calculator service
│   ├── server.js               # Node.js server for damage calculations
│   └── runbuncalc/             # Calculator library
├── simulate_battle_full.py     # Full battle simulation script
└── tests/                      # Test suite

```

## Installation

### Prerequisites

- Python 3.9+
- Node.js 14+ (for damage calculator service)
- npm (comes with Node.js)

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/targoon/pokemon_rnb_helper.git
   cd pokemon_rnb_helper
   ```

2. **Install Python dependencies**

   ```bash
   pip install requests
   ```

3. **Install Calculator Service**

   ```bash
   cd calc_service
   npm install
   cd ..
   ```

4. **Start the damage calculator service**

   ```bash
   ./start_services.sh
   ```

   Or manually:

   ```bash
   cd calc_service
   node server.js
   ```

## Usage

### Running a Battle Simulation

```bash
python3 simulate_battle_full.py
```

This will:

- Run a full 6v6 Pokemon battle
- Display turn-by-turn action log
- Show Pokemon stats with stage modifiers
- Display damage ranges for all moves
- Save complete battle log to `battle_simulation_log.txt`

### Example Output

```
=== Turn 1 ===
Player Active: Adams (Growlithe) (38/38)
AI Active:     Champ (Machop) (35/35)
DEBUG: Turn=1 Active=Growlithe
  Player Stats: ATK:26 (26+0) DEF:18 (18+0) SPA:21 (21+0) SPD:19 (19+0) SPE:21 (21+0)
  AI Stats: ATK:16 (25-1) DEF:15 (15+0) SPA:10 (10+0) SPD:15 (15+0) SPE:15 (15+0)
Player Choice: Move: Flame Wheel (Random)
AI Choice: Move: Leer (Random)
[PLAYER] Growlithe used Flame Wheel (STAB!)
  [Damage Range: 16-21]
  Machop: 16/35 HP (45%) (-19 dmg)
  Machop ate its Oran Berry (+10)!
  Secondary Effect: Machop was burned!
[AI] Machop used Leer
  Growlithe: 38/38 HP (100%) (-0 dmg)
  Growlithe's DEF fell to -1!
```

### Battle Log Features

The exported `battle_simulation_log.txt` includes:

- Complete turn-by-turn history
- Pokemon stats every turn (format: `STAT:effective (base±stage)`)
- Damage ranges showing min-max possible damage
- All status effects, stat changes, and abilities
- Entry hazards, weather, and field effects
- Final battle outcome

## Key Fixes & Improvements

### Recent Updates

✅ **Fixed Teleport Bug** - Teleport no longer causes permanent battle stalls

- Removed from pivot moves (only works to flee wild battles)
- Now properly failswith message in trainer battles

✅ **Consolidated Battle Engine** - Refactored `execute_turn_action`

- Single unified path for move effect application
- Eliminated double stat boost bugs
- Rich data properly loaded for all moves

✅ **Fixed Guts Ability** - No longer double-applies ATK boost

- Conditional abilities excluded from generic modifier loop

✅ **Complete Logging** - All battle details exported

- Pokemon stats with effective values and stages
- Damage ranges for every damaging move
- Dual-print system saves to file and console

## Testing

Run specific test suites:

```bash
# Test complex move mechanics
python3 test_complex_moves.py

# Test damage modifiers
python3 test_damage_modifiers.py

# Test stat changes
python3 test_bulk_verification.py

# Test critical hits
python3 test_crit_verify.py
```

## Architecture

### Battle Engine Flow

1. **Turn Start**: Apply start-of-turn effects (Quick Claw, abilities)
2. **Move Selection**: Determine action order by priority and speed
3. **Move Execution**:
   - Check status conditions (sleep, paralysis, etc.)
   - Check accuracy
   - Calculate damage with modifiers
   - Apply move effects (damage, stat changes, status)
   - Trigger secondary effects
4. **End of Turn**: Apply weather, status damage, field effects
5. **Win Check**: Determine if battle should continue

### Key Components

- **`BattleEngine`**: Main battle orchestration and move execution
- **`Mechanics`**: Static utility methods for stat calculations and boosts
- **`Simulation`**: AI decision making with minimax-style tree search
- **`AIScorer`**: Move evaluation based on damage and strategic value

## Data Sources

- **Moves/Abilities/Items**: Scraped from Pokemon Showdown's data
- **Pokemon Stats**: Extracted from game ROM via Lua scripts
- **Type Chart**: Standard Pokemon type effectiveness table
- **Mechanics**: Combination of Bulbapedia, Smogon, and game testing

## Known Limitations

- Wild battle mechanics (Teleport, flee) not fully implemented
- Some Gen 9+ moves may have incomplete data
- Double battles not supported
- Z-Moves, Mega Evolution, Dynamax not implemented

## Contributing

Contributions welcome! Areas that need work:

- Additional test coverage for edge cases
- More comprehensive move effect testing
- Performance optimization for simulation
- UI/visualization for battle playback

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Pokemon Showdown for comprehensive mechanics data
- RunBun Calculator for damage calculation algorithms
- Bulbapedia and Smogon University for mechanics documentation

---

**Note**: This is a fan project and is not affiliated with Nintendo, Game Freak, or The Pokemon Company.
