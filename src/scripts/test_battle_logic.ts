// @ts-nocheck
import { BattleState } from '../engine/battle.ts';
import { PokemonInstance } from '../data/types.ts';

// Mock Data mimicking API response
const mockApiData = {
    weather: 0,
    playerParty: [
        { id: 'p1', speciesId: 'Turtwig', level: 12, currentHp: 35, maxHp: 35, moves: ['tackle'] }
    ],
    enemyTeam: [], // Simulate missing/empty enemy team
    activeMons: [
        { slot: 0, speciesId: 'Turtwig', level: 12, currentHp: 35, maxHp: 35, moves: ['tackle'], stats: { hp: 35, atk: 10, def: 10, spa: 10, spd: 10, spe: 10 } },
        { slot: 1, speciesId: 'Poochyena', level: 5, currentHp: 20, maxHp: 20, moves: ['tackle'], stats: { hp: 20, atk: 10, def: 10, spa: 10, spd: 10, spe: 10 } }
    ]
};

// Mock mapToPokemon
const mapToPokemon = (m: any): PokemonInstance => ({
    id: m.id || 'temp-' + Math.random(),
    speciesId: m.speciesId,
    nickname: m.nickname || m.speciesId,
    level: m.level,
    currentHp: m.currentHp,
    maxHp: m.maxHp,
    nature: 'Hardy',
    ability: 'Unknown',
    item: 0,
    moves: m.moves,
    ivs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
    evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
    stats: m.stats || { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
    otId: 0,
    personality: 0,
    gender: 'genderless',
    species: m.speciesId,
    statusNum: 0,
    statStages: { hp: 6, atk: 6, def: 6, spa: 6, spd: 6, spe: 6, acc: 6, eva: 6 }
});

function runTest() {
    console.log("Running Battle Logic Test...");

    const data = mockApiData;
    let playerParty = data.playerParty.map(mapToPokemon);
    let enemyTeam = data.enemyTeam.map(mapToPokemon);

    const playerMonData = data.activeMons.find((m: any) => m.slot === 0 || m.slot === 2);
    const enemyMonData = data.activeMons.find((m: any) => m.slot === 1 || m.slot === 3);

    if (!playerMonData || !enemyMonData) {
        console.error("FAIL: Could not find active mons in mock data");
        return;
    }

    // Logic from page.tsx
    let myActive = playerParty.find(p => p.speciesId === playerMonData.speciesId && p.level === playerMonData.level);

    // Fallback logic
    if (!myActive) {
        console.log("Player active not found in party (unexpected for this test)");
    }

    let enemyActive = enemyTeam.find(p => p.speciesId === enemyMonData.speciesId && p.level === enemyMonData.level);

    // Fallback logic from page.tsx
    if (!enemyActive && data.enemyTeam) {
        const enemies = data.enemyTeam.map((m: any) => mapToPokemon(m));
        enemyActive = enemies.find(p => p.speciesId === enemyMonData.speciesId && p.level === enemyMonData.level);
    }

    if (!enemyActive) {
        console.log("FAIL: Enemy Active NOT found. This is the bug.");
        console.log("Reason: Enemy Team is empty, and we don't construct from activeMons directly.");
    } else {
        console.log("SUCCESS: Enemy Active found.");
    }

    if (myActive && enemyActive) {
        console.log("Battle State would be created successfully.");
    } else {
        console.log("Battle State creation SKIPPED.");
    }
}

runTest();
