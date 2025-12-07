-- Dump Battle Struct and Global Data
-- Run this script while in a battle!

local PLAYER_ADDR = 0x020233FC
-- Standard Emerald Weather is 0x02023F48. Let's check around there.
local WEATHER_ADDR = 0x02023F48 

console:log("Dumping Battle Struct for Player (0x" .. string.format("%X", PLAYER_ADDR) .. ")")
console:log("Offset | Value (Hex) | Value (Dec)")
console:log("-------|-------------|------------")

-- Dump 0x00 to 0x60 (covering most of the struct)
for i = 0x00, 0x60, 4 do
    local val = emu:read32(PLAYER_ADDR + i)
    console:log(string.format("+0x%02X   | 0x%08X  | %d", i, val, val))
end

console:log("----------------------------------")
console:log("Checking Potential Weather Address (Standard Emerald: 0x02023F48)")
local w = emu:read16(WEATHER_ADDR)
console:log(string.format("0x%X: 0x%04X (%d)", WEATHER_ADDR, w, w))

console:log("----------------------------------")
console:log("Please tell me:")
console:log("1. Your Status Condition (Burn, Para, None, etc.)")
console:log("2. Any Stat Changes (e.g. +1 Atk)")
console:log("3. Current Weather (Rain, Sun, None)")
