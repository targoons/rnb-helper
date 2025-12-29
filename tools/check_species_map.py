import re

INPUT_FILE = "../pokemon-run-and-bun/data/raw/Learnset, Evolution Methods and Abilities (2).txt"

def parse_names():
    names = []
    with open(INPUT_FILE, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Heuristic: A name line does NOT start with common keywords
        # and usually doesn't contain a colon (unless it's a form like "Meowth: Alolan"?)
        # The file format seems to be "Bulbasaur" just on a line.
        if line.startswith("Lv."): continue
        if line.startswith("Ability"): continue
        if line.startswith("Hidden"): continue
        if line.startswith("Evolves"): continue
        if line.startswith("Note"): continue
        if line.startswith("-"): continue
        if line.startswith("Tm"): continue 
        if line.startswith("Tr"): continue # Move tutor?
        if "Base Stats:" in line: continue
        if "Type:" in line: continue
        
        # It seems names are just "Bulbasaur" etc.
        # Let's check if it looks like a name (alphanumeric, maybe space/dash).
        # And ensure it's not some other metadata.
        
        names.append(line)

    print(f"Found {len(names)} entries.")
    
    with open("found_species.txt", "w") as f:
        for i, n in enumerate(names):
            f.write(f"{i+1}: {n}\n")
            
    # Check specific indices
    targets = ["Zigzagoon", "Flutter Mane"]
    
    for i, name in enumerate(names):
        idx = i + 1 
        for t in targets:
            if t.lower() in name.lower():
                print(f"Index {idx}: {name}")
                
    if len(names) >= 987:
        print(f"--> Index 987 is: {names[986]}")

if __name__ == "__main__":
    parse_names()
