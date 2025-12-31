import requests

CALC_SERVICE_URL = "http://127.0.0.1:3000/batch-calculate"

def get_damage_rolls(attacker, defender, moves, field_conditions):
    """
    Sends a request to the Node.js service to get damage rolls.
    """
    payload = {
        "attacker": attacker,
        "defender": defender,
        "moves": moves,
        "field": field_conditions
    }
    
    try:
        # print(f"DEBUG: Calling Calc Service with {len(moves)} moves...")
        response = requests.post(CALC_SERVICE_URL, json=payload)
        if response.status_code != 200:
            print(f"Error calling calc service: {response.status_code} - {response.text}")
            return []
        data = response.json()
        # print(f"Calc Service Returned: {len(data)} results")
        return data
    except Exception as e:
        print(f"Error calling calc service: {e}")
        return []
