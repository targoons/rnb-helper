"""
Local damage calculation module.
Replaces external Node.js calculator with pure Python implementation.
Implements Gen 3+ damage formula.
"""

def get_type_effectiveness(move_type, defender_types):
    """Calculate type effectiveness multiplier."""
    TYPE_CHART = {
        'Normal': {'Rock': 0.5, 'Ghost': 0, 'Steel': 0.5},
        'Fire': {'Fire': 0.5, 'Water': 0.5, 'Grass': 2, 'Ice': 2, 'Bug': 2, 'Rock': 0.5, 'Dragon': 0.5, 'Steel': 2},
        'Water': {'Fire': 2, 'Water': 0.5, 'Grass': 0.5, 'Ground': 2, 'Rock': 2, 'Dragon': 0.5},
        'Electric': {'Water': 2, 'Electric': 0.5, 'Grass': 0.5, 'Ground': 0, 'Flying': 2, 'Dragon': 0.5},
        'Grass': {'Fire': 0.5, 'Water': 2, 'Grass': 0.5, 'Poison': 0.5, 'Ground': 2, 'Flying': 0.5, 'Bug': 0.5, 'Rock': 2, 'Dragon': 0.5, 'Steel': 0.5},
        'Ice': {'Fire': 0.5, 'Water': 0.5, 'Grass': 2, 'Ice': 0.5, 'Ground': 2, 'Flying': 2, 'Dragon': 2, 'Steel': 0.5},
        'Fighting': {'Normal': 2, 'Ice': 2, 'Poison': 0.5, 'Flying': 0.5, 'Psychic': 0.5, 'Bug': 0.5, 'Rock': 2, 'Ghost': 0, 'Dark': 2, 'Steel': 2, 'Fairy': 0.5},
        'Poison': {'Grass': 2, 'Poison': 0.5, 'Ground': 0.5, 'Rock': 0.5, 'Ghost': 0.5, 'Steel': 0, 'Fairy': 2},
        'Ground': {'Fire': 2, 'Electric': 2, 'Grass': 0.5, 'Poison': 2, 'Flying': 0, 'Bug': 0.5, 'Rock': 2, 'Steel': 2},
        'Flying': {'Electric': 0.5, 'Grass': 2, 'Fighting': 2, 'Bug': 2, 'Rock': 0.5, 'Steel': 0.5},
        'Psychic': {'Fighting': 2, 'Poison': 2, 'Psychic': 0.5, 'Dark': 0, 'Steel': 0.5},
        'Bug': {'Fire': 0.5, 'Grass': 2, 'Fighting': 0.5, 'Poison': 0.5, 'Flying': 0.5, 'Psychic': 2, 'Ghost': 0.5, 'Dark': 2, 'Steel': 0.5, 'Fairy': 0.5},
        'Rock': {'Fire': 2, 'Ice': 2, 'Fighting': 0.5, 'Ground': 0.5, 'Flying': 2, 'Bug': 2, 'Steel': 0.5},
        'Ghost': {'Normal': 0, 'Psychic': 2, 'Ghost': 2, 'Dark': 0.5},
        'Dragon': {'Dragon': 2, 'Steel': 0.5, 'Fairy': 0},
        'Dark': {'Fighting': 0.5, 'Psychic': 2, 'Ghost': 2, 'Dark': 0.5, 'Fairy': 0.5},
        'Steel': {'Fire': 0.5, 'Water': 0.5, 'Electric': 0.5, 'Ice': 2, 'Rock': 2, 'Steel': 0.5, 'Fairy': 2},
        'Fairy': {'Fire': 0.5, 'Fighting': 2, 'Poison': 0.5, 'Dragon': 2, 'Dark': 2, 'Steel': 0.5},
    }
    
    effectiveness = 1.0
    for def_type in defender_types:
        if move_type in TYPE_CHART and def_type in TYPE_CHART[move_type]:
            effectiveness *= TYPE_CHART[move_type][def_type]
    
    return effectiveness


def calculate_damage(attacker, defender, move_name, move_data, field=None, move_type_override=None, move_bp_override=None):
    """
    Calculate damage using strict integer arithmetic and specific modifier order.
    Order: Base -> Random (85-100%) -> STAB -> Type Effectiveness -> Other Modifiers
    Uses Mechanics class for stat and modifier logic.
    """
    from pkh_app.mechanics import Mechanics
    
    category = move_data.get('category', 'Physical')
    
    # Status moves do no damage
    if category == 'Status':
        return {
            'damage': [0], 'damage_rolls': [0], 'effectiveness': 1.0,
            'type_effectiveness': 1.0, 'is_stab': False, 'critRatio': 1, 'is_crit': False,
            'can_crit': False
        }

    # 0. Fixed Damage (Sonic Boom, Dragon Rage, etc.)
    if 'damage' in move_data:
        fixed_dmg = move_data['damage']
        # Level-based damage (e.g. Seismic Toss, Night Shade)
        if fixed_dmg == 'level':
            fixed_dmg = attacker.get('level', 50)
        
        move_type = move_data.get('type', 'Normal')
        eff = Mechanics.get_type_effectiveness_with_abilities(move_type, defender, attacker)
        
        if eff == 0:
            fixed_dmg = 0
            
        return {
            'damage': [fixed_dmg], 'damage_rolls': [fixed_dmg] * 16, 'effectiveness': eff,
            'type_effectiveness': eff, 'is_stab': False, 'critRatio': 1, 'is_crit': False,
            'can_crit': False
        }
    
    # 0. Base Power Modifiers
    power = move_bp_override if move_bp_override is not None else move_data.get('basePower', 0)
    if power == 0:
        power = Mechanics.get_variable_bp(move_name, attacker, defender, field)
    
    
    if power is None or power == 0:
        return {
            'damage': [0], 'damage_rolls': [0], 'effectiveness': 1.0,
            'type_effectiveness': 1.0, 'is_stab': False, 'critRatio': 1, 'is_crit': False
        }
        
    # --- Context Injection (EARLY) for modifiers like Expert Belt ---
    move_type = move_type_override if move_type_override is not None else move_data.get('type', 'Normal')
    effectiveness = Mechanics.get_type_effectiveness_with_abilities(move_type, defender, attacker)
    
    if field is None: field = {}
    context = field.get('context', {})
    if not isinstance(context, dict): context = {} 
    context['effectiveness'] = effectiveness
    field['context'] = context
        
    # Apply onBasePower modifiers (Technician, Strong Jaw, Expert Belt, etc.)
    bp_mod = Mechanics.get_modifier(attacker, 'onBasePower', move_data, field, target=defender)
    power = int(power * bp_mod)
    
    level = attacker.get('level', 50)
    
    # 1. Effective Stats (Includes stages and stat items like Choice Band, Eviolite)
    if category == 'Physical':
        atk = Mechanics.get_effective_stat(attacker, 'atk', field)
        defense = Mechanics.get_effective_stat(defender, 'def', field)
    else:
        atk = Mechanics.get_effective_stat(attacker, 'spa', field)
        defense = Mechanics.get_effective_stat(defender, 'spd', field)
    
    defense = max(1, defense)
    
    # defense = max(1, defense)
    
    # --- STRICT BASE DAMAGE FORMULA ---
    # 1. floor(2 * L / 5 + 2)
    level_factor = (2 * level // 5) + 2
    
    
    # 2. floor(Power * Atk * Factor)
    dmg = (level_factor * power * atk)
    
    # 3. floor(dmg / Def)
    dmg = dmg // defense
    
    # 4. floor(dmg / 50) + 2
    base_calc = (dmg // 50) + 2
    
    # Type effectiveness and STAB (re-use effectiveness from above)
    is_stab = move_type in attacker.get('types', [])
    
    # Other Modifiers (Life Orb, etc.)
    dmg_mod = Mechanics.get_modifier(attacker, 'onModifyDamage', move_data, field, target=defender)
    src_mod = Mechanics.get_modifier(defender, 'onSourceModifyDamage', move_data, field, target=attacker)
    final_mod = dmg_mod * src_mod
    
    if bp_mod != 1.0 or final_mod != 1.0:
        print(f"[DEBUG_CALC] Item: {attacker.get('item')}, Move: {move_name}, BP_Mod: {bp_mod}, Dmg_Mod: {dmg_mod}, Src_Mod: {src_mod}, Final: {final_mod}")

    # Generate 16 damage rolls
    damage_rolls = []
    crit_rolls = []
    
    for roll in range(85, 101):
        # Step 1: Apply Random Factor FIRST
        r_dmg = (base_calc * roll) // 100
        
        # Step 2: Apply STAB
        if is_stab:
            stab_mult = Mechanics.get_stab_multiplier(attacker, move_type)
            r_dmg = int(r_dmg * stab_mult)
            
        # Step 3: Apply Type Effectiveness (Integer truncation)
        r_dmg = int(r_dmg * effectiveness)
        
        # Step 4: Apply Other Modifiers (Life Orb, Expert Belt, etc.)
        r_dmg = int(r_dmg * final_mod)
        
        # Step 5: Weather (Rain/Sun)
        weather = field.get('weather')
        if weather:
             # Check suppression
             weather_negated = False
             # Look in field for active_mons or check participants
             for p in [attacker, defender]:
                  if p.get('ability') in ['Cloud Nine', 'Air Lock']:
                       weather_negated = True
             
             if not weather_negated:
                  if weather in ['Rain', 'Rain Dance']:
                       if move_type == 'Water': r_dmg = int(r_dmg * 1.5)
                       elif move_type == 'Fire': r_dmg = int(r_dmg * 0.5)
                  elif weather in ['Sun', 'Sunny Day']:
                       if move_type == 'Fire': r_dmg = int(r_dmg * 1.5)
                       elif move_type == 'Water': r_dmg = int(r_dmg * 0.5)
        
        # Minimum 1 if not immune and not explicitly 0 damage
        if effectiveness > 0 and r_dmg < 1 and final_mod > 0 and bp_mod > 0:
            r_dmg = 1
        
        damage_rolls.append(r_dmg)
        
        # Crit Calculation (Simplified: 1.5x of final damage)
        # TODO: Implement strict ignore-stat-changes logic for crits
        c_dmg = int(r_dmg * 1.5)
        if effectiveness > 0 and c_dmg < 1: c_dmg = 1
        crit_rolls.append(c_dmg)
    
    # The user's snippet had a syntax error in the return statement and undefined 'final_damage'.
    is_crit = False
    if attacker.get('ability') == 'Merciless' and defender.get('status') in ['psn', 'tox']:
         is_crit = True
    
    return {
        'damage': damage_rolls,
        'damage_rolls': damage_rolls,
        'crit_rolls': crit_rolls,
        'effectiveness': effectiveness,
        'type_effectiveness': effectiveness,
        'is_stab': is_stab,
        'critRatio': 1,
        'is_crit': is_crit,
        'can_crit': True
    }


# Status moves result update (adding can_crit: False)
def _get_status_res():
    return {
        'damage': [0], 'damage_rolls': [0], 'effectiveness': 1.0,
        'type_effectiveness': 1.0, 'is_stab': False, 'critRatio': 1, 'is_crit': False,
        'can_crit': False
    }


