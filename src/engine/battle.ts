import { PokemonInstance, Move } from '@/data/types';
import { calculateDamage } from './damage';
import { POKEDEX, MOVES } from '@/data/pokedex';
import { getPokemonStats } from './stats';

export type ActionType = 'MOVE' | 'SWITCH';

export interface Action {
    type: ActionType;
    moveId?: string; // If MOVE
    switchTargetId?: string; // If SWITCH
    priority: number;
}

export class BattleState {
    myActive: PokemonInstance;
    myTeam: PokemonInstance[];
    enemyActive: PokemonInstance;
    enemyTeam: PokemonInstance[];
    turn: number;
    forceSwitch: boolean;

    constructor(
        myActive: PokemonInstance,
        myTeam: PokemonInstance[],
        enemyActive: PokemonInstance,
        enemyTeam: PokemonInstance[],
        turn: number = 0,
        forceSwitch: boolean = false
    ) {
        this.myActive = JSON.parse(JSON.stringify(myActive));
        this.myTeam = JSON.parse(JSON.stringify(myTeam));
        this.enemyActive = JSON.parse(JSON.stringify(enemyActive));
        this.enemyTeam = JSON.parse(JSON.stringify(enemyTeam));
        this.turn = turn;
        this.forceSwitch = forceSwitch;
    }

    getPossibleActions(isMyTurn: boolean): Action[] {
        const active = isMyTurn ? this.myActive : this.enemyActive;
        const team = isMyTurn ? this.myTeam : this.enemyTeam;
        const actions: Action[] = [];

        // 1. Moves
        // In a real engine, we check for PP, Disable, Choice Items, etc.
        for (const moveId of active.moves) {
            const move = MOVES[moveId];
            if (move) {
                actions.push({
                    type: 'MOVE',
                    moveId: moveId,
                    priority: move.priority || 0,
                });
            }
        }

        // 2. Switches
        // Can switch if not trapped (Shadow Tag, etc. - ignored for MVP)
        for (const p of team) {
            if (p.id !== active.id && p.currentHp > 0) {
                actions.push({
                    type: 'SWITCH',
                    switchTargetId: p.id,
                    priority: 6, // Switch is usually high priority
                });
            }
        }

        return actions;
    }

    // Apply a full turn (My Action + Enemy Action)
    // For Minimax, we usually apply one ply (half-turn) at a time, but Pokemon is simultaneous.
    // We will simulate a full turn where both choose, then speed decides order.
    applyTurn(myAction: Action, enemyAction: Action): BattleState {
        // If we are in a Force Switch state, handle it immediately
        if (this.forceSwitch) {
            const nextState = new BattleState(
                this.myActive,
                this.myTeam,
                this.enemyActive,
                this.enemyTeam,
                this.turn,
                false // Reset flag
            );

            // Apply Switch
            if (this.myActive.currentHp === 0 && myAction.type === 'SWITCH') {
                const newActive = nextState.myTeam.find(p => p.id === myAction.switchTargetId);
                if (newActive) nextState.myActive = newActive;
            }
            if (this.enemyActive.currentHp === 0 && enemyAction.type === 'SWITCH') {
                const newActive = nextState.enemyTeam.find(p => p.id === enemyAction.switchTargetId);
                if (newActive) nextState.enemyActive = newActive;
            }
            return nextState;
        }

        const nextState = new BattleState(
            this.myActive,
            this.myTeam,
            this.enemyActive,
            this.enemyTeam,
            this.turn + 1
        );

        // Determine Turn Order
        let first = 'me';
        const mySpeed = nextState.myActive.ivs.spe; // Simplified
        const enemySpeed = nextState.enemyActive.ivs.spe;

        if (myAction.priority > enemyAction.priority) first = 'me';
        else if (enemyAction.priority > myAction.priority) first = 'enemy';
        else if (mySpeed > enemySpeed) first = 'me';
        else if (enemySpeed > mySpeed) first = 'enemy';
        else first = Math.random() > 0.5 ? 'me' : 'enemy';

        const executeAction = (actor: 'me' | 'enemy', action: Action) => {
            const attacker = actor === 'me' ? nextState.myActive : nextState.enemyActive;
            const defender = actor === 'me' ? nextState.enemyActive : nextState.myActive;

            if (attacker.currentHp <= 0) return; // Dead mon can't move

            if (action.type === 'SWITCH') {
                // Handle Switch
                const team = actor === 'me' ? nextState.myTeam : nextState.enemyTeam;
                const newActive = team.find(p => p.id === action.switchTargetId);
                if (newActive) {
                    if (actor === 'me') nextState.myActive = newActive;
                    else nextState.enemyActive = newActive;
                }
            } else if (action.type === 'MOVE' && action.moveId) {
                // Handle Move
                const move = MOVES[action.moveId];
                if (move) {
                    // Accuracy Check
                    let accuracy = move.accuracy;
                    if ((accuracy as unknown) === true) accuracy = 100;

                    const accStage = attacker.statStages?.acc || 6;
                    const evaStage = defender.statStages?.eva || 6;
                    const stageDiff = (accStage - 6) - (evaStage - 6);

                    let stageMult = 1.0;
                    if (stageDiff >= 0) stageMult = (3 + stageDiff) / 3;
                    else stageMult = 3 / (3 + Math.abs(stageDiff));

                    const hitChance = (accuracy / 100) * stageMult;

                    // Damage Calculation
                    const result = calculateDamage(attacker, defender, move);
                    const avgDamage = result.rolls[7]; // Use average roll
                    const expectedDamage = avgDamage * hitChance;

                    defender.currentHp = Math.max(0, defender.currentHp - expectedDamage);
                }
            }
        };

        if (first === 'me') {
            executeAction('me', myAction);
            executeAction('enemy', enemyAction);
        } else {
            executeAction('enemy', enemyAction);
            executeAction('me', myAction);
        }

        // Check for Faints -> Set Force Switch Flag
        if (nextState.myActive.currentHp === 0 || nextState.enemyActive.currentHp === 0) {
            // Only set force switch if someone has a replacement
            const myAlive = nextState.myTeam.some(p => p.currentHp > 0 && p.id !== nextState.myActive.id);
            const enemyAlive = nextState.enemyTeam.some(p => p.currentHp > 0 && p.id !== nextState.enemyActive.id);

            if ((nextState.myActive.currentHp === 0 && myAlive) || (nextState.enemyActive.currentHp === 0 && enemyAlive)) {
                nextState.forceSwitch = true;
            }
        }

        return nextState;
    }

    evaluate(): number {
        // Simple heuristic: (My HP / My Max HP) - (Enemy HP / Enemy Max HP)

        const getTeamHealth = (team: PokemonInstance[]) => {
            let total = 0;
            for (const p of team) {
                const stats = getPokemonStats(p);
                const maxHp = stats.hp;
                total += p.currentHp / maxHp;
            }
            return total;
        };

        const myScore = getTeamHealth(this.myTeam);
        const enemyScore = getTeamHealth(this.enemyTeam);

        // Bonus for killing enemy active
        if (this.enemyActive.currentHp === 0) {
            // Even if we lose (enemy dies), we want to minimize Player HP.
            // Score = 1000 + (My HP %)
            // Enemy wants to MINIMIZE this.
            // So Enemy prefers My HP % to be lower.
            return 1000 + (this.myActive.currentHp / this.myActive.maxHp) * 100;
        }
        // Penalty for losing my active
        if (this.myActive.currentHp === 0) {
            // If I die, score is low (good for enemy).
            // Score = -1000 - (Enemy HP %)
            return -1000 - (this.enemyActive.currentHp / this.enemyActive.maxHp) * 100;
        }

        return (myScore - enemyScore) * 100;
    }
}
