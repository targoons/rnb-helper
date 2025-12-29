-- Verify Stats Table Candidates
-- We suspect the table might be at one of these addresses derived from pointers near the Names Table.

local candidates = {
    0x096CC898, -- Pointed to by 0x866C8F4 (which was pointed to by 0x8000140)
    0x0866C098, -- Pointed to by 0x800013C
    0x083A4486, -- Pointed to by 0x8000148
    0x08254784, -- FireRed Default
    0x08000000 -- Just to test
}

console:log("Verifying Stats Table Candidates...")

function verify(addr, name)
    -- Check ID 1 (Bulbasaur)
    -- Assume Size 28
    local bAddr = addr + 28 
    local hp = emu:read8(bAddr)
    local atk = emu:read8(bAddr + 1)
    local def = emu:read8(bAddr + 2)
    local t1 = emu:read8(bAddr + 6)
    local t2 = emu:read8(bAddr + 7)
    local a1 = emu:read8(bAddr + 22)
    
    console:log(string.format("Checking %s (0x%X)...", name, addr))
    console:log(string.format("  [ID 1] HP:%d Atk:%d Type:%d/%d Abil:%d", hp, atk, t1, t2, a1))
    
    if t1 == 12 and t2 == 3 and a1 == 65 then
        console:log("  MATCH! Found Stats Table (Gen 3 Format).")
        return true
    end
    -- Try Size 32?
    local bAddr32 = addr + 32
    local hp = emu:read8(bAddr32)
    local t1 = emu:read8(bAddr32 + 6)
    local a1 = emu:read8(bAddr32 + 22)
    if t1 == 12 and a1 == 65 then
        console:log("  MATCH! Found Stats Table (Size 32).")
        return true
    end
end

for _, c in ipairs(candidates) do
    verify(c, "Candidate")
end
