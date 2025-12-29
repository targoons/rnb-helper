-- Find Base Stats Table (v5) - Torchic / Galarian Zigzagoon
-- Torchic (ID 255): Fire (10), Blaze (66). Gen 3 Pure Type is usually [Type, Type] or [Type, None]? Vanilla FireRed is [Type, Type].
-- Run&Bun might conform to [Type, Type].
-- Fire=10 (0x0A). Blaze=66 (0x42).
-- Search: 0A 0A ... 42 00 (or 42 42?) -> Abil 2 usually None (0).

-- ZigzagoonGalarian (ID 987): Dark/Normal is most likely. 
-- Dark=17 (0x11), Normal=0.
-- Gluttony=82 (0x52).
-- Search: 11 00 ... 52 00 (or 00 11 ... 52 00)
-- 987 * StructSize is large offset.

local startAddr = 0x08000000
local endAddr = 0x09FFFFFF

console:log("Scanning for Stats Table via Torchic (ID 255)...")

function checkTorchic(addr)
    local t1 = emu:read8(addr + 6)
    local t2 = emu:read8(addr + 7)
    local a1 = emu:read8(addr + 22)
    
    -- Check Torchic (Fire/Fire or Fire/None, Blaze)
    if (t1 == 10) and (a1 == 66) then
        return true
    end
    return false
end

function verifyTable(tableAddr, size)
    -- Check Bulbasaur (ID 1): Grass/Poison (12, 3), Overgrow (65)
    local addr = tableAddr + (1 * size)
    -- Or Check Charmander (ID 4): Fire (10), Blaze (66)
    local addr4 = tableAddr + (4 * size)
    
    if emu:read8(addr + 6) == 12 and emu:read8(addr + 7) == 3 and emu:read8(addr + 22) == 65 then
        return true
    end
    if emu:read8(addr4 + 6) == 10 and emu:read8(addr4 + 22) == 66 then
        return true
    end
    return false
end

for addr = startAddr, endAddr, 4 do
    if (addr % 0x100000) == 0 then console:log(string.format("Scanning 0x%X...", addr)) end
    
    if checkTorchic(addr) then
        -- Assume this is ID 255
        local sizes = {28, 32, 36}
        for _, size in ipairs(sizes) do
            local start = addr - (255 * size)
            -- Verify
            if verifyTable(start, size) then
                console:log(string.format("FOUND Stats Table at: 0x%X (Size %d, via Torchic)", start, size))
                return
            end
        end
    end
end
console:log("Scan complete.")
