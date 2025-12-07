'use client';

import { useState, useEffect } from 'react';
import { useBoxStore } from '@/store/boxStore';
import { TRAINERS } from '@/data/trainers';
import { BattleState, Action } from '@/engine/battle';
import { getBestAction } from '@/solver/minimax';
import { PokemonInstance } from '@/data/types';
import { POKEDEX, MOVES } from '@/data/pokedex';
import { getPokemonStats } from '@/engine/stats';
import Link from 'next/link';

export default function BattlePage() {
    const box = useBoxStore((state) => state.box);
    const [battleState, setBattleState] = useState<BattleState | null>(null);
    const [suggestion, setSuggestion] = useState<Action | null>(null);
    const [log, setLog] = useState<string[]>([]);

    // Setup
    const [selectedMonId, setSelectedMonId] = useState<string>('');
    const [selectedTrainerId, setSelectedTrainerId] = useState<string>('roxanne');

    const startBattle = () => {
        const myMon = box.find(p => p.id === selectedMonId);
        const trainer = TRAINERS[selectedTrainerId];

        if (!myMon || !trainer) return;

        // Initialize HP for my team (if not already set correctly)
        // For box mons, we assume they are full HP or we should calc it.
        // Let's calc it to be safe.
        const myTeam = box.map(p => {
            const stats = getPokemonStats(p);
            return { ...p, currentHp: stats.hp };
        });
        const myActive = myTeam.find(p => p.id === selectedMonId)!;

        // Initialize HP for enemy team
        const enemyTeam = trainer.team.map(p => {
            const stats = getPokemonStats(p);
            return { ...p, currentHp: stats.hp };
        });
        const enemyActive = enemyTeam[0];

        // Create initial state
        const state = new BattleState(
            myActive,
            myTeam,
            enemyActive,
            enemyTeam
        );
        setBattleState(state);
        setLog(['Battle started!']);
    };

    const syncBattle = async () => {
        try {
            const res = await fetch('/api/battle');
            if (!res.ok) throw new Error('Failed to fetch battle data');
            const data = await res.json();
            console.log("Battle Data:", data);

            if (!data.enemyTeam || data.enemyTeam.length === 0) {
                alert('No enemy team found in battle data.');
                return;
            }

            // 1. Determine Player's Active Pokemon
            let myActive = battleState?.myActive;
            let myTeam = battleState?.myTeam || box; // Default to full box if no team set

            // Check if live data has active player mon info
            if (data.activeMons && data.activeMons.length > 0) {
                // Find the player's slot (usually 0 or 2)
                // We assume activeMons contains all active mons.
                // We need to distinguish friend from foe.
                // In single battles: Slot 0 = Player, Slot 1 = Enemy.
                const playerMonData = data.activeMons.find((m: any) => m.slot === 0 || m.slot === 2);
                console.log("Player Mon Data:", playerMonData);

                if (playerMonData) {
                    // Find matching pokemon in Team (Party or Box)
                    const found = myTeam.find(p =>
                        p.speciesId === playerMonData.speciesId &&
                        p.level === playerMonData.level
                    );
                    console.log("Found in Team:", found);

                    if (found) {
                        myActive = {
                            ...found,
                            currentHp: playerMonData.currentHp,
                            // Update stats from active mon if available (real stats)
                            stats: playerMonData.stats || found.stats
                        };
                        // Update team with active state
                        myTeam = myTeam.map(p => p.id === found.id ? myActive! : p);
                    } else {
                        console.warn("Could not find active player mon in Team:", playerMonData);
                    }
                }
            }

            if (!myActive) {
                console.log("No active mon found. Selected ID:", selectedMonId);
                // If no battle running and no live data found, try to use selected mon
                const selected = box.find(p => p.id === selectedMonId);
                if (selected) {
                    myActive = selected;
                } else {
                    // If we still don't have an active mon, we can't start/sync.
                    // But maybe we just show the enemy?
                    // For now, alert.
                    alert('Could not detect your active Pokemon. Please select one manually or ensure you are in battle.');
                    return;
                }
            }

            // 2. Construct Enemy Team from JSON
            const enemyTeam = data.enemyTeam.map((m: any) => ({
                id: 'enemy-' + Math.random(), // Temp ID
                speciesId: m.speciesId,
                nickname: m.nickname,
                level: m.level,
                currentHp: m.currentHp,
                nature: m.nature,
                ability: 'Unknown',
                item: m.item,
                moves: m.moves,
                ivs: m.ivs,
                evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
                stats: m.stats,
                maxHp: m.maxHp
            }));

            const enemyActive = enemyTeam[0];

            const newState = new BattleState(
                myActive!,
                myTeam!,
                enemyActive,
                enemyTeam
            );
            setBattleState(newState);
            setLog(prev => ['Synced with Live Battle!', ...prev]);

        } catch (e) {
            console.error("Sync Error:", e);
            alert('Error syncing battle. Check console for details.');
        }
    };

    const getAdvice = () => {
        if (!battleState) return;
        const action = getBestAction(battleState, 3); // Depth 3
        setSuggestion(action);
    };

    const applyTurn = () => {
        // In a real app, we'd ask "What did the enemy do?"
        // Here we just simulate one turn forward using the suggestion + random enemy move
        if (!battleState || !suggestion) return;

        // Simulate Enemy Move (Random for now)
        const enemyActions = battleState.getPossibleActions(false);
        const enemyAction = enemyActions[Math.floor(Math.random() * enemyActions.length)];

        const nextState = battleState.applyTurn(suggestion, enemyAction);
        setBattleState(nextState);

        setLog(prev => [
            `Turn ${nextState.turn}: You used ${suggestion.moveId || 'Switch'}, Enemy used ${enemyAction.moveId || 'Switch'}`,
            ...prev
        ]);
        setSuggestion(null);
    };

    if (!battleState) {
        return (
            <main className="min-h-screen p-8 bg-slate-900 text-white">
                <div className="max-w-2xl mx-auto">
                    <h1 className="text-3xl font-bold mb-8">Start Battle</h1>

                    <div className="space-y-4">
                        <div>
                            <label className="block mb-2">Select Your Lead</label>
                            <select
                                className="w-full p-2 bg-slate-700 rounded"
                                value={selectedMonId}
                                onChange={e => setSelectedMonId(e.target.value)}
                            >
                                <option value="">Select Pokemon...</option>
                                {box.map(p => (
                                    <option key={p.id} value={p.id}>{p.nickname} (Lv. {p.level})</option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block mb-2">Select Enemy Trainer</label>
                            <select
                                className="w-full p-2 bg-slate-700 rounded"
                                value={selectedTrainerId}
                                onChange={e => setSelectedTrainerId(e.target.value)}
                            >
                                {Object.values(TRAINERS).map(t => (
                                    <option key={t.id} value={t.id}>{t.name}</option>
                                ))}
                            </select>
                        </div>

                        <div className="flex gap-4">
                            <button
                                onClick={startBattle}
                                disabled={!selectedMonId}
                                className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 rounded font-bold disabled:opacity-50"
                            >
                                Start Battle
                            </button>
                            <button
                                onClick={syncBattle}
                                className="flex-1 py-3 bg-purple-600 hover:bg-purple-700 rounded font-bold"
                            >
                                Sync Live
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        );
    }

    const mySpecies = POKEDEX[battleState.myActive.speciesId];
    const enemySpecies = POKEDEX[battleState.enemyActive.speciesId];

    const myStats = getPokemonStats(battleState.myActive);
    const enemyStats = getPokemonStats(battleState.enemyActive);

    return (
        <main className="min-h-screen p-8 bg-slate-900 text-white">
            <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Battle View */}
                <div className="col-span-2 flex justify-between items-center bg-slate-800 p-8 rounded-xl">
                    <div className="flex flex-col items-center">
                        <div className="flex items-center gap-4">
                            <div className="relative">
                                <img
                                    src={`https://img.pokemondb.net/sprites/home/normal/${battleState.myActive.speciesId.toLowerCase()}.png`}
                                    alt={battleState.myActive.speciesId}
                                    className="w-24 h-24 object-contain"
                                    onError={(e) => (e.target as HTMLImageElement).style.display = 'none'}
                                />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold">{battleState.myActive.nickname}</h2>
                                <p className="text-gray-400">Lv. {battleState.myActive.level} {mySpecies?.name}</p>
                                <p className="text-purple-400 text-sm font-bold">{battleState.myActive.nature} Nature</p>
                            </div>
                        </div>
                        <div className="w-48 bg-gray-700 rounded-full h-4 mt-2 relative">
                            <div
                                className={`h-full rounded-full transition-all duration-500 ${(battleState.myActive.currentHp / battleState.myActive.maxHp) > 0.5 ? 'bg-green-500' :
                                    (battleState.myActive.currentHp / battleState.myActive.maxHp) > 0.2 ? 'bg-yellow-500' : 'bg-red-500'
                                    }`}
                                style={{ width: `${(battleState.myActive.currentHp / battleState.myActive.maxHp) * 100}%` }}
                            />
                            <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white drop-shadow-md">
                                {Math.ceil(battleState.myActive.currentHp)} / {battleState.myActive.maxHp}
                            </span>
                        </div>
                        {/* My Stats & Moves */}
                        <div className="mt-4 w-full bg-slate-900/50 p-3 rounded text-sm">
                            <div className="grid grid-cols-6 gap-1 text-center mb-2 text-xs">
                                <span className="text-gray-500">HP</span><span className="text-gray-500">Atk</span><span className="text-gray-500">Def</span>
                                <span className="text-gray-500">SpA</span><span className="text-gray-500">SpD</span><span className="text-gray-500">Spe</span>
                                <span className="font-bold text-green-400">{myStats.hp}</span>
                                <span className="font-bold">{myStats.atk}</span>
                                <span className="font-bold">{myStats.def}</span>
                                <span className="font-bold">{myStats.spa}</span>
                                <span className="font-bold">{myStats.spd}</span>
                                <span className="font-bold text-blue-400">{myStats.spe}</span>
                            </div>
                            <div className="flex flex-wrap gap-1 justify-center">
                                {battleState.myActive.moves.map(m => (
                                    <span key={m} className="px-2 py-1 bg-slate-700 rounded text-xs border border-slate-600">{m}</span>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="text-xl font-bold text-gray-500">VS</div>

                    <div className="flex flex-col items-center">
                        <div className="flex items-center gap-4">
                            <div>
                                <h2 className="text-2xl font-bold text-red-400">Enemy {enemySpecies?.name}</h2>
                                <p className="text-gray-400">Lv. {battleState.enemyActive.level}</p>
                                <p className="text-purple-400 text-sm font-bold text-right">{battleState.enemyActive.nature} Nature</p>
                            </div>
                            <div className="relative">
                                <img
                                    src={`https://img.pokemondb.net/sprites/home/normal/${battleState.enemyActive.speciesId.toLowerCase()}.png`}
                                    alt={battleState.enemyActive.speciesId}
                                    className="w-24 h-24 object-contain"
                                    onError={(e) => (e.target as HTMLImageElement).style.display = 'none'}
                                />
                            </div>
                        </div>
                        <div className="w-48 bg-gray-700 rounded-full h-4 mt-2 relative">
                            <div
                                className={`h-full rounded-full transition-all duration-500 ${(battleState.enemyActive.currentHp / battleState.enemyActive.maxHp) > 0.5 ? 'bg-green-500' :
                                    (battleState.enemyActive.currentHp / battleState.enemyActive.maxHp) > 0.2 ? 'bg-yellow-500' : 'bg-red-500'
                                    }`}
                                style={{ width: `${(battleState.enemyActive.currentHp / battleState.enemyActive.maxHp) * 100}%` }}
                            />
                            <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white drop-shadow-md">
                                {Math.ceil(battleState.enemyActive.currentHp)} / {battleState.enemyActive.maxHp}
                            </span>
                        </div>
                        {/* Enemy Stats & Moves */}
                        <div className="mt-4 w-full bg-slate-900/50 p-3 rounded text-sm">
                            <div className="grid grid-cols-6 gap-1 text-center mb-2 text-xs">
                                <span className="text-gray-500">HP</span><span className="text-gray-500">Atk</span><span className="text-gray-500">Def</span>
                                <span className="text-gray-500">SpA</span><span className="text-gray-500">SpD</span><span className="text-gray-500">Spe</span>
                                <span className="font-bold text-green-400">{enemyStats.hp}</span>
                                <span className="font-bold">{enemyStats.atk}</span>
                                <span className="font-bold">{enemyStats.def}</span>
                                <span className="font-bold">{enemyStats.spa}</span>
                                <span className="font-bold">{enemyStats.spd}</span>
                                <span className="font-bold text-blue-400">{enemyStats.spe}</span>
                            </div>
                            <div className="flex flex-wrap gap-1 justify-center">
                                {battleState.enemyActive.moves.map(m => (
                                    <span key={m} className="px-2 py-1 bg-red-900/50 rounded text-xs border border-red-800">{m}</span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Controls */}
                <div className="bg-slate-800 p-6 rounded-xl">
                    <h3 className="text-xl font-bold mb-4">Advisor</h3>

                    {!suggestion ? (
                        <button
                            onClick={getAdvice}
                            className="w-full py-3 bg-purple-600 hover:bg-purple-700 rounded font-bold mb-4"
                        >
                            Get AI Suggestion
                        </button>
                    ) : (
                        <div className="mb-4 p-4 bg-purple-900/50 border border-purple-500 rounded">
                            <p className="font-bold text-lg">Suggested Action:</p>
                            <p className="text-xl text-purple-200">
                                {suggestion.type === 'MOVE'
                                    ? `Use ${MOVES[suggestion.moveId!]?.name || suggestion.moveId}`
                                    : `Switch to ${box.find(p => p.id === suggestion.switchTargetId)?.nickname}`}
                            </p>
                            <button
                                onClick={applyTurn}
                                className="mt-4 w-full py-2 bg-green-600 hover:bg-green-700 rounded"
                            >
                                Apply & Next Turn
                            </button>
                        </div>
                    )}

                    <div className="mt-4">
                        <h4 className="font-bold mb-2">Battle Log</h4>
                        <div className="h-32 overflow-y-auto bg-slate-900 p-2 rounded text-sm font-mono text-gray-400">
                            {log.map((l, i) => <div key={i}>{l}</div>)}
                        </div>
                    </div>
                </div>

                {/* Manual Overrides (MVP) */}
                <div className="bg-slate-800 p-6 rounded-xl">
                    <h3 className="text-xl font-bold mb-4">Manual Adjustments</h3>
                    <p className="text-sm text-gray-400 mb-4">
                        If the simulation diverges (e.g. crit, miss), adjust HP manually.
                    </p>
                    <div className="grid grid-cols-2 gap-4">
                        <button className="p-2 bg-slate-700 rounded">Adjust My HP</button>
                        <button className="p-2 bg-slate-700 rounded">Adjust Enemy HP</button>
                    </div>
                </div>
            </div>
        </main>
    );
}
