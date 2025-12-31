
from typing import List, Dict, Tuple
import threading
import queue
import statistics
from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.ai_scorer import AIScorer

class Simulation:
    def __init__(self, battle_engine: BattleEngine, ai_scorer: AIScorer):
        self.engine = battle_engine
        self.ai = ai_scorer
        self.beam_width = 3
        self.max_depth = 20 # Increased for convergence search
        
    def run(self, initial_state: BattleState) -> Dict:
        """
        Runs the simulation using Iterative Deepening.
        """
        valid_actions = self.engine.get_valid_actions(initial_state, 'player')
        results = {}
        paths = {}
        
        # Track best action history for convergence
        best_action_history = []
        final_depth = 1
        status = "Max Depth"
        
        for depth in range(1, self.max_depth + 1):
            iteration_scores = {}
            iteration_paths = {}
            
            for p_action in valid_actions:
                ai_probs = self.get_ai_action_probs(initial_state)
                total_score = 0
                branch_results = []
                
                for ai_action, prob in ai_probs.items():
                    next_state, turn_log = self.engine.apply_turn(initial_state.deep_copy(), p_action, ai_action)
                    
                    # recursive search
                    # Start action log with the current turn
                    value, full_path, acts = self.simulate_branch(
                        next_state, 
                        depth=depth-1, 
                        path_log=[turn_log],
                        action_log=[(p_action, ai_action)],
                        visited={initial_state.get_hash()}
                    )
                    
                    total_score += value * prob
                    branch_results.append({
                        'ai_action': ai_action,
                        'prob': prob,
                        'value': value,
                        'path': full_path,
                        'action_log': acts
                    })
                
                iteration_scores[p_action] = total_score
                branch_results.sort(key=lambda x: x['prob'], reverse=True)
                iteration_paths[p_action] = branch_results
            
            current_best = max(iteration_scores, key=iteration_scores.get, default=None)
            best_action_history.append(current_best)
            
            # Update global results with latest depth info
            results = iteration_scores
            paths = iteration_paths
            final_depth = depth
            
            # 1. Total KO Check (Check if top path of best action ends in total KO)
            if current_best and iteration_paths[current_best]:
                top_branch = iteration_paths[current_best][0]
                if abs(top_branch['value']) >= 10000: # Total KO score threshold
                    status = "Total KO"
                    break
            
            # 2. Convergence Check (Best action stable for 4 depths, min depth 4)
            if len(best_action_history) >= 4:
                last_4 = best_action_history[-4:]
                if all(a == last_4[0] for a in last_4):
                    status = "Converged"
                    break
        
        # 3. Post-Process: Greedy Finalize the top paths
        # This extends the visual forecast until Match End (KO) or turn limit
        for p_action in paths:
            for branch in paths[p_action]:
                # Only finalize top-probability branches to save time/noise
                if branch['prob'] >= 0.1: 
                    # Replay actions to reconstruct terminal state of the search
                    state = initial_state.deep_copy()
                    replay_visited = set()
                    
                    for p_act, a_act in branch['action_log']:
                        h = state.get_hash()
                        hp = state.ai_active.get('current_hp')
                        # print(f"DEBUG: Replay Hash={h} HP={hp}")
                        replay_visited.add(h)
                        state, _ = self.engine.apply_turn(state, p_act, a_act)
                        
                    # Now extend from this state
                    final_value, extended_path, final_state = self.run_greedy_simulation(state, depth=50, path_log=branch['path'], visited=replay_visited)
                    branch['path'] = extended_path
                    branch['value'] = final_value

        return {
            'best_action': best_action_history[-1] if best_action_history else None,
            'scores': results,
            'paths': paths,
            'final_depth': final_depth,
            'status': status
        }

    def run_greedy_simulation(self, state: BattleState, depth: int, path_log: List[List[str]], visited: set) -> Tuple[float, List[List[str]], BattleState]:
        """
        Extends a simulation greedily until KO or turn limit. Returns (value, path, final_state).
        """
        state_hash = state.get_hash()
        if state_hash in visited:
            # print(f"DEBUG: Cycle detected. Hash={state_hash} Visited={visited}")
            return self.evaluate_state(state), path_log, state
        visited.add(state_hash)
        
        terminal = self.is_total_ko(state)
        # print(f"DEBUG: Greedy Depth={depth} Terminal={terminal}")
        if depth <= 0 or terminal:
            # print("DEBUG: Greedy Terminal reached")
            return self.evaluate_state(state), path_log, state
            
        valid_actions = self.engine.get_valid_actions(state, 'player')
        if not valid_actions:
             print("DEBUG: No valid actions")
             return self.evaluate_state(state), path_log, state

        # Player picks best action based on immediate evaluation (greedy)
        # Note: In a forced switch scenario, valid_actions only contains switches.
        best_p_act = max(valid_actions, key=lambda a: self.evaluate_state(self.engine.apply_turn(state.deep_copy(), a, "Move: Struggle")[0]))
        
        ai_probs = self.get_ai_action_probs(state)
        best_a_act = max(ai_probs, key=ai_probs.get) if ai_probs else "Move: Struggle"
        
        next_state, turn_log = self.engine.apply_turn(state.deep_copy(), best_p_act, best_a_act)
        return self.run_greedy_simulation(next_state, depth - 1, path_log + [turn_log], visited)

    def get_ai_action_probs(self, state: BattleState) -> Dict[str, float]:
        scored = self.ai.score_moves(state, 'ai')
        matrix = scored.get('matrix', [])
        move_names = scored.get('moves', [])
        weights = scored.get('variant_weights', [1.0])
        if not matrix: return {"Move: Struggle": 1.0}
        action_probs = {}
        num_variants = len(weights)
        for row_idx, scores in enumerate(matrix):
            v_idx = row_idx % num_variants
            state_prob = (1.0 / 16.0) * weights[v_idx]
            if not scores:
                return {"Move: Struggle": 1.0}
            max_s = max(scores)
            winners = [move_names[i] for i, s in enumerate(scores) if s == max_s]
            prob_per_winner = state_prob / len(winners)
            for w in winners:
                if w.startswith("Switch:"):
                     act = w
                else:
                     act = f"Move: {w}"
                action_probs[act] = action_probs.get(act, 0) + prob_per_winner
        return {k: v for k, v in action_probs.items() if v > 0.001}

    def is_total_ko(self, state: BattleState):
        """Checks if an entire party is KO'ed."""
        p_alive = any(m.get('current_hp', 0) > 0 for m in state.player_party)
        a_alive = any(m.get('current_hp', 0) > 0 for m in state.ai_party)
        if not p_alive: return 'ai_win'
        if not a_alive: return 'player_win'
        return None

    def simulate_branch(self, state: BattleState, depth: int, path_log: List[List[str]], action_log: List[Tuple[str, str]], visited: set) -> Tuple[float, List[List[str]], List[Tuple[str, str]]]:
        """
        Recursive search. Picks best player action and response to build a forecast line.
        """
        state_hash = state.get_hash()
        if state_hash in visited:
            # Cycle detected
            return self.evaluate_state(state, depth), path_log, action_log
        visited.add(state_hash)
        
        terminal = self.is_total_ko(state)
        if depth <= 0 or terminal:
            return self.evaluate_state(state, depth), path_log, action_log
            
        valid_actions = self.engine.get_valid_actions(state, 'player')
        if not valid_actions:
             return self.evaluate_state(state, depth), path_log, action_log

        # Greedy selection for the forecast line (player maximizes value)
        # We need to handle forced switches (valid_actions will only contain switches)
        best_p_act = max(valid_actions, key=lambda a: self.evaluate_state(self.engine.apply_turn(state.deep_copy(), a, "Move: Struggle")[0], depth))
        
        ai_probs = self.get_ai_action_probs(state)
        # AI maximizes its own score (heuristic)
        best_a_act = max(ai_probs, key=ai_probs.get) if ai_probs else "Move: Struggle"
        
        next_state, turn_log = self.engine.apply_turn(state.deep_copy(), best_p_act, best_a_act)
        return self.simulate_branch(next_state, depth - 1, path_log + [turn_log], action_log + [(best_p_act, best_a_act)], visited)

    def evaluate_state(self, state: BattleState, depth: int = 0) -> float:
        # Score = (PlayerHP% - AIHP%) + Bonuses
        p_active = state.player_active
        a_active = state.ai_active
        
        # Total Party KO Check
        terminal = self.is_total_ko(state)
        if terminal == 'player_win':
            return 10000 + depth * 100 # Prioritize faster wins
        if terminal == 'ai_win':
            return -10000 - depth * 100 # Penalize faster losses
            
        p_hp_raw = max(0, min(p_active.get('current_hp', 0), p_active.get('max_hp', 1)))
        a_hp_raw = max(0, min(a_active.get('current_hp', 0), a_active.get('max_hp', 1)))
        
        p_hp = p_hp_raw / p_active.get('max_hp', 1)
        a_hp = a_hp_raw / a_active.get('max_hp', 1)
        
        # Base HP score: 0 to 100
        score = (p_hp - a_hp) * 100
        
        # Survival Bonus for active mon
        if p_active.get('current_hp', 0) > 0:
            score += 50
        else:
            score -= 1000 # Strict Penalty for losing a mon (was -200)
            
        # Alive Count Bonus (Prioritize keeping party numbers up)
        p_alive_count = sum(1 for m in state.player_party if m.get('current_hp', 0) > 0)
        a_alive_count = sum(1 for m in state.ai_party if m.get('current_hp', 0) > 0)
        score += (p_alive_count - a_alive_count) * 200

        # Party Health
        p_party_hp = sum(m.get('current_hp', 0) / m.get('max_hp', 1) for m in state.player_party)
        a_party_hp = sum(m.get('current_hp', 0) / m.get('max_hp', 1) for m in state.ai_party)
        
        score += (p_party_hp - a_party_hp) * 50
            
        return score
