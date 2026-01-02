
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pkh_app.battle_engine import BattleEngine

class MockCalc:
    pass

def test_ingestion():
    logging.basicConfig(level=logging.INFO)
    engine = BattleEngine(MockCalc())
    
    # Test checking a move flag
    print("\n--- Testing Move: Iron Head ---")
    contact = engine._check_mechanic('Iron Head', 'moves', 'isContact')
    print(f"Iron Head makes contact? {contact} (Expected: 1 or True)")
    
    print("\n--- Testing Move: Hyper Voice ---")
    sound = engine._check_mechanic('Hyper Voice', 'moves', 'isSound')
    print(f"Hyper Voice is sound? {sound} (Expected: 1 or True)")
    
    # Test checking an ability property
    print("\n--- Testing Ability: Huge Power ---")
    mod_atk = engine._check_mechanic('Huge Power', 'abilities', 'onModifyAtkPriority')
    print(f"Huge Power modifies Atk priority? {mod_atk} (Expected: 5)")
    
    # Test checking an item property
    print("\n--- Testing Item: Choice Band ---")
    priority = engine._check_mechanic('Choice Band', 'items', 'onModifyAtkPriority')
    print(f"Choice Band modify Atk priority? {priority} (Expected: 1)")

if __name__ == "__main__":
    test_ingestion()
