
import sys
import os
from unittest.mock import MagicMock

# Ensure we can import from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from pkh_app.battle_engine import BattleEngine

def create_mocked_engine():
    """
    Creates a BattleEngine instance with a MagicMock calc_client 
    and populated rich_data for common test scenarios.
    """
    calc_client = MagicMock()
    # Default behavior for calc_client: return 10 damage
    # DamageCalculator calls calc_damage(attacker, defender, move_name, field)
    calc_client.calc_damage.return_value = {'damage_rolls': [10], 'moveName': 'Test Move'}
    
    engine = BattleEngine(calc_client)
    
    # Populate standard test data
    # IMPORTANT: Update existing dict so references in Enricher/TriggerHandler remain valid
    if not engine.rich_data:
        engine.rich_data.update({
            'moves': {},
            'abilities': {},
            'items': {}
        })
    else:
        # Ensure keys exist
        for key in ['moves', 'abilities', 'items']:
            engine.rich_data.setdefault(key, {})
    engine.move_names = {}
    
    # Helper to add move
    def add_move(name, type, category, bp=0, accuracy=100, effect=None, target='normal', priority=0, flags=None):
        id = name.lower().replace(" ", "").replace("-", "")
        engine.rich_data['moves'][id] = {
            'name': name,
            'type': type,
            'category': category,
            'basePower': bp,
            'accuracy': accuracy,
            'target': target,
            'priority': priority,
            'flags': flags or {}
        }
        if effect:
            engine.rich_data['moves'][id].update(effect)
        engine.move_names[name] = name
        
    # Common Moves
    add_move('Tackle', 'Normal', 'Physical', 40, flags={'contact': 1})
    add_move('Scratch', 'Normal', 'Physical', 40, flags={'contact': 1})
    add_move('Growl', 'Normal', 'Status', 0, target='allAdjacentFoes')
    add_move('Flamethrower', 'Fire', 'Special', 90)
    add_move('Vine Whip', 'Grass', 'Physical', 45, flags={'contact': 1})
    add_move('Water Gun', 'Water', 'Special', 40)
    add_move('Flamethrower', 'Fire', 'Special', 90)
    add_move('Thunder Shock', 'Electric', 'Special', 40)
    add_move('Hyper Voice', 'Normal', 'Special', 90, flags={'sound': 1})
    add_move('Toxic', 'Poison', 'Status', 0, accuracy=100)
    add_move('Will-O-Wisp', 'Fire', 'Status', 0, accuracy=85)
    add_move('Explosion', 'Normal', 'Physical', 250, target='allAdjacent')
    add_move('Thunderbolt', 'Electric', 'Special', 90)
    add_move('Thunder Wave', 'Electric', 'Status', 0, accuracy=100, flags={'reflectable': 1})
    add_move('Knock Off', 'Dark', 'Physical', 65, flags={'contact': 1})
    add_move('Ember', 'Fire', 'Special', 40)
    add_move('Sludge Bomb', 'Poison', 'Special', 90)
    add_move('Psychic', 'Psychic', 'Special', 90)
    add_move('Earthquake', 'Ground', 'Physical', 100, target='allAdjacent')
    add_move('Surf', 'Water', 'Special', 90, target='allAdjacent')
    add_move('Protect', 'Normal', 'Status', 0, priority=4)
    add_move('Double-Edge', 'Normal', 'Physical', 120, flags={'contact': 1}, effect={'recoil': [1, 3]}) # 1/3 recoil
    add_move('Absorb', 'Grass', 'Special', 20, effect={'drain': [1, 2]}) # 50% drain
    add_move('Bullet Seed', 'Grass', 'Physical', 25, flags={'bullet': 1}) # Multihit handled by engine
    
    # Abilities (Just need existence usually, logic is in code)
    abilities = [
        'Static', 'Sturdy', 'Overgrow', 'Blaze', 'Torrent', 'Flash Fire', 'Levitate', 
        'Soundproof', 'Rough Skin', 'Skill Link', 'Technician', 'Sheer Force', 
        'Sap Sipper', 'Storm Drain', 'Intimidate', 'Natural Cure', 'Pixilate', 
        'No Guard', 'Unburden', 'Thick Fat', 'Weak Armor', 'Ice Face', 'Aura Break',
        'Dark Aura', 'Fairy Aura', 'Bad Dreams', 'Beast Boost', 'Color Change',
        'Cotton Down', 'Mirror Armor', 'Magic Bounce', 'Liquid Ooze', 
        'Anticipation', 'Mold Breaker'
    ]
    for a in abilities:
        id = a.lower().replace(" ", "")
        engine.rich_data['abilities'][id] = {'name': a}
        
    # Items
    items = ['Leftovers', 'Life Orb', 'Choice Band', 'Choice Scarf', 'Choice Specs', 'Focus Sash', 'Rocky Helmet', 'Protective Pads', 'Sitrus Berry', 'Oran Berry']
    for i in items:
        id = i.lower().replace(" ", "")
        engine.rich_data['items'][id] = {'name': i}
        
    return engine
