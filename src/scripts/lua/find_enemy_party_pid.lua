-- Find Enemy Party by PID
-- Reads the PID of the active enemy (Slot 1) and searches for it in memory
-- This helps locate the Enemy Party array

local BATTLE_MON_START = 0x020233FC
local SLOT_1_ADDR = BATTLE_MON_START + (1 * 0x5C) -- Slot 1 is usually the first enemy

function scan()
    -- 1. Read PID from Active Enemy
    local pid = emu:read32(SLOT_1_ADDR)
    local species = emu:read16(SLOT_1_ADDR + 0x00)
    
    console:log(string.format("Active Enemy (Slot 1): Species %d, PID 0x%08X", species, pid))
    
    if pid == 0 then
        console:log("Error: Active Enemy has PID 0. Are you in a battle?")
        return
    end

    -- 2. Search for this PID in WRAM (0x02000000 - 0x02040000)
    console:log("Scanning memory for PID...")
    local foundCount = 0
    
    for addr = 0x02020000, 0x02030000, 4 do
        local val = emu:read32(addr)
        if val == pid then
            -- We found the PID. Is it the Party?
            -- Party mons are 100 bytes. PID is at offset 0.
            -- Let's check if it looks like a party mon.
            -- Check OTID (next 4 bytes)
            local otid = emu:read32(addr + 4)
            
            -- Check Level (offset 84)
            local level = emu:read8(addr + 84)
            
            console:log(string.format("MATCH at 0x%X! Level: %d, OTID: 0x%08X", addr, level, otid))
            
            -- If it's the party, the previous/next 100 bytes might also be mons
            foundCount = foundCount + 1
        end
    end
    
    if foundCount == 0 then
        console:log("PID not found in memory (except active struct).")
    end
end

scan()
