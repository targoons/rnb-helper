-- Dump Memory around Battle Struct
-- Run this script while in a battle!

local PLAYER_ADDR = 0x020233FC

console:log("Dumping Memory for Player Slot (0x" .. string.format("%X", PLAYER_ADDR) .. ")")
console:log("Offset | Value (Hex) | Value (Dec)")
console:log("-------|-------------|------------")

for i = 0x20, 0x38, 2 do
    local val = emu:read16(PLAYER_ADDR + i)
    console:log(string.format("+0x%X  | 0x%04X      | %d", i, val, val))
end

console:log("----------------------------------")
console:log("Please tell me your ACTUAL Current HP and Max HP!")
