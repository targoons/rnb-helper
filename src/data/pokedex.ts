import { PokemonSpecies, Move } from './types';
import pokedexData from './pokedex.json';
import movesData from './moves.json';

export const POKEDEX: Record<string, PokemonSpecies> = pokedexData as unknown as Record<string, PokemonSpecies>;

export const MOVES: Record<string, Move> = movesData as unknown as Record<string, Move>;
