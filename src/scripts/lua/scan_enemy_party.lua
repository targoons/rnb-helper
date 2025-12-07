-- Scan for Enemy Party based on Active Mon Stats
-- Run this while in a battle with an enemy

local BATTLE_MON_START = 0x020233FC
local ENEMY_SLOT = 1 -- Slot 1 is usually enemy

function scanForParty()
    -- 1. Read Stats from Active Enemy
    local addr = BATTLE_MON_START + (ENEMY_SLOT * 0x5C)
    local maxHp = emu:read16(addr + 0x2E)
    local atk = emu:read16(addr + 0x02)
    local def = emu:read16(addr + 0x04)
    local spe = emu:read16(addr + 0x06)
    local spa = emu:read16(addr + 0x08)
    local spd = emu:read16(addr + 0x0A)
    
    console:log(string.format("Scanning for Stats: HP:%d Atk:%d Def:%d Spe:%d SpA:%d SpD:%d", 
        maxHp, atk, def, spe, spa, spd))

    -- 2. Scan RAM
    local startAddr = 0x02000000
    local endAddr = 0x02040000
    
    for i = startAddr, endAddr, 4 do
        -- Check MaxHP first (it's at offset +88 in Party Struct usually)
        -- But we don't know the offset relative to the start of the struct.
        -- We are looking for the sequence of stats.
        -- In Gen 3 Party:
        -- +88: MaxHP
        -- +90: Atk
        -- +92: Def
        -- +94: Speed
        -- +96: SpAtk
        -- +98: SpDef
        
        local val = emu:read16(i)
        if val == maxHp then
            -- Check the rest
            if emu:read16(i + 2) == atk and
               emu:read16(i + 4) == def and
               emu:read16(i + 6) == spe and
               emu:read16(i + 8) == spa and
               emu:read16(i + 10) == spd then
               
               console:log(string.format("FOUND MATCH at 0x%X", i))
               -- The match is at MaxHP offset (+88).
               -- So Party Start is i - 88.
               local partyStart = i - 88
               console:log(string.format("Potential Party Start: 0x%X", partyStart))
               
               -- Verify Species at +0 (PID) or +32 (Encrypted Data)
               -- Actually, let's just print it.
            end
        end
    end
    console:log("Scan complete.")
end

scanForParty()
