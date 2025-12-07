-- Export Box and Party to JSON for Battle Helper
-- Run this script in mGBA (Tools -> Scripting -> Load Script)

local OUTPUT_FILE = "/Users/targoon/Pokemon/battle-helper/src/data/imports/box.json"

-- Memory Offsets (Emerald / Run and Bun)
local partyloc = 0x2023a98
local partyCount = 0x2023a95
local storageLoc = 0x2028848
local boxMonSize = 80
local partyMonSize = 100

-- Character Map (Simplified for JSON export)
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

-- Helper Functions
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
	mon.language = emu:read8(address + 18)
	local flags = emu:read8(address + 19)
	mon.isBadEgg = flags & 1
	mon.hasSpecies = (flags >> 1) & 1
	mon.isEgg = (flags >> 2) & 1
	
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
	
	-- Substruct 2: EVs & Condition
	mon.hpEV = ss[2][0] & 0xFF
	mon.atkEV = (ss[2][0] >> 8) & 0xFF
	mon.defEV = (ss[2][0] >> 16) & 0xFF
	mon.speEV = ss[2][0] >> 24
	mon.spaEV = ss[2][1] & 0xFF
	mon.spdEV = (ss[2][1] >> 8) & 0xFF
	
	-- Substruct 3: Misc
	local misc1 = ss[3][0]
	local misc2 = ss[3][1]
	mon.ivs = misc2
    -- Run and Bun (and some Gen 3) seems to shift IVs by 1 bit?
    -- Copying logic from runandbun (1).lua:
    -- flags = ss3[1]
	-- mon.hpIV = (flags >> 1) & 0x1F
	mon.hpIV = (misc2 >> 1) & 0x1F
	mon.atkIV = (misc2 >> 6) & 0x1F
	mon.defIV = (misc2 >> 11) & 0x1F
	mon.speIV = (misc2 >> 16) & 0x1F
	mon.spaIV = (misc2 >> 21) & 0x1F
	mon.spdIV = (misc2 >> 26) & 0x1F
	
	-- Nature
	-- runandbun (1).lua:
    -- if (mon.hiddenNature == 26) then return nature[(mon.personality % 25)+1] end
    -- return nature[mon.hiddenNature+1]
    -- We need hiddenNature from ss[0][2]
    
    mon.hiddenNature = (ss[0][2] >> 16) & 0x1F
	local natures = {
		"Hardy","Lonely","Brave","Adamant","Naughty",
		"Bold","Docile","Relaxed","Impish","Lax",
		"Timid","Hasty","Serious","Jolly","Naive",
		"Modest","Mild","Quiet","Bashful","Rash",
		"Calm","Gentle","Sassy","Careful","Quirky"
	}
    if mon.hiddenNature == 26 or mon.hiddenNature == nil then -- 26 might be default/none?
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

-- JSON Export
function exportData()
	local file = io.open(OUTPUT_FILE, "w")
	if not file then
		console:log("Error: Could not open file " .. OUTPUT_FILE)
		return
	end

	file:write("[\n")
	local first = true

	-- 1. Party
	local partyCountVal = emu:read8(partyCount)
	for i = 0, partyCountVal - 1 do
		local addr = partyloc + (i * partyMonSize)
		local mon = readPartyMon(addr)
		if mon.species > 0 then
			if not first then file:write(",\n") end
			writeMonJson(file, mon, true)
			first = false
		end
	end

	-- 2. Box
	-- 14 Boxes * 30 Mons
	for i = 0, 419 do
		local addr = storageLoc + 4 + (i * boxMonSize)
		-- Check if slot is empty (species 0)
		-- Need to read raw first to check encryption? No, readBoxMon handles it?
		-- Actually, if species is 0, it's empty.
		-- But we need to read it to know species.
		-- Optimization: Check if personality is 0?
		local p = emu:read32(addr)
		if p ~= 0 then
			local mon = readBoxMon(addr)
			if mon.species > 0 and not mon.isEgg then
				if not first then file:write(",\n") end
				writeMonJson(file, mon, false)
				first = false
			end
		end
	end

	file:write("\n]")
	file:close()
	console:log("Exported to " .. OUTPUT_FILE)
end

function writeMonJson(file, mon, isParty)
	file:write("  {\n")
	file:write(string.format('    "speciesId": "%d",\n', mon.species)) -- We'll map ID to Name in App
	file:write(string.format('    "nickname": "%s",\n', mon.nickname:gsub('"', '\\"')))
    file:write(string.format('    "otId": %d,\n', mon.otId))
    file:write(string.format('    "personality": %d,\n', mon.personality))
	file:write(string.format('    "level": %d,\n', mon.level or 0)) -- Box mons don't have level stored directly!
	-- For box mons, level is calculated from Exp. We'll skip for now or calc simple.
	-- App can calc level from Exp if needed, or we just default to 100/50?
	-- Wait, box struct has Exp.
	file:write(string.format('    "experience": %d,\n', mon.experience))
	file:write(string.format('    "nature": "%s",\n', mon.nature))
	file:write(string.format('    "abilityNum": %d,\n', 0)) -- Need to determine ability from bit
	file:write(string.format('    "item": %d,\n', mon.heldItem))
	file:write('    "moves": [')
	for i = 1, 4 do
		file:write(mon.moves[i])
		if i < 4 then file:write(", ") end
	end
	file:write('],\n')
	file:write('    "ivs": {')
	file:write(string.format('"hp": %d, "atk": %d, "def": %d, "spa": %d, "spd": %d, "spe": %d', 
		mon.hpIV, mon.atkIV, mon.defIV, mon.spaIV, mon.spdIV, mon.speIV))
	file:write('},\n')
	file:write('    "evs": {')
	file:write(string.format('"hp": %d, "atk": %d, "def": %d, "spa": %d, "spd": %d, "spe": %d', 
		mon.hpEV, mon.atkEV, mon.defEV, mon.spaEV, mon.spdEV, mon.speEV))
	file:write('}\n')
	file:write("  }")
end

-- Run once on load
if emu then
	exportData()
end

-- Add menu item
callbacks:add("keysRead", function()
    -- Optional: Trigger on key press?
end)
