import json
import os

JSON_PATH = "data/mechanics_dump.json"
OUTPUT_PATH = "/Users/targoon/.gemini/antigravity/brain/768d80f8-600d-4724-932f-9924916694e0/mechanics_status.md"

def main():
    with open(JSON_PATH, 'r') as f:
        data = json.load(f)

    with open(OUTPUT_PATH, 'w') as f:
        f.write("# Mechanics Support Status\n\n")
        f.write("This document tracks the implementation status of Abilities, Items, and Moves in the Battle Engine.\n")
        f.write(f"- **Total Abilities**: {data['counts']['abilities']}\n")
        f.write(f"- **Total Items**: {data['counts']['items']}\n")
        f.write(f"- **Total Moves**: {data['counts']['moves']}\n\n")
        
        f.write("## Legend\n")
        f.write("- **[Calc]**: Handled by Damage Calculator (Node.js)\n")
        f.write("- **[Engine]**: Implemented in Battle Engine (Python)\n")
        f.write("- **[Pending]**: Not yet implemented / needs verification\n\n")
        
        f.write("## Abilities\n")
        f.write("| Ability | Status | Notes |\n")
        f.write("| :--- | :--- | :--- |\n")
        for x in data['abilities']:
            f.write(f"| {x['name']} | [Pending] | |\n")
            
        f.write("\n## Items\n")
        f.write("| Item | Status | Notes |\n")
        f.write("| :--- | :--- | :--- |\n")
        for x in data['items']:
            f.write(f"| {x['name']} | [Pending] | |\n")

        f.write("\n## Moves\n")
        f.write("| Move | Status | Notes |\n")
        f.write("| :--- | :--- | :--- |\n")
        for x in data['moves']:
             f.write(f"| {x['name']} | [Pending] | |\n")

if __name__ == "__main__":
    main()
