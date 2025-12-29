import requests
import json

def fetch_abilities():
    url = "https://pokeapi.co/api/v2/ability?limit=1000"
    print(f"Fetching {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        print(f"Found {len(results)} abilities.")
        
        lua_lines = []
        lua_lines.append("local ABILITIES = {")
        
        abilities_map = {}
        
        for item in results:
            name = item['name']
            url = item['url']
            a_id = int(url.split('/')[-2])
            
            formatted_name = name.replace("-", " ").title()
            abilities_map[a_id] = formatted_name
            
        for aid in sorted(abilities_map.keys()):
            lua_lines.append(f'    [{aid}]="{abilities_map[aid]}",')
            
        lua_lines.append("}")
        
        content = "\n".join(lua_lines)
        with open("lua_abilities_table.txt", "w") as f:
            f.write(content)
            
        print("Written to lua_abilities_table.txt")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_abilities()
