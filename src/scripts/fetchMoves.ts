import fs from 'fs';
import path from 'path';
import XLSX from 'xlsx';

const TRAINERS_FILE = path.join(process.cwd(), 'src/data/trainers.json');
const CHANGES_FILE = path.join(process.cwd(), 'src/data/raw/Move Changes.xlsx');
const OUTPUT_FILE = path.join(process.cwd(), 'src/data/moves.json');

interface MoveData {
    id: string;
    name: string;
    type: string;
    category: string;
    power: number;
    accuracy: number;
    pp: number;
    priority: number;
    effect?: string;
}

function normalizeId(name: string): string {
    return name.toLowerCase().replace(/[^a-z0-9]/g, '-');
}

async function fetchMoves() {
    // 1. Collect all moves from Trainers
    const trainersRaw = fs.readFileSync(TRAINERS_FILE, 'utf-8');
    const trainers = JSON.parse(trainersRaw);
    const uniqueMoves = new Set<string>();

    for (const tId in trainers) {
        const trainer = trainers[tId];
        for (const p of trainer.team) {
            for (const m of p.moves) {
                uniqueMoves.add(normalizeId(m));
            }
        }
    }

    // 2. Read Changes to add those moves too
    const workbook = XLSX.readFile(CHANGES_FILE);
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    const data = XLSX.utils.sheet_to_json<any[]>(sheet, { header: 1 });

    const changes: Record<string, any> = {};

    // Parse Columns A-F (Stat Changes)
    for (let i = 1; i < data.length; i++) {
        const row = data[i];
        if (!row || !row[0]) continue;

        const name = row[0];
        const id = normalizeId(name);
        uniqueMoves.add(id);

        changes[id] = {
            bp: row[1],
            pp: row[2],
            acc: row[3],
            effChance: row[4],
            type: row[5]
        };
    }

    // Parse Columns H-I (Effect Changes)
    for (let i = 1; i < data.length; i++) {
        const row = data[i];
        if (!row || !row[7]) continue; // Column H is index 7

        const name = row[7];
        const id = normalizeId(name);
        uniqueMoves.add(id);

        if (!changes[id]) changes[id] = {};
        changes[id].effect = row[8];
    }

    console.log(`Found ${uniqueMoves.size} unique moves.`);

    const moves: Record<string, MoveData> = {};
    const moveList = Array.from(uniqueMoves);
    const BATCH_SIZE = 10;

    for (let i = 0; i < moveList.length; i += BATCH_SIZE) {
        const batch = moveList.slice(i, i + BATCH_SIZE);
        await Promise.all(batch.map(async (id) => {
            try {
                // Fetch base data
                const res = await fetch(`https://pokeapi.co/api/v2/move/${id}`);
                if (!res.ok) {
                    console.warn(`Failed to fetch move ${id}: ${res.status}`);
                    // Fallback or skip? Better to create a dummy so app doesn't crash
                    moves[id] = {
                        id,
                        name: id,
                        type: 'Normal',
                        category: 'Physical',
                        power: 0,
                        accuracy: 100,
                        pp: 0,
                        priority: 0,
                        effect: 'Unknown'
                    };
                    return;
                }
                const data = await res.json();

                const move: MoveData = {
                    id,
                    name: data.names.find((n: any) => n.language.name === 'en')?.name || data.name,
                    type: data.type.name.charAt(0).toUpperCase() + data.type.name.slice(1),
                    category: data.damage_class.name.charAt(0).toUpperCase() + data.damage_class.name.slice(1),
                    power: data.power || 0,
                    accuracy: data.accuracy || 100,
                    pp: data.pp,
                    priority: data.priority,
                    effect: data.effect_entries?.[0]?.short_effect || ''
                };

                // Apply Changes
                if (changes[id]) {
                    const c = changes[id];

                    if (c.bp && c.bp.includes('>')) {
                        move.power = parseInt(c.bp.split('>')[1].trim());
                    }
                    if (c.acc && c.acc.includes('>')) {
                        move.accuracy = parseInt(c.acc.split('>')[1].replace('%', '').trim());
                    }
                    if (c.type && c.type.includes('>')) {
                        move.type = c.type.split('>')[1].trim();
                    }
                    if (c.effect) {
                        move.effect = c.effect;
                    }
                }

                moves[id] = move;
                // console.log(`Processed ${id}`);
            } catch (e) {
                console.error(`Error processing ${id}:`, e);
            }
        }));
        if (i % 50 === 0) console.log(`Processed ${i} moves...`);
    }

    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(moves, null, 2));
    console.log('Moves saved.');
}

fetchMoves();
