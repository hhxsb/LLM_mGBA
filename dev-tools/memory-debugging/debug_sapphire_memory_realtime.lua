-- Real-time Pokemon Sapphire memory debugging script
-- Load this in mGBA Script Viewer to find correct player data addresses

-- Create debug buffer
function setupDebugBuffer()
    if not debugBuffer then
        debugBuffer = console:createBuffer("Sapphire Memory Debug")
        debugBuffer:setSize(120, 50)
        debugBuffer:clear()
    end
end

-- Known Pokemon Sapphire addresses to test
local testAddresses = {
    -- Format: {base_address, description}
    {0x02031DBC, "Common Sapphire (Set 1)"},
    {0x02024EA4, "Alternative Sapphire (Set 2)"},
    {0x02037BA8, "Alternative Sapphire (Set 3)"},
    {0x020013E0, "Discovered Address"},
    {0x02025734, "Possibility 1"},
    {0x02031E50, "Possibility 2"},
    {0x0203AB68, "Possibility 3"},
    {0x0203AB00, "Possibility 4"},
}

-- Store previous values to detect changes
local previousValues = {}

function initializePreviousValues()
    for i, addrInfo in ipairs(testAddresses) do
        local addr = addrInfo[1]
        previousValues[addr] = {
            x = emu:read16(addr),
            y = emu:read16(addr + 2),
            direction = emu:read8(addr + 4),
            mapId = emu:read8(addr + 6)
        }
    end
end

function analyzeMemoryAddresses()
    debugBuffer:clear()
    debugBuffer:print("=== Pokemon Sapphire Memory Analysis ===\n")
    debugBuffer:print("ROM: " .. (emu:romName() or "Unknown") .. "\n\n")
    
    local changedAddresses = {}
    
    for i, addrInfo in ipairs(testAddresses) do
        local addr = addrInfo[1]
        local desc = addrInfo[2]
        
        local x = emu:read16(addr)
        local y = emu:read16(addr + 2)
        local direction = emu:read8(addr + 4)
        local mapId = emu:read8(addr + 6)
        
        -- Check if values changed
        local prev = previousValues[addr]
        local changed = false
        if prev then
            if prev.x ~= x or prev.y ~= y or prev.direction ~= direction or prev.mapId ~= mapId then
                changed = true
                table.insert(changedAddresses, {addr = addr, desc = desc})
            end
        end
        
        -- Format output
        local status = changed and "*** CHANGED ***" or ""
        debugBuffer:print(string.format("%s (0x%08X):\n", desc, addr))
        debugBuffer:print(string.format("  X=%d, Y=%d, Dir=%d, Map=%d %s\n", 
                         x or -1, y or -1, direction or -1, mapId or -1, status))
        
        -- Update previous values
        previousValues[addr] = {x = x, y = y, direction = direction, mapId = mapId}
    end
    
    -- Highlight changed addresses
    if #changedAddresses > 0 then
        debugBuffer:print("\n=== ADDRESSES WITH CHANGES ===\n")
        for i, info in ipairs(changedAddresses) do
            debugBuffer:print(string.format("-> %s (0x%08X)\n", info.desc, info.addr))
        end
        debugBuffer:print("\nThese addresses are likely the correct player data!\n")
    else
        debugBuffer:print("\nNo changes detected - try moving your character!\n")
    end
    
    debugBuffer:print("\n=== Instructions ===\n")
    debugBuffer:print("1. Move your character around\n")
    debugBuffer:print("2. Turn in different directions\n")
    debugBuffer:print("3. Watch for addresses that change\n")
    debugBuffer:print("4. The correct address should show:\n")
    debugBuffer:print("   - X/Y changes when moving\n")
    debugBuffer:print("   - Direction changes when turning\n")
    debugBuffer:print("   - Map changes when entering new areas\n")
end

-- Real-time monitoring
function monitorPlayerData()
    analyzeMemoryAddresses()
end

-- Direction decoder for Pokemon Sapphire
function decodeDirection(value)
    local directions = {
        [1] = "DOWN",
        [2] = "UP", 
        [3] = "LEFT",
        [4] = "RIGHT"
    }
    return directions[value] or ("UNKNOWN(" .. value .. ")")
end

-- Enhanced analysis with direction decoding
function detailedAnalysis()
    debugBuffer:clear()
    debugBuffer:print("=== DETAILED ANALYSIS ===\n")
    
    for i, addrInfo in ipairs(testAddresses) do
        local addr = addrInfo[1]
        local desc = addrInfo[2]
        
        local x = emu:read16(addr)
        local y = emu:read16(addr + 2)
        local direction = emu:read8(addr + 4)
        local mapId = emu:read8(addr + 6)
        
        debugBuffer:print(string.format("%s:\n", desc))
        debugBuffer:print(string.format("  Address: 0x%08X\n", addr))
        debugBuffer:print(string.format("  X: %d (0x%04X)\n", x or -1, x or 0))
        debugBuffer:print(string.format("  Y: %d (0x%04X)\n", y or -1, y or 0))
        debugBuffer:print(string.format("  Direction: %d -> %s\n", direction or -1, decodeDirection(direction)))
        debugBuffer:print(string.format("  Map ID: %d (0x%02X)\n", mapId or -1, mapId or 0))
        debugBuffer:print("\n")
    end
end

-- Initialize on load
if emu then
    setupDebugBuffer()
    debugBuffer:print("Pokemon Sapphire Memory Debugger loaded!\n\n")
    debugBuffer:print("Available functions:\n")
    debugBuffer:print("- analyzeMemoryAddresses(): Check all known addresses\n")
    debugBuffer:print("- detailedAnalysis(): Show detailed info for all addresses\n")
    debugBuffer:print("- initializePreviousValues(): Reset change detection\n\n")
    debugBuffer:print("The script will auto-monitor for changes.\n")
    debugBuffer:print("MOVE YOUR CHARACTER to see which addresses change!\n\n")
    
    -- Initialize change detection
    initializePreviousValues()
    
    -- Set up automatic monitoring every 60 frames (1 second)
    local frameCount = 0
    callbacks:add("frame", function()
        frameCount = frameCount + 1
        if frameCount >= 60 then
            frameCount = 0
            monitorPlayerData()
        end
    end)
end