-- Simple Pokemon Sapphire Memory Address Finder
-- Load this script in mGBA to find the correct player data addresses
-- This script is designed to be error-free and easy to use

-- Create debug output
local debugBuffer = console:createBuffer("Memory Finder")
debugBuffer:setSize(100, 40)
debugBuffer:clear()

-- Known Pokemon Sapphire addresses to test
local testAddresses = {
    0x02031DBC,  -- Common Sapphire address
    0x02024EA4,  -- Alternative 1
    0x02037BA8,  -- Alternative 2
    0x020013E0,  -- Currently discovered
    0x02025734,  -- Possibility 1
    0x02031E50,  -- Possibility 2
}

-- Previous values for change detection
local previousValues = {}

function initializePrevious()
    for i, addr in ipairs(testAddresses) do
        previousValues[addr] = {
            x = emu:read16(addr),
            y = emu:read16(addr + 2),
            direction = emu:read8(addr + 4),
            mapId = emu:read8(addr + 6)
        }
    end
    debugBuffer:print("Previous values initialized.\n")
end

function checkForChanges()
    debugBuffer:clear()
    debugBuffer:print("=== Pokemon Sapphire Memory Check ===\n")
    debugBuffer:print("Move your character to see which addresses change!\n\n")
    
    local foundChanges = false
    
    for i, addr in ipairs(testAddresses) do
        local x = emu:read16(addr)
        local y = emu:read16(addr + 2)
        local direction = emu:read8(addr + 4)
        local mapId = emu:read8(addr + 6)
        
        -- Check for changes
        local prev = previousValues[addr]
        local changed = false
        if prev then
            if prev.x ~= x or prev.y ~= y or prev.direction ~= direction or prev.mapId ~= mapId then
                changed = true
                foundChanges = true
            end
        end
        
        -- Show results
        local status = changed and " *** CHANGED ***" or ""
        debugBuffer:print(string.format("0x%08X: X=%d Y=%d Dir=%d Map=%d%s\n", 
                         addr, x or -1, y or -1, direction or -1, mapId or -1, status))
        
        -- Update previous values
        previousValues[addr] = {x = x, y = y, direction = direction, mapId = mapId}
    end
    
    if foundChanges then
        debugBuffer:print("\n*** ADDRESSES WITH CHANGES FOUND! ***\n")
        debugBuffer:print("The addresses marked as CHANGED are likely correct.\n")
    else
        debugBuffer:print("\nNo changes detected - try moving your character!\n")
    end
    
    debugBuffer:print("\nPress F5 to check again.\n")
end

-- Initialize when script loads
if emu then
    debugBuffer:print("Pokemon Sapphire Memory Finder loaded!\n")
    debugBuffer:print("Instructions:\n")
    debugBuffer:print("1. Move your character around\n")
    debugBuffer:print("2. Press F5 to check for changes\n")
    debugBuffer:print("3. Look for addresses marked as CHANGED\n\n")
    
    initializePrevious()
    
    -- Check automatically every 3 seconds
    local frameCounter = 0
    callbacks:add("frame", function()
        frameCounter = frameCounter + 1
        if frameCounter >= 180 then  -- 3 seconds at 60fps
            frameCounter = 0
            checkForChanges()
        end
    end)
    
    -- Manual check with F5 key
    callbacks:add("keyreleased", function(key)
        if key == "f5" then
            checkForChanges()
        end
    end)
end