-- Find Battle Mons Offset
-- Run this script while in a battle!

console:log("Scanning for Battle Structs...")

-- Ask user for the Species ID of the ACTIVE ENEMY Pokemon
-- You can look this up on a Pokedex (e.g. Turtwig = 387)
-- Or just tell me what it is and I'll hardcode it for the scan.
-- Let's assume the user can edit this variable:
local TARGET_SPECIES = 387 -- CHANGE THIS TO THE ENEMY SPECIES ID

-- Common GBA RAM range
local START_ADDR = 0x02020000
local END_ADDR = 0x02030000

function scanForSpecies()
    console:log("Scanning for Species ID: " .. TARGET_SPECIES)
    local found = 0
    
    for addr = START_ADDR, END_ADDR, 4 do
        -- Read 16-bit value
        local val = emu:read16(addr)
        
        if val == TARGET_SPECIES then
            -- Potential match. Check if it looks like a Battle Struct.
            -- Battle Struct (Gen 3) usually has:
            -- +0x00 Species
            -- +0x2A Current HP (should be > 0)
            -- +0x2C Level (should be reasonable, e.g. 1-100)
            
            local hp = emu:read16(addr + 0x28) -- Current HP is usually at 0x28 or 0x2A?
            -- In Emerald: 0x28 = Current HP? No, 0x28 is usually Max HP?
            -- Let's check my previous assumption:
            -- mon.currentHp = emu:read16(address + 0x28)
            -- mon.maxHp = emu:read16(address + 0x2A)
            
            local level = emu:read8(addr + 0x2C)
            
            if level > 0 and level <= 100 then
                console:log(string.format("Found Candidate at: 0x%X (Level: %d)", addr, level))
                found = found + 1
            end
        end
    end
    
    if found == 0 then
        console:log("No matches found for Species " .. TARGET_SPECIES)
    else
        console:log("Scan complete. Found " .. found .. " candidates.")
    end
end

scanForSpecies()
