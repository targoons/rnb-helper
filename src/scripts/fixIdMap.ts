import fs from 'fs';
import path from 'path';

const ID_MAP_FILE = path.join(process.cwd(), 'src/data/id_map.json');

function fixIdMap() {
    if (!fs.existsSync(ID_MAP_FILE)) {
        console.error('ID Map file missing');
        return;
    }

    const raw = fs.readFileSync(ID_MAP_FILE, 'utf-8');
    const idMap: Record<string, string> = JSON.parse(raw);
    const newMap: Record<string, string> = {};

    Object.entries(idMap).forEach(([key, value]) => {
        const newKey = String(Number(key) + 1);
        newMap[newKey] = value;
    });

    // Add 0 for MissingNo/None if needed, or just leave it.
    // Usually 0 is empty slot.
    newMap["0"] = "?????";

    fs.writeFileSync(ID_MAP_FILE, JSON.stringify(newMap, null, 2));
    console.log('ID Map fixed (shifted +1).');
}

fixIdMap();
