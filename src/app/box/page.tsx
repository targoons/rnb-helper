'use client';

import { useBoxStore } from '@/store/boxStore';
import AddPokemonForm from '@/components/AddPokemonForm';
import { POKEDEX } from '@/data/pokedex';
import { getPokemonStats } from '@/engine/stats';
import Link from 'next/link';
import { useState } from 'react';

export default function BoxPage() {
    const box = useBoxStore((state) => state.box);
    const removePokemon = useBoxStore((state) => state.removePokemon);
    const addPokemon = useBoxStore((state) => state.addPokemon);
    const clearBox = useBoxStore((state) => state.clearBox);

    const [importing, setImporting] = useState(false);
    const [isAdding, setIsAdding] = useState(false); // Added isAdding state

    const importFromLua = async () => {
        setImporting(true);
        try {
            // Clear existing box before import
            clearBox();

            const res = await fetch('/api/box');
            if (!res.ok) throw new Error('Failed to fetch');
            const data = await res.json();

            // Add imported pokemon to store
            let addedCount = 0;
            data.forEach((p: any) => {
                // Check if species exists in Pokedex (mapped correctly)
                // We might need to normalize the speciesId to match Pokedex keys (e.g. "Bulbasaur" -> "bulbasaur"?)
                // Pokedex keys are usually IDs like "bulbasaur".
                // The ID Map currently maps to "Bulbasaur" (Capitalized).
                // Let's check Pokedex keys.

                // Assuming Pokedex keys are lowercase names or IDs.
                // If POKEDEX["Bulbasaur"] is undefined, we need to lower case it.

                let speciesId = p.speciesId;
                if (!POKEDEX[speciesId] && POKEDEX[speciesId.toLowerCase()]) {
                    speciesId = speciesId.toLowerCase();
                }

                if (POKEDEX[speciesId]) {
                    // Create a clean instance
                    const newMon: any = {
                        id: p.id,
                        speciesId: speciesId,
                        nickname: p.nickname,
                        level: p.level,
                        currentHp: p.currentHp || 100, // Default if missing
                        maxHp: p.maxHp || 100,
                        moves: p.moves,
                        ivs: p.ivs,
                        evs: p.evs || { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
                        nature: p.nature,
                        ability: p.ability || 'Unknown',
                        item: p.heldItem ? String(p.heldItem) : undefined, // Map item later
                    };
                    addPokemon(newMon);
                    addedCount++;
                } else {
                    console.warn(`Skipping unknown species: ${p.speciesId}`);
                }
            });

            alert(`Successfully imported ${addedCount} Pokemon!`);
        } catch (e) {
            alert('Error importing box. Make sure Lua script ran.');
        } finally {
            setImporting(false);
        }
    };

    return (
        <main className="min-h-screen p-8 bg-slate-900 text-white">
            <div className="max-w-6xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-3xl font-bold">Pokemon Box</h1>
                    <div className="space-x-4">
                        <button
                            onClick={importFromLua}
                            disabled={importing}
                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded disabled:opacity-50"
                        >
                            {importing ? 'Importing...' : 'Import from Lua'}
                        </button>
                        <button
                            onClick={() => setIsAdding(!isAdding)}
                            className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded"
                        >
                            {isAdding ? 'Cancel' : 'Add Pokemon'}
                        </button>
                    </div>
                </div>

                {isAdding && (
                    <div className="mb-8 p-6 bg-slate-800 rounded-xl">
                        <AddPokemonForm onAdd={() => setIsAdding(false)} />
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {box.map((p) => (
                        <div key={p.id} className="bg-slate-800 p-4 rounded-lg flex items-start gap-4">
                            <img
                                src={`https://img.pokemondb.net/sprites/home/normal/${p.speciesId.toLowerCase()}.png`}
                                alt={p.speciesId}
                                className="w-20 h-20 object-contain"
                                onError={(e) => {
                                    (e.target as HTMLImageElement).style.display = 'none';
                                }}
                            />
                            <div className="flex-1">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h3 className="font-bold text-lg">{p.nickname}</h3>
                                        <p className="text-gray-400 text-sm">{p.speciesId} (Lv. {p.level})</p>
                                        <p className="text-purple-400 text-xs font-bold mt-1">{p.nature} Nature</p>
                                    </div>
                                    <button
                                        onClick={() => removePokemon(p.id)}
                                        className="text-red-400 hover:text-red-300 text-sm"
                                    >
                                        Release
                                    </button>
                                </div>

                                {/* Stats Grid */}
                                <div className="grid grid-cols-6 gap-1 mt-3 text-center text-xs bg-slate-900 p-2 rounded">
                                    <div className="text-gray-500">HP</div>
                                    <div className="text-gray-500">Atk</div>
                                    <div className="text-gray-500">Def</div>
                                    <div className="text-gray-500">SpA</div>
                                    <div className="text-gray-500">SpD</div>
                                    <div className="text-gray-500">Spe</div>

                                    {/* We need to calculate stats here if we want actual values, or just show IVs? 
                                        User asked for "stats". Let's show calculated stats. 
                                        We need to import getPokemonStats. */}
                                    {(() => {
                                        const stats = getPokemonStats(p);
                                        return (
                                            <>
                                                <div className="font-bold text-green-400">{stats.hp}</div>
                                                <div className="font-bold">{stats.atk}</div>
                                                <div className="font-bold">{stats.def}</div>
                                                <div className="font-bold">{stats.spa}</div>
                                                <div className="font-bold">{stats.spd}</div>
                                                <div className="font-bold text-blue-400">{stats.spe}</div>
                                            </>
                                        );
                                    })()}
                                </div>

                                <div className="flex gap-2 mt-3 flex-wrap">
                                    {p.moves.map(m => (
                                        <span key={m} className="text-xs bg-slate-700 px-2 py-1 rounded">{m}</span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ))}
                    {box.length === 0 && (
                        <div className="col-span-full text-center text-gray-500 py-12">
                            Box is empty. Add some Pokemon!
                        </div>
                    )}
                </div>
            </div>
        </main>
    );
}
