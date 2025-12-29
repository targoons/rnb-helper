const { Generations, Pokemon } = require('@smogon/calc');
const fs = require('fs');

const gen = 8; // Run & Bun is based on Gen 3 but has Gen 8 mechanics/mons
const GenData = Generations.get(gen);

let luaOutput = "local SPECIES_ABIL_MAP = {\n";

let count = 0;
for (const species of GenData.species) {
    // species is an object with name, id (maybe), abilities?
    // Actually GenData.species is an iterable.

    // We need ID. Smogon uses names.
    // PokeAPI ID is needed.
    // We can infer ID if possible?
    // Or we fetch from PokeAPI for ID?
    // Wait, I need to map ID (integer) -> Abilities.
    // Smogon data doesn't guarantee ID? 
    // Let's check `species.id` property? Usually it's name-based key.
    // But maybe `species.num` exists?

    // Let's try to find ID.
    // If not, we have a challenge.
    // However, I have `lua_species_table.txt` (from previous step) which maps ID -> Name.
    // I can parse `lua_species_table.txt` to get ID -> Name.
    // Then look up Name in Smogon data.
    // Then output ID -> Smogon Abilities.
}

// Better plan: Read `lua_species_table.txt` in JS.
const speciesTableRaw = fs.readFileSync('../lua_species_table.txt', 'utf8');
// Format: [1]="Bulbasaur",
const entries = speciesTableRaw.matchAll(/\[(\d+)\]="([^"]+)"/g);

for (const match of entries) {
    const id = match[1];
    const name = match[2];

    // Lookup in Smogon
    // Smogon lookup by name
    const spec = GenData.species.get(name);
    if (spec) {
        const a0 = spec.abilities[0];
        let a1 = spec.abilities[1];
        if (!a1) a1 = a0; // Duplicate if single ability

        luaOutput += `    [${id}]={[0]="${a0}", [1]="${a1}"},\n`;
        count++;
    } else {
        // Try fuzzy match or skip?
        // Some names might differ e.g. "Nidoran-f"
    }
}

luaOutput += "}\n";

// Add safe accessor function
luaOutput += `
function getSpeciesAbility(speciesId, pid)
    local map = SPECIES_ABIL_MAP[speciesId]
    if not map then return nil end
    local bit = pid & 1
    return map[bit]
end
`;

fs.writeFileSync('../lua_species_abilities_map.txt', luaOutput);
console.log(`Generated map for ${count} species.`);
