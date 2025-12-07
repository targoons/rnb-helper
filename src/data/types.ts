export type Type =
  | 'Normal' | 'Fire' | 'Water' | 'Grass' | 'Electric' | 'Ice' | 'Fighting'
  | 'Poison' | 'Ground' | 'Flying' | 'Psychic' | 'Bug' | 'Rock' | 'Ghost'
  | 'Dragon' | 'Steel' | 'Dark' | 'Fairy';

export type Category = 'Physical' | 'Special' | 'Status';

export interface Stats {
  hp: number;
  atk: number;
  def: number;
  spa: number;
  spd: number;
  spe: number;
}

export interface Move {
  id: string;
  name: string;
  type: Type;
  category: Category;
  power: number;
  accuracy: number;
  pp: number;
  priority: number;
  effect?: string; // Description or ID for effect logic
}

export interface PokemonSpecies {
  id: string;
  name: string;
  types: [Type] | [Type, Type];
  baseStats: Stats;
  abilities: string[];
}

export interface PokemonInstance {
  id: string; // Unique ID for this instance
  speciesId: string;
  nickname?: string;
  level: number;
  ability: string;
  nature: string;
  item?: string;
  moves: string[]; // Move IDs
  ivs: Stats;
  evs: Stats; // Usually 0 in Run and Bun, but good to have
  stats?: Stats; // Actual stats (if read from memory or calculated)
  currentHp: number;
  maxHp: number;
  status?: 'PAR' | 'BRN' | 'FRZ' | 'PSN' | 'TOX' | 'SLP';
  statusNum?: number; // Raw status value
  statStages?: {
    hp: number;
    atk: number;
    def: number;
    spa: number;
    spd: number;
    spe: number;
    acc: number;
    eva: number;
  };
  otId?: number;
  personality?: number;
  gender?: 'male' | 'female' | 'genderless';
  species?: string; // Name (fallback)
}

export interface Trainer {
  id: string;
  name: string;
  team: PokemonInstance[];
  aiLogic?: string; // ID for specific AI behavior
}
