# Pokemon Run & Bun Helper Tool

A comprehensive assistant for the "Pokemon Run & Bun" ROM hack. This tool provides real-time battle intelligence, AI move prediction, and deep simulation to help players navigate one of the most challenging Pokemon experiences.

## Core Components

- **Lua Overlay**: An in-game script that extracts live battle data and displays enemy stats, party info, and move predictions directly on the emulator.
- **Orchestrator (Python)**: The brain of the project. It coordinates data extraction, runs simulations, and generates strategy recommendations.
- **Battle Engine (Python)**: A custom-built engine designed for high-fidelity simulation of Gen 8 mechanics (with Run & Bun specific tweaks).
- **Calc Service (Node.js)**: A lightweight wrapper around `@smogon/calc` that provides accurate damage rolls for the engine and AI scorer.

## Features

- **High-Fidelity Simulation**: Supports complex mechanics including Weather, Terrain, Hazards, Screens, and Speed Control (Tailwind/Trick Room).
- **AI Prediction**: Models the opponent's behavior based on the specific AI heuristics used in the ROM hack.
- **Advanced Forecasting**: Uses Beam Search with Iterative Deepening to project battle outcomes up to 20 turns ahead.
- **Status Tracking**: Accurately tracks primary and volatile statuses (Sleep counters, Confusion turns, Taunt durations).

## Getting Started

1. **Services**: Start the Calc Service and Orchestrator using `./start_services.sh`.
2. **Emulator**: Load the Lua script located in `lua/` into your emulator (designed for mGBA/BizHawk).
3. **Overlay**: The overlay will automatically update as the battle progresses.

## Project Structure

- `app/`: Core Python logic (Battle Engine, Strategy Advisor, AI Scorer).
- `calc_service/`: Node.js damage calculation microservice.
- `lua/`: Emulator scripts for data extraction and UI overlay.
- `data/`: Game metadata (Moves, Species, Trainers) and test cases.
- `tools/`: CLI utilities for running simulations and debugging.

## Status

For a detailed roadmap and current implementation status, see [FULL_IMPLEMENTATION_PLAN.md](./FULL_IMPLEMENTATION_PLAN.md).
