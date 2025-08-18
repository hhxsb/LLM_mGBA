-- Comprehensive Pokemon Sapphire Direction Search
-- Searches across entire GBA RAM for direction data stored separately from coordinates
-- Based on user confirmation: 0x02025734=X, 0x02025736=Y, 0x0202573A=Map, Direction=Unknown

local debugBuffer = console:createBuffer("Direction Search")
debugBuffer:setSize(160, 80)
debugBuffer:clear()

-- Confirmed working addresses
local confirmedAddresses = {
    playerX = 0x02025734,
    playerY = 0x02025736,
    mapId = 0x0202573A
}

-- GBA RAM search parameters
local searchRanges = {
    -- Main RAM regions in Pokemon Sapphire
    {start = 0x02000000, ending = 0x02040000, step = 1, name = "Main RAM"},
    {start = 0x03000000, ending = 0x03008000, step = 1, name = "Internal RAM"},
    {start = 0x02025000, ending = 0x02026000, step = 1, name = "Near Working Address"}  -- Focused search
}

-- Direction encoding mappings
local standardDirections = {[1] = "DOWN", [2] = "UP", [3] = "LEFT", [4] = "RIGHT"}
local tblDirections = {[0x79] = "UP", [0x7A] = "DOWN", [0x7B] = "LEFT", [0x7C] = "RIGHT"}

-- Tracking variables
local directionCandidates = {}
local previousDirections = {}
local searchPhase = 1
local currentRange = 1
local currentAddress = 0
local totalCandidates = 0

-- Validation functions
function isValidStandardDirection(value)
    return value >= 1 and value <= 4
end

function isValidTblDirection(value)
    return value == 0x79 or value == 0x7A or value == 0x7B or value == 0x7C
end

function getDirectionText(value)
    return standardDirections[value] or tblDirections[value] or "UNKNOWN"
end

function initializeSearch()
    debugBuffer:print("=== Comprehensive Pokemon Sapphire Direction Search ===\n")
    debugBuffer:print("Confirmed addresses:\n")
    debugBuffer:print(string.format("  X: 0x%08X = %d\n", confirmedAddresses.playerX, emu:read16(confirmedAddresses.playerX)))
    debugBuffer:print(string.format("  Y: 0x%08X = %d\n", confirmedAddresses.playerY, emu:read16(confirmedAddresses.playerY)))
    debugBuffer:print(string.format("  Map: 0x%08X = %d\n", confirmedAddresses.mapId, emu:read8(confirmedAddresses.mapId)))
    debugBuffer:print("\nSearching for direction data stored separately...\n")
    debugBuffer:print("AUTOMATED TESTING: Script will auto-press buttons!\n\n")
    
    -- Initialize candidates storage safely
    directionCandidates = directionCandidates or {}
    previousDirections = previousDirections or {}
    addressScores = addressScores or {}
    searchPhase = 1
    currentRange = 1
    totalCandidates = 0
end

function quickScanAroundWorkingAddress()
    debugBuffer:clear()
    debugBuffer:print("=== Wide Range Direction Search ===\n")
    
    -- Much wider search ranges across GBA RAM
    local scanRanges = {
        {start = 0x02020000, ending = 0x02030000, name = "Wide Range 1 (64KB)"},
        {start = 0x02030000, ending = 0x02040000, name = "Wide Range 2 (64KB)"},
        {start = 0x02010000, ending = 0x02020000, name = "Wide Range 3 (64KB)"},
        {start = 0x03000000, ending = 0x03008000, name = "Internal RAM (32KB)"},
        {start = 0x02000000, ending = 0x02010000, name = "Early RAM (64KB)"}
    }
    
    local candidates = {}
    
    for _, range in ipairs(scanRanges) do
        debugBuffer:print(string.format("Scanning %s (0x%08X - 0x%08X)...\n", range.name, range.start, range.ending))
        
        for addr = range.start, range.ending, 1 do  -- Check every byte
            local value = emu:read8(addr)
            
            if isValidStandardDirection(value) or isValidTblDirection(value) then
                local dirText = getDirectionText(value)
                local encodingType = isValidStandardDirection(value) and "Standard" or "TBL"
                
                table.insert(candidates, {
                    address = addr,
                    value = value,
                    direction = dirText,
                    encoding = encodingType,
                    distance = math.abs(addr - confirmedAddresses.playerX)
                })
            end
        end
    end
    
    -- Sort by distance from working address
    table.sort(candidates, function(a, b) return a.distance < b.distance end)
    
    debugBuffer:print(string.format("\nFound %d direction candidates:\n", #candidates))
    debugBuffer:print("ADDR     | VALUE | DIRECTION | TYPE     | DISTANCE\n")
    debugBuffer:print("---------|-------|-----------|----------|----------\n")
    
    local maxShow = math.min(#candidates, 50)  -- Show top 50
    for i = 1, maxShow do
        local c = candidates[i]
        debugBuffer:print(string.format("0x%08X | %3d   | %-9s | %-8s | %d bytes\n", 
                         c.address, c.value, c.direction, c.encoding, c.distance))
    end
    
    if #candidates > maxShow then
        debugBuffer:print(string.format("... and %d more candidates\n", #candidates - maxShow))
    end
    
    -- Store for change detection
    for _, c in ipairs(candidates) do
        previousDirections[c.address] = c.value
    end
    
    debugBuffer:print("\nNow TURN YOUR CHARACTER and press F6 to check for changes!\n")
    return candidates
end

function checkDirectionChangesWithInstruction()
    -- Don't clear buffer - append to existing instruction display
    debugBuffer:print(string.format("Checking for changes from PREVIOUS instruction: %s\n", lastInstructedDirection or "none"))
    debugBuffer:print("=== Direction Change Detection Results ===\n")
    
    local totalAddresses = 0
    for _ in pairs(previousDirections) do totalAddresses = totalAddresses + 1 end
    debugBuffer:print(string.format("Monitoring %d addresses for changes...\n", totalAddresses))
    
    local changedAddresses = {}
    local correctMatches = 0
    local incorrectChanges = 0
    
    -- Check all previously found candidates
    for addr, prevValue in pairs(previousDirections) do
        local currentValue = emu:read8(addr)
        
        if currentValue ~= prevValue then
            local prevDir = getDirectionText(prevValue)
            local currentDir = getDirectionText(currentValue)
            
            -- Check if both values are valid directions
            local prevValid = isValidStandardDirection(prevValue) or isValidTblDirection(prevValue)
            local currentValid = isValidStandardDirection(currentValue) or isValidTblDirection(currentValue)
            
            if prevValid and currentValid then
                local encodingType = isValidStandardDirection(currentValue) and "Standard" or "TBL"
                
                -- Check if this matches our instruction
                local matchesInstruction = (lastInstructedDirection and currentDir == lastInstructedDirection)
                
                -- Update score tracking
                if not addressScores[addr] then
                    addressScores[addr] = {correct = 0, total = 0, encoding = encodingType}
                end
                addressScores[addr].total = addressScores[addr].total + 1
                if matchesInstruction then
                    addressScores[addr].correct = addressScores[addr].correct + 1
                    correctMatches = correctMatches + 1
                else
                    incorrectChanges = incorrectChanges + 1
                end
                
                table.insert(changedAddresses, {
                    address = addr,
                    prevValue = prevValue,
                    currentValue = currentValue,
                    prevDirection = prevDir,
                    currentDirection = currentDir,
                    encoding = encodingType,
                    distance = math.abs(addr - confirmedAddresses.playerX),
                    matchesInstruction = matchesInstruction
                })
            end
        end
        
        -- Update stored value
        previousDirections[addr] = currentValue
    end
    
    debugBuffer:print(string.format("Changes: %d correct matches, %d other changes\n", correctMatches, incorrectChanges))
    
    if #changedAddresses > 0 then
        debugBuffer:print("*** DIRECTION CHANGES DETECTED! ***\n")
        debugBuffer:print("ADDR     | PREV->CURR | DIRECTION CHANGE | MATCH? | TYPE     | DISTANCE\n")
        debugBuffer:print("---------|------------|------------------|--------|----------|----------\n")
        
        -- Sort by instruction match first, then by distance
        table.sort(changedAddresses, function(a, b) 
            if a.matchesInstruction ~= b.matchesInstruction then
                return a.matchesInstruction and not b.matchesInstruction
            end
            return a.distance < b.distance 
        end)
        
        for _, change in ipairs(changedAddresses) do
            local matchSymbol = change.matchesInstruction and "✅" or "❌"
            debugBuffer:print(string.format("0x%08X | %3d->%-3d  | %-8s->%-8s | %s    | %-8s | %d bytes\n",
                             change.address, change.prevValue, change.currentValue, 
                             change.prevDirection, change.currentDirection, matchSymbol, change.encoding, change.distance))
        end
    else
        debugBuffer:print("No direction changes detected.\n")
        debugBuffer:print("Make sure you turned your character in the instructed direction!\n")
    end
    
    -- Show top scoring addresses
    showTopScoringAddresses()
    
    debugBuffer:print(string.format("\nNext instruction in 5 seconds... (Test cycle %d)\n", testCycle))
end

function checkDirectionChanges()
    debugBuffer:clear()
    debugBuffer:print("=== Direction Change Detection ===\n")
    
    local totalAddresses = 0
    for _ in pairs(previousDirections) do totalAddresses = totalAddresses + 1 end
    debugBuffer:print(string.format("Monitoring %d addresses for changes...\n", totalAddresses))
    
    local changedAddresses = {}
    local validChanges = 0
    local invalidChanges = 0
    
    -- Check all previously found candidates
    for addr, prevValue in pairs(previousDirections) do
        local currentValue = emu:read8(addr)
        
        if currentValue ~= prevValue then
            local prevDir = getDirectionText(prevValue)
            local currentDir = getDirectionText(currentValue)
            
            -- Check if both values are valid directions
            local prevValid = isValidStandardDirection(prevValue) or isValidTblDirection(prevValue)
            local currentValid = isValidStandardDirection(currentValue) or isValidTblDirection(currentValue)
            
            if prevValid and currentValid then
                local encodingType = isValidStandardDirection(currentValue) and "Standard" or "TBL"
                
                table.insert(changedAddresses, {
                    address = addr,
                    prevValue = prevValue,
                    currentValue = currentValue,
                    prevDirection = prevDir,
                    currentDirection = currentDir,
                    encoding = encodingType,
                    distance = math.abs(addr - confirmedAddresses.playerX)
                })
                validChanges = validChanges + 1
            else
                invalidChanges = invalidChanges + 1
            end
        end
        
        -- Update stored value
        previousDirections[addr] = currentValue
    end
    
    debugBuffer:print(string.format("Changes detected: %d valid, %d invalid\n", validChanges, invalidChanges))
    
    if #changedAddresses > 0 then
        debugBuffer:print("*** DIRECTION CHANGES DETECTED! ***\n")
        debugBuffer:print("ADDR     | PREV->CURR | DIRECTION CHANGE | TYPE     | DISTANCE\n")
        debugBuffer:print("---------|------------|------------------|----------|----------\n")
        
        for _, change in ipairs(changedAddresses) do
            debugBuffer:print(string.format("0x%08X | %3d->%-3d  | %-8s->%-8s | %-8s | %d bytes\n",
                             change.address, change.prevValue, change.currentValue, 
                             change.prevDirection, change.currentDirection, change.encoding, change.distance))
        end
        
        -- Highlight the best candidate (closest to working address)
        table.sort(changedAddresses, function(a, b) return a.distance < b.distance end)
        local best = changedAddresses[1]
        
        debugBuffer:print(string.format("\n*** RECOMMENDED DIRECTION ADDRESS ***\n"))
        debugBuffer:print(string.format("Address: 0x%08X\n", best.address))
        debugBuffer:print(string.format("Encoding: %s (%s)\n", best.encoding, 
                         best.encoding == "Standard" and "1-4 values" or "121-124 values"))
        debugBuffer:print(string.format("Distance from X coordinate: %d bytes\n", best.distance))
        debugBuffer:print(string.format("Current direction: %s (value %d)\n", best.currentDirection, best.currentValue))
        
    else
        debugBuffer:print("No direction changes detected.\n")
        debugBuffer:print("Try turning your character in different directions!\n")
        debugBuffer:print("Make sure you ran a scan first (F5).\n")
    end
    
    debugBuffer:print("\nPress F5 to rescan, F6 to check changes again.\n")
end

function autoPressButton(direction)
    -- Button indices from main script.lua: A=0, B=1, SELECT=2, START=3, RIGHT=4, LEFT=5, UP=6, DOWN=7, R=8, L=9
    local buttonMap = {
        UP = 6,
        DOWN = 7, 
        LEFT = 5,
        RIGHT = 4
    }
    
    local buttonIndex = buttonMap[direction]
    if buttonIndex then
        debugBuffer:print(string.format("🎮 AUTO-PRESSING: %s (index: %d)\n", direction, buttonIndex))
        
        -- Start button press (exactly like script.lua)
        currentKeyIndex = buttonIndex
        keyPressDuration = 2  -- Use same default as script.lua (defaultKeyPressFrames)
        keyPressStartFrame = emu:currentFrame()  -- Use emu:currentFrame() like script.lua
        
        -- Press the key immediately (like script.lua line 767)
        emu:addKey(currentKeyIndex)
        
        debugBuffer:print("  - Button press started!\n")
        
    else
        debugBuffer:print(string.format("❌ Unknown direction: %s\n", direction))
    end
end

function handleButtonPress()
    -- Handle button press and release (exactly like script.lua handleKeyPress function)
    if currentKeyIndex ~= nil then
        local currentFrame = emu:currentFrame()
        local framesPassed = currentFrame - keyPressStartFrame
        
        if framesPassed < keyPressDuration then
            -- Keep pressing the key every frame (like script.lua line 601)
            emu:addKey(currentKeyIndex)
        else
            -- Release the key after sufficient frames (like script.lua line 604)
            emu:clearKeys(0x3FF)
            local keyNames = { "A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L" }
            debugBuffer:print(string.format("  - Released %s after %d frames\n", keyNames[currentKeyIndex + 1], framesPassed))
            currentKeyIndex = nil
        end
    end
end

function showTopScoringAddresses()
    debugBuffer:print("\n=== TOP SCORING DIRECTION ADDRESSES ===\n")
    
    if next(addressScores) == nil then
        debugBuffer:print("No scoring data yet. Continue testing...\n")
        return
    end
    
    -- Convert to sorted array
    local sortedAddresses = {}
    for addr, score in pairs(addressScores) do
        local accuracy = score.total > 0 and (score.correct / score.total * 100) or 0
        table.insert(sortedAddresses, {
            address = addr,
            correct = score.correct,
            total = score.total,
            accuracy = accuracy,
            encoding = score.encoding,
            distance = math.abs(addr - confirmedAddresses.playerX)
        })
    end
    
    -- Sort by accuracy (descending), then by total tests (descending), then by distance (ascending)
    table.sort(sortedAddresses, function(a, b)
        if math.abs(a.accuracy - b.accuracy) < 0.1 then  -- Similar accuracy
            if a.total ~= b.total then
                return a.total > b.total  -- More tests is better
            end
            return a.distance < b.distance  -- Closer is better
        end
        return a.accuracy > b.accuracy  -- Higher accuracy is better
    end)
    
    debugBuffer:print("RANK | ADDRESS  | ACCURACY | TESTS | TYPE     | DISTANCE\n")
    debugBuffer:print("-----|----------|----------|-------|----------|----------\n")
    
    local maxShow = math.min(#sortedAddresses, 10)
    for i = 1, maxShow do
        local addr = sortedAddresses[i]
        debugBuffer:print(string.format("%2d   | 0x%08X | %6.1f%% | %2d/%-2d | %-8s | %d bytes\n",
                         i, addr.address, addr.accuracy, addr.correct, addr.total, addr.encoding, addr.distance))
    end
    
    if #sortedAddresses > 0 then
        local best = sortedAddresses[1]
        if best.accuracy >= 75 and best.total >= 3 then
            debugBuffer:print("\n🎯 RECOMMENDED DIRECTION ADDRESS:\n")
            debugBuffer:print(string.format("Address: 0x%08X\n", best.address))
            debugBuffer:print(string.format("Accuracy: %.1f%% (%d/%d tests)\n", best.accuracy, best.correct, best.total))
            debugBuffer:print(string.format("Encoding: %s\n", best.encoding))
            debugBuffer:print(string.format("Distance from coordinates: %d bytes\n", best.distance))
        end
    end
end

function showFinalResults()
    debugBuffer:clear()
    debugBuffer:print("████████████████████████████████████████████████████████████\n")
    debugBuffer:print("█                                                          █\n")
    debugBuffer:print("█                🎯 TESTING COMPLETE! 🎯                 █\n")
    debugBuffer:print("█                                                          █\n")
    debugBuffer:print("████████████████████████████████████████████████████████████\n")
    debugBuffer:print("\n")
    
    debugBuffer:print(string.format("Completed %d test cycles with direction instructions.\n", maxTestCycles or 25))
    debugBuffer:print("Analyzing results to find the Pokemon Sapphire direction address...\n\n")
    
    if next(addressScores) == nil then
        debugBuffer:print("❌ No direction changes detected during testing.\n")
        debugBuffer:print("This could mean:\n")
        debugBuffer:print("- Direction data is stored outside the scanned memory range\n")
        debugBuffer:print("- Direction uses a different encoding system\n")
        debugBuffer:print("- Direction data is not stored in a single byte\n")
        return
    end
    
    -- Convert to sorted array
    local sortedAddresses = {}
    for addr, score in pairs(addressScores) do
        local accuracy = score.total > 0 and (score.correct / score.total * 100) or 0
        table.insert(sortedAddresses, {
            address = addr,
            correct = score.correct,
            total = score.total,
            accuracy = accuracy,
            encoding = score.encoding,
            distance = math.abs(addr - confirmedAddresses.playerX)
        })
    end
    
    -- Sort by correct count first (most important), then by accuracy, then by distance
    table.sort(sortedAddresses, function(a, b)
        if a.correct ~= b.correct then
            return a.correct > b.correct  -- More correct responses is better
        end
        if math.abs(a.accuracy - b.accuracy) > 0.1 then
            return a.accuracy > b.accuracy  -- Higher accuracy is better
        end
        return a.distance < b.distance  -- Closer to coordinates is better
    end)
    
    debugBuffer:print("=== TOP 10 DIRECTION ADDRESS CANDIDATES (by correct count) ===\n")
    debugBuffer:print("RANK | ADDRESS  | CORRECT | TOTAL | ACCURACY | TYPE     | DISTANCE\n")
    debugBuffer:print("-----|----------|---------|-------|----------|----------|----------\n")
    
    local maxShow = math.min(#sortedAddresses, 10)
    for i = 1, maxShow do
        local addr = sortedAddresses[i]
        debugBuffer:print(string.format("%2d   | 0x%08X |   %2d    |  %2d   |  %6.1f%% | %-8s | %d bytes\n",
                         i, addr.address, addr.correct, addr.total, addr.accuracy, addr.encoding, addr.distance))
    end
    
    if #sortedAddresses > 0 then
        local best = sortedAddresses[1]
        debugBuffer:print("\n🎯 FINAL RECOMMENDATION - MOST LIKELY DIRECTION ADDRESS:\n")
        debugBuffer:print("████████████████████████████████████████████████████████████\n")
        debugBuffer:print(string.format("Address: 0x%08X\n", best.address))
        debugBuffer:print(string.format("Correct responses: %d out of %d tests\n", best.correct, best.total))
        debugBuffer:print(string.format("Accuracy: %.1f%%\n", best.accuracy))
        debugBuffer:print(string.format("Encoding type: %s\n", best.encoding))
        debugBuffer:print(string.format("Distance from X coordinate: %d bytes\n", best.distance))
        debugBuffer:print("████████████████████████████████████████████████████████████\n")
        
        -- Additional confidence assessment
        if best.correct >= 15 and best.accuracy >= 80 then
            debugBuffer:print("✅ HIGH CONFIDENCE: This address is very likely correct!\n")
        elseif best.correct >= 8 and best.accuracy >= 60 then
            debugBuffer:print("⚠️  MEDIUM CONFIDENCE: This address is probably correct.\n")
        else
            debugBuffer:print("❓ LOW CONFIDENCE: Results are inconclusive.\n")
        end
        
        debugBuffer:print(string.format("\nTo use this address, update your Pokemon Sapphire config:\n"))
        debugBuffer:print(string.format("playerDirection: 0x%08X\n", best.address))
        
    else
        debugBuffer:print("❌ No reliable direction address found.\n")
    end
    
    debugBuffer:print("\n" .. string.rep("=", 60) .. "\n")
    debugBuffer:print("🎯 TESTING COMPLETE - FINAL RESULTS DISPLAYED ABOVE 🎯\n")
    debugBuffer:print("Auto-scanning has stopped. Reload script to test again.\n")
    debugBuffer:print(string.rep("=", 60) .. "\n")
end

function showCurrentGameState()
    debugBuffer:clear()
    debugBuffer:print("=== Current Game State ===\n")
    
    local x = emu:read16(confirmedAddresses.playerX)
    local y = emu:read16(confirmedAddresses.playerY) 
    local mapId = emu:read8(confirmedAddresses.mapId)
    
    debugBuffer:print(string.format("X coordinate (0x%08X): %d\n", confirmedAddresses.playerX, x))
    debugBuffer:print(string.format("Y coordinate (0x%08X): %d\n", confirmedAddresses.playerY, y))
    debugBuffer:print(string.format("Map ID (0x%08X): %d\n", confirmedAddresses.mapId, mapId))
    
    debugBuffer:print(string.format("\nTotal direction candidates found: %d\n", totalCandidates))
    debugBuffer:print(string.format("Addresses being monitored: %d\n", 0))
    local count = 0
    for _ in pairs(previousDirections) do count = count + 1 end
    debugBuffer:print(string.format("Addresses being monitored: %d\n", count))
end

-- Auto-scan timing
local lastScanFrame = 0
local scanInterval = 3000  -- 5 seconds at 60 FPS (5 * 60 = 300 frames)
local autoScanEnabled = false
local scanPhaseState = "init"  -- "init", "scanning", "monitoring"
local frameCount = 0  -- Initialize frame counter immediately

-- Direction instruction system
local directionInstructions = {"UP", "DOWN", "LEFT", "RIGHT"}
local currentInstructionIndex = 1
local lastInstructedDirection = nil
local addressScores = {}  -- Track how many times each address correctly responds
local testCycle = 0
local maxTestCycles = 25  -- Timebox to 25 rounds
local testingComplete = false

-- Button press management (like script.lua)
local currentKeyIndex = nil
local keyPressStartFrame = 0
local keyPressDuration = 4  -- Hold button for 4 frames (like script.lua)

-- Initialize other required variables
local previousDirections = {}
local directionCandidates = {}
local searchPhase = 1
local currentRange = 1
local currentAddress = 0
local totalCandidates = 0

-- Initialize when script loads
if emu then
    debugBuffer:print("Comprehensive Pokemon Sapphire Direction Search loaded!\n\n")
    debugBuffer:print("This script searches for direction data stored separately from coordinates.\n\n")
    debugBuffer:print("AUTO-SCAN MODE: Scans every 5 seconds\n")
    debugBuffer:print("Controls:\n")
    debugBuffer:print("F5 - Manual scan around working address\n")
    debugBuffer:print("F6 - Manual check for direction changes\n")
    debugBuffer:print("F7 - Show current game state\n")
    debugBuffer:print("F8 - Toggle auto-scan (currently OFF)\n\n")
    
    initializeSearch()
    
    -- Manual controls
    callbacks:add("keyreleased", function(key)
        if key == "f5" then
            quickScanAroundWorkingAddress()
            scanPhaseState = "monitoring"
        elseif key == "f6" then
            checkDirectionChanges()
        elseif key == "f7" then
            showCurrentGameState()
        elseif key == "f8" then
            autoScanEnabled = not autoScanEnabled
            debugBuffer:print(string.format("Auto-scan %s\n", autoScanEnabled and "ENABLED" or "DISABLED"))
            if autoScanEnabled then
                scanPhaseState = "init"
                lastScanFrame = frameCount
                debugBuffer:print("Turn your character and auto-scan will start in 5 seconds...\n")
            end
        end
    end)
    
    -- Auto-scan loop
    callbacks:add("frame", function()
        frameCount = frameCount + 1
        
        -- Handle button press/release every frame (like script.lua)
        handleButtonPress()
        
        if not autoScanEnabled or testingComplete then
            return  -- Stop all processing when testing is complete
        end
        
        if frameCount - lastScanFrame >= scanInterval then
            lastScanFrame = frameCount
            
            if scanPhaseState == "init" then
                debugBuffer:print("🔄 Auto-scan: Initial scan...\n")
                quickScanAroundWorkingAddress()
                scanPhaseState = "monitoring"
                lastInstructedDirection = nil
                debugBuffer:print("🔄 Auto-scan: Now monitoring for changes every 5 seconds...\n")
            elseif scanPhaseState == "monitoring" then
                -- Check if testing is complete
                if testCycle >= maxTestCycles then
                    if not testingComplete then
                        testingComplete = true
                        autoScanEnabled = false  -- Stop auto-scanning completely
                        scanPhaseState = "complete"  -- Change state to prevent further processing
                        showFinalResults()
                    end
                    return  -- Exit completely, don't process anything else
                end
                
                -- Give direction instruction BEFORE checking changes
                testCycle = testCycle + 1
                currentInstructionIndex = ((testCycle - 1) % #directionInstructions) + 1
                local newDirection = directionInstructions[currentInstructionIndex]
                
                -- First show the current instruction prominently
                debugBuffer:clear()
                debugBuffer:print("████████████████████████████████████████████████████████████\n")
                debugBuffer:print("█                                                          █\n")
                debugBuffer:print(string.format("█      🎮 PRESS %s NOW! 🎮 TEST %d/%d        █\n", newDirection, testCycle, maxTestCycles))
                debugBuffer:print("█                                                          █\n")
                debugBuffer:print("████████████████████████████████████████████████████████████\n")
                debugBuffer:print("\n")
                
                -- Try automatic button press but don't rely on it
                autoPressButton(newDirection)
                debugBuffer:print("If auto-press doesn't work, manually press the arrow key!\n\n")
                
                -- Then check for changes from the PREVIOUS instruction
                if lastInstructedDirection then
                    checkDirectionChangesWithInstruction()
                else
                    debugBuffer:print("Starting instruction cycle...\n")
                end
                
                -- Set new instruction for next cycle
                lastInstructedDirection = newDirection
            end
        end
    end)
    
    -- Auto-enable auto-scan after 3 seconds (1800 frames at 60 FPS)
    local autoEnableCallback
    autoEnableCallback = callbacks:add("frame", function()
        if not autoScanEnabled and frameCount > 1800 then
            autoScanEnabled = true
            scanPhaseState = "init"
            lastScanFrame = frameCount
            debugBuffer:print("🔄 Auto-scan ENABLED - scanning every 5 seconds\n")
            debugBuffer:print("Turn your character to test direction detection!\n")
            -- Remove this callback after first run
            callbacks:remove("frame", autoEnableCallback)
        end
    end)
end