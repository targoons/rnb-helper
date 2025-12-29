const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const { calculate, Generations, Pokemon, Move, Field } = require('@smogon/calc');

const app = express();
const port = 3000;

app.use(bodyParser.json());

// Load Moves Map
const MOVES_PATH = path.join(__dirname, '../data/moves.json');
let MOVES_MAP = {};
// Load Custom Moves
let CUSTOM_MOVES = {};
try {
    const customPath = path.join(__dirname, 'custom_moves.json');
    if (fs.existsSync(customPath)) {
        CUSTOM_MOVES = JSON.parse(fs.readFileSync(customPath, 'utf8'));
        console.log(`Loaded ${Object.keys(CUSTOM_MOVES).length} custom moves.`);
    }
} catch (e) {
    console.log("Error loading custom_moves.json:", e.message);
}
try {
    const data = fs.readFileSync(MOVES_PATH, 'utf8');
    MOVES_MAP = JSON.parse(data);
    console.log(`Loaded ${Object.keys(MOVES_MAP).length} moves.`);
} catch (e) {
    console.error("Failed to load moves.json", e);
}

// Stub Species Map (Needs full expansion or external file)
// Load Species Map
const SPECIES_PATH = path.join(__dirname, '../data/species.json');
let SPECIES_MAP = {};
try {
    const data = fs.readFileSync(SPECIES_PATH, 'utf8');
    SPECIES_MAP = JSON.parse(data);
    console.log(`Loaded ${Object.keys(SPECIES_MAP).length} species.`);
} catch (e) {
    console.error("Failed to load species.json", e);
    // Fallback stub
    SPECIES_MAP = { "1": "Bulbasaur", "25": "Pikachu" };
}

function getSpeciesName(id) {
    return SPECIES_MAP[String(id)] || "Pikachu";
}

function getMoveName(id) {
    if (MOVES_MAP[String(id)]) return MOVES_MAP[String(id)];
    // If it's a string like "Bite" that isn't a key, just return it
    if (isNaN(id)) return id;
    return "Struggle";
}

app.post('/batch-calculate', (req, res) => {
    try {
        const { attacker: attData, defender: defData, moves, field } = req.body;

        // Gen 8 is generally safe for modern-mechanics ROM hacks (Phy/Spe split, Fairy type)
        const gen = Generations.get(8);

        const stages = attData.statStages || attData.stat_stages;

        // Pre-calculate correct boosts
        let correctBoosts = {};
        if (stages) {
            const mapStage = (s) => (s === undefined ? 0 : (s || 6) - 6);
            correctBoosts = {
                atk: mapStage(stages.atk),
                def: mapStage(stages.def),
                spa: mapStage(stages.spa),
                spd: mapStage(stages.spd),
                spe: mapStage(stages.spe),
            };
        }

        // Helper to find a safe species name for @smogon/calc
        const findSafeSpecies = (name) => {
            if (!name) return "Pikachu";
            if (gen.species.get(name.toLowerCase())) return name.toLowerCase();

            // Try squashed ID (lower case, no non-alphanumeric)
            const id = name.toLowerCase().replace(/[^a-z0-9]/g, '');
            if (gen.species.get(id)) return id;

            // Try hyphen-to-space normalization
            const spaceName = name.replace(/-/g, ' ');
            if (gen.species.get(spaceName.toLowerCase())) return spaceName.toLowerCase();

            // Try space-to-hyphen
            const hyphenName = name.replace(/ /g, '-');
            if (gen.species.get(hyphenName)) return hyphenName;

            // Log and fallback
            console.warn(`Species not found in Gen ${gen.num}: "${name}". Using Pikachu as base.`);
            return "Pikachu";
        };

        let attacker, defender;
        try {
            // Create Attacker
            const rawAttName = attData.name || getSpeciesName(attData.speciesId || attData.species_id);
            const attName = findSafeSpecies(rawAttName);
            attacker = new Pokemon(gen, attName, {
                item: typeof attData.item === 'string' ? attData.item : undefined,
                nature: attData.nature === 'Unknown' ? 'Hardy' : attData.nature,
                level: attData.level || 50,
                curHP: attData.currentHp || attData.current_hp,
                ivs: attData.ivs ? {
                    hp: attData.ivs.hp !== undefined ? attData.ivs.hp : 31,
                    atk: attData.ivs.atk !== undefined ? attData.ivs.atk : 31,
                    def: attData.ivs.def !== undefined ? attData.ivs.def : 31,
                    spa: attData.ivs.spa !== undefined ? attData.ivs.spa : 31,
                    spd: attData.ivs.spd !== undefined ? attData.ivs.spd : 31,
                    spe: attData.ivs.spe !== undefined ? attData.ivs.spe : 31
                } : undefined,
                boosts: correctBoosts
            });

            if (attData.stats && attacker.stats) {
                if (attData.stats.hp !== undefined) attacker.stats.hp = attData.stats.hp;
                if (attData.stats.atk !== undefined) attacker.stats.atk = attData.stats.atk;
                if (attData.stats.def !== undefined) attacker.stats.def = attData.stats.def;
                if (attData.stats.spa !== undefined) attacker.stats.spa = attData.stats.spa;
                if (attData.stats.spd !== undefined) attacker.stats.spd = attData.stats.spd;
                if (attData.stats.spe !== undefined) attacker.stats.spe = attData.stats.spe;
            }
            attacker.originalCurHP = attData.currentHp || attData.current_hp;

            // Create Defender
            const rawDefName = defData.name || getSpeciesName(defData.speciesId || defData.species_id);
            const defName = findSafeSpecies(rawDefName);

            const dStages = defData.statStages || defData.stat_stages;
            let dBoosts = {};
            if (dStages) {
                const mapStage = (s) => (s || 6) - 6;
                dBoosts = {
                    atk: mapStage(dStages.atk),
                    def: mapStage(dStages.def),
                    spa: mapStage(dStages.spa),
                    spd: mapStage(dStages.spd),
                    spe: mapStage(dStages.spe),
                };
            }

            defender = new Pokemon(gen, defName, {
                item: typeof defData.item === 'string' ? defData.item : undefined,
                nature: defData.nature === 'Unknown' ? 'Hardy' : defData.nature,
                level: defData.level || 50,
                ivs: defData.ivs ? {
                    hp: defData.ivs.hp !== undefined ? defData.ivs.hp : 31,
                    atk: defData.ivs.atk !== undefined ? defData.ivs.atk : 31,
                    def: defData.ivs.def !== undefined ? defData.ivs.def : 31,
                    spa: defData.ivs.spa !== undefined ? defData.ivs.spa : 31,
                    spd: defData.ivs.spd !== undefined ? defData.ivs.spd : 31,
                    spe: defData.ivs.spe !== undefined ? defData.ivs.spe : 31
                } : undefined,
                boosts: dBoosts
            });

            const dHP = defData.currentHp || defData.current_hp;
            if (dHP !== undefined) defender.curHP = dHP;

            if (defData.stats && defender.stats) {
                if (defData.stats.hp !== undefined) defender.stats.hp = defData.stats.hp;
                if (defData.stats.atk !== undefined) defender.stats.atk = defData.stats.atk;
                if (defData.stats.def !== undefined) defender.stats.def = defData.stats.def;
                if (defData.stats.spa !== undefined) defender.stats.spa = defData.stats.spa;
                if (defData.stats.spd !== undefined) defender.stats.spd = defData.stats.spd;
                if (defData.stats.spe !== undefined) defender.stats.spe = defData.stats.spe;
            }
            defender.originalCurHP = defData.currentHp || defData.current_hp;

        } catch (e) {
            console.error("Setup Error:", e.message, "at", e.stack);
            console.error("Attacker Data:", JSON.stringify(attData));
            console.error("Defender Data:", JSON.stringify(defData));
            return res.status(400).json({ error: "Pokemon Setup Failed: " + e.message });
        }

        // Helper to clone/snapshot a Pokemon
        const cloneWithStats = (p) => {
            if (!p) return null;
            const options = {
                level: p.level,
                item: p.item,
                nature: p.nature,
                ability: p.ability,
                status: p.status,
                ivs: p.ivs,
                evs: p.evs,
                curHP: p.curHP
            };
            if (p.boosts) options.boosts = { ...p.boosts };
            if (p.stats) options.overrides = { stats: { ...p.stats } };
            return new Pokemon(gen, p.name, options);
        };

        // Calculate
        const results = (moves || []).map(moveId => {
            try {
                if (moveId === 0) return null;
                let moveName = getMoveName(moveId);
                if (moveName === "Struggle" && typeof moveId === 'string') {
                    moveName = moveId;
                }

                // Custom Overrides (BP / Type)
                const custom = CUSTOM_MOVES[moveName] || {};
                const moveOptions = {};
                if (custom.bp) moveOptions.basePower = custom.bp;
                if (custom.type) moveOptions.type = custom.type;

                const move = new Move(gen, moveName, moveOptions);

                // Clone to avoid side effects
                const att = cloneWithStats(attacker);
                const def = cloneWithStats(defender);

                // 1. Run & Bun Specific: Paralysis drops speed by 50% (to 0.5x) in Gen 8/modern.
                if (att.status === 'par') att.stats.spe = Math.floor(att.stats.spe * 0.5);
                if (def.status === 'par') def.stats.spe = Math.floor(def.stats.spe * 0.5);

                const fData = field || {};
                const defenderSide = defData.side || (attData.side === 'player' ? 'ai' : 'player');
                const fObj = new Field({
                    gen: 8,
                    weather: fData.weather,
                    terrain: fData.terrain,
                    isReflect: fData.screens && fData.screens[defenderSide] && fData.screens[defenderSide].reflect > 0,
                    isLightScreen: fData.screens && fData.screens[defenderSide] && fData.screens[defenderSide].light_screen > 0,
                    isAuroraVeil: fData.screens && fData.screens[defenderSide] && fData.screens[defenderSide].aurora_veil > 0,
                    isStealthRock: fData.hazards && fData.hazards[defenderSide] && fData.hazards[defenderSide].includes('Stealth Rock'),
                    spikes: fData.hazards && fData.hazards[defenderSide] ? fData.hazards[defenderSide].filter(h => h === 'Spikes').length : 0,
                    isStickyWeb: fData.hazards && fData.hazards[defenderSide] && fData.hazards[defenderSide].includes('Sticky Web'),
                    isToxicSpikes: fData.hazards && fData.hazards[defenderSide] && fData.hazards[defenderSide].includes('Toxic Spikes'),
                });

                const result = calculate(gen, att, def, move, fObj);

                let damageRolls = result.damage;
                if (typeof damageRolls === 'number') damageRolls = [damageRolls];
                if (!Array.isArray(damageRolls)) damageRolls = [0];

                // Crit Calculation (Clone move options, enable crit)
                const critOptions = { ...moveOptions, isCrit: true };
                const critMove = new Move(gen, moveName, critOptions);
                const attCrit = cloneWithStats(attacker);
                const defCrit = cloneWithStats(defender);
                const critResult = calculate(gen, attCrit, defCrit, critMove);
                let critRolls = critResult.damage;
                if (typeof critRolls === 'number') critRolls = [critRolls];
                if (!Array.isArray(critRolls)) critRolls = [0];

                const secondaries = move.secondaries || [];

                let descText = "";
                try {
                    descText = result.desc();
                } catch (descErr) {
                    if (damageRolls[0] === 0) descText = "Does not affect";
                    else descText = "Error calculating description";
                }

                const toID = (text) => text.toLowerCase().replace(/[^a-z0-9]/g, '');
                const rawMove = gen.moves.get(toID(moveName));

                const fs = require('fs');
                if (moveName === 'Confuse Ray') {
                    try {
                        fs.writeFileSync('/Users/targoon/Pokemon/debug_move.log', JSON.stringify({ moveObj: move, raw: rawMove }, null, 2));
                    } catch (err) {
                        fs.writeFileSync('/Users/targoon/Pokemon/debug_move.log', 'Error logging raw: ' + err);
                    }
                }

                return {
                    move: moveId,
                    moveName: moveName,
                    damage_rolls: damageRolls,
                    crit_rolls: critRolls,
                    secondaries: secondaries,
                    desc: descText,
                    priority: move.priority,
                    category: move.category,
                    type: move.type,
                    flags: move.flags,
                    drain: move.drain,
                    recoil: move.recoil,
                    self: move.self,
                    target_boosts: move.boosts,
                    multihit: move.multihit || (rawMove ? rawMove.multihit : undefined),
                    critRatio: move.critRatio || (rawMove ? rawMove.critRatio : undefined),
                };
            } catch (e) {
                const fs = require('fs');
                fs.appendFileSync('/Users/targoon/Pokemon/calc_error.log', `Move ${moveId} Error: ${e.message}\n${e.stack}\n`);
                console.log(`Skipping move ${moveId}: ${e.message}`);
                return null;
            }
        }).filter(r => r !== null);

        res.json(results);

    } catch (error) {
        fs.appendFileSync('/Users/targoon/Pokemon/calc_error.log', `Global Error: ${error.message}\n${error.stack}\n`);
        console.error("Internal calc error:", error);
        res.status(500).json({ error: error.message });
    }
});

app.listen(port, () => {
    console.log(`Real Calc service listening on port ${port}`);
});
