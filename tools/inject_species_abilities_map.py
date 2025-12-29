import os

LUA_FILE = "lua/extract_state.lua"
MAP_FILE = "lua_species_abilities_map.txt"

def main():
    with open(LUA_FILE, 'r') as f:
        lua_content = f.read()
        
    with open(MAP_FILE, 'r') as f:
        map_content = f.read()
        
    # Insert before "local SPECIES ="
    split_point = "local SPECIES = {"
    if split_point not in lua_content:
        print("Could not find insertion point 'local SPECIES = {'")
        return
        
    parts = lua_content.split(split_point)
    
    new_content = parts[0] + "\n" + map_content + "\n\n" + split_point + parts[1]
    
    with open(LUA_FILE, 'w') as f:
        f.write(new_content)
        
    print(f"Injected species ability map ({len(map_content)} bytes).")

if __name__ == "__main__":
    main()
