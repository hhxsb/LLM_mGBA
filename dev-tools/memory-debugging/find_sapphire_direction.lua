-- Find Pokemon Sapphire Direction Address
-- We know 0x02025734 has X, Y, Map - now find the direction address

local debugBuffer = console:createBuffer("Direction Finder")
debugBuffer:setSize(120, 50)
debugBuffer:clear()

-- Base address that works for X, Y, Map
local baseAddress = 0x02025734

-- Check nearby addresses for direction data
local directionCandidates = {}

-- Offsets to check around the working address
local offsetsToCheck = {
    -16, -12, -8, -4, -2, -1,  -- Before base
    4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 20, 24, 28, 32  -- After base
}

-- Previous direction values for change detection
local previousDirections = {}

function initializeDirectionTracking()
    debugBuffer:print("Initializing direction tracking around working address 0x02025734...\n\n")
    
    for i, offset in ipairs(offsetsToCheck) do
        local addr = baseAddress + offset
        local value = emu:read8(addr)
        previousDirections[addr] = value
    end
    
    debugBuffer:print("Previous direction values stored.\n")
    debugBuffer:print("Now TURN YOUR CHARACTER in different directions!\n")
    debugBuffer:print("Press F5 to check which addresses change.\n\n")
end

function checkDirectionChanges()
    debugBuffer:clear()
    debugBuffer:print("=== Direction Address Search ===\n")
    debugBuffer:print("Base address 0x02025734 has X, Y, Map\n")
    debugBuffer:print("Looking for direction address nearby...\n\n")
    
    -- First show the working base address data
    local baseX = emu:read16(baseAddress)
    local baseY = emu:read16(baseAddress + 2)
    local baseMap = emu:read8(baseAddress + 6)
    debugBuffer:print(string.format("Base (0x%08X): X=%d, Y=%d, Map=%d\n\n", 
                     baseAddress, baseX, baseY, baseMap))
    
    local foundDirectionChanges = {}
    
    debugBuffer:print("Direction candidates:\n")
    for i, offset in ipairs(offsetsToCheck) do
        local addr = baseAddress + offset
        local value = emu:read8(addr)
        local prevValue = previousDirections[addr]
        
        local changed = (prevValue ~= nil and prevValue ~= value)
        local status = ""
        
        if changed then
            status = " *** CHANGED ***"
            table.insert(foundDirectionChanges, {addr = addr, offset = offset, value = value, prev = prevValue})
        end
        
        -- Check if value looks like a direction (1-4 for GBA games)
        local validDirection = (value >= 1 and value <= 4)
        local directionText = ""
        if validDirection then
            local directions = {[1] = "DOWN", [2] = "UP", [3] = "LEFT", [4] = "RIGHT"}
            directionText = " -> " .. directions[value]
        end
        
        debugBuffer:print(string.format("  +%d (0x%08X): %d%s%s\n", 
                         offset, addr, value, directionText, status))
        
        -- Update previous value
        previousDirections[addr] = value
    end
    
    if #foundDirectionChanges > 0 then
        debugBuffer:print("\n*** DIRECTION ADDRESSES THAT CHANGED: ***\n")
        for i, change in ipairs(foundDirectionChanges) do
            debugBuffer:print(string.format("-> Offset +%d (0x%08X): %d -> %d\n", 
                             change.offset, change.addr, change.prev, change.value))
        end
        debugBuffer:print("\nThese are likely the direction address!\n")
    else
        debugBuffer:print("\nNo direction changes found.\n")
        debugBuffer:print("Try turning your character in different directions!\n")
    end
    
    debugBuffer:print("\nPress F5 to check again after turning.\n")
end

function showDetailedAnalysis()
    debugBuffer:clear()
    debugBuffer:print("=== Detailed Memory Analysis ===\n")
    debugBuffer:print("Around working address 0x02025734:\n\n")
    
    for i, offset in ipairs(offsetsToCheck) do
        local addr = baseAddress + offset
        local value8 = emu:read8(addr)
        local value16 = emu:read16(addr)
        
        debugBuffer:print(string.format("Offset +%d (0x%08X):\n", offset, addr))
        debugBuffer:print(string.format("  8-bit: %d (0x%02X)\n", value8, value8))
        debugBuffer:print(string.format("  16-bit: %d (0x%04X)\n", value16, value16))
        
        -- Check if looks like direction
        if value8 >= 1 and value8 <= 4 then
            local directions = {[1] = "DOWN", [2] = "UP", [3] = "LEFT", [4] = "RIGHT"}
            debugBuffer:print(string.format("  Direction: %s\n", directions[value8]))
        end
        debugBuffer:print("\n")
    end
end

-- Initialize when script loads
if emu then
    debugBuffer:print("Pokemon Sapphire Direction Finder loaded!\n")
    debugBuffer:print("We know 0x02025734 has X, Y, Map data.\n")
    debugBuffer:print("Now finding the direction address...\n\n")
    debugBuffer:print("Controls:\n")
    debugBuffer:print("F5 - Check for direction changes\n")
    debugBuffer:print("F6 - Show detailed memory analysis\n\n")
    
    initializeDirectionTracking()
    
    -- Auto-check every 2 seconds
    local frameCounter = 0
    callbacks:add("frame", function()
        frameCounter = frameCounter + 1
        if frameCounter >= 120 then  -- 2 seconds at 60fps
            frameCounter = 0
            checkDirectionChanges()
        end
    end)
    
    -- Manual controls
    callbacks:add("keyreleased", function(key)
        if key == "f5" then
            checkDirectionChanges()
        elseif key == "f6" then
            showDetailedAnalysis()
        end
    end)
end