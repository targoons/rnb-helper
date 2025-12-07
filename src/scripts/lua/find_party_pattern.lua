-- Find Enemy Party by Pattern
-- Scans memory for a sequence of Pokemon structs that might be the Enemy Party
-- It looks for the Active Enemy's PID, then checks if it's part of an array of 6 mons (100 bytes each)

local BATTLE_MON_START = 0x020233FC
local SLOT_1_ADDR = BATTLE_MON_START + (1 * 0x5C) -- Active Enemy

function scan()
    -- 1. Get Active Enemy PID
    local pid = emu:read32(SLOT_1_ADDR)
    local otid = emu:read32(SLOT_1_ADDR + 4) -- Note: Battle struct might not have OTID at +4?
    -- Battle Struct (0x5C) layout:
    -- 0x00: Species, Atk, Def...
    -- 0x30: Nickname
    -- 0x50: Status
    -- It does NOT have PID/OTID at the start like Box/Party mons.
    -- Wait, Battle Struct DOES have PID/OTID but at different offsets?
    -- Actually, in Gen 3 Battle Struct, PID is at offset 0x00? No, Species is at 0x00.
    -- Let's check where PID is in Battle Struct.
    -- Usually it's NOT in the unencrypted battle struct.
    -- But the user's previous scan found PID at 0x2023458 (Slot 1 start).
    -- This means in Run and Bun (or this ROM), the Battle Struct MIGHT start with PID?
    -- OR the user's scan found the PID at the *start* of the struct, meaning the struct layout is different?
    
    -- User output: "Active Enemy (Slot 1): Species 261, PID 0x000C0105"
    -- "MATCH at 0x2023458! Level: 0, OTID: 0x000A000A"
    -- 0x2023458 IS Slot 1.
    -- If PID is at 0x2023458, then PID is at offset 0.
    -- But Species is ALSO read as 261.
    -- 261 = 0x105.
    -- PID = 0x000C0105.
    -- 0x105 is the lower 16 bits of PID.
    -- So PID contains Species ID? That's weird.
    -- Unless... it's not a PID, but just the first word which happens to be Species (low) + something else (high).
    -- 0x000C0105 -> Low: 0x0105 (261). High: 0x000C.
    -- So the first word IS Species (and maybe held item or something).
    -- It is NOT a PID.
    
    -- So searching for "PID" 0x000C0105 was actually searching for "Species 261 + High Word 0x000C".
    -- And we found it at Slot 1.
    
    -- To find the Party, we need the REAL PID.
    -- Party Mons (100 bytes) start with PID (4 bytes) and OTID (4 bytes).
    -- The Battle Struct usually doesn't have the full PID easily accessible unless we find the "Personality" field.
    -- In standard Gen 3 Battle Struct, Personality is at offset 0x20? Or 0x00?
    -- Let's assume we don't know the PID.
    
    -- Strategy: Search for a sequence of 6 structs where at least one of them has the Enemy Species.
    -- But Party data is encrypted. The Species ID is encrypted.
    -- So we can't search for Species ID directly in the party.
    
    -- However, we know the Player Party is at 0x02023A98.
    -- In Emerald, Enemy Party is usually BEFORE or AFTER Player Party.
    -- Player Party: 0x020244EC (Std). Found at 0x02023A98 (-0xA54).
    -- Enemy Party: 0x0202402C (Std). Expected at 0x020235D8 (-0xA54).
    -- User dumped 0x020235D8 and found 0s.
    
    -- Maybe it's shifted differently?
    -- Let's scan for ANY block of memory that looks like a Party.
    -- A Party has 6 slots of 100 bytes.
    -- Valid Party Mon:
    --   Level (offset 84) is 1-100.
    --   Status (offset 80) is usually 0.
    --   Current HP (offset 86) <= Max HP (offset 88).
    
    console:log("Scanning for Enemy Party candidates (Valid Level/HP checks)...")
    
    for addr = 0x02020000, 0x02030000, 4 do
        -- Check if this address could be the start of a party (Slot 0)
        -- We check Slot 0, 1, 2...
        
        local validCount = 0
        for i = 0, 5 do
            local monAddr = addr + (i * 100)
            local level = emu:read8(monAddr + 84)
            local curHp = emu:read16(monAddr + 86)
            local maxHp = emu:read16(monAddr + 88)
            
            if level > 0 and level <= 100 and maxHp > 0 and curHp <= maxHp then
                validCount = validCount + 1
            else
                -- If it's empty (all 0s), it might be valid if it's the end of the party
                if level == 0 and maxHp == 0 then
                    -- Empty slot, acceptable if we found at least 1 valid before
                else
                    -- Invalid data, break
                    break
                end
            end
        end
        
        if validCount >= 1 then
            -- Found a potential party!
            -- Check if it's the Player Party (we know that one)
            if addr == 0x02023A98 then
                -- Ignore Player Party
            else
                console:log(string.format("Potential Enemy Party at 0x%X (Valid Mons: %d)", addr, validCount))
                -- Dump the first mon's details to verify
                local level = emu:read8(addr + 84)
                local curHp = emu:read16(addr + 86)
                local maxHp = emu:read16(addr + 88)
                console:log(string.format("  Slot 0: Lv %d, HP %d/%d", level, curHp, maxHp))
            end
        end
    end
end

scan()
