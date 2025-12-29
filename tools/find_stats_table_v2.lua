-- Find Base Stats Table (v2)
-- Scans for Bulbasaur Types/Abilities (Grass/Poison, Overgrow/None)
-- Entry Size: 28 bytes
-- ID 1 (Bulbasaur) -> Table Start + 28*1

local startAddr = 0x08000000
local endAddr = 0x09FFFFFF
-- Type values (Standard Gen 3)
-- Normal 0, Fight 1, Fly 2, Poison 3, Ground 4, Rock 5, Bug 6, Ghost 7, Steel 8
-- ??? 9, Fire 10, Water 11, Grass 12, Elec 13, Psychic 14, Ice 15, Dragon 16, Dark 17
local TYPE_GRASS = 12 -- 0x0C
local TYPE_POISON = 3 -- 0x03
local ABIL_OVERGROW = 65 -- 0x41

console:log("Scanning for Base Stats Table (by Types/Ability)...")

function checkEntry(addr)
    -- Check Types at +6, +7
    if emu:read8(addr + 6) ~= TYPE_GRASS then return false end
    if emu:read8(addr + 7) ~= TYPE_POISON then return false end
    -- Check Abilities at +22, +23
    if emu:read8(addr + 22) ~= ABIL_OVERGROW then return false end
    -- Abil 2 usually 0 for Bulbasaur
    if emu:read8(addr + 23) ~= 0 then return false end
    return true
end

local found = false
-- Scan for ID 1 (Bulbasaur) directly.
-- Table start would be addr - 28.
for addr = startAddr, endAddr, 4 do
    if checkEntry(addr) then
        -- Verify ID 4 (Charmander) at addr + (28*3) = addr + 84
        -- Charmander: Fire/Fire (10,10) or Fire/None? Blaze (66)
        local cAddr = addr + 84
        local type1 = emu:read8(cAddr + 6)
        local abil1 = emu:read8(cAddr + 22)
        
        -- Fire is 10 (0x0A). Blaze is 66 (0x42).
        if type1 == 10 and abil1 == 66 then
            local tableStart = addr - 28
            console:log(string.format("Found Base Stats Table at: 0x%X", tableStart))
            found = true
            break
        end
    end
end

if not found then
    console:log("Not found.")
end
