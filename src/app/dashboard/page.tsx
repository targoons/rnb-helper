'use client';

import { useState, useEffect } from 'react';
import { useBoxStore } from '@/store/boxStore';
import { BattleState, Action } from '@/engine/battle';
import { getBestAction } from '@/solver/minimax';
import { PokemonInstance } from '@/data/types';
import { POKEDEX, MOVES } from '@/data/pokedex';
import { getPokemonStats } from '@/engine/stats';
import { calculateDamage } from '@/engine/damage';

export default function DashboardPage() {
    const [battleState, setBattleState] = useState<BattleState | null>(null);
    const [playerParty, setPlayerParty] = useState<PokemonInstance[]>([]);
    const [enemyTeam, setEnemyTeam] = useState<PokemonInstance[]>([]);
    const [suggestion, setSuggestion] = useState<Action | null>(null);
    const [lastSyncTime, setLastSyncTime] = useState<string>('');
    const [weather, setWeather] = useState<number>(0);

    const syncLive = async () => {
        try {
            const res = await fetch('/api/battle');
            if (!res.ok) throw new Error('Failed to fetch battle data');
            const data = await res.json();

            if (data.weather !== undefined) setWeather(data.weather);

            // 1. Update Party
            if (data.playerParty) {
                const party = data.playerParty.map((m: any) => mapToPokemon(m));
                setPlayerParty(party);
            }

            // 2. Update Enemy Team
            if (data.enemyTeam) {
                const enemies = data.enemyTeam.map((m: any) => mapToPokemon(m));
                setEnemyTeam(enemies);
            }

            // 3. Update Battle State (if active)
            if (data.activeMons && data.activeMons.length > 0) {
                const playerMonData = data.activeMons.find((m: any) => m.slot === 0 || m.slot === 2);
                const enemyMonData = data.activeMons.find((m: any) => m.slot === 1 || m.slot === 3);

                if (playerMonData && enemyMonData) {
                    // Find active instances in our lists
                    // For player, find in party
                    let myActive = playerParty.find(p => p.speciesId === playerMonData.speciesId && p.level === playerMonData.level);
                    // Fallback to creating one if not found (or if party not yet updated in state)
                    if (!myActive && data.playerParty) {
                        const party = data.playerParty.map((m: any) => mapToPokemon(m));
                        myActive = party.find(p => p.speciesId === playerMonData.speciesId && p.level === playerMonData.level);
                    }

                    // For enemy, find in enemyTeam
                    let enemyActive = enemyTeam.find(p => p.speciesId === enemyMonData.speciesId && p.level === enemyMonData.level);
                    if (!enemyActive && data.enemyTeam) {
                        const enemies = data.enemyTeam.map((m: any) => mapToPokemon(m));
                        enemyActive = enemies.find(p => p.speciesId === enemyMonData.speciesId && p.level === enemyMonData.level);
                    }

                    if (myActive && enemyActive) {
                        // Update current HP and Status from active data
                        myActive = {
                            ...myActive,
                            currentHp: playerMonData.currentHp,
                            stats: playerMonData.stats || myActive.stats,
                            statusNum: playerMonData.status,
                            statStages: playerMonData.statStages
                        };
                        enemyActive = {
                            ...enemyActive,
                            currentHp: enemyMonData.currentHp,
                            stats: enemyMonData.stats || enemyActive.stats,
                            statusNum: enemyMonData.status,
                            statStages: enemyMonData.statStages
                        };

                        const state = new BattleState(
                            myActive,
                            playerParty.length > 0 ? playerParty : [myActive], // Use full party if available
                            enemyActive,
                            enemyTeam.length > 0 ? enemyTeam : [enemyActive]
                        );
                        setBattleState(state);
                        setSuggestion(null); // Reset suggestion on new state
                    }
                }
            }

            setLastSyncTime(new Date().toLocaleTimeString());

        } catch (e) {
            console.error(e);
            alert('Error syncing. Make sure Lua script is running.');
        }
    };

    const getAdvice = () => {
        if (!battleState) return;
        const action = getBestAction(battleState, 3);
        setSuggestion(action);
    };

    // Helper to map JSON to PokemonInstance
    const mapToPokemon = (m: any): PokemonInstance => ({
        id: m.id || 'temp-' + Math.random(),
        speciesId: m.speciesId,
        nickname: m.nickname,
        level: m.level,
        currentHp: m.currentHp,
        maxHp: m.maxHp,
        nature: m.nature,
        ability: m.ability || POKEDEX[m.speciesId]?.abilities.join('/') || 'Unknown',
        item: m.item,
        moves: m.moves,
        ivs: m.ivs,
        evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
        stats: m.stats,
        otId: m.otId || 0,
        personality: m.personality || 0,
        gender: 'genderless',
        species: m.speciesId,
        statusNum: m.status,
        statStages: m.statStages
    });

    const getWeatherName = (w: number) => {
        // Map weather ID to name (Standard Gen 3)
        // 0: None, 1: Rain, 2: Sun, 3: Sand, 4: Hail?
        // Need to verify IDs. Assuming 0 is None for now.
        if (w === 0 || w === 65535) return 'Clear';
        if (w === 1) return 'Rain';
        if (w === 2) return 'Sun';
        if (w === 3) return 'Sandstorm';
        if (w === 4) return 'Hail';
        return `Weather ${w}`;
    };

    const getStatusName = (s: number | undefined) => {
        if (!s) return null;
        if (s & 0x7) return 'SLP';
        if (s & 0x8) return 'PSN';
        if (s & 0x10) return 'BRN';
        if (s & 0x20) return 'FRZ';
        if (s & 0x40) return 'PAR';
        if (s & 0x80) return 'TOX';
        return null;
    };

    const renderStatStages = (stages: any) => {
        if (!stages) return null;
        const stats = ['atk', 'def', 'spa', 'spd', 'spe', 'acc', 'eva'];
        return (
            <div className="flex gap-1 flex-wrap text-[10px] mt-1">
                {stats.map(s => {
                    const val = stages[s];
                    if (val === 6) return null; // Neutral
                    const diff = val - 6;
                    return (
                        <span key={s} className={`px-1 rounded ${diff > 0 ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                            {s.toUpperCase()} {diff > 0 ? '+' : ''}{diff}
                        </span>
                    );
                })}
            </div>
        );
    };

    return (
        <main className="min-h-screen p-4 bg-slate-900 text-white">
            {/* Header */}
            <div className="flex justify-between items-center mb-6 bg-slate-800 p-4 rounded-xl shadow-lg">
                <h1 className="text-2xl font-bold">Run & Bun Dashboard</h1>
                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <div className="text-xs text-gray-400">Weather</div>
                        <div className="font-bold text-yellow-400">{getWeatherName(weather)}</div>
                    </div>
                    <span className="text-sm text-gray-400">Last Sync: {lastSyncTime || 'Never'}</span>
                    <button
                        onClick={syncLive}
                        className="py-2 px-6 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold shadow-md transition-all active:scale-95"
                    >
                        SYNC LIVE
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-12 gap-6">
                {/* Left Column: Player Party (3 cols) */}
                <div className="col-span-3 space-y-4">
                    <h2 className="text-xl font-bold text-gray-300 border-b border-gray-700 pb-2">My Party</h2>
                    <div className="space-y-2">
                        {playerParty.map((p, i) => (
                            <div key={i} className={`p-3 rounded-lg flex items-center gap-3 ${battleState?.myActive.id === p.id ? 'bg-blue-900/50 border border-blue-500' : 'bg-slate-800'}`}>
                                <img
                                    src={`https://img.pokemondb.net/sprites/home/normal/${p.speciesId.toLowerCase()}.png`}
                                    className="w-12 h-12 object-contain"
                                    onError={(e) => (e.target as HTMLImageElement).style.display = 'none'}
                                />
                                <div>
                                    <div className="font-bold text-sm">{p.nickname}</div>
                                    <div className="text-xs text-gray-400">Lv. {p.level}</div>
                                    <div className="w-24 bg-gray-700 h-1.5 rounded-full mt-1">
                                        <div
                                            className={`h-full rounded-full ${p.currentHp / p.maxHp > 0.5 ? 'bg-green-500' : 'bg-red-500'}`}
                                            style={{ width: `${(p.currentHp / p.maxHp) * 100}%` }}
                                        />
                                    </div>
                                    <div className="text-xs text-right text-gray-500">{p.currentHp}/{p.maxHp}</div>
                                    {p.statusNum ? <span className="text-[10px] bg-purple-600 px-1 rounded ml-1">{getStatusName(p.statusNum)}</span> : null}
                                </div>
                            </div>
                        ))}
                        {playerParty.length === 0 && <div className="text-gray-500 italic">No party data. Sync to load.</div>}
                    </div>
                </div>

                {/* Center Column: Battle Arena (6 cols) */}
                <div className="col-span-6">
                    <h2 className="text-xl font-bold text-gray-300 border-b border-gray-700 pb-2 mb-4">Active Battle</h2>
                    {battleState ? (
                        <div className="bg-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
                            {/* Background decoration */}
                            <div className="absolute inset-0 bg-gradient-to-br from-slate-800 to-slate-900 z-0"></div>

                            <div className="relative z-10 flex justify-between items-end mb-8">
                                {/* Enemy */}
                                <div className="text-right">
                                    <div className="text-2xl font-bold text-red-400">{battleState.enemyActive.speciesId}</div>
                                    <div className="text-sm text-gray-400">Lv. {battleState.enemyActive.level}</div>
                                    <div className="w-48 bg-gray-700 h-3 rounded-full ml-auto mt-2 relative">
                                        <div
                                            className="h-full bg-red-500 rounded-full transition-all duration-500"
                                            style={{ width: `${(battleState.enemyActive.currentHp / battleState.enemyActive.maxHp) * 100}%` }}
                                        />
                                    </div>
                                    <div className="text-sm font-mono mt-1 mb-1">{battleState.enemyActive.currentHp}/{battleState.enemyActive.maxHp}</div>
                                    <div className="flex justify-end gap-2">
                                        {getStatusName(battleState.enemyActive.statusNum) && (
                                            <span className="px-2 py-0.5 bg-purple-600 rounded text-xs font-bold">{getStatusName(battleState.enemyActive.statusNum)}</span>
                                        )}
                                    </div>
                                    {renderStatStages(battleState.enemyActive.statStages)}
                                </div>
                                <img
                                    src={`https://img.pokemondb.net/sprites/home/normal/${battleState.enemyActive.speciesId.toLowerCase()}.png`}
                                    className="w-32 h-32 object-contain"
                                />
                            </div>

                            <div className="relative z-10 flex justify-between items-end mb-6">
                                {/* Player */}
                                <img
                                    src={`https://img.pokemondb.net/sprites/home/normal/${battleState.myActive.speciesId.toLowerCase()}.png`}
                                    className="w-32 h-32 object-contain"
                                />
                                <div>
                                    <div className="text-2xl font-bold text-blue-400">{battleState.myActive.nickname}</div>
                                    <div className="text-sm text-gray-400">Lv. {battleState.myActive.level}</div>
                                    <div className="w-48 bg-gray-700 h-3 rounded-full mt-2 relative">
                                        <div
                                            className="h-full bg-green-500 rounded-full transition-all duration-500"
                                            style={{ width: `${(battleState.myActive.currentHp / battleState.myActive.maxHp) * 100}%` }}
                                        />
                                    </div>
                                    <div className="text-sm font-mono mt-1 mb-1">{battleState.myActive.currentHp}/{battleState.myActive.maxHp}</div>
                                    <div className="flex gap-2">
                                        {getStatusName(battleState.myActive.statusNum) && (
                                            <span className="px-2 py-0.5 bg-purple-600 rounded text-xs font-bold">{getStatusName(battleState.myActive.statusNum)}</span>
                                        )}
                                    </div>
                                    {renderStatStages(battleState.myActive.statStages)}
                                </div>
                            </div>

                            {/* Damage Calculator */}
                            <div className="mt-4 grid grid-cols-2 gap-4">
                                {/* Player -> Enemy */}
                                <div className="bg-slate-900/50 p-3 rounded-lg">
                                    <h3 className="text-sm font-bold text-blue-300 mb-2">My Damage</h3>
                                    <div className="space-y-1">
                                        {battleState.myActive.moves.map(mId => {
                                            const move = MOVES[mId];
                                            if (!move || move.category === 'Status') return null;
                                            const result = calculateDamage(battleState.myActive, battleState.enemyActive, move);
                                            const minPct = ((result.min / battleState.enemyActive.maxHp) * 100).toFixed(1);
                                            const maxPct = ((result.max / battleState.enemyActive.maxHp) * 100).toFixed(1);
                                            return (
                                                <div key={mId} className="flex justify-between text-xs">
                                                    <span>{move.name}</span>
                                                    <span className={result.killChance >= 100 ? 'text-green-400 font-bold' : 'text-gray-300'}>
                                                        {minPct}% - {maxPct}%
                                                    </span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* Enemy -> Player */}
                                <div className="bg-slate-900/50 p-3 rounded-lg">
                                    <h3 className="text-sm font-bold text-red-300 mb-2">Enemy Damage</h3>
                                    <div className="space-y-1">
                                        {battleState.enemyActive.moves.map(mId => {
                                            const move = MOVES[mId];
                                            if (!move || move.category === 'Status') return null;
                                            const result = calculateDamage(battleState.enemyActive, battleState.myActive, move);
                                            const minPct = ((result.min / battleState.myActive.maxHp) * 100).toFixed(1);
                                            const maxPct = ((result.max / battleState.myActive.maxHp) * 100).toFixed(1);
                                            return (
                                                <div key={mId} className="flex justify-between text-xs">
                                                    <span>{move.name}</span>
                                                    <span className={result.killChance >= 100 ? 'text-red-400 font-bold' : 'text-gray-300'}>
                                                        {minPct}% - {maxPct}%
                                                    </span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>

                            {/* Advisor */}
                            <div className="mt-6 pt-6 border-t border-slate-700">
                                {!suggestion ? (
                                    <button
                                        onClick={getAdvice}
                                        className="w-full py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-bold shadow-lg"
                                    >
                                        ASK ADVISOR
                                    </button>
                                ) : (
                                    <div className="bg-purple-900/40 border border-purple-500 p-4 rounded-lg text-center animate-pulse">
                                        <div className="text-purple-300 text-sm uppercase tracking-wider font-bold mb-1">Suggested Action</div>
                                        <div className="text-2xl font-bold text-white">
                                            {suggestion.type === 'MOVE'
                                                ? `Use ${MOVES[suggestion.moveId!]?.name || suggestion.moveId}`
                                                : `Switch to ${playerParty.find(p => p.id === suggestion.switchTargetId)?.nickname}`}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="bg-slate-800 rounded-xl p-12 text-center text-gray-500 border-2 border-dashed border-slate-700">
                            No active battle detected.
                            <br />
                            Start a battle in-game and click "SYNC LIVE".
                        </div>
                    )}
                </div>

                {/* Right Column: Enemy Team (3 cols) */}
                <div className="col-span-3 space-y-4">
                    <h2 className="text-xl font-bold text-gray-300 border-b border-gray-700 pb-2">Enemy Team</h2>
                    <div className="space-y-2">
                        {enemyTeam.map((p, i) => (
                            <div key={i} className={`p-3 rounded-lg flex items-center gap-3 ${battleState?.enemyActive.id === p.id ? 'bg-red-900/30 border border-red-500' : 'bg-slate-800'}`}>
                                <img
                                    src={`https://img.pokemondb.net/sprites/home/normal/${p.speciesId.toLowerCase()}.png`}
                                    className="w-10 h-10 object-contain"
                                    onError={(e) => (e.target as HTMLImageElement).style.display = 'none'}
                                />
                                <div>
                                    <div className="font-bold text-sm">{p.speciesId}</div>
                                    <div className="text-xs text-gray-400">Lv. {p.level} • {p.nature}</div>
                                    <div className="flex gap-1 mt-1 flex-wrap">
                                        {p.moves.slice(0, 2).map(m => (
                                            <span key={m} className="text-[10px] bg-slate-700 px-1 rounded">{MOVES[m]?.name || m}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ))}
                        {enemyTeam.length === 0 && <div className="text-gray-500 italic">No enemy data.</div>}
                    </div>
                </div>
            </div>
        </main>
    );
}
