-- Find Species Names Table
-- Scans for "Bulbasaur"

local startAddr = 0x08000000
local endAddr = 0x09FFFFFF -- 32MB ROM (Expanded)
local pattern = {0xBC, 0xE9, 0xE0, 0xD6, 0xD5, 0xE7, 0xD5, 0xE9, 0xE6, 0xFF}
-- Bulbasaur + Terminator

console:log("Scanning for Species Table (byte-by-byte)...")

function checkPattern(addr)
    for i=1, #pattern do
        local val = emu:read8(addr + i - 1)
        if val ~= pattern[i] then return false end
    end
    return true
end

local found = false
for addr = startAddr, endAddr, 1 do -- Scan EVERY byte (Names are 11 bytes, not aligned)
    if checkPattern(addr) then
        console:log(string.format("Found 'Bulbasaur' at: 0x%X", addr))
        -- Verify 'Ivysaur' at addr + 11?
        -- Ivysaur: I=0xC3 v=0xEA y=0xED ...
        -- Just report match.
        found = true
        break -- Stop at first match (usually correct, usually in low ROM or repointed text section)
    end
end

if not found then
    console:log("Not found.")
end
