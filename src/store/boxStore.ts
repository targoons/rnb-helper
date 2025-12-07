import { create } from 'zustand';
import { PokemonInstance } from '@/data/types';

interface BoxState {
    box: PokemonInstance[];
    addPokemon: (pokemon: PokemonInstance) => void;
    removePokemon: (id: string) => void;
    updatePokemon: (id: string, updates: Partial<PokemonInstance>) => void;
    clearBox: () => void;
}

export const useBoxStore = create<BoxState>((set) => ({
    box: [],
    addPokemon: (pokemon) =>
        set((state) => ({ box: [...state.box, pokemon] })),
    removePokemon: (id) =>
        set((state) => ({ box: state.box.filter((p) => p.id !== id) })),
    updatePokemon: (id, updates) =>
        set((state) => ({
            box: state.box.map((p) => (p.id === id ? { ...p, ...updates } : p)),
        })),
    clearBox: () => set({ box: [] }),
}));
