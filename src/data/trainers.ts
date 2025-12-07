import { Trainer, PokemonInstance } from './types';
import trainersData from './trainers.json';
// import { v4 as uuidv4 } from 'uuid'; // We don't have uuid installed, using random

// Helper to generate IDs
const generateId = () => Math.random().toString(36).substring(7);

// Map JSON data to Trainer interface
const mappedTrainers: Record<string, Trainer> = {};

Object.values(trainersData).forEach((t: any) => {
    mappedTrainers[t.id] = {
        id: t.id,
        name: t.name,
        team: t.team.map((p: any) => ({
            id: generateId(),
            speciesId: p.speciesId, // Note: This must match POKEDEX keys. 
            // Our fetchPokedex used the same keys as trainers.json, so it should match.
            // But we need to handle case sensitivity if any.
            nickname: p.speciesId,
            level: p.level,
            ability: p.ability,
            nature: p.nature,
            item: p.item,
            moves: p.moves.map((m: string) => m.toLowerCase().replace(/[^a-z0-9]/g, '-')), // Normalize move IDs
            ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 }, // Assume 31 IVs for trainers
            evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 }, // Run and Bun has no EVs
            currentHp: 100, // Placeholder, will be calc'd
        }))
    };
});

export const TRAINERS = mappedTrainers;
