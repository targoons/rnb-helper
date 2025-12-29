const { Generations } = require('@smogon/calc');

const gen = Generations.get(8);

function toArray(collection) {
    const arr = [];
    let success = false;

    // Try iterator
    try {
        for (const item of collection) {
            if (Array.isArray(item) && item.length === 2) {
                // Map entry [key, val]
                arr.push({ id: item[0], name: item[1].name });
            } else if (item && item.name) {
                // Direct item
                arr.push({ id: item.id || item.name, name: item.name });
            }
        }
        if (arr.length > 0) success = true;
    } catch (e) {
        // failed
    }

    if (success) return arr;

    // Try object keys
    try {
        for (const id in collection) {
            // skip prototype
            const val = collection[id];
            if (val && val.name) {
                arr.push({ id, name: val.name });
            }
        }
    } catch (e) { }

    return arr;
}

const abilities = toArray(gen.abilities);
const items = toArray(gen.items);
const moves = toArray(gen.moves);

const output = {
    abilities: abilities.sort((a, b) => a.name.localeCompare(b.name)),
    items: items.sort((a, b) => a.name.localeCompare(b.name)),
    moves: moves.sort((a, b) => a.name.localeCompare(b.name)),
    counts: {
        abilities: abilities.length,
        items: items.length,
        moves: moves.length
    }
};

console.log(JSON.stringify(output, null, 2));
