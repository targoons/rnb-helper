import { Move, PokemonInstance, PokemonSpecies } from '@/data/types';
import { getEffectiveness } from '@/data/typeChart';
import { POKEDEX } from '@/data/pokedex';
import { getPokemonStats } from './stats';

export interface DamageResult {
    min: number;
    max: number;
    rolls: number[]; // All possible damage values
    killChance: number; // Percentage chance to KO
}

export function calculateDamage(
    attacker: PokemonInstance,
    defender: PokemonInstance,
    move: Move,
    isCrit: boolean = false
): DamageResult {
    const attackerSpecies = POKEDEX[attacker.speciesId];
    const defenderSpecies = POKEDEX[defender.speciesId];

    if (!attackerSpecies || !defenderSpecies) {
        return { min: 0, max: 0, rolls: [], killChance: 0 };
    }

    if (move.category === 'Status') {
        return { min: 0, max: 0, rolls: [], killChance: 0 };
    }

    // 1. Stats
    const attackerStats = getPokemonStats(attacker);
    const defenderStats = getPokemonStats(defender);

    const atkStat = move.category === 'Physical' ? 'atk' : 'spa';
    const defStat = move.category === 'Physical' ? 'def' : 'spd';

    const A = attackerStats[atkStat];
    const D = defenderStats[defStat];

    // 2. Base Damage
    const levelFactor = (2 * attacker.level) / 5 + 2;
    let damage = ((levelFactor * move.power * (A / D)) / 50) + 2;

    // 3. Modifiers
    // Critical Hit (Gen 6+ / Run & Bun = 1.5x)
    if (isCrit) {
        damage *= 1.5;
    }

    // STAB
    if (attackerSpecies.types.includes(move.type)) {
        damage *= 1.5;
    }

    // Type Effectiveness
    const effectiveness = getEffectiveness(move.type, defenderSpecies.types);
    damage *= effectiveness;

    // Random (0.85 to 1.00) - 16 possible rolls
    const rolls: number[] = [];
    for (let i = 85; i <= 100; i++) {
        rolls.push(Math.floor(damage * (i / 100)));
    }

    const min = rolls[0];
    const max = rolls[rolls.length - 1];

    // Kill Chance
    const kills = rolls.filter(r => r >= defender.currentHp).length;
    const killChance = (kills / 16) * 100;

    return {
        min,
        max,
        rolls,
        killChance
    };
}
