import os

LUA_FILE = "lua/extract_state.lua"
ABILITIES_FILE = "lua_abilities_table.txt"

def main():
    with open(LUA_FILE, 'r') as f:
        lua_content = f.read()
        
    with open(ABILITIES_FILE, 'r') as f:
        abilities_content = f.read()
        
    # Insert before "local MOVES" or "local SPECIES"
    # To keep it organized, let's put it before SPECIES if possible.
    
    split_point = "local SPECIES = {"
    if split_point not in lua_content:
        # Fallback
        split_point = "local MOVES = {"
        
    if split_point not in lua_content:
        print("Could not find insertion point")
        return
        
    parts = lua_content.split(split_point)
    
    new_content = parts[0] + "\n" + abilities_content + "\n\n" + split_point + parts[1]
    
    with open(LUA_FILE, 'w') as f:
        f.write(new_content)
        
    print(f"Injected abilities table ({len(abilities_content)} bytes).")

if __name__ == "__main__":
    main()
