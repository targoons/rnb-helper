'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { BattleState, Action } from '@/engine/battle';
import { getBestAction, getEnemyPredictions, getBestSwitch } from '@/solver/minimax';

import MOVES_DATA from '@/data/moves.json';
const MOVES = MOVES_DATA as any;
import { POKEDEX } from '@/data/pokedex';
import { getPokemonStats } from '@/engine/stats';
import TRAINERS_DATA from '@/data/trainers.json';
const TRAINERS = TRAINERS_DATA as Record<string, any>;
import BOX_DATA from '@/data/imports/box.json';
const BOX = BOX_DATA as any[];

interface BattleNode {
    id: string;
    parentId: string | null;
    state: BattleState;
    myAction: Action | null; // Action taken to reach this state (null for root)
    enemyAction: Action | null;
    children: string[];
    turnNumber: number;
    probability?: number; // Probability of this specific enemy action occurring
}

export default function PlannerPage() {
    const [nodes, setNodes] = useState<Record<string, BattleNode>>({});
    const [rootId, setRootId] = useState<string | null>(null);
    const [currentNodeId, setCurrentNodeId] = useState<string | null>(null);

    // Modals
    const [showTrainerModal, setShowTrainerModal] = useState(false);
    const [showTeamBuilderModal, setShowTeamBuilderModal] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [builderTeam, setBuilderTeam] = useState<any[]>([]);

    // Inputs for next turn
    const [mySelectedAction, setMySelectedAction] = useState<Action | null>(null);
    // Enemy action is now auto-determined, but we can keep a manual override if needed.
    // For this "sophisticated" version, let's focus on the auto-branching.

    useEffect(() => {
        // Initial Load (Default or from LocalStorage)
        const stored = localStorage.getItem('plannerInitialState');
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                const state = new BattleState(
                    parsed.myActive,
                    parsed.myTeam,
                    parsed.enemyActive,
                    parsed.enemyTeam,
                    parsed.turn
                );
                initializeTree(state);
            } catch (e) {
                console.error('Failed to load planner state', e);
            }
        }
    }, []);

    const initializeTree = (state: BattleState) => {
        const root: BattleNode = {
            id: 'root',
            parentId: null,
            state: state,
            myAction: null,
            enemyAction: null,
            children: [],
            turnNumber: 0,
            probability: 100
        };
        setNodes({ 'root': root });
        setRootId('root');
        setCurrentNodeId('root');
    };

    const loadTrainerTeam = (trainerId: string) => {
        const trainer = TRAINERS[trainerId];
        if (!trainer || !currentNodeId) return;

        // Convert Trainer JSON to PokemonInstance[]
        const enemyTeam = trainer.team.map((p: any) => {
            const base = {
                id: `enemy-${p.speciesId}-${Math.random()}`,
                speciesId: p.speciesId,
                nickname: p.speciesId,
                level: p.level,
                nature: p.nature,
                ability: p.ability,
                item: p.item,
                moves: p.moves.map((m: string) => {
                    const entry = Object.entries(MOVES).find(([_, v]: any) => v.name === m);
                    return entry ? entry[0] : '1';
                }),
                ivs: p.ivs || { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 },
                evs: p.evs || { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
            };
            // Calculate stats WITHOUT passing a placeholder 'stats' property
            const stats = getPokemonStats(base as any);
            return {
                ...base,
                stats: stats,
                maxHp: stats.hp,
                currentHp: stats.hp
            };
        });

        const enemyActive = enemyTeam[0];

        // Update Current State with New Enemy Team
        // We are "resetting" the battle with this new enemy
        if (nodes[currentNodeId]) {
            const currentState = nodes[currentNodeId].state;
            const newState = new BattleState(
                currentState.myActive,
                currentState.myTeam,
                enemyActive,
                enemyTeam,
                0 // Reset turn to 0
            );
            initializeTree(newState);
            setShowTrainerModal(false);
        }
    };

    // Auto-save nodes (Optional)
    useEffect(() => {
        if (rootId) {
            // We could save the whole tree, but BattleState is complex to serialize/deserialize fully with methods.
            // For now, we rely on rehydration from initial state + actions? 
            // Or just save the nodes map.
            // localStorage.setItem('plannerTree', JSON.stringify(nodes));
        }
    }, [nodes, rootId]);

    const addToTeam = (pokemon: any) => {
        if (builderTeam.length >= 6) return;
        const newMon = {
            ...pokemon,
            id: `my-${pokemon.speciesId}-${Math.random()}`,
            currentHp: 100, // Placeholder
            maxHp: 100,     // Placeholder
            stats: getPokemonStats(pokemon)
        };
        newMon.maxHp = newMon.stats.hp;
        newMon.currentHp = newMon.stats.hp;
        setBuilderTeam([...builderTeam, newMon]);
    };

    const confirmTeam = () => {
        if (builderTeam.length === 0 || !currentNodeId) return;

        const currentState = nodes[currentNodeId].state;
        const newState = new BattleState(
            builderTeam[0],
            builderTeam,
            currentState.enemyActive,
            currentState.enemyTeam,
            0
        );
        initializeTree(newState);
        setShowTeamBuilderModal(false);
    };

    const handleNextTurn = () => {
        if (!currentNodeId || !nodes[currentNodeId]) return;

        const currentNode = nodes[currentNodeId];
        const currentState = currentNode.state;

        // Handle Force Switch Phase
        if (currentState.forceSwitch) {
            let myAction = mySelectedAction;
            let enemyAction: Action | null = null;

            // If I need to switch and haven't selected, return
            if (currentState.myActive.currentHp === 0 && !myAction) return;

            // If I don't need to switch, I do nothing (pass a dummy action or null?)
            // Actually applyTurn expects actions. If I'm not switching, I'm waiting.
            // But applyTurn handles "dead mon can't move".
            // We should pass a dummy action if we are not the one switching.
            if (currentState.myActive.currentHp > 0) {
                myAction = { type: 'MOVE', priority: 0, moveId: 'wait' }; // Dummy
            }

            // Enemy Switch
            if (currentState.enemyActive.currentHp === 0) {
                // Predict Enemy Switch
                enemyAction = getBestSwitch(currentState, false);
            } else {
                enemyAction = { type: 'MOVE', priority: 0, moveId: 'wait' }; // Dummy
            }

            if (!myAction || !enemyAction) return;

            const nextState = currentState.applyTurn(myAction, enemyAction);

            const newNodeId = `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            const newNode: BattleNode = {
                id: newNodeId,
                parentId: currentNodeId,
                state: nextState,
                myAction: myAction,
                enemyAction: enemyAction,
                children: [],
                turnNumber: currentNode.turnNumber, // Turn doesn't increment on switch phase usually? Or does it? 
                // In competitive, replacing a fainted mon doesn't take a turn.
                // But our engine increments turn in applyTurn.
                // Let's keep it consistent with engine for now.
                probability: 100
            };

            const newNodes = { ...nodes };
            newNodes[newNodeId] = newNode;
            newNodes[currentNodeId] = {
                ...currentNode,
                children: [...currentNode.children, newNodeId]
            };

            setNodes(newNodes);
            setCurrentNodeId(newNodeId);
            setMySelectedAction(null);
            return;
        }

        if (!mySelectedAction) return;

        // Standard Turn Logic (Predictions)
        // 1. Get Enemy Predictions (Probabilities)
        const predictions = getEnemyPredictions(currentState, 2); // Depth 2 for prediction

        // If no predictions (e.g. struggle?), default to something?
        // getEnemyPredictions should always return at least one action if possible.

        const newNodes = { ...nodes };
        const newChildrenIds: string[] = [];

        // 2. Create a branch for EACH prediction
        predictions.forEach(pred => {
            const enemyAction = pred;
            const probability = pred.probability || 0;

            // Apply Turn
            const nextState = currentState.applyTurn(mySelectedAction, enemyAction);

            // Create New Node
            const newNodeId = `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            const newNode: BattleNode = {
                id: newNodeId,
                parentId: currentNodeId,
                state: nextState,
                myAction: mySelectedAction,
                enemyAction: enemyAction,
                children: [],
                turnNumber: currentNode.turnNumber + 1,
                probability: probability
            };

            newNodes[newNodeId] = newNode;
            newChildrenIds.push(newNodeId);
        });

        // Update Parent's children
        newNodes[currentNodeId] = {
            ...currentNode,
            children: [...currentNode.children, ...newChildrenIds]
        };

        setNodes(newNodes);

        // Auto-navigate to the most likely branch?
        // Or stay on current and let user choose?
        // Let's navigate to the highest probability one for convenience.
        if (newChildrenIds.length > 0) {
            setCurrentNodeId(newChildrenIds[0]);
        }

        setMySelectedAction(null);
    };

    const handleAutoPlay = () => {
        if (!currentNodeId || !nodes[currentNodeId]) return;

        let currentId = currentNodeId;
        let state = nodes[currentId].state;
        let newNodes = { ...nodes };

        // Simulate up to 5 turns
        for (let i = 0; i < 5; i++) {
            if (state.myActive.currentHp <= 0 || state.enemyActive.currentHp <= 0) break;

            const myAction = getBestAction(state, 3);
            const enemyPredictions = getEnemyPredictions(state, 2);
            const enemyAction = enemyPredictions[0];

            if (!myAction || !enemyAction) break;

            const nextState = state.applyTurn(myAction, enemyAction);
            const newNodeId = `node-${Date.now()}-${i}`;

            const newNode: BattleNode = {
                id: newNodeId,
                parentId: currentId,
                state: nextState,
                myAction: myAction,
                enemyAction: enemyAction,
                children: [],
                turnNumber: newNodes[currentId].turnNumber + 1
            };

            newNodes[newNodeId] = newNode;
            newNodes[currentId] = {
                ...newNodes[currentId],
                children: [...newNodes[currentId].children, newNodeId]
            };

            currentId = newNodeId;
            state = nextState;
        }

        setNodes(newNodes);
        setCurrentNodeId(currentId);
    };

    const navigateToNode = (nodeId: string) => {
        if (nodes[nodeId]) {
            setCurrentNodeId(nodeId);
        }
    };

    // Get Active Path (Root -> Current)
    const activePath: BattleNode[] = [];
    let ptr = currentNodeId;
    while (ptr && nodes[ptr]) {
        activePath.unshift(nodes[ptr]);
        ptr = nodes[ptr].parentId;
    }

    // Risk Analysis on Active Path
    const riskReport = (() => {
        if (activePath.length <= 1) return null; // Root only
        let minHpPercent = 100;
        let riskLevel = 'Safe';
        let riskReason = '';

        activePath.forEach((node, i) => {
            if (i === 0) return; // Skip root (initial state)
            const myHp = node.state.myActive.currentHp;
            const myMax = node.state.myActive.maxHp;
            const pct = (myHp / myMax) * 100;
            if (pct < minHpPercent) minHpPercent = pct;

            if (pct < 30) {
                riskLevel = 'Dangerous';
                riskReason = `Low HP on Turn ${node.turnNumber}`;
            } else if (pct < 50 && riskLevel !== 'Dangerous') {
                riskLevel = 'Risky';
                riskReason = `Below 50% HP on Turn ${node.turnNumber}`;
            }
        });

        return { minHpPercent, riskLevel, riskReason };
    })();

    if (!rootId || !currentNodeId || !nodes[currentNodeId]) {
        return <div className="p-8 text-white">Loading planner... (Go back to Dashboard and click 'Plan Line')</div>;
    }

    const currentNode = nodes[currentNodeId];
    const currentState = currentNode.state;

    const myMoves = currentState.getPossibleActions(true);
    const enemyMoves = currentState.getPossibleActions(false);

    return (
        <main className="min-h-screen p-4 bg-slate-900 text-white flex flex-col gap-4">
            {/* Header */}
            <div className="flex justify-between items-center border-b border-slate-700 pb-4">
                <h1 className="text-2xl font-bold flex items-center gap-2">
                    <span>📝</span> Battle Planner
                </h1>
                <div className="flex gap-4">
                    <button onClick={() => setShowTrainerModal(true)} className="px-4 py-2 bg-red-700 hover:bg-red-600 rounded text-sm font-bold">
                        VS Load Enemy Trainer
                    </button>
                    <button onClick={() => setShowTeamBuilderModal(true)} className="px-4 py-2 bg-blue-700 hover:bg-blue-600 rounded text-sm font-bold">
                        My Team Builder
                    </button>
                    <Link href="/" className="text-blue-400 hover:underline text-sm flex items-center">
                        &larr; Dashboard
                    </Link>
                </div>
            </div>

            {/* Trainer Modal */}
            {showTrainerModal && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
                    <div className="bg-slate-800 p-6 rounded-xl w-[600px] max-h-[80vh] flex flex-col">
                        <h2 className="text-xl font-bold mb-4">Select Enemy Trainer</h2>
                        <input
                            type="text"
                            placeholder="Search Trainer..."
                            className="w-full p-2 bg-slate-700 rounded mb-4"
                            onChange={(e) => setSearchTerm(e.target.value.toLowerCase())}
                        />
                        <div className="overflow-y-auto flex-1 space-y-2">
                            {Object.values(TRAINERS)
                                .filter((t: any) => t.name.toLowerCase().includes(searchTerm))
                                .map((t: any) => (
                                    <button
                                        key={t.id}
                                        onClick={() => loadTrainerTeam(t.id)}
                                        className="w-full text-left p-3 bg-slate-700 hover:bg-slate-600 rounded flex justify-between items-center"
                                    >
                                        <span className="font-bold">{t.name}</span>
                                        <span className="text-xs text-gray-400">{t.team.length} Pokemon</span>
                                    </button>
                                ))}
                        </div>
                        <button onClick={() => setShowTrainerModal(false)} className="mt-4 text-red-400 hover:underline">Close</button>
                    </div>
                </div>
            )}

            {/* Team Builder Modal */}
            {showTeamBuilderModal && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
                    <div className="bg-slate-800 p-6 rounded-xl w-[800px] max-h-[80vh] flex flex-col">
                        <h2 className="text-xl font-bold mb-4">My Team Builder ({builderTeam.length}/6)</h2>

                        <div className="grid grid-cols-2 gap-4 flex-1 overflow-hidden">
                            {/* Box */}
                            <div className="flex flex-col border-r border-slate-700 pr-4">
                                <h3 className="font-bold mb-2 text-blue-300">Box</h3>
                                <div className="overflow-y-auto space-y-2 flex-1">
                                    {BOX.map((p: any, i) => (
                                        <div key={i} className="p-3 bg-slate-700 rounded flex justify-between items-center">
                                            <span>{p.nickname || p.speciesId} (Lv. {p.level})</span>
                                            <button
                                                onClick={() => addToTeam(p)}
                                                disabled={builderTeam.length >= 6}
                                                className="text-xs bg-green-700 hover:bg-green-600 px-2 py-1 rounded disabled:opacity-50"
                                            >
                                                Add
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Current Team */}
                            <div className="flex flex-col pl-4">
                                <h3 className="font-bold mb-2 text-green-300">New Team</h3>
                                <div className="space-y-2 flex-1 overflow-y-auto">
                                    {builderTeam.map((p, i) => (
                                        <div key={p.id} className="p-3 bg-slate-700 rounded flex justify-between items-center border border-green-900">
                                            <span>{p.nickname}</span>
                                            <button
                                                onClick={() => setBuilderTeam(builderTeam.filter((_, idx) => idx !== i))}
                                                className="text-xs text-red-400 hover:underline"
                                            >
                                                Remove
                                            </button>
                                        </div>
                                    ))}
                                    {builderTeam.length === 0 && <div className="text-gray-500 italic">No Pokemon selected</div>}
                                </div>
                                <button
                                    onClick={confirmTeam}
                                    disabled={builderTeam.length === 0}
                                    className="mt-4 w-full py-2 bg-blue-600 hover:bg-blue-700 rounded font-bold disabled:bg-slate-700 disabled:text-gray-500"
                                >
                                    Confirm Team & Start Battle
                                </button>
                            </div>
                        </div>

                        <button onClick={() => setShowTeamBuilderModal(false)} className="mt-4 text-red-400 hover:underline self-center">Close</button>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
                {/* Left: Simulator Controls */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Battle View */}
                    <div className="grid grid-cols-2 gap-4">
                        {/* Me */}
                        <div className="bg-slate-800 p-4 rounded-xl border border-blue-900 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-2 opacity-10">
                                <img src="/pokeball.png" className="w-32 h-32" />
                            </div>
                            <h2 className="text-blue-300 font-bold mb-2 flex justify-between">
                                <span>My Active</span>
                                <span className="text-xs bg-blue-900 px-2 py-1 rounded text-blue-200">Lv. {currentState.myActive.level}</span>
                            </h2>
                            <div className="flex items-center gap-4 relative z-10">
                                <img src={`https://img.pokemondb.net/sprites/home/normal/${currentState.myActive.speciesId.toLowerCase()}.png`} className="w-20 h-20" />
                                <div className="flex-1">
                                    <div className="font-bold text-lg">{currentState.myActive.nickname}</div>
                                    <div className="text-xs text-gray-400 mb-1">
                                        {currentState.myActive.item ? `Item: ${currentState.myActive.item}` : 'No Item'}
                                    </div>
                                    <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden mb-1">
                                        <div
                                            className={`h-full ${currentState.myActive.currentHp / currentState.myActive.maxHp < 0.2 ? 'bg-red-500' : currentState.myActive.currentHp / currentState.myActive.maxHp < 0.5 ? 'bg-yellow-500' : 'bg-green-500'}`}
                                            style={{ width: `${(currentState.myActive.currentHp / currentState.myActive.maxHp) * 100}%` }}
                                        />
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span>{currentState.myActive.currentHp}/{currentState.myActive.maxHp} HP</span>
                                        {currentState.myActive.status && <span className="px-1 bg-purple-600 rounded text-xs">{currentState.myActive.status}</span>}
                                    </div>
                                    {/* Stat Stages */}
                                    <div className="flex gap-1 mt-2 text-[10px] text-gray-400">
                                        {Object.entries(currentState.myActive.statStages || {}).map(([stat, val]) => {
                                            if (val === 0) return null;
                                            return <span key={stat} className={val > 0 ? 'text-green-400' : 'text-red-400'}>{stat.toUpperCase()} {val > 0 ? '+' : ''}{val}</span>
                                        })}
                                    </div>
                                </div>
                            </div>
                        </div>
                        {/* Enemy */}
                        <div className="bg-slate-800 p-4 rounded-xl border border-red-900 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-2 opacity-10">
                                <img src="/pokeball.png" className="w-32 h-32" />
                            </div>
                            <h2 className="text-red-300 font-bold mb-2 flex justify-between">
                                <span>Enemy Active</span>
                                <span className="text-xs bg-red-900 px-2 py-1 rounded text-red-200">Lv. {currentState.enemyActive.level}</span>
                            </h2>
                            <div className="flex items-center gap-4 relative z-10">
                                <img src={`https://img.pokemondb.net/sprites/home/normal/${currentState.enemyActive.speciesId.toLowerCase()}.png`} className="w-20 h-20" />
                                <div className="flex-1">
                                    <div className="font-bold text-lg">{currentState.enemyActive.speciesId}</div>
                                    <div className="text-xs text-gray-400 mb-1">
                                        {currentState.enemyActive.item ? `Item: ${currentState.enemyActive.item}` : 'No Item'}
                                    </div>
                                    <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden mb-1">
                                        <div
                                            className={`h-full ${currentState.enemyActive.currentHp / currentState.enemyActive.maxHp < 0.2 ? 'bg-red-500' : currentState.enemyActive.currentHp / currentState.enemyActive.maxHp < 0.5 ? 'bg-yellow-500' : 'bg-green-500'}`}
                                            style={{ width: `${(currentState.enemyActive.currentHp / currentState.enemyActive.maxHp) * 100}%` }}
                                        />
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span>{currentState.enemyActive.currentHp}/{currentState.enemyActive.maxHp} HP</span>
                                        {currentState.enemyActive.status && <span className="px-1 bg-purple-600 rounded text-xs">{currentState.enemyActive.status}</span>}
                                    </div>
                                    {/* Stat Stages */}
                                    <div className="flex gap-1 mt-2 text-[10px] text-gray-400">
                                        {Object.entries(currentState.enemyActive.statStages || {}).map(([stat, val]) => {
                                            if (val === 0) return null;
                                            return <span key={stat} className={val > 0 ? 'text-green-400' : 'text-red-400'}>{stat.toUpperCase()} {val > 0 ? '+' : ''}{val}</span>
                                        })}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Action Selection or Force Switch */}
                    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                        {currentState.forceSwitch ? (
                            <div>
                                <h3 className="font-bold text-lg mb-4 text-yellow-400">⚠️ Switch Phase</h3>
                                <div className="grid grid-cols-2 gap-6">
                                    {/* My Switch */}
                                    {currentState.myActive.currentHp === 0 ? (
                                        <div>
                                            <label className="block text-blue-300 text-sm font-bold mb-2">Choose Replacement</label>
                                            <div className="space-y-2">
                                                {currentState.myTeam.filter(p => p.currentHp > 0 && p.id !== currentState.myActive.id).map(p => (
                                                    <button
                                                        key={p.id}
                                                        onClick={() => {
                                                            const action: Action = { type: 'SWITCH', switchTargetId: p.id, priority: 6 };
                                                            setMySelectedAction(action);
                                                        }}
                                                        className={`w-full p-3 rounded text-left flex justify-between items-center border ${mySelectedAction?.switchTargetId === p.id
                                                            ? 'bg-blue-900 border-blue-500'
                                                            : 'bg-slate-700 border-slate-600 hover:bg-slate-600'
                                                            }`}
                                                    >
                                                        <span className="font-bold">{p.nickname}</span>
                                                        <span className="text-sm">{p.currentHp}/{p.maxHp} HP</span>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="opacity-50">
                                            <label className="block text-blue-300 text-sm font-bold mb-2">My Active</label>
                                            <div className="p-2 bg-slate-700 rounded border border-slate-600">
                                                {currentState.myActive.nickname} is active.
                                            </div>
                                        </div>
                                    )}

                                    {/* Enemy Switch */}
                                    {currentState.enemyActive.currentHp === 0 ? (
                                        <div>
                                            <label className="block text-red-300 text-sm font-bold mb-2">Enemy Replacement (Predicted)</label>
                                            <div className="p-2 bg-slate-700 rounded border border-slate-600 text-gray-400 text-sm italic">
                                                AI will choose the best counter.
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="opacity-50">
                                            <label className="block text-red-300 text-sm font-bold mb-2">Enemy Active</label>
                                            <div className="p-2 bg-slate-700 rounded border border-slate-600">
                                                {currentState.enemyActive.speciesId} is active.
                                            </div>
                                        </div>
                                    )}
                                </div>
                                <div className="mt-6">
                                    <button
                                        onClick={handleNextTurn}
                                        disabled={currentState.myActive.currentHp === 0 && !mySelectedAction}
                                        className="w-full py-3 bg-yellow-600 hover:bg-yellow-700 disabled:bg-slate-700 disabled:text-gray-500 rounded-lg font-bold shadow-lg transition-colors"
                                    >
                                        Execute Switch &rarr;
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <>
                                <h3 className="font-bold text-lg mb-4">Plan Next Turn</h3>
                                <div className="grid grid-cols-2 gap-6">
                                    <div>
                                        <label className="block text-blue-300 text-sm font-bold mb-2">My Action</label>
                                        <select
                                            className="w-full p-2 bg-slate-700 rounded border border-slate-600"
                                            onChange={(e) => {
                                                const idx = parseInt(e.target.value);
                                                setMySelectedAction(myMoves[idx]);
                                            }}
                                            value={mySelectedAction ? myMoves.indexOf(mySelectedAction) : ''}
                                        >
                                            <option value="">Select Action...</option>
                                            {myMoves.map((a, i) => (
                                                <option key={i} value={i}>
                                                    {a.type === 'MOVE' ? `Use ${MOVES[a.moveId!]?.name || a.moveId}` : `Switch to ${currentState.myTeam.find(p => p.id === a.switchTargetId)?.nickname}`}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-red-300 text-sm font-bold mb-2">Enemy Action (Auto-Predicted)</label>
                                        <div className="p-2 bg-slate-700 rounded border border-slate-600 text-gray-400 text-sm italic">
                                            The AI will automatically generate branches for all likely enemy moves based on probability.
                                        </div>
                                    </div>
                                </div>
                                <div className="flex gap-4 mt-6">
                                    <button
                                        onClick={handleNextTurn}
                                        disabled={!mySelectedAction}
                                        className="flex-1 py-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-700 disabled:text-gray-500 rounded-lg font-bold shadow-lg transition-colors"
                                    >
                                        Simulate Turn &rarr;
                                    </button>
                                    <button
                                        onClick={handleAutoPlay}
                                        className="flex-1 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-bold shadow-lg transition-colors flex items-center justify-center gap-2"
                                    >
                                        <span>🪄</span> Auto-Play (Solve)
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Right: Timeline */}
                <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 h-full overflow-y-auto">
                    <h2 className="text-xl font-bold mb-4 flex justify-between items-center">
                        <span>Timeline (Tree)</span>
                        <button onClick={() => rootId && navigateToNode(rootId)} className="text-xs text-red-400 hover:underline">Reset to Start</button>
                    </h2>

                    {/* Risk Report */}
                    {riskReport && (
                        <div className={`mb-4 p-3 rounded border ${riskReport.riskLevel === 'Dangerous' ? 'bg-red-900/50 border-red-500' :
                            riskReport.riskLevel === 'Risky' ? 'bg-yellow-900/50 border-yellow-500' :
                                'bg-green-900/50 border-green-500'
                            }`}>
                            <div className="flex justify-between items-center mb-1">
                                <span className="font-bold text-sm uppercase tracking-wider">Line Analysis</span>
                                <span className={`text-xs font-bold px-2 py-0.5 rounded ${riskReport.riskLevel === 'Dangerous' ? 'bg-red-600' :
                                    riskReport.riskLevel === 'Risky' ? 'bg-yellow-600' :
                                        'bg-green-600'
                                    }`}>{riskReport.riskLevel}</span>
                            </div>
                            <div className="text-xs text-gray-300">
                                Min HP: {riskReport.minHpPercent.toFixed(1)}%
                                {riskReport.riskReason && ` • ${riskReport.riskReason}`}
                            </div>
                        </div>
                    )}

                    <div className="space-y-4 relative">
                        {/* Vertical Line */}
                        <div className="absolute left-4 top-2 bottom-2 w-0.5 bg-slate-600" />

                        {activePath.map((node, i) => {
                            if (i === 0) return null; // Skip root for display (it's the start state)

                            const isCurrent = node.id === currentNodeId;
                            const hasChildren = node.children.length > 0;
                            const prob = node.probability !== undefined ? node.probability : 100;

                            return (
                                <div key={node.id} className="relative pl-10 group">
                                    {/* Dot */}
                                    <div
                                        className={`absolute left-[13px] top-3 w-2 h-2 rounded-full ring-4 ring-slate-800 cursor-pointer transition-colors ${isCurrent ? 'bg-green-500 ring-green-900' : 'bg-blue-500 hover:bg-yellow-400'
                                            }`}
                                        onClick={() => navigateToNode(node.id)}
                                    />

                                    <div
                                        className={`p-3 rounded text-sm relative border ${isCurrent ? 'bg-slate-700 border-green-500' : 'bg-slate-700 border-transparent hover:border-slate-500'
                                            }`}
                                        onClick={() => navigateToNode(node.id)}
                                    >
                                        <div className="font-bold text-gray-300 mb-1 flex justify-between">
                                            <span>Turn {node.turnNumber}</span>
                                            <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-gray-400 border border-slate-600">
                                                {prob.toFixed(0)}% Chance
                                            </span>
                                        </div>
                                        <div className="text-blue-300">
                                            You: {node.myAction?.type === 'MOVE' ? MOVES[node.myAction.moveId!]?.name : 'Switch'}
                                        </div>
                                        <div className="text-red-300">
                                            Enemy: {node.enemyAction?.type === 'MOVE' ? MOVES[node.enemyAction.moveId!]?.name : 'Switch'}
                                        </div>

                                        {/* Branch Navigation (Siblings) */}
                                        {node.parentId && nodes[node.parentId].children.length > 1 && (
                                            <div className="mt-2 pt-2 border-t border-slate-600 flex gap-2 overflow-x-auto">
                                                {nodes[node.parentId].children.map(childId => {
                                                    const child = nodes[childId];
                                                    if (child.id === node.id) return null; // Skip self
                                                    return (
                                                        <button
                                                            key={childId}
                                                            onClick={(e) => { e.stopPropagation(); navigateToNode(childId); }}
                                                            className="text-[10px] px-2 py-1 bg-slate-800 hover:bg-slate-600 rounded border border-slate-600 whitespace-nowrap"
                                                        >
                                                            Switch to {child.probability?.toFixed(0)}% Branch
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}

                        {/* Current State Marker */}
                        <div className="relative pl-10">
                            <div className="absolute left-[11px] top-3 w-3 h-3 rounded-full bg-green-500 ring-4 ring-slate-800 animate-pulse" />
                            <div className="text-green-400 font-bold text-sm pt-2">
                                Current State
                                {currentNode.children.length > 0 && (
                                    <div className="text-xs text-gray-400 font-normal mt-1">
                                        (You are viewing a past state. Simulating will create new branches.)
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
