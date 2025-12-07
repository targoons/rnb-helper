import { BattleState, Action } from '@/engine/battle';

export function getBestAction(state: BattleState, depth: number = 2): Action {
    // 1. Get possible actions for me
    const myActions = state.getPossibleActions(true);

    let bestScore = -Infinity;
    let bestAction = myActions[0];

    for (const action of myActions) {
        // Simulate Enemy's Best Response (Minimax)
        // For simplicity, we assume Enemy acts randomly or uses simple AI in this MVP
        // But ideally we iterate over enemy actions too.

        const enemyActions = state.getPossibleActions(false);
        let minScore = Infinity;

        for (const enemyAction of enemyActions) {
            const nextState = state.applyTurn(action, enemyAction);
            const result = evaluateState(nextState, depth - 1);

            if (result.score < minScore) {
                minScore = result.score;
            }
        }

        if (minScore > bestScore) {
            bestScore = minScore;
            bestAction = action;
        }
    }

    return bestAction;
}

interface EvaluationResult {
    score: number;
    path: Action[];
}

function evaluateState(state: BattleState, depth: number): EvaluationResult {
    if (depth === 0 || state.myActive.currentHp <= 0 || state.enemyActive.currentHp <= 0) {
        return { score: state.evaluate(), path: [] };
    }

    // Recursive step
    const myActions = state.getPossibleActions(true);
    let maxScore = -Infinity;
    let bestPath: Action[] = [];

    for (const action of myActions) {
        const enemyActions = state.getPossibleActions(false);
        let minScore = Infinity;
        let bestEnemyPath: Action[] = [];
        let bestEnemyAction: Action | null = null;

        for (const enemyAction of enemyActions) {
            const nextState = state.applyTurn(action, enemyAction);
            const result = evaluateState(nextState, depth - 1);

            if (result.score < minScore) {
                minScore = result.score;
                bestEnemyPath = result.path;
                bestEnemyAction = enemyAction;
            }
        }

        if (minScore > maxScore) {
            maxScore = minScore;
            // Path: [MyAction, EnemyAction, ...rest]
            // But wait, applyTurn applies BOTH.
            // So the path from this node should be:
            // MyAction -> EnemyAction -> ...
            if (bestEnemyAction) {
                bestPath = [action, bestEnemyAction, ...bestEnemyPath];
            }
        }
    }

    return { score: maxScore, path: bestPath };
}

export interface ScoredAction extends Action {
    score: number;
    probability?: number; // 0-100
    explanation?: Action[];
}

export function getEnemyPredictions(state: BattleState, depth: number = 2): ScoredAction[] {
    const enemyActions = state.getPossibleActions(false);
    const results: ScoredAction[] = [];

    for (const enemyAction of enemyActions) {
        // Simulate Player's Best Response (Minimax)
        const myActions = state.getPossibleActions(true);
        let maxScore = -Infinity; // Player tries to maximize

        for (const myAction of myActions) {
            const nextState = state.applyTurn(myAction, enemyAction);
            const result = evaluateState(nextState, depth - 1);
            // Evaluate from PLAYER perspective.
            // If Enemy makes a good move, this score should be LOW.
            const score = result.score;

            if (score > maxScore) {
                maxScore = score;
            }
        }

        // The score represents the outcome for the PLAYER.
        // Lower score = Better for Enemy.
        results.push({ ...enemyAction, score: maxScore });
    }

    // Calculate Probabilities using Softmax on inverted scores
    // We want lower scores to have higher probability.
    // Invert score: -score.
    // Scale: Divide by 50 to smooth out differences (damage ranges usually 0-300).
    const scores = results.map(r => -r.score / 50);
    const maxVal = Math.max(...scores);
    const expScores = scores.map(s => Math.exp(s - maxVal)); // Stable softmax
    const sumExp = expScores.reduce((a, b) => a + b, 0);

    results.forEach((r, i) => {
        r.probability = (expScores[i] / sumExp) * 100;
    });

    // Sort by score ascending (Lower is better for enemy)
    return results.sort((a, b) => a.score - b.score);
}

export function analyzeAllActions(state: BattleState, depth: number = 2): ScoredAction[] {
    const myActions = state.getPossibleActions(true);
    const results: ScoredAction[] = [];

    for (const action of myActions) {
        // Assume Enemy plays optimally (Minimizes Player Score)
        const enemyActions = state.getPossibleActions(false);
        let minScore = Infinity;
        let bestEnemyPath: Action[] = [];
        let bestEnemyAction: Action | null = null;

        for (const enemyAction of enemyActions) {
            const nextState = state.applyTurn(action, enemyAction);
            const result = evaluateState(nextState, depth - 1);
            if (result.score < minScore) {
                minScore = result.score;
                bestEnemyPath = result.path;
                bestEnemyAction = enemyAction;
            }
        }

        // Normalize Score to 0-100 "Win Chance"
        // Heuristic: Score 0 = Even. Score > 100 = Winning. Score < -100 = Losing.
        // Sigmoid: 1 / (1 + exp(-score / 50))
        const winChance = (1 / (1 + Math.exp(-minScore / 50))) * 100;

        // Explanation: EnemyResponse -> (Next Turn MyMove -> Next Turn EnemyMove ...)
        const explanation = bestEnemyAction ? [bestEnemyAction, ...bestEnemyPath] : [];

        results.push({ ...action, score: minScore, probability: winChance, explanation });
    }

    return results.sort((a, b) => b.score - a.score); // Higher is better for player
}

export function getBestSwitch(state: BattleState, isMyTurn: boolean): Action | null {
    const team = isMyTurn ? state.myTeam : state.enemyTeam;

    const availableSwitches = team.filter(p => p.currentHp > 0 && p.id !== (isMyTurn ? state.myActive.id : state.enemyActive.id));

    if (availableSwitches.length === 0) return null;

    // Simple Heuristic: Best Type Matchup
    let bestSwitch = availableSwitches[0];
    let bestScore = -Infinity;

    for (const candidate of availableSwitches) {
        // Placeholder score: Random for now, but ideally based on type matchup
        const score = Math.random();
        if (score > bestScore) {
            bestScore = score;
            bestSwitch = candidate;
        }
    }

    return {
        type: 'SWITCH',
        switchTargetId: bestSwitch.id,
        priority: 6
    };
}
