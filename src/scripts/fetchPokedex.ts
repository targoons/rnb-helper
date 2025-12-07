import fs from 'fs';
import path from 'path';

const TRAINERS_FILE = path.join(process.cwd(), 'src/data/trainers.json');
const OUTPUT_FILE = path.join(process.cwd(), 'src/data/pokedex.json');

interface PokemonSpecies {
    id: string;
    name: string;
    types: string[];
    baseStats: {
        hp: number;
        atk: number;
        def: number;
        spa: number;
        spd: number;
        spe: number;
    };
    abilities: string[];
}

// Normalization map for Run and Bun names to PokeAPI names
function normalizeName(name: string): string {
    let lower = name.toLowerCase();

    // Handle forms
    if (lower.includes('_alolan')) return lower.replace('_alolan', '-alola');
    if (lower.includes('_galarian')) return lower.replace('_galarian', '-galar');
    if (lower.includes('_hisuian')) return lower.replace('_hisuian', '-hisui');
    if (lower.includes('_paldean')) return lower.replace('_paldean', '-paldea');
    if (lower.includes('_mega')) return lower.replace('_mega', '-mega');
    if (lower.includes('_primal')) return lower.replace('_primal', '-primal');

    // Specific fixes
    if (lower === 'farfetchd') return 'farfetchd'; // PokeAPI is farfetchd
    if (lower === 'farfetchd_galarian') return 'farfetchd-galar';
    if (lower === 'mr_mime') return 'mr-mime';
    if (lower === 'mime_jr') return 'mime-jr';
    if (lower === 'type_null') return 'type-null';
    if (lower === 'tapu_koko') return 'tapu-koko'; // and others

    // General replacement of _ with -
    return lower.replace(/_/g, '-');
}

async function fetchPokedex() {
    const trainersRaw = fs.readFileSync(TRAINERS_FILE, 'utf-8');
    const trainers = JSON.parse(trainersRaw);

    const uniqueSpecies = new Set<string>();

    // Collect all species
    for (const tId in trainers) {
        const trainer = trainers[tId];
        for (const p of trainer.team) {
            uniqueSpecies.add(p.speciesId);
        }
    }

    console.log(`Found ${uniqueSpecies.size} unique Pokemon species.`);

    const pokedex: Record<string, PokemonSpecies> = {};
    const speciesList = Array.from(uniqueSpecies);

    // Fetch in batches
    const BATCH_SIZE = 5;

    for (let i = 0; i < speciesList.length; i += BATCH_SIZE) {
        const batch = speciesList.slice(i, i + BATCH_SIZE);
        await Promise.all(batch.map(async (originalName) => {
            const apiName = normalizeName(originalName);
            try {
                const res = await fetch(`https://pokeapi.co/api/v2/pokemon/${apiName}`);
                if (!res.ok) {
                    console.error(`Failed to fetch ${originalName} (as ${apiName}): ${res.status}`);
                    // Create dummy entry to avoid crashing app
                    pokedex[originalName] = {
                        id: originalName,
                        name: originalName,
                        types: ['Normal'],
                        baseStats: { hp: 50, atk: 50, def: 50, spa: 50, spd: 50, spe: 50 },
                        abilities: ['Unknown']
                    };
                    return;
                }

                const data = await res.json();

                pokedex[originalName] = {
                    id: originalName, // Keep original ID for lookup
                    name: data.name, // Or keep originalName? Let's use API name for display maybe? No, keep original ID key.
                    types: data.types.map((t: any) => t.type.name.charAt(0).toUpperCase() + t.type.name.slice(1)),
                    baseStats: {
                        hp: data.stats[0].base_stat,
                        atk: data.stats[1].base_stat,
                        def: data.stats[2].base_stat,
                        spa: data.stats[3].base_stat,
                        spd: data.stats[4].base_stat,
                        spe: data.stats[5].base_stat,
                    },
                    abilities: data.abilities.map((a: any) => a.ability.name)
                };
                console.log(`Fetched ${originalName}`);
            } catch (e) {
                console.error(`Error fetching ${originalName}:`, e);
            }
        }));
    }

    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(pokedex, null, 2));
    console.log('Pokedex saved.');
}

fetchPokedex();
