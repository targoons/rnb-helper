const { Generations, Pokemon } = require('@smogon/calc');
const fs = require('fs');

const gen = 8;
const GenData = Generations.get(gen);

let luaOutput = "local SPECIES_ABIL_MAP = {\n";

const speciesTableRaw = fs.readFileSync('../lua_species_table.txt', 'utf8');
const entries = speciesTableRaw.matchAll(/\[(\d+)\]="([^"]+)"/g);

let count = 0;
for (const match of entries) {
    const id = match[1];
    const name = match[2];

    // Lookup in Smogon (try lowercase ID logic usually)
    // Smogon ID is usually lowercased name without special chars.
    let spec = GenData.species.get(name);
    if (!spec) spec = GenData.species.get(name.toLowerCase());

    if (count < 5) console.log(`Checking ${name} -> ${spec ? 'Found' : 'Not Found'}`);

    if (spec) {
        const a0 = spec.abilities[0];
        let a1 = spec.abilities[1];
        if (!a1) a1 = a0;

        luaOutput += `    [${id}]={[0]="${a0}", [1]="${a1}"},\n`;
        count++;
    }
}

luaOutput += "}\n\n";
luaOutput += `function getSpeciesAbility(speciesId, pid)
    local map = SPECIES_ABIL_MAP[speciesId]
    if not map then return nil end
    local bit = pid & 1
    return map[bit]
end
`;

fs.writeFileSync('../lua_species_abilities_map.txt', luaOutput);
console.log(`Generated map for ${count} species.`);
