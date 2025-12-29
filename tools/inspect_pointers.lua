-- Inspect Pointers around 0x08000144 (Names Table Pointer)
-- We expect the Base Stats pointer to be nearby.

local center = 0x08000144
local startAddr = center - 32
local endAddr = center + 32

console:log(string.format("Inspecting pointers around 0x%X...", center))

for addr = startAddr, endAddr, 4 do
    local val = emu:read32(addr)
    local tag = ""
    if addr == center then tag = " <- NAMES POINTER" end
    
    -- Check if it's a ROM pointer
    if (val & 0xFE000000) == 0x08000000 then
        -- Read data at destination (First 32 bytes)
        local dest = val
        -- If this is Base Stats, matching ID 0 (?) or ID 1?
        -- Gen 3 Base Stats Table starts with ID 0 (?????). ID 1 (Bulbasaur) is at dest + StructSize.
        -- StructSize is unknown (28, 32, 36?).
        -- Let's print the first 64 bytes at dest.
        local bytes = emu:readRange(dest, 64)
        local hex = ""
        -- readRange returns a string in some versions
        if type(bytes) == "string" then
            for i=1, #bytes do
                hex = hex .. string.format("%02X ", string.byte(bytes, i))
            end
        else
            -- Table fallback
            for i=1, #bytes do
                hex = hex .. string.format("%02X ", bytes[i])
            end
        end
        console:log(string.format("Addr 0x%X -> Ptr 0x%X%s: Data: %s", addr, val, tag, hex))
        
        -- Analyze for Bulbasaur (ID 1)
        -- Look for 0C 03 (Grass Poison) and 41 (Overgrow)
        -- We don't know the stride (StructSize).
        -- We'll search the first 100 bytes for this signature.
    else
        console:log(string.format("Addr 0x%X -> Val 0x%X%s (Not a ROM pointer)", addr, val, tag))
    end
end
