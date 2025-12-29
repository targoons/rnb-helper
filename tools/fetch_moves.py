import requests
import json

def fetch_moves():
    url = "https://pokeapi.co/api/v2/move?limit=1000"
    print(f"Fetching {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        print(f"Found {len(results)} moves.")
        
        # We need to get the ID from the URL since it's not in the list summary
        # url: "https://pokeapi.co/api/v2/move/1/"
        
        lua_lines = []
        lua_lines.append("local MOVES = {")
        
        moves_map = {}
        
        for move in results:
            name = move['name']
            move_url = move['url']
            # Extract ID
            move_id = int(move_url.split('/')[-2])
            
            # Format name: "pound" -> "Pound", "karate-chop" -> "Karate Chop"
            formatted_name = name.replace("-", " ").title()
            
            moves_map[move_id] = formatted_name
            
        # Store sorted
        for mid in sorted(moves_map.keys()):
            # Handle special characters if any? simple string usually fine
            lua_lines.append(f'    [{mid}]="{moves_map[mid]}",')
            
        lua_lines.append("}")
        
        content = "\n".join(lua_lines)
        with open("lua_moves_table.txt", "w") as f:
            f.write(content)
            
        print("Written to lua_moves_table.txt")
        
        # Also write JSON for Python/Node
        with open("data/moves.json", "w") as f:
            json.dump(moves_map, f, indent=4)
        print("Written to data/moves.json")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_moves()
