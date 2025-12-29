-- Find Base Stats Table
-- Scans for Bulbasaur Stats (Gen 3 Order: HP, Atk, Def, Spd, SpA, SpD)
-- 45, 49, 49, 45, 65, 65
-- 0x2D, 0x31, 0x31, 0x2D, 0x41, 0x41

local startAddr = 0x08000000
local endAddr = 0x09FFFFFF
local pattern = {0x2D, 0x31, 0x31, 0x2D, 0x41, 0x41}

console:log("Scanning for Base Stats Table...")

function checkPattern(addr)
    for i=1, #pattern do
        local val = emu:read8(addr + i - 1)
        if val ~= pattern[i] then return false end
    end
    return true
end

-- Validate by checking Ivysaur at addr + 28?
-- Ivysaur: 60, 62, 63, 60, 80, 80
-- 0x3C, 0x3E, 0x3F, 0x3C, 0x50, 0x50
-- Gen 3 Entry Size is 28 bytes.

local found = false
for addr = startAddr, endAddr, 4 do -- Stats table is usually aligned
    if checkPattern(addr) then
        -- Check Ivysaur
        local addr2 = addr + 28
        local hp2 = emu:read8(addr2)
        if hp2 == 0x3C then
             console:log(string.format("Found Base Stats Table at: 0x%X", addr))
             found = true
             break
        end
    end
end

if not found then
    console:log("Not found.")
end
