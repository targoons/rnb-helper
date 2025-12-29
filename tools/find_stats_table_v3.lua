-- Find Base Stats Table (v3) - Pointer Scan
-- Names Table found at 0x083A0F80.
-- We search for pointer to Names Table: 0x083A0F80 (LE: 80 0F 3A 08)
-- Base Stats pointer is usually nearby.

local nameTableAddr = 0x083A0F80
local pByte1 = nameTableAddr & 0xFF
local pByte2 = (nameTableAddr >> 8) & 0xFF
local pByte3 = (nameTableAddr >> 16) & 0xFF
local pByte4 = (nameTableAddr >> 24) & 0xFF

local startAddr = 0x08000000 -- ROM Start
local endAddr = 0x08500000 -- First 5MB of ROM

console:log("Scanning for Pointer to Names Table (0x083A0F80)...")

function checkBulbasaur(tableAddr, size)
    -- ID 1 is at tableAddr + (1 * size) assuming 0-indexed or 1-indexed?
    -- Gen 3 ID 0 is ?????. ID 1 is Bulbasaur.
    -- So offset = tableAddr + size.
    local addr = tableAddr + size
    
    -- Check Types (Offset 6, 7)
    if emu:read8(addr + 6) ~= 12 then return false end -- Grass
    if emu:read8(addr + 7) ~= 3 then return false end -- Poison
    
    -- Check Abilities (Offset 22)
    if emu:read8(addr + 22) ~= 65 then return false end -- Overgrow (0x41)
    
    return true
end

function checkNearbyPointers(matchAddr)
    -- Look -100 to +100 bytes from match
    for offset = -100, 100, 4 do
        local ptrAddr = matchAddr + offset
        -- Read potential pointer
        local val = emu:read32(ptrAddr)
        -- Must be valid ROM pointer 0x08xxxxxx or 0x09xxxxxx
        if (val & 0xFE000000) == 0x08000000 then
            -- Test 28 byte size (Vanilla)
            if checkBulbasaur(val, 28) then
                console:log(string.format("FOUND CANDIDATE! Stats Table at: 0x%X (Size 28) found near 0x%X", val, matchAddr))
                return true
            end
             -- Test 32 byte size (Expanded?)
            if checkBulbasaur(val, 32) then
                console:log(string.format("FOUND CANDIDATE! Stats Table at: 0x%X (Size 32) found near 0x%X", val, matchAddr))
                return true
            end
        end
    end
end

for addr = startAddr, endAddr, 4 do
    if (addr % 0x100000) == 0 then console:log(string.format("Scanning 0x%X...", addr)) end
    if emu:read8(addr) == pByte1 and emu:read8(addr+1) == pByte2 and emu:read8(addr+2) == pByte3 and emu:read8(addr+3) == pByte4 then
        console:log(string.format("Found Names Pointer at: 0x%X", addr))
        checkNearbyPointers(addr)
    end
end
console:log("Scan complete.")
