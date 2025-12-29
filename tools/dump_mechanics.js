const { Generations } = require('@smogon/calc');
const fs = require('fs');

const gen = Generations.get(8);

const abilities = [];
for (const [id, data] of gen.abilities) {
    abilities.push({ name: data.name, id: id });
}

const items = [];
for (const [id, data] of gen.items) {
    items.push({ name: data.name, id: id });
}

const moves = [];
for (const [id, data] of gen.moves) {
    moves.push({ name: data.name, id: id, bp: data.bp, type: data.type, category: data.category });
}

const output = {
    abilities: abilities.sort((a, b) => a.name.localeCompare(b.name)),
    items: items.sort((a, b) => a.name.localeCompare(b.name)),
    moves: moves.sort((a, b) => a.name.localeCompare(b.name))
};

console.log(JSON.stringify(output, null, 2));
