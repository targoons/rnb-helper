-- Find Base Stats Table (v4) - Zigzagoon Method
-- ID 263 (Zigzagoon).
-- Type: Normal/Normal (0, 0)
-- Abil: Pickup/Gluttony (53, 82) -> (0x35, 0x52)
-- Offsets: Type1=6, Type2=7, Abil1=22, Abil2=23.

local startAddr = 0x08000000
local endAddr = 0x09FFFFFF

console:log("Scanning for Stats Table via Zigzagoon (ID 263)...")

function checkZigzagoon(addr)
    if emu:read8(addr + 6) ~= 0 then return false end
    if emu:read8(addr + 7) ~= 0 then return false end
    if emu:read8(addr + 22) ~= 0x35 then return false end
    if emu:read8(addr + 23) ~= 0x52 then return false end
    return true
end

function verifyTable(tableAddr, size)
    -- Check ID 1 (Bulbasaur)
    -- Type: Grass/Poison (12, 3) -> (0x0C, 0x03)
    -- Abil1: Overgrow (65) -> (0x41)
    local addr = tableAddr + (1 * size) -- Assuming ID 1 is at index 1?
    -- Actually 0-indexed means ID 1 is at offset 1*size.
    -- (ID 0 is ?????).
    
    if emu:read8(addr + 6) == 0x0C and emu:read8(addr + 7) == 0x03 and emu:read8(addr + 22) == 0x41 then
        return true
    end
    return false
end

for addr = startAddr, endAddr, 4 do -- Alignment 4
    if checkZigzagoon(addr) then
        -- This address is potentially Zigzagoon.
        -- Calculate Table Start assuming ID 263.
        -- Try Size 28
        local tableStart28 = addr - (263 * 28)
        if verifyTable(tableStart28, 28) then
            console:log(string.format("FOUND Stats Table at: 0x%X (Size 28, via Zigzagoon)", tableStart28))
            return
        end
        
        -- Try Size 32
        local tableStart32 = addr - (263 * 32)
        if verifyTable(tableStart32, 32) then
            console:log(string.format("FOUND Stats Table at: 0x%X (Size 32, via Zigzagoon)", tableStart32))
            return
        end
        -- Try Size 36 (some expansions)
        local tableStart36 = addr - (263 * 36)
        if verifyTable(tableStart36, 36) then
            console:log(string.format("FOUND Stats Table at: 0x%X (Size 36, via Zigzagoon)", tableStart36))
            return
        end
    end
end

console:log("Not found.")
