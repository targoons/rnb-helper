import fs from 'fs';
import path from 'path';

const INPUT_FILE = path.join(process.cwd(), 'src/data/raw/Trainer Battles (2).txt');
const OUTPUT_FILE = path.join(process.cwd(), 'src/data/trainers.json');

interface TrainerData {
    id: string;
    name: string;
    location: string;
    team: any[];
}

function parseTrainers() {
    const content = fs.readFileSync(INPUT_FILE, 'utf-8');
    const lines = content.split('\n');

    const trainers: Record<string, TrainerData> = {};
    let currentTrainer: TrainerData | null = null;
    let currentLocation = '';

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        // Location Header
        if (line.startsWith('------')) {
            // Next line is location
            if (lines[i + 1] && !lines[i + 1].startsWith('------')) {
                currentLocation = lines[i + 1].trim();
                i += 2; // Skip location and closing dashes
            }
            continue;
        }

        // Trainer Name (Usually ends with [Boss] or [Double] or just a name)
        // Heuristic: Line doesn't start with a Pokemon name or "Lv."
        // And it's not a comment
        if (!line.includes('Lv.') && !line.startsWith('-') && !line.startsWith('~')) {
            if (currentTrainer) {
                trainers[currentTrainer.id] = currentTrainer;
            }

            const name = line;
            const id = name.toLowerCase().replace(/[^a-z0-9]/g, '_');

            currentTrainer = {
                id,
                name,
                location: currentLocation,
                team: []
            };
            continue;
        }

        // Pokemon Line
        // Format: Species Lv.X @Item: Move1, Move2 [Nature|Ability]
        // Or: Species Lv.X [Nature|Ability] (Level up moves)
        if (line.includes('Lv.') && currentTrainer) {
            // Regex to parse
            // Example: Grubbin Lv.6 @Oran Berry: Bug Bite, Spark, Vice Grip [Bashful|Swarm]

            // 1. Full Format: Species Lv.X @Item: Moves [Nature|Ability]
            const fullMatch = line.match(/^(.+?) Lv\.(\d+) @(.+?): (.+?) \[(.+?)\|(.+?)\]$/);

            // 2. No Item, but Moves: Species Lv.X Moves [Nature|Ability]
            // Note: Moves are separated by commas. We need to be careful not to eat the Nature part.
            // But Nature is always at the end in [].
            const noItemMatch = line.match(/^(.+?) Lv\.(\d+) (.+?) \[(.+?)\|(.+?)\]$/);

            // 3. Level Up Moves (No moves listed): Species Lv.X [Nature|Ability]
            // Or Species Lv.X @Item [Nature|Ability] (Item but level up moves? Unlikely but possible)
            const levelUpMatch = line.match(/^(.+?) Lv\.(\d+) \[(.+?)\|(.+?)\]$/);

            if (fullMatch) {
                const [_, species, level, item, movesStr, nature, ability] = fullMatch;
                currentTrainer.team.push({
                    speciesId: species.trim(),
                    level: parseInt(level),
                    item: item.trim(),
                    moves: movesStr.split(',').map(m => m.trim()),
                    nature: nature.trim(),
                    ability: ability.trim()
                });
            } else if (noItemMatch) {
                // This might match "Species Lv.5 [Nature|Ability]" if (.+?) is greedy?
                // No, because there is a space before [.
                // But "Species Lv.5 Moves [Nature|Ability]" vs "Species Lv.5 [Nature|Ability]"
                // If moves exist, there is text between Lv.X and [.

                // Let's check if it's actually format 3 first.
                if (levelUpMatch) {
                    const [_, species, level, nature, ability] = levelUpMatch;
                    currentTrainer.team.push({
                        speciesId: species.trim(),
                        level: parseInt(level),
                        item: undefined,
                        moves: [],
                        nature: nature.trim(),
                        ability: ability.trim()
                    });
                } else {
                    const [_, species, level, movesStr, nature, ability] = noItemMatch;
                    currentTrainer.team.push({
                        speciesId: species.trim(),
                        level: parseInt(level),
                        item: undefined,
                        moves: movesStr.split(',').map(m => m.trim()),
                        nature: nature.trim(),
                        ability: ability.trim()
                    });
                }
            } else if (levelUpMatch) {
                // Fallback if regex 2 didn't catch it (it should have if written correctly)
                const [_, species, level, nature, ability] = levelUpMatch;
                currentTrainer.team.push({
                    speciesId: species.trim(),
                    level: parseInt(level),
                    item: undefined,
                    moves: [],
                    nature: nature.trim(),
                    ability: ability.trim()
                });
            } else {
                console.warn(`Failed to parse line: ${line}`);
            }
        }
    }

    // Add last trainer
    if (currentTrainer) {
        trainers[currentTrainer.id] = currentTrainer;
    }

    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(trainers, null, 2));
    console.log(`Parsed ${Object.keys(trainers).length} trainers.`);
}

parseTrainers();
