import os

LUA_FILE = "lua/extract_state.lua"
SPECIES_FILE = "lua_species_table.txt"

def main():
    with open(LUA_FILE, 'r') as f:
        lua_content = f.read()
        
    with open(SPECIES_FILE, 'r') as f:
        species_content = f.read()
        
    # We want to insert 'species_content' before "local MOVES = {"
    if "local SPECIES = {" in lua_content:
        print("Species table already exists?")
        return

    split_point = "local MOVES = {"
    if split_point not in lua_content:
        print("Could not find insertion point 'local MOVES = {'")
        return
        
    parts = lua_content.split(split_point)
    
    new_content = parts[0] + "\n" + species_content + "\n\n" + split_point + parts[1]
    
    # Also add the helper function
    helper_Split = "-- Moves Map (Partial / Stub)"
    # We can add helper after SPECIES definition. 
    # Let's add it right after value.
    
    # Actually, let's just write the new file.
    
    
    with open(LUA_FILE, 'w') as f:
        f.write(new_content)
        
    print(f"Injected species table ({len(species_content)} bytes).")

if __name__ == "__main__":
    main()
