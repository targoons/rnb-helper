import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
    const filePath = path.join(process.cwd(), 'src/data/imports/battle.json');

    if (!fs.existsSync(filePath)) {
        return NextResponse.json({ error: 'Battle file not found. Run the Lua script first.' }, { status: 404 });
    }

    try {
        const data = fs.readFileSync(filePath, 'utf-8');
        const battleData = JSON.parse(data);

        // Load ID Map
        const mapPath = path.join(process.cwd(), 'src/data/id_map.json');
        let idMap: Record<string, string> = {};
        if (fs.existsSync(mapPath)) {
            idMap = JSON.parse(fs.readFileSync(mapPath, 'utf-8'));
        }

        // Load Move Map
        const moveMapPath = path.join(process.cwd(), 'src/data/move_map.json');
        let moveMap: Record<string, string> = {};
        if (fs.existsSync(moveMapPath)) {
            moveMap = JSON.parse(fs.readFileSync(moveMapPath, 'utf-8'));
        }

        // Helper to normalize keys
        const normalize = (str: string) => str.toLowerCase().replace(/ /g, '-');

        // Map Enemy Team IDs
        if (battleData.enemyTeam) {
            battleData.enemyTeam = battleData.enemyTeam.map((mon: any) => ({
                ...mon,
                speciesId: idMap[mon.speciesId] || mon.speciesId,
                moves: mon.moves.map((mId: number) => {
                    const name = moveMap[mId];
                    return name ? normalize(name) : String(mId);
                }).filter((m: string) => m !== '0' && m !== ''),
            }));
        }

        // Map Active Mons IDs
        if (battleData.activeMons) {
            battleData.activeMons = battleData.activeMons.map((mon: any) => ({
                ...mon,
                speciesId: idMap[mon.speciesId] || mon.speciesId,
                moves: mon.moves.map((mId: number) => {
                    const name = moveMap[mId];
                    return name ? normalize(name) : String(mId);
                }).filter((m: string) => m !== '0' && m !== ''),
            }));
        }

        // Map Player Party IDs
        if (battleData.playerParty) {
            battleData.playerParty = battleData.playerParty.map((mon: any) => ({
                ...mon,
                speciesId: idMap[mon.speciesId] || mon.speciesId,
                // Ensure ID is string for app consistency
                id: (mon.otId && mon.personality)
                    ? `${mon.otId}-${mon.personality}`
                    : `temp-${Math.random().toString(36).substring(7)}`,
                moves: mon.moves.map((mId: number) => {
                    const name = moveMap[mId];
                    return name ? normalize(name) : String(mId);
                }).filter((m: string) => m !== '0' && m !== ''),
            }));
        }

        return NextResponse.json(battleData);
    } catch (e) {
        return NextResponse.json({ error: 'Failed to parse battle file.' }, { status: 500 });
    }
}
