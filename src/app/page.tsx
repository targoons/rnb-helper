'use client';

import { useState, useEffect } from 'react';
import { useBoxStore } from '@/store/boxStore';
import { BattleState, Action } from '@/engine/battle';
import { getBestAction, getEnemyPredictions, analyzeAllActions, ScoredAction } from '@/solver/minimax';
import { PokemonInstance } from '@/data/types';
import { POKEDEX, MOVES } from '@/data/pokedex';
import { MOVE_IDS } from '@/data/moveIds';
import { getPokemonStats } from '@/engine/stats';
import { calculateDamage } from '@/engine/damage';

export default function HomePage() {
  const [battleState, setBattleState] = useState<BattleState | null>(null);
  const [playerParty, setPlayerParty] = useState<PokemonInstance[]>([]);
  const [enemyTeam, setEnemyTeam] = useState<PokemonInstance[]>([]);
  const [suggestion, setSuggestion] = useState<Action | null>(null);
  const [enemyPredictions, setEnemyPredictions] = useState<ScoredAction[]>([]);
  const [playerWinChances, setPlayerWinChances] = useState<ScoredAction[]>([]);
  const [lastSyncTime, setLastSyncTime] = useState<string>('');
  const [weather, setWeather] = useState<number>(0);
  const [showCrit, setShowCrit] = useState<boolean>(false);

  const syncLive = async () => {
    try {
      const res = await fetch('/api/battle');
      if (!res.ok) throw new Error('Failed to fetch battle data');
      const data = await res.json();

      if (data.weather !== undefined) setWeather(data.weather);

      // 1. Update Party (Use local variable for immediate use)
      let currentParty: PokemonInstance[] = [];
      if (data.playerParty) {
        currentParty = data.playerParty.map((m: any) => mapToPokemon(m));
        setPlayerParty(currentParty);
      }

      // 2. Update Enemy Team (Use local variable for immediate use)
      let currentEnemies: PokemonInstance[] = [];
      if (data.enemyTeam) {
        currentEnemies = data.enemyTeam.map((m: any) => mapToPokemon(m));
        setEnemyTeam(currentEnemies);
      }

      // 3. Update Battle State (if active)
      if (data.activeMons && data.activeMons.length > 0) {
        const playerMonData = data.activeMons.find((m: any) => m.slot === 0 || m.slot === 2);
        const enemyMonData = data.activeMons.find((m: any) => m.slot === 1 || m.slot === 3);

        if (playerMonData && enemyMonData) {
          // Find active instances in our lists using LOCAL variables
          let myActive = currentParty.find(p => p.speciesId === playerMonData.speciesId && p.level === playerMonData.level);
          if (!myActive) {
            // Fallback: Create from activeMonData directly
            myActive = mapToPokemon(playerMonData);
          }

          let enemyActive = currentEnemies.find(p => p.speciesId === enemyMonData.speciesId && p.level === enemyMonData.level);
          if (!enemyActive) {
            // Fallback: Create from activeMonData directly
            enemyActive = mapToPokemon(enemyMonData);
          }
          if (myActive && enemyActive) {
            // Update current HP and Status from active data
            myActive = {
              ...myActive,
              currentHp: playerMonData.currentHp,
              stats: playerMonData.stats || myActive.stats,
              statusNum: playerMonData.status,
              statStages: playerMonData.statStages
            };
            enemyActive = {
              ...enemyActive,
              currentHp: enemyMonData.currentHp,
              stats: enemyMonData.stats || enemyActive.stats,
              statusNum: enemyMonData.status,
              statStages: enemyMonData.statStages
            };

            const state = new BattleState(
              myActive,
              currentParty.length > 0 ? currentParty : [myActive],
              enemyActive,
              currentEnemies.length > 0 ? currentEnemies : [enemyActive]
            );
            setBattleState(state);
            setSuggestion(null);
            setEnemyPredictions([]);
            setPlayerWinChances([]);

            // Auto-predict enemy moves
            const predictions = getEnemyPredictions(state, 2);
            setEnemyPredictions(predictions);

            // Analyze Player Actions (Win Chance)
            const winChances = analyzeAllActions(state, 2);
            setPlayerWinChances(winChances);
          }
        }
      }

      setLastSyncTime(new Date().toLocaleTimeString());

    } catch (e) {
      console.error(e);
      alert('Error syncing. Make sure Lua script is running.');
    }
  };

  const getAdvice = () => {
    if (!battleState) return;
    const action = getBestAction(battleState, 3);
    setSuggestion(action);
  };

  const openPlanner = () => {
    if (!battleState) return;
    // Save state to LocalStorage for the planner to pick up
    localStorage.setItem('plannerInitialState', JSON.stringify(battleState));
    window.location.href = '/planner';
  };

  const mapToPokemon = (m: any): PokemonInstance => ({
    id: m.id || `${m.speciesId}-${m.level}-${m.currentHp}`,
    speciesId: m.speciesId,
    nickname: m.nickname,
    level: m.level,
    currentHp: m.currentHp,
    maxHp: m.maxHp,
    nature: m.nature,
    ability: m.ability || POKEDEX[m.speciesId]?.abilities.join('/') || 'Unknown',
    item: m.item,
    moves: Array.isArray(m.moves) ? m.moves.map((id: number) => MOVE_IDS[id] || id.toString()) : [],
    ivs: m.ivs,
    evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 },
    stats: m.stats,
    otId: m.otId || 0,
    personality: m.personality || 0,
    gender: 'genderless',
    species: m.speciesId,
    statusNum: m.status,
    statStages: m.statStages
  });

  const getWeatherName = (w: number) => {
    if (w === 0 || w === 65535) return 'Clear';
    if (w === 1) return 'Rain';
    if (w === 2) return 'Sun';
    if (w === 3) return 'Sandstorm';
    if (w === 4) return 'Hail';
    return `Weather ${w}`;
  };

  const getStatusName = (s: number | undefined) => {
    if (!s) return null;
    if (s & 0x7) return 'SLP';
    if (s & 0x8) return 'PSN';
    if (s & 0x10) return 'BRN';
    if (s & 0x20) return 'FRZ';
    if (s & 0x40) return 'PAR';
    if (s & 0x80) return 'TOX';
    return null;
  };

  const renderStatStages = (stages: any) => {
    if (!stages) return null;
    const stats = ['atk', 'def', 'spa', 'spd', 'spe', 'acc', 'eva'];
    return (
      <div className="flex gap-1 flex-wrap text-[10px] mt-1">
        {stats.map(s => {
          const val = stages[s];
          if (val === 6) return null;
          const diff = val - 6;
          return (
            <span key={s} className={`px-1 rounded ${diff > 0 ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
              {s.toUpperCase()} {diff > 0 ? '+' : ''}{diff}
            </span>
          );
        })}
      </div>
    );
  };

  return (
    <main className="min-h-screen p-4 bg-slate-900 text-white">
      {/* Header */}
      <div className="flex justify-between items-center mb-6 bg-slate-800 p-4 rounded-xl shadow-lg">
        <h1 className="text-2xl font-bold">Run & Bun Dashboard</h1>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs text-gray-400">Weather</div>
            <div className="font-bold text-yellow-400">{getWeatherName(weather)}</div>
          </div>
          <span className="text-sm text-gray-400">Last Sync: {lastSyncTime || 'Never'}</span>
          <button
            onClick={openPlanner}
            className="py-2 px-4 bg-purple-600 hover:bg-purple-700 rounded-lg font-bold shadow-md transition-all active:scale-95 flex items-center gap-2"
          >
            <span>📝</span> PLAN LINE
          </button>
          <button
            onClick={syncLive}
            className="py-2 px-6 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold shadow-md transition-all active:scale-95"
          >
            SYNC LIVE
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left Column: Player Party (3 cols) */}
        <div className="col-span-3 space-y-4">
          <h2 className="text-xl font-bold text-gray-300 border-b border-gray-700 pb-2">My Party</h2>
          <div className="space-y-2">
            {playerParty.map((p, i) => (
              <div key={i} className={`p-3 rounded-lg flex items-center gap-3 ${battleState?.myActive.id === p.id ? 'bg-blue-900/50 border border-blue-500' : 'bg-slate-800'}`}>
                <img
                  src={`https://img.pokemondb.net/sprites/home/normal/${p.speciesId.toLowerCase()}.png`}
                  className="w-12 h-12 object-contain"
                  onError={(e) => (e.target as HTMLImageElement).style.display = 'none'}
                />
                <div>
                  <div className="font-bold text-sm">{p.nickname}</div>
                  <div className="text-xs text-gray-400">Lv. {p.level}</div>
                  <div className="w-24 bg-gray-700 h-1.5 rounded-full mt-1">
                    <div
                      className={`h-full rounded-full ${p.currentHp / p.maxHp > 0.5 ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ width: `${(p.currentHp / p.maxHp) * 100}%` }}
                    />
                  </div>
                  <div className="text-xs text-right text-gray-500">{p.currentHp}/{p.maxHp}</div>
                  {p.statusNum ? <span className="text-[10px] bg-purple-600 px-1 rounded ml-1">{getStatusName(p.statusNum)}</span> : null}
                  {/* Win Chance for Switch */}
                  {battleState && playerWinChances.find(a => a.type === 'SWITCH' && a.switchTargetId === p.speciesId) && (
                    <span className="ml-2 text-[10px] font-bold text-green-400">
                      {playerWinChances.find(a => a.type === 'SWITCH' && a.switchTargetId === p.speciesId)?.probability?.toFixed(0)}% Win
                    </span>
                  )}
                </div>
              </div>
            ))}
            {playerParty.length === 0 && <div className="text-gray-500 italic">No party data. Sync to load.</div>}
          </div>
        </div>

        {/* Center Column: Battle Arena (6 cols) */}
        <div className="col-span-6">
          <h2 className="text-xl font-bold text-gray-300 border-b border-gray-700 pb-2 mb-4">Active Battle</h2>
          {battleState ? (
            <div className="bg-slate-800 rounded-xl p-6 shadow-xl relative" >
              <div className="absolute inset-0 bg-gradient-to-br from-slate-800 to-slate-900 z-0"></div>

              <div className="relative z-10 flex justify-between items-end mb-8">
                {/* Enemy */}
                <div className="text-right">
                  <div className="text-2xl font-bold text-red-400">{battleState.enemyActive.speciesId}</div>
                  <div className="text-sm text-gray-400">Lv. {battleState.enemyActive.level}</div>
                  <div className="w-48 bg-gray-700 h-3 rounded-full ml-auto mt-2 relative">
                    <div
                      className="h-full bg-red-500 rounded-full transition-all duration-500"
                      style={{ width: `${(battleState.enemyActive.currentHp / battleState.enemyActive.maxHp) * 100}%` }}
                    />
                  </div>
                  <div className="text-sm font-mono mt-1 mb-1">{battleState.enemyActive.currentHp}/{battleState.enemyActive.maxHp}</div>
                  <div className="flex justify-end gap-2">
                    {getStatusName(battleState.enemyActive.statusNum) && (
                      <span className="px-2 py-0.5 bg-purple-600 rounded text-xs font-bold">{getStatusName(battleState.enemyActive.statusNum)}</span>
                    )}
                  </div>
                  {renderStatStages(battleState.enemyActive.statStages)}
                </div>
                <img
                  src={`https://img.pokemondb.net/sprites/home/normal/${battleState.enemyActive.speciesId.toLowerCase()}.png`}
                  className="w-32 h-32 object-contain"
                />
              </div>

              <div className="relative z-10 flex justify-between items-end mb-6">
                {/* Player */}
                <img
                  src={`https://img.pokemondb.net/sprites/home/normal/${battleState.myActive.speciesId.toLowerCase()}.png`}
                  className="w-32 h-32 object-contain"
                />
                <div>
                  <div className="text-2xl font-bold text-blue-400">{battleState.myActive.nickname}</div>
                  <div className="text-sm text-gray-400">Lv. {battleState.myActive.level}</div>
                  <div className="w-48 bg-gray-700 h-3 rounded-full mt-2 relative">
                    <div
                      className="h-full bg-green-500 rounded-full transition-all duration-500"
                      style={{ width: `${(battleState.myActive.currentHp / battleState.myActive.maxHp) * 100}%` }}
                    />
                  </div>
                  <div className="text-sm font-mono mt-1 mb-1">{battleState.myActive.currentHp}/{battleState.myActive.maxHp}</div>
                  <div className="flex gap-2">
                    {getStatusName(battleState.myActive.statusNum) && (
                      <span className="px-2 py-0.5 bg-purple-600 rounded text-xs font-bold">{getStatusName(battleState.myActive.statusNum)}</span>
                    )}
                  </div>
                  {renderStatStages(battleState.myActive.statStages)}
                </div>
              </div>



              {/* Damage Calculator */}
              <div className="mt-4 grid grid-cols-2 gap-4 relative z-10">
                {/* Top Strategies (Moved Inside) */}
                <div className="col-span-2 bg-purple-900 p-4 rounded-xl border border-blue-900/50 shadow-lg mb-2">
                  <h3 className="text-sm font-bold text-blue-300 mb-2 flex items-center gap-2">
                    <span className="text-lg">🏆</span> Top Strategies ({playerWinChances.length})
                  </h3>
                  <div className="space-y-2">
                    {playerWinChances
                      .sort((a, b) => (b.probability || 0) - (a.probability || 0))
                      .map((action, i) => (
                        <div key={i} className="flex flex-col bg-slate-900/50 p-2 rounded">
                          <div className="flex justify-between items-center text-sm">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-gray-300">#{i + 1}</span>
                              <span className="text-white">
                                {action.type === 'MOVE'
                                  ? `Use ${MOVES[action.moveId!]?.name || action.moveId}`
                                  : `Switch to ${playerParty.find(p => p.id === action.switchTargetId)?.nickname || 'Unknown'}`
                                }
                              </span>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-green-500"
                                  style={{ width: `${action.probability || 0}%` }}
                                />
                              </div>
                              <span className="font-bold text-green-400 w-12 text-right">
                                {(action.probability || 0).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                          {/* Explanation (PV) */}
                          {action.explanation && action.explanation.length > 0 && (
                            <div className="mt-1 text-[10px] text-gray-400 flex flex-wrap gap-1 items-center ml-6">
                              <span className="text-gray-500">Then:</span>
                              {action.explanation.map((step, stepIdx) => {
                                const isEnemy = stepIdx % 2 === 0; // 0=Enemy, 1=Me...
                                const actorName = isEnemy ? 'Enemy' : 'You';
                                const actionName = step.type === 'MOVE'
                                  ? MOVES[step.moveId!]?.name
                                  : `Switch to ${isEnemy
                                    ? (enemyTeam.find(p => p.id === step.switchTargetId)?.speciesId || 'Unknown')
                                    : (playerParty.find(p => p.id === step.switchTargetId)?.nickname || 'Unknown')}`;

                                return (
                                  <span key={stepIdx} className="flex items-center gap-1">
                                    {stepIdx > 0 && <span className="text-gray-600">→</span>}
                                    <span className={isEnemy ? 'text-red-300' : 'text-blue-300'}>
                                      {actorName} {step.type === 'MOVE' ? 'uses' : 'switches to'} {actionName}
                                    </span>
                                  </span>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      ))}
                    {playerWinChances.length === 0 && <div className="text-white font-bold text-xs">DEBUG: No strategies found. Sync Live?</div>}
                  </div>
                </div>
                {/* Player -> Enemy */}
                <div className="bg-slate-900/50 p-3 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-sm font-bold text-blue-300">My Damage</h3>
                    <label className="flex items-center gap-1 text-[10px] text-gray-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={showCrit}
                        onChange={(e) => setShowCrit(e.target.checked)}
                        className="rounded bg-slate-700 border-gray-600"
                      />
                      Crit
                    </label>
                  </div>
                  <div className="space-y-1">
                    {Array.isArray(battleState.myActive.moves) && battleState.myActive.moves.map(mId => {
                      const move = MOVES[mId];
                      if (!move || move.category === 'Status') return null;

                      // Find Win Chance
                      const winAction = playerWinChances.find(a => a.type === 'MOVE' && a.moveId === mId);

                      try {
                        const result = calculateDamage(battleState.myActive, battleState.enemyActive, move, showCrit);
                        const minPct = ((result.min / battleState.enemyActive.maxHp) * 100).toFixed(1);
                        const maxPct = ((result.max / battleState.enemyActive.maxHp) * 100).toFixed(1);
                        return (
                          <div key={mId} className="flex justify-between text-xs items-center">
                            <div className="flex flex-col">
                              <span>{move.name}</span>
                              {winAction && winAction.probability !== undefined && (
                                <span className="text-[10px] text-green-500 font-bold">{winAction.probability.toFixed(0)}% Win</span>
                              )}
                            </div>
                            <span className={result.killChance >= 100 ? 'text-green-400 font-bold' : 'text-gray-300'}>
                              {minPct}% - {maxPct}%
                            </span>
                          </div>
                        );
                      } catch (e: any) {
                        return <div key={mId} className="text-red-500 text-xs">Err: {e.message}</div>;
                      }
                    })}
                    {(!battleState.myActive.moves || battleState.myActive.moves.length === 0) && <div className="text-xs text-gray-500">No moves found</div>}
                  </div>
                </div>

                {/* Enemy -> Player */}
                <div className="bg-slate-900/50 p-3 rounded-lg">
                  <h3 className="text-sm font-bold text-red-300 mb-2">Enemy Damage</h3>
                  <div className="space-y-1">
                    {Array.isArray(battleState.enemyActive.moves) && battleState.enemyActive.moves.map(mId => {
                      const move = MOVES[mId];
                      if (!move) return null;
                      try {
                        const result = calculateDamage(battleState.enemyActive, battleState.myActive, move, showCrit);
                        const minPct = ((result.min / battleState.myActive.maxHp) * 100).toFixed(1);
                        const maxPct = ((result.max / battleState.myActive.maxHp) * 100).toFixed(1);
                        return (
                          <div key={mId} className="flex justify-between text-xs">
                            <span>{move.name}</span>
                            <span className={result.killChance >= 100 ? 'text-red-400 font-bold' : 'text-gray-300'}>
                              {minPct}% - {maxPct}%
                            </span>
                          </div>
                        );
                      } catch (e) {
                        return null;
                      }
                    })}
                    {(!battleState.enemyActive.moves || battleState.enemyActive.moves.length === 0) && <div className="text-xs text-gray-500">No moves found</div>}
                  </div>

                  <h3 className="text-sm font-bold text-red-300 mt-4 mb-2">Enemy Intentions</h3>
                  <div className="space-y-2">
                    {enemyPredictions.length === 0 ? (
                      <div className="text-xs text-gray-500 italic">
                        Uncertain (No clear best move)
                      </div>
                    ) : (
                      enemyPredictions.map((action, i) => (
                        <div key={i} className="flex justify-between text-xs items-center">
                          <span className="text-gray-300">
                            {action.type === 'MOVE'
                              ? `Use ${MOVES[action.moveId!]?.name || action.moveId}`
                              : `Switch to ${enemyTeam.find(p => p.id === action.switchTargetId)?.speciesId || 'Unknown'}`
                            }
                          </span>
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-red-500"
                                style={{ width: `${action.probability || 0}%` }}
                              />
                            </div>
                            <span className="text-gray-400 text-[10px]">
                              {(action.probability || 0).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Advisor */}
              <div className="mt-6 pt-6 border-t border-slate-700">
                {!suggestion ? (
                  <button
                    onClick={getAdvice}
                    className="w-full py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-bold shadow-lg"
                  >
                    ASK ADVISOR
                  </button>
                ) : (
                  <div className="space-y-2">
                    <div className="bg-purple-900/40 border border-purple-500 p-4 rounded-lg text-center animate-pulse">
                      <div className="text-purple-300 text-sm uppercase tracking-wider font-bold mb-1">Suggested Action</div>
                      <div className="text-2xl font-bold text-white">
                        {suggestion.type === 'MOVE'
                          ? `Use ${MOVES[suggestion.moveId!]?.name || suggestion.moveId}`
                          : `Switch to ${playerParty.find(p => p.id === suggestion.switchTargetId)?.nickname}`}
                      </div>
                    </div>
                  </div>
                )}
                <button
                  onClick={openPlanner}
                  className="w-full mt-2 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold shadow-lg text-sm"
                >
                  📝 PLAN LINE (BETA)
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-slate-800 rounded-xl p-12 text-center text-gray-500 border-2 border-dashed border-slate-700">
              No active battle detected.
              <br />
              Start a battle in-game and click "SYNC LIVE".
            </div>
          )}
        </div>

        {/* Right Column: Enemy Team (3 cols) */}
        <div className="col-span-3 space-y-4">
          <h2 className="text-xl font-bold text-gray-300 border-b border-gray-700 pb-2">Enemy Team</h2>
          <div className="space-y-2">
            {enemyTeam.map((p, i) => (
              <div key={i} className={`p-3 rounded-lg flex items-center gap-3 ${battleState?.enemyActive.id === p.id ? 'bg-red-900/30 border border-red-500' : 'bg-slate-800'}`}>
                <img
                  src={`https://img.pokemondb.net/sprites/home/normal/${p.speciesId.toLowerCase()}.png`}
                  className="w-10 h-10 object-contain"
                  onError={(e) => (e.target as HTMLImageElement).style.display = 'none'}
                />
                <div>
                  <div className="font-bold text-sm">{p.speciesId}</div>
                  <div className="text-xs text-gray-400">Lv. {p.level} • {p.nature}</div>
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {p.moves.slice(0, 2).map(m => (
                      <span key={m} className="text-[10px] bg-slate-700 px-1 rounded">{MOVES[m]?.name || m}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
            {enemyTeam.length === 0 && <div className="text-gray-500 italic">No enemy data.</div>}
          </div>
        </div>
      </div>

    </main>
  );
}
