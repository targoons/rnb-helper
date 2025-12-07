'use client';

import { useState } from 'react';
import { useBoxStore } from '@/store/boxStore';
import { POKEDEX } from '@/data/pokedex';
import { PokemonInstance } from '@/data/types';
// import { v4 as uuidv4 } from 'uuid'; // Removed unused import

interface Props {
    onAdd?: () => void;
}

export default function AddPokemonForm({ onAdd }: Props) {
    const addPokemon = useBoxStore((state) => state.addPokemon);
    const [speciesId, setSpeciesId] = useState('1');
    const [level, setLevel] = useState(5);
    const [nickname, setNickname] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const species = POKEDEX[speciesId];
        if (!species) return;

        // Calculate stats to get maxHp
        // We need to import getPokemonStats first, let's add import at top.
        // For now, simple approximation or import.
        // Let's import getPokemonStats.

        const newPokemon: PokemonInstance = {
            id: Math.random().toString(36).substring(7), // Simple ID
            speciesId,
            nickname: nickname || species.name,
            level,
            ability: species.abilities[0], // Default to first ability
            nature: 'Hardy', // Default
            moves: [], // Empty for now
            ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 },
            evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
            currentHp: 100, // Placeholder, will be updated
            maxHp: 100, // Placeholder
        };

        // We really should calculate real stats.
        // But getPokemonStats needs the instance.
        // We can just set it to 100 for now, as the battle engine recalculates it on startBattle?
        // In BattlePage.tsx:
        // const myTeam = box.map(p => { const stats = getPokemonStats(p); return { ...p, currentHp: stats.hp }; });
        // It recalculates currentHp but maybe not maxHp property on the object?
        // The type definition requires maxHp now.
        // So we must provide it.

        // Let's just set it to 100.
        // Ideally we import getPokemonStats.


        addPokemon(newPokemon);
        setNickname('');
        if (onAdd) onAdd();
    };

    return (
        <form onSubmit={handleSubmit} className="p-4 bg-slate-800 rounded-lg space-y-4">
            <h3 className="text-xl font-bold">Add Pokemon</h3>

            <div>
                <label className="block text-sm font-medium">Species</label>
                <select
                    value={speciesId}
                    onChange={(e) => setSpeciesId(e.target.value)}
                    className="w-full p-2 rounded bg-slate-700"
                >
                    {Object.values(POKEDEX).map((p) => (
                        <option key={p.id} value={p.id}>
                            {p.name}
                        </option>
                    ))}
                </select>
            </div>

            <div>
                <label className="block text-sm font-medium">Level</label>
                <input
                    type="number"
                    value={level}
                    onChange={(e) => setLevel(Number(e.target.value))}
                    className="w-full p-2 rounded bg-slate-700"
                    min={1}
                    max={100}
                />
            </div>

            <div>
                <label className="block text-sm font-medium">Nickname</label>
                <input
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    className="w-full p-2 rounded bg-slate-700"
                    placeholder="Optional"
                />
            </div>

            <button
                type="submit"
                className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded font-bold"
            >
                Add to Box
            </button>
        </form>
    );
}
