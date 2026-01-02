import sys
import os
import unittest
import random
import traceback

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from pkh_app.battle_engine import BattleEngine, BattleState
from pkh_app.mechanics import Mechanics

class TestDamageModifiers(unittest.TestCase):
    def setUp(self):
        # Use local damage calculator (no calc_client needed)
        self.engine = BattleEngine()
        self.player_mon = {
            'species': 'Charizard',
            'max_hp': 400,
            'current_hp': 400,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Fire', 'Flying'],
            'moves': ['Flamethrower', 'Water Pulse', 'Thunderbolt', 'Leaf Blade', 'Dragon Claw'],
            'volatiles': [],
            'stat_stages': {},
            'item': None,
            'ability': 'Blaze',
            'level': 100
        }
        self.ai_mon = {
            'species': 'Blastoise',
            'max_hp': 400,
            'current_hp': 400,
            'stats': {'atk': 100, 'def': 100, 'spa': 100, 'spd': 100, 'spe': 100},
            'types': ['Water'],
            'moves': ['Tackle'],
            'volatiles': [],
            'stat_stages': {},
            'item': None,
            'ability': 'Torrent',
            'level': 100
        }
        self.state = BattleState(
            player_party=[self.player_mon],
            ai_party=[self.ai_mon],
            player_active=self.player_mon,
            ai_active=self.ai_mon,
            fields={
                'weather': None, 
                'terrain': None, 
                'hazards': {'player': [], 'ai': []}, 
                'screens': {
                    'player': {'reflect': 0, 'light_screen': 0, 'aurora_veil': 0}, 
                    'ai': {'reflect': 0, 'light_screen': 0, 'aurora_veil': 0}
                }
            }
        )

    def test_weather_modifiers(self):
        print("\nTesting Weather Modifiers...")
        
        # 1. Rain + Water (+50%)
        self.state.fields['weather'] = 'Rain'
        log = []
        initial_hp = self.ai_mon['current_hp']
        self.engine.execute_turn_action(self.state, 'player', 'Move: Water Pulse', 'ai', log)
        water_damage_rain = initial_hp - self.ai_mon['current_hp']
        print(f"Rain + Water Damage: {water_damage_rain}")
        self.assertGreater(water_damage_rain, 0, "Water move should deal damage in rain")
        
        # Reset and test without rain for comparison
        self.ai_mon['current_hp'] = initial_hp
        self.state.fields['weather'] = None
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Move: Water Pulse', 'ai', log)
        water_damage_normal = initial_hp - self.ai_mon['current_hp']
        print(f"Normal Water Damage: {water_damage_normal}")
        
        # Rain should boost water damage
        self.assertGreater(water_damage_rain, water_damage_normal, "Rain should boost water damage")
        
        # Reset for fire test
        self.ai_mon['current_hp'] = initial_hp
        self.state.fields['weather'] = 'Rain'
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Move: Flamethrower', 'ai', log)
        fire_damage_rain = initial_hp - self.ai_mon['current_hp']
        print(f"Rain + Fire Damage: {fire_damage_rain}")
        
        # Reset and test fire without rain
        self.ai_mon['current_hp'] = initial_hp
        self.state.fields['weather'] = None
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Move: Flamethrower', 'ai', log)
        fire_damage_normal = initial_hp - self.ai_mon['current_hp']
        print(f"Normal Fire Damage: {fire_damage_normal}")
        
        # Rain should reduce fire damage
        self.assertLess(fire_damage_rain, fire_damage_normal, "Rain should reduce fire damage")

    def test_terrain_modifiers(self):
        print("\nTesting Terrain Modifiers...")
        # Switch player to a grounded pokemon
        self.player_mon['species'] = 'Pikachu'
        self.player_mon['types'] = ['Electric']
        
        # 1. Electric Terrain + Electric move (+30%)
        initial_hp = self.ai_mon['current_hp']
        self.state.fields['terrain'] = 'Electric'
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Move: Thunderbolt', 'ai', log)
        electric_damage_terrain = initial_hp - self.ai_mon['current_hp']
        print(f"Electric Terrain + Electric Damage: {electric_damage_terrain}")
        self.assertGreater(electric_damage_terrain, 0, "Electric move should deal damage")
        
        # Test without terrain
        self.ai_mon['current_hp'] = initial_hp
        self.state.fields['terrain'] = None
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Move: Thunderbolt', 'ai', log)
        electric_damage_normal = initial_hp - self.ai_mon['current_hp']
        print(f"Normal Electric Damage: {electric_damage_normal}")
        
        # Terrain should boost damage
        self.assertGreater(electric_damage_terrain, electric_damage_normal, 
                          "Electric Terrain should boost Electric damage")

    def test_screen_modifiers(self):
        print("\nTesting Screen Modifiers...")
        
        # 1. Reflect (Physical -50%)
        initial_hp = self.ai_mon['current_hp']
        self.state.fields['screens']['ai']['reflect'] = 5
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Move: Leaf Blade', 'ai', log)
        reflect_damage = initial_hp - self.ai_mon['current_hp']
        print(f"Reflect + Physical Damage: {reflect_damage}")
        
        # Test without reflect
        self.ai_mon['current_hp'] = initial_hp
        self.state.fields['screens']['ai']['reflect'] = 0
        log = []
        self.engine.execute_turn_action(self.state, 'player', 'Move: Leaf Blade', 'ai', log)
        normal_damage = initial_hp - self.ai_mon['current_hp']
        print(f"Normal Physical Damage: {normal_damage}")
        
        # Reflect should reduce damage
        self.assertLess(reflect_damage, normal_damage, "Reflect should reduce physical damage")
        self.assertGreater(normal_damage, 0, "Move should deal damage")

if __name__ == '__main__':
    unittest.main()
