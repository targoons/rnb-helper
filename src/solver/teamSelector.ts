import { PokemonInstance, Trainer } from '@/data/types';
import { POKEDEX } from '@/data/pokedex';
import { getEffectiveness } from '@/data/typeChart';

export function suggestTeam(box: PokemonInstance[], trainer: Trainer): PokemonInstance[] {
    // Simple Heuristic:
    // 1. Score each box mon against the trainer's team
    // 2. Score = (Offensive Advantage) + (Defensive Advantage)

    const scores = box.map(p => {
        let score = 0;
        const pSpecies = POKEDEX[p.speciesId];

        for (const enemy of trainer.team) {
            const eSpecies = POKEDEX[enemy.speciesId];

            // Offensive: Do I have a super effective move?
            // Simplified: Do I have a type advantage?
            let maxEffectiveness = 0;
            for (const type of pSpecies.types) {
                const eff = getEffectiveness(type, eSpecies.types);
                if (eff > maxEffectiveness) maxEffectiveness = eff;
            }
            score += maxEffectiveness * 10;

            // Defensive: Do they have a super effective move against me?
            // Simplified: Do they have a type advantage?
            let maxIncoming = 0;
            for (const type of eSpecies.types) {
                const eff = getEffectiveness(type, pSpecies.types);
                if (eff > maxIncoming) maxIncoming = eff;
            }
            score -= maxIncoming * 10;
        }

        return { pokemon: p, score };
    });

    // Sort by score desc
    scores.sort((a, b) => b.score - a.score);

    // Return top 6
    return scores.slice(0, 6).map(s => s.pokemon);
}
