-- Find Enemy Party Offset
-- Scans memory for a sequence of Pokemon species IDs matching the enemy team
-- Usage: Update TARGET_SPECIES with the species ID of the first enemy Pokemon (or any known enemy)

local TARGET_SPECIES = 261 -- Poochyena (Change this if needed)
local START_ADDR = 0x02000000
local END_ADDR = 0x02040000

console:log("Scanning for Enemy Party (Species: " .. TARGET_SPECIES .. ")...")

function scan()
    local foundCount = 0
    for addr = START_ADDR, END_ADDR, 4 do
        -- Check for unencrypted species ID first (unlikely for party, but possible)
        local val = emu:read16(addr)
        if val == TARGET_SPECIES then
            -- Check if it looks like a party struct (Level, HP, etc nearby)
            local level = emu:read8(addr + 84)
            if level > 0 and level < 100 then
                 console:log(string.format("Found Potential Unencrypted Match at 0x%X (Level: %d)", addr, level))
            end
        end

        -- Check for Encrypted Party Data
        -- Party data is encrypted with OTID and Personality
        -- We can't easily decrypt every word, but we can look for the PID/OTID pattern
        -- Or we can look for the KNOWN party count if we knew it.
        
        -- Alternative: Look for the Enemy Trainer's Party pointer?
        -- In Emerald, Enemy Party pointer is at 0x0202402C (Standard).
        -- Let's check around there.
    end
    
    -- Specific check for Run and Bun offset area
    -- Standard Emerald Enemy Party: 0x0202402C
    -- We found Player Party at 0x02023A98 (Diff -0xA54)
    -- Maybe Enemy Party is also shifted by -0xA54?
    -- 0x0202402C - 0xA54 = 0x020235D8 (This is what we are currently using)
    
    -- Let's dump memory around 0x020235D8 to see if it looks like a party
    console:log("Dumping memory around 0x020235D8 (Current Guess):")
    for i = 0, 5 do
        local addr = 0x020235D8 + (i * 100)
        local pid = emu:read32(addr)
        local otid = emu:read32(addr + 4)
        console:log(string.format("Slot %d (0x%X): PID: %08X, OTID: %08X", i, addr, pid, otid))
    end
end

scan()
