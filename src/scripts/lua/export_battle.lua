-- Export Battle State to JSON for Battle Helper
-- Run this script in mGBA (Tools -> Scripting -> Load Script)

local OUTPUT_FILE = "/Users/targoon/Pokemon/battle-helper/src/data/imports/battle.json"

-- Memory Offsets (Emerald Standard)
-- Memory Offsets (Run and Bun - Calculated from Party Offset 0x02023A98)
-- Standard Emerald Party: 0x020244EC. Diff: -0xA54.
-- Standard Emerald Enemy Party: 0x0202402C. New: 0x020235D8.
-- Standard Emerald Battle Mons: 0x02024744. New: 0x02023CF0.

-- Memory Addresses (Run and Bun / Emerald)
-- Confirmed by user scan: Enemy (Slot 1) is at 0x020233FC.
-- Therefore, Slot 0 (Player) is at 0x020233FC - 0x58 = 0x020233A4.
local BATTLE_MON_START = 0x020233FC
local ENEMY_PARTY_LOC = 0x02023CF0 -- Confirmed: Immediately after Player Party (0x02023A98 + 600)
local PLAYER_PARTY_LOC = 0x02023A98 -- From runandbun (1).lua
local PLAYER_PARTY_COUNT = 0x02023A95 -- From runandbun (1).lua
local enemyPartyCount = 6 
local partyMonSize = 100

-- Character Map (Same as box)
local charmap = { [0]=
	" ", "À", "Á", "Â", "Ç", "È", "É", "Ê", "Ë", "Ì", "こ", "Î", "Ï", "Ò", "Ó", "Ô",
	"Œ", "Ù", "Ú", "Û", "Ñ", "ß", "à", "á", "ね", "ç", "è", "é", "ê", "ë", "ì", "ま",
	"î", "ï", "ò", "ó", "ô", "œ", "ù", "ú", "û", "ñ", "º", "ª", "", "&", "+", "あ",
	"ぃ", "ぅ", "ぇ", "ぉ", "v", "=", "ょ", "が", "ぎ", "ぐ", "げ", "ご", "ざ", "じ", "ず", "ぜ",
	"ぞ", "だ", "ぢ", "づ", "で", "ど", "ば", "び", "ぶ", "べ", "ぼ", "ぱ", "ぴ", "ぷ", "ぺ", "ぽ",
	"っ", "¿", "¡", "Pk", "Mn", "Po", "Ke", "", "", "", "Í", "%", "(", ")", "セ", "ソ",
	"タ", "チ", "ツ", "テ", "ト", "ナ", "ニ", "ヌ", "â", "ノ", "ハ", "ヒ", "フ", "ヘ", "ホ", "í",
	"ミ", "ム", "メ", "モ", "ヤ", "ユ", "ヨ", "ラ", "リ", "⬆", "⬇", "⬅", "➡", "ヲ", "ン", "ァ",
	"ィ", "ゥ", "ェ", "ォ", "ャ", "ュ", "ョ", "ガ", "ギ", "グ", "ゲ", "ゴ", "ザ", "ジ", "ズ", "ゼ",
	"ゾ", "ダ", "ヂ", "ヅ", "デ", "ド", "バ", "ビ", "ブ", "ベ", "ボ", "パ", "ピ", "プ", "ペ", "ポ",
	"ッ", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "!", "?", ".", "-", "・",
	"…", "“", "”", "‘", "’", "♂", "♀", "$", ",", "×", "/", "A", "B", "C", "D", "E",
	"F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U",
	"V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k",
	"l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "▶",
	":", "Ä", "Ö", "Ü", "ä", "ö", "ü", "⬆", "⬇", "⬅", "", "", "", "", "", ""
}
local terminator = 0xFF

function toString(rawstring)
	local string = ""
	for _, char in ipairs({rawstring:byte(1, #rawstring)}) do
		if char == terminator then break end
		if charmap[char] then
			string = string..charmap[char]
		else
			string = string.."?"
		end
	end
	return string
end

function readBoxMon(address)
	local mon = {}
	mon.personality = emu:read32(address + 0)
	mon.otId = emu:read32(address + 4)
	mon.nickname = toString(emu:readRange(address + 8, 10))
	
	-- Decryption
	local key = mon.otId ~ mon.personality
	local substructSelector = {
		[ 0] = {0, 1, 2, 3}, [ 1] = {0, 1, 3, 2}, [ 2] = {0, 2, 1, 3}, [ 3] = {0, 3, 1, 2},
		[ 4] = {0, 2, 3, 1}, [ 5] = {0, 3, 2, 1}, [ 6] = {1, 0, 2, 3}, [ 7] = {1, 0, 3, 2},
		[ 8] = {2, 0, 1, 3}, [ 9] = {3, 0, 1, 2}, [10] = {2, 0, 3, 1}, [11] = {3, 0, 2, 1},
		[12] = {1, 2, 0, 3}, [13] = {1, 3, 0, 2}, [14] = {2, 1, 0, 3}, [15] = {3, 1, 0, 2},
		[16] = {2, 3, 0, 1}, [17] = {3, 2, 0, 1}, [18] = {1, 2, 3, 0}, [19] = {1, 3, 2, 0},
		[20] = {2, 1, 3, 0}, [21] = {3, 1, 2, 0}, [22] = {2, 3, 1, 0}, [23] = {3, 2, 1, 0},
	}

	local pSel = substructSelector[mon.personality % 24]
	local ss = {}
	for i = 0, 3 do
		ss[i] = {}
		for j = 0, 2 do
			ss[i][j] = emu:read32(address + 32 + pSel[i+1] * 12 + j * 4) ~ key
		end
	end

	-- Substruct 0: Growth
	mon.species = ss[0][0] & 0xFFFF
	mon.heldItem = ss[0][0] >> 16
	mon.experience = ss[0][1]
	
	-- Substruct 1: Attacks
	mon.moves = {
		ss[1][0] & 0xFFFF,
		ss[1][0] >> 16,
		ss[1][1] & 0xFFFF,
		ss[1][1] >> 16
	}
	
	-- Substruct 3: Misc (IVs)
	local misc2 = ss[3][1]
	mon.ivs = misc2
    -- Corrected IV shift
	mon.hpIV = (misc2 >> 1) & 0x1F
	mon.atkIV = (misc2 >> 6) & 0x1F
	mon.defIV = (misc2 >> 11) & 0x1F
	mon.speIV = (misc2 >> 16) & 0x1F
	mon.spaIV = (misc2 >> 21) & 0x1F
	mon.spdIV = (misc2 >> 26) & 0x1F
	
	-- Nature
    mon.hiddenNature = (ss[0][2] >> 16) & 0x1F
	local natures = {
		"Hardy","Lonely","Brave","Adamant","Naughty",
		"Bold","Docile","Relaxed","Impish","Lax",
		"Timid","Hasty","Serious","Jolly","Naive",
		"Modest","Mild","Quiet","Bashful","Rash",
		"Calm","Gentle","Sassy","Careful","Quirky"
	}
    if mon.hiddenNature == 26 or mon.hiddenNature == nil then
        mon.nature = natures[(mon.personality % 25) + 1]
    else
        mon.nature = natures[mon.hiddenNature + 1] or natures[(mon.personality % 25) + 1]
    end

	return mon
end

function readPartyMon(address)
	local mon = readBoxMon(address)
	mon.status = emu:read32(address + 80)
	mon.level = emu:read8(address + 84)
	mon.currentHp = emu:read16(address + 86)
	mon.maxHp = emu:read16(address + 88)
	return mon
end

-- Battle Mons (Unencrypted, Active Pokemon)
-- Offset 0x020233FC (Run and Bun Confirmed)
-- Size 0x5C
function readBattleMon(index)
    local address = BATTLE_MON_START + (index * 0x5C)
    local mon = {}
    
    -- Structure (Approximate for Gen 3)
    mon.species = emu:read16(address + 0x00)
    mon.atk = emu:read16(address + 0x02)
    mon.def = emu:read16(address + 0x04)
    mon.spe = emu:read16(address + 0x06)
    mon.spa = emu:read16(address + 0x08)
    mon.spd = emu:read16(address + 0x0A)
    
    mon.moves = {
        emu:read16(address + 0x0C),
        emu:read16(address + 0x0E),
        emu:read16(address + 0x10),
        emu:read16(address + 0x12)
    }
    
    mon.currentHp = emu:read16(address + 0x2A)
    mon.maxHp = emu:read16(address + 0x2E)
    mon.level = emu:read8(address + 0x2C)
    mon.heldItem = 0 
    mon.nickname = toString(emu:readRange(address + 0x30, 10))
    
    -- Status (0x50)
    mon.status = emu:read32(address + 0x50)

    -- Stat Stages (0x18 - 0x1F)
    -- Order: HP, Atk, Def, Speed, SpAtk, SpDef, Acc, Evasion
    mon.statStages = {
        hp = emu:read8(address + 0x18),
        atk = emu:read8(address + 0x19),
        def = emu:read8(address + 0x1A),
        spe = emu:read8(address + 0x1B),
        spa = emu:read8(address + 0x1C),
        spd = emu:read8(address + 0x1D),
        acc = emu:read8(address + 0x1E),
        eva = emu:read8(address + 0x1F)
    }
    
    mon.nature = "Unknown" 
    
    -- Dummy IVs
    mon.hpIV = 0
    mon.atkIV = 0
    mon.defIV = 0
    mon.speIV = 0
    mon.spaIV = 0
    mon.spdIV = 0
    
    return mon
end

function exportBattle()
    -- Write JSON
    local file = io.open(OUTPUT_FILE, "w")
    if not file then
        console:log("Error: Could not open file " .. OUTPUT_FILE)
        return
    end

    file:write('{\n')

    -- Global Data (Weather)
    local weather = emu:read16(0x02023F48)
    file:write(string.format('  "weather": %d,\n', weather))
    
    -- 1. Export Player Party (Live Data)
    local pCount = emu:read8(PLAYER_PARTY_COUNT)
    file:write('  "playerParty": [\n')
    local firstParty = true
    for i = 0, pCount - 1 do
        local addr = PLAYER_PARTY_LOC + (i * partyMonSize)
        -- Check if valid (species > 0)
        -- readPartyMon reads encrypted data
        local mon = readPartyMon(addr)
        if mon.species > 0 then
            if not firstParty then file:write(',\n') end
            file:write('    {\n')
            writeMonJson(file, mon)
            file:write('\n    }')
            firstParty = false
        end
    end
    file:write('\n  ],\n')

    -- 2. Export ALL Active Mons (Slots 0-3)
    file:write('  "activeMons": [\n')
    local firstActive = true
    for i = 0, 3 do
        local addr = BATTLE_MON_START + (i * 0x5C)
        local species = emu:read16(addr + 0x00)
        
        if species > 0 and species < 2000 then -- Simple sanity check
            if not firstActive then file:write(',\n') end
            file:write('    {\n')
            file:write(string.format('      "slot": %d,\n', i))
            file:write(string.format('      "address": "0x%X",\n', addr))
            writeMonJson(file, readBattleMon(i))
            file:write('\n    }')
            firstActive = false
        end
    end
    file:write('\n  ],\n')

    file:write('  "enemyTeam": [\n')
    
    local first = true
    local foundCount = 0
    
    -- 3. Try to read Enemy Party (Encrypted) FIRST
    console:log("Checking Enemy Party at " .. string.format("0x%X", ENEMY_PARTY_LOC))
    for i = 0, 5 do
        local addr = ENEMY_PARTY_LOC + (i * partyMonSize)
        -- Check personality to see if exists
        local p = emu:read32(addr)
        console:log(string.format("Slot %d (0x%X): PID %u", i, addr, p))
        
        if p ~= 0 then
            local mon = readPartyMon(addr)
            console:log(string.format("  Decrypted Species: %d, Name: %s", mon.species, mon.nickname))
            
            if mon.species > 0 and mon.species < 2000 then
                if not first then file:write(",\n") end
                file:write('    {\n')
                writeMonJson(file, mon)
                file:write('\n    }')
                first = false
                foundCount = foundCount + 1
            end
        end
    end

    -- 4. If No Party found (e.g. Wild Battle), use Active Mons
    if foundCount == 0 then
        console:log("No Enemy Party found. Using Active Battle Structs...")
        for i = 0, 3 do
            local mon = readBattleMon(i)
            if mon.species > 0 and mon.species < 2000 then
                -- Heuristic: If it's slot 1 or 3, it's definitely enemy.
                if i == 1 or i == 3 then
                    if not first then file:write(",\n") end
                    file:write('    {\n')
                    writeMonJson(file, mon)
                    file:write('\n    }')
                    first = false
                    foundCount = foundCount + 1
                end
            end
        end
    end

    file:write('\n  ],\n')
    file:write('  "debug": "Scanned slots 0-3 and Party"\n')
    file:write('}\n')
    file:close()
    console:log("Exported " .. foundCount .. " enemies to " .. OUTPUT_FILE)
end

function writeMonJson(file, mon)
    file:write(string.format('      "speciesId": "%d",\n', mon.species))
    file:write(string.format('      "nickname": "%s",\n', mon.nickname:gsub('"', '\\"')))
    file:write(string.format('      "level": %d,\n', mon.level))
    file:write(string.format('      "currentHp": %d,\n', mon.currentHp))
    file:write(string.format('      "maxHp": %d,\n', mon.maxHp))
    file:write(string.format('      "nature": "%s",\n', mon.nature))
    file:write(string.format('      "item": %d,\n', mon.heldItem))
    file:write('      "moves": [')
    for i = 1, 4 do
        file:write(mon.moves[i])
        if i < 4 then file:write(", ") end
    end
    file:write('],\n')
    
    -- Write Real Stats (if available)
    if mon.atk then
        file:write('      "stats": {')
        file:write(string.format('"hp": %d, "atk": %d, "def": %d, "spa": %d, "spd": %d, "spe": %d', 
            mon.maxHp, mon.atk, mon.def, mon.spa, mon.spd, mon.spe))
        file:write('},\n')
    end

    file:write('      "ivs": {')
    file:write(string.format('"hp": %d, "atk": %d, "def": %d, "spa": %d, "spd": %d, "spe": %d', 
        mon.hpIV, mon.atkIV, mon.defIV, mon.spaIV, mon.spdIV, mon.speIV))
    file:write('}')

    -- Write Status and Stat Stages (if available)
    if mon.status then
        file:write(',\n')
        file:write(string.format('      "status": %d', mon.status))
    end
    if mon.statStages then
        file:write(',\n')
        file:write('      "statStages": {')
        file:write(string.format('"hp": %d, "atk": %d, "def": %d, "spa": %d, "spd": %d, "spe": %d, "acc": %d, "eva": %d', 
            mon.statStages.hp, mon.statStages.atk, mon.statStages.def, mon.statStages.spa, mon.statStages.spd, mon.statStages.spe, mon.statStages.acc, mon.statStages.eva))
        file:write('}')
    end
    file:write('\n')
end

-- Run continuously or on key?
-- Let's run every 60 frames (1 second)
local frameCount = 0
callbacks:add("frame", function()
	frameCount = frameCount + 1
	if frameCount >= 60 then
		exportBattle()
		frameCount = 0
	end
end)

-- Run once on load
exportBattle()
