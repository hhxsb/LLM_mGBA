-- Debug script for Pokemon Sapphire memory addresses
-- Load this in mGBA Script Viewer to manually test memory locations

-- Create debug buffer
function setupDebugBuffer()
    if not debugBuffer then
        debugBuffer = console:createBuffer("Sapphire Debug")
        debugBuffer:setSize(120, 40)
        debugBuffer:clear()
    end
end

-- Test a specific memory address set
function testAddressSet(addresses, name)
    debugBuffer:print("Testing " .. name .. ":\n")
    
    local x = emu:read16(addresses.playerX)
    local y = emu:read16(addresses.playerY) 
    local direction = emu:read8(addresses.playerDirection)
    local mapId = emu:read8(addresses.mapId)
    
    debugBuffer:print("  Player X: " .. (x or "nil") .. " (at " .. string.format("0x%08X", addresses.playerX) .. ")\n")
    debugBuffer:print("  Player Y: " .. (y or "nil") .. " (at " .. string.format("0x%08X", addresses.playerY) .. ")\n")
    debugBuffer:print("  Direction: " .. (direction or "nil") .. " (at " .. string.format("0x%08X", addresses.playerDirection) .. ")\n")
    debugBuffer:print("  Map ID: " .. (mapId or "nil") .. " (at " .. string.format("0x%08X", addresses.mapId) .. ")\n")
    
    -- Check if values are reasonable
    local valid = true
    if not x or not y or not direction or not mapId then
        valid = false
        debugBuffer:print("  Status: INVALID - Some values are nil\n")
    elseif x < 0 or x > 1000 or y < 0 or y > 1000 then
        valid = false
        debugBuffer:print("  Status: INVALID - Coordinates out of range\n")
    elseif direction < 1 or direction > 4 then
        valid = false
        debugBuffer:print("  Status: INVALID - Direction out of range (should be 1-4)\n")
    elseif mapId < 0 or mapId > 255 then
        valid = false
        debugBuffer:print("  Status: INVALID - Map ID out of range\n")
    else
        valid = true
        debugBuffer:print("  Status: VALID - All values look reasonable\n")
    end
    
    debugBuffer:print("\n")
    return valid
end

-- Test all known Pokemon Sapphire address sets
function testAllSapphireAddresses()
    setupDebugBuffer()
    debugBuffer:clear()
    
    debugBuffer:print("=== Pokemon Sapphire Memory Address Testing ===\n\n")
    
    -- ROM info
    local romName = emu:romName() or "Unknown"
    local romCRC = emu:romCRC32() or 0
    debugBuffer:print("ROM Name: " .. romName .. "\n")
    debugBuffer:print("ROM CRC32: " .. tostring(romCRC) .. "\n\n")
    
    -- Known address sets for Pokemon Sapphire
    local addressSets = {
        {
            name = "Set 1 (Common)",
            playerX = 0x02031DBC,
            playerY = 0x02031DBE,
            playerDirection = 0x02031DC0,
            mapId = 0x02031DC2,
        },
        {
            name = "Set 2 (Alternative)",
            playerX = 0x02024EA4,
            playerY = 0x02024EA6,
            playerDirection = 0x02024EA8,
            mapId = 0x02024EAA,
        },
        {
            name = "Set 3 (Variant)",
            playerX = 0x02037BA8,
            playerY = 0x02037BAA,
            playerDirection = 0x02037BAC,
            mapId = 0x02037BAE,
        }
    }
    
    local validSets = {}
    for i, addrSet in ipairs(addressSets) do
        if testAddressSet(addrSet, addrSet.name) then
            table.insert(validSets, addrSet.name)
        end
    end
    
    debugBuffer:print("=== SUMMARY ===\n")
    if #validSets > 0 then
        debugBuffer:print("Valid address sets found: " .. table.concat(validSets, ", ") .. "\n")
        debugBuffer:print("Recommendation: Use the first valid set in script.lua\n")
    else
        debugBuffer:print("No valid address sets found!\n")
        debugBuffer:print("Try moving your character and running this test again.\n")
        debugBuffer:print("You may need to find new addresses for this ROM version.\n")
    end
end

-- Manual memory scanning function
function scanMemoryRange(startAddr, endAddr)
    setupDebugBuffer()
    debugBuffer:clear()
    
    debugBuffer:print("=== Manual Memory Scan ===\n")
    debugBuffer:print("Scanning from " .. string.format("0x%08X", startAddr) .. " to " .. string.format("0x%08X", endAddr) .. "\n\n")
    
    local foundAddresses = {}
    
    for addr = startAddr, endAddr, 4 do
        local x = emu:read16(addr)
        local y = emu:read16(addr + 2)
        local direction = emu:read8(addr + 4)
        local mapId = emu:read8(addr + 6)
        
        -- Check if values look like player data
        if x and y and direction and mapId then
            if x >= 0 and x <= 1000 and y >= 0 and y <= 1000 and direction >= 1 and direction <= 4 and mapId >= 0 and mapId <= 255 then
                table.insert(foundAddresses, {
                    baseAddr = addr,
                    x = x,
                    y = y,
                    direction = direction,
                    mapId = mapId
                })
                
                debugBuffer:print("Potential match at " .. string.format("0x%08X", addr) .. ":\n")
                debugBuffer:print("  X=" .. x .. ", Y=" .. y .. ", Dir=" .. direction .. ", Map=" .. mapId .. "\n\n")
            end
        end
    end
    
    debugBuffer:print("Found " .. #foundAddresses .. " potential player data locations.\n")
    
    return foundAddresses
end

-- Quick scan of common GBA memory regions
function quickScan()
    -- Scan Work RAM and Internal Work RAM regions
    local results1 = scanMemoryRange(0x02000000, 0x02010000)  -- First part of EWRAM
    local results2 = scanMemoryRange(0x02030000, 0x02040000)  -- Second part of EWRAM
    
    return results1, results2
end

-- Initialize on load
if emu then
    setupDebugBuffer()
    debugBuffer:print("Pokemon Sapphire Memory Debug Tool loaded!\n\n")
    debugBuffer:print("Available functions:\n")
    debugBuffer:print("- testAllSapphireAddresses(): Test known address sets\n")
    debugBuffer:print("- quickScan(): Scan memory for player data\n")
    debugBuffer:print("- scanMemoryRange(start, end): Custom memory scan\n\n")
    debugBuffer:print("Run testAllSapphireAddresses() first!\n")
end