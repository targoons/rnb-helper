-- Find Battle Slots (Player and Enemy)
-- Run this script while in a battle!

console:log("Scanning for Battle Slots...")

-- CHANGE THESE TO MATCH YOUR CURRENT BATTLE
local PLAYER_SPECIES = 387 -- Turtwig (Change this if you are using something else!)
local ENEMY_SPECIES = 261  -- Poochyena

-- Common GBA RAM range
local START_ADDR = 0x02020000
local END_ADDR = 0x02030000

function scanForSlots()
    console:log("Scanning for Player: " .. PLAYER_SPECIES .. " and Enemy: " .. ENEMY_SPECIES)
    
    local playerAddr = nil
    local enemyAddr = nil
    
    for addr = START_ADDR, END_ADDR, 4 do
        local val = emu:read16(addr)
        
        -- Check for Player
        if val == PLAYER_SPECIES then
            -- Check if it looks like a Battle Struct (Level at +0x2C is valid)
            local level = emu:read8(addr + 0x2C)
            if level > 0 and level <= 100 then
                 -- Additional check: Max HP at +0x28 should be > 0
                 local maxHp = emu:read16(addr + 0x2A) -- 0x2A is MaxHP in Emerald
                 if maxHp > 0 then
                    console:log(string.format("Found Player Candidate at: 0x%X (Level: %d)", addr, level))
                    if not playerAddr then playerAddr = addr end
                 end
            end
        end
        
        -- Check for Enemy
        if val == ENEMY_SPECIES then
            local level = emu:read8(addr + 0x2C)
            if level > 0 and level <= 100 then
                 local maxHp = emu:read16(addr + 0x2A)
                 if maxHp > 0 then
                    console:log(string.format("Found Enemy Candidate at:  0x%X (Level: %d)", addr, level))
                    if not enemyAddr then enemyAddr = addr end
                 end
            end
        end
    end
    
    if playerAddr and enemyAddr then
        local diff = enemyAddr - playerAddr
        console:log("--------------------------------------------------")
        console:log(string.format("Player Address: 0x%X", playerAddr))
        console:log(string.format("Enemy Address:  0x%X", enemyAddr))
        console:log(string.format("Difference:     0x%X (%d bytes)", diff, diff))
        console:log("--------------------------------------------------")
    else
        console:log("Could not find both candidates. Please verify Species IDs.")
    end
end

scanForSlots()
