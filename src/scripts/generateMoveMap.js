const fs = require('fs');
const path = require('path');

const LUA_FILE = path.join(process.cwd(), 'src/data/raw/runandbun (1).lua');
const OUTPUT_FILE = path.join(process.cwd(), 'src/data/move_map.json');

function generateMap() {
    if (!fs.existsSync(LUA_FILE)) {
        console.error('Lua file not found:', LUA_FILE);
        return;
    }

    const content = fs.readFileSync(LUA_FILE, 'utf-8');

    // Find the 'move' table
    // move = { ... }
    const match = content.match(/move\s*=\s*\{([^}]+)\}/s);
    if (!match) {
        console.error('Could not find move table in Lua file');
        return;
    }

    const tableContent = match[1];

    // Regex for strings like "Pound"
    const names = tableContent.match(/"([^"]*)"/g);

    if (!names) {
        console.error('No names found');
        return;
    }

    const map = {};
    names.forEach((nameQuoted, index) => {
        // Remove quotes
        const name = nameQuoted.replace(/"/g, '');
        // Index 0 is "" (empty) in the Lua file
        if (name) {
            // Normalize name to match Pokedex keys?
            // Pokedex keys (MOVES) are usually kebab-case or just lowercase?
            // Let's check MOVES keys.
            // For now, map to the name in Lua.
            map[index] = name;
        }
    });

    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(map, null, 2));
    console.log(`Generated map with ${Object.keys(map).length} entries to ${OUTPUT_FILE}`);
}

generateMap();
