import requests
import json

def fetch_species():
    url = "https://pokeapi.co/api/v2/pokemon-species?limit=2000"
    print(f"Fetching {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        print(f"Found {len(results)} species.")
        
        lua_lines = []
        lua_lines.append("local SPECIES = {")
        
        species_map = {}
        
        for mon in results:
            name = mon['name']
            url = mon['url']
            # Extract ID
            s_id = int(url.split('/')[-2])
            
            # Format name: "bulbasaur" -> "Bulbasaur"
            formatted_name = name.title()
            
            species_map[s_id] = formatted_name
            
        # Store sorted
        for sid in sorted(species_map.keys()):
            lua_lines.append(f'    [{sid}]="{species_map[sid]}",')
            
        lua_lines.append("}")
        
        lua_lines.append("}")
        
        content = "\n".join(lua_lines)
        with open("lua_species_table.txt", "w") as f:
            f.write(content)
            
        # Write JSON for Python/Node
        with open("data/species.json", "w") as f:
            json.dump({str(k): v for k, v in species_map.items()}, f, indent=4)
            
        print("Written to lua_species_table.txt and data/species.json")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_species()
