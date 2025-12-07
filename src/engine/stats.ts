import { PokemonInstance, PokemonSpecies, Stats } from '@/data/types';
import { POKEDEX } from '@/data/pokedex';

const NATURES: Record<string, [keyof Stats, keyof Stats] | null> = {
    'Hardy': null, 'Docile': null, 'Serious': null, 'Bashful': null, 'Quirky': null,
    'Lonely': ['atk', 'def'], 'Brave': ['atk', 'spe'], 'Adamant': ['atk', 'spa'], 'Naughty': ['atk', 'spd'],
    'Bold': ['def', 'atk'], 'Relaxed': ['def', 'spe'], 'Impish': ['def', 'spa'], 'Lax': ['def', 'spd'],
    'Timid': ['spe', 'atk'], 'Hasty': ['spe', 'def'], 'Jolly': ['spe', 'spa'], 'Naive': ['spe', 'spd'],
    'Modest': ['spa', 'atk'], 'Mild': ['spa', 'def'], 'Quiet': ['spa', 'spe'], 'Rash': ['spa', 'spd'],
    'Calm': ['spd', 'atk'], 'Gentle': ['spd', 'def'], 'Sassy': ['spd', 'spe'], 'Careful': ['spd', 'spa']
};

export function getNatureMultiplier(nature: string, stat: keyof Stats): number {
    const mods = NATURES[nature];
    if (!mods) return 1.0;
    if (mods[0] === stat) return 1.1;
    if (mods[1] === stat) return 0.9;
    return 1.0;
}

export function calculateStat(
    base: number,
    iv: number,
    ev: number,
    level: number,
    nature: string,
    stat: keyof Stats
): number {
    if (stat === 'hp') {
        if (base === 1) return 1; // Shedinja
        return Math.floor(((2 * base + iv + Math.floor(ev / 4)) * level) / 100) + level + 10;
    } else {
        const val = Math.floor(((2 * base + iv + Math.floor(ev / 4)) * level) / 100) + 5;
        return Math.floor(val * getNatureMultiplier(nature, stat));
    }
}

export function getPokemonStats(p: PokemonInstance): Stats {
    // If we have real stats (e.g. from live battle export), use them!
    if (p.stats) return p.stats;

    const species = POKEDEX[p.speciesId];
    if (!species) return { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 };

    return {
        hp: calculateStat(species.baseStats.hp, p.ivs.hp, p.evs.hp, p.level, p.nature, 'hp'),
        atk: calculateStat(species.baseStats.atk, p.ivs.atk, p.evs.atk, p.level, p.nature, 'atk'),
        def: calculateStat(species.baseStats.def, p.ivs.def, p.evs.def, p.level, p.nature, 'def'),
        spa: calculateStat(species.baseStats.spa, p.ivs.spa, p.evs.spa, p.level, p.nature, 'spa'),
        spd: calculateStat(species.baseStats.spd, p.ivs.spd, p.evs.spd, p.level, p.nature, 'spd'),
        spe: calculateStat(species.baseStats.spe, p.ivs.spe, p.evs.spe, p.level, p.nature, 'spe'),
    };
}
