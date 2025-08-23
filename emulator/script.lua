---@diagnostic disable: lowercase-global
-- Socket setup for communication with Python controller
statusSocket = nil
waitingForRequest = true -- New flag to indicate if we're waiting for controller request

-- Global variables for key press tracking
local buttonQueue = {}     -- Queue of buttons to press
local durationQueue = {}   -- Queue of durations for each button
local currentKeyIndex = nil
local currentKeyDuration = 2  -- Current button duration in frames
local keyPressStartFrame = 0
local defaultKeyPressFrames = 2   -- Default hold duration for keys
local buttonSeparationFrames = 58  -- Wait frames between button presses
local separationStartFrame = 0
local inSeparationPeriod = false

-- Video recording variables
local isRecording = false
local videoStartFrame = 0
local videoEndFrame = 0
local totalButtonCount = 0
local postSequenceWaitFrames = 60  -- 1 second wait after last button

-- Path settings (relative to project root)
-- Note: Update these paths to match your project location
local projectRoot = "/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red"  -- Change this to your project path
local screenshotPath = projectRoot .. "/data/screenshots/screenshot.png"
local previousScreenshotPath = projectRoot .. "/data/screenshots/previous_screenshot.png"
local videoPath = projectRoot .. "/data/videos/video_sequence.mp4"

-- Screenshot session tracking for before/after pairs
local currentSessionTimestamp = nil

-- Game configuration system (received from Python service)
local currentGame = nil
local memoryAddresses = {}
local gameConfig = {}
local gameConfigReceived = false

-- Handle game configuration received from Python service
function handleGameConfig(configString)
    debugBuffer:print("Received game configuration from Python service\n")
    debugBuffer:print("Config string length: " .. string.len(configString) .. "\n")
    
    -- For Pokemon Sapphire, use hardcoded configuration to avoid parsing issues
    if string.find(configString, "pokemon_sapphire") then
        debugBuffer:print("Detected Pokemon Sapphire config - using hardcoded fallback\n")
        
        -- Set game configuration directly
        currentGame = "pokemon_sapphire"
        gameConfig = {
            id = "pokemon_sapphire",
            name = "Pokemon Sapphire",
            platform = "Game Boy Advance",
            memoryType = "dynamic",
            memoryAddresses = {
                playerDirection = nil,
                playerX = nil,
                playerY = nil,
                mapId = nil,
            },
            directionEncoding = {
                [1] = "DOWN",
                [2] = "UP",
                [3] = "LEFT",
                [4] = "RIGHT"
            },
            fallbackAddresses = {
                -- Working address set (user confirmed X, Y, Map work, direction discovered)
                {
                    playerX = 0x02025734,
                    playerY = 0x02025736,
                    playerDirection = 0x0202002F,  -- Discovered by comprehensive direction search
                    mapId = 0x0202573A,
                },
                -- Original known addresses (backup)
                {
                    playerX = 0x02031DBC,
                    playerY = 0x02031DBE,
                    playerDirection = 0x02031DC0,
                    mapId = 0x02031DC2,
                },
                {
                    playerX = 0x02024EA4,
                    playerY = 0x02024EA6,
                    playerDirection = 0x02024EA8,
                    mapId = 0x02024EAA,
                }
            }
        }
        gameConfigReceived = true
        
        debugBuffer:print("Game configured: Pokemon Sapphire (Game Boy Advance)\n")
        debugBuffer:print("Dynamic memory discovery needed\n")
        discoverMemoryAddresses()
        
        return true
    end
    
    -- For other games, try to parse the config string
    debugBuffer:print("Attempting to parse config string...\n")
    local loadFunc, err = load("return " .. configString)
    if not loadFunc then
        debugBuffer:print("Error parsing game config: " .. (err or "unknown error") .. "\n")
        debugBuffer:print("First 100 chars: " .. string.sub(configString, 1, 100) .. "\n")
        return false
    end
    
    local success, config = pcall(loadFunc)
    if not success then
        debugBuffer:print("Error loading game config: " .. (config or "unknown error") .. "\n")
        return false
    end
    
    -- Set game configuration
    currentGame = config.id
    gameConfig = config
    gameConfigReceived = true
    
    debugBuffer:print("Game configured: " .. config.name .. " (" .. config.platform .. ")\n")
    
    -- Set up memory addresses
    if config.memoryType == "static" then
        memoryAddresses = config.memoryAddresses
        debugBuffer:print("Using static memory addresses\n")
    elseif config.memoryType == "dynamic" then
        debugBuffer:print("Dynamic memory discovery needed\n")
        discoverMemoryAddresses()
    end
    
    return true
end

-- Wait for game configuration from Python service
function waitForGameConfig()
    debugBuffer:print("Waiting for game configuration from Python service...\n")
    -- Configuration will be received via socket when Python service detects the game
end

-- Dynamic memory address discovery for GBA games
function discoverMemoryAddresses()
    debugBuffer:print("Attempting to discover memory addresses...\n")
    
    if gameConfig.memoryType == "dynamic" then
        -- First, inspect known addresses for debugging
        inspectMemoryAddresses()
        
        -- Try fallback addresses first (they're more reliable)
        if gameConfig.fallbackAddresses then
            debugBuffer:print("Trying fallback addresses first...\n")
            memoryAddresses = testFallbackAddresses(gameConfig.fallbackAddresses)
            if memoryAddresses and memoryAddresses.playerX then
                debugBuffer:print("Using fallback addresses\n")
                return
            end
        end
        
        -- If fallbacks don't work, try memory scanning
        debugBuffer:print("Fallbacks failed, trying memory scanning...\n")
        local discovered = scanForPlayerData()
        
        if discovered then
            memoryAddresses = discovered
            debugBuffer:print("Successfully discovered memory addresses\n")
        else
            debugBuffer:print("Memory scan failed - using first fallback set\n")
            if gameConfig.fallbackAddresses and #gameConfig.fallbackAddresses > 0 then
                memoryAddresses = gameConfig.fallbackAddresses[1]
            else
                debugBuffer:print("No fallback addresses available\n")
                memoryAddresses = {}
            end
        end
    else
        -- Use static addresses for other games
        memoryAddresses = gameConfig.memoryAddresses
        debugBuffer:print("Using static addresses\n")
    end
end

-- Enhanced memory scan for Pokemon Ruby/Sapphire player data
function scanForPlayerData()
    debugBuffer:print("Scanning memory for player data patterns...\n")
    
    -- GBA RAM typically starts at 0x02000000 and goes to 0x02040000
    local searchStart = 0x02000000
    local searchEnd = 0x02040000
    local searchStep = 4  -- Search every 4 bytes (word-aligned)
    
    local candidates = {}
    
    -- First pass: Find all potential candidates
    debugBuffer:print("Phase 1: Finding potential candidates...\n")
    for address = searchStart, searchEnd, searchStep do
        if isValidPlayerDataLocation(address) then
            local x = emu:read16(address)
            local y = emu:read16(address + 2)
            local direction = emu:read8(address + 4)
            local mapId = emu:read8(address + 6)
            
            table.insert(candidates, {
                address = address,
                x = x,
                y = y,
                direction = direction,
                mapId = mapId
            })
            
            if #candidates <= 5 then  -- Only log first 5 candidates
                debugBuffer:print("Candidate " .. #candidates .. " at " .. string.format("0x%08X", address) .. 
                                 ": X=" .. x .. ", Y=" .. y .. ", Dir=" .. direction .. ", Map=" .. mapId .. "\n")
            end
        end
    end
    
    debugBuffer:print("Found " .. #candidates .. " potential candidates\n")
    
    if #candidates == 0 then
        debugBuffer:print("No candidates found - trying fallback addresses\n")
        return nil
    end
    
    -- If we have candidates, use the first one for now
    -- In a real implementation, we'd want to validate by checking if values change when player moves
    local best = candidates[1]
    debugBuffer:print("Using candidate 1 at " .. string.format("0x%08X", best.address) .. "\n")
    
    return {
        playerX = best.address,
        playerY = best.address + 2,
        playerDirection = best.address + 4,
        mapId = best.address + 6,
    }
end

-- Enhanced direction validation for both standard and TBL encodings
function isValidDirection(direction)
    -- Standard GBA encoding (1-4)
    if direction >= 1 and direction <= 4 then
        return true
    end
    
    -- TBL hex encoding (0x79-0x7C)
    if direction == 0x79 or direction == 0x7A or direction == 0x7B or direction == 0x7C then
        return true
    end
    
    return false
end

-- Check if an address contains valid player data
function isValidPlayerDataLocation(address)
    -- Try to read potential coordinate values
    local x = emu:read16(address)
    local y = emu:read16(address + 2)
    local direction = emu:read8(address + 4)
    local mapId = emu:read8(address + 6)
    
    -- Validate that values are within reasonable ranges
    if x and y and direction and mapId then
        -- Coordinates should be reasonable (0-100 range is more typical for Pokemon maps)
        if x >= 0 and x <= 100 and y >= 0 and y <= 100 then
            -- Enhanced direction validation for both encodings
            if isValidDirection(direction) then
                -- Map ID should be reasonable (0-255 range, but usually much smaller)
                if mapId >= 0 and mapId <= 255 then
                    -- Additional validation: check if the values look like real game data
                    -- X and Y shouldn't both be 0 (unless player is actually at origin)
                    return true
                end
            end
        end
    end
    
    return false
end

-- Test fallback addresses from configuration
function testFallbackAddresses(fallbackAddresses)
    debugBuffer:print("Testing " .. #fallbackAddresses .. " fallback address sets...\n")
    
    -- Test each set of addresses to see which one works
    for i, addresses in ipairs(fallbackAddresses) do
        debugBuffer:print("Testing address set " .. i .. "...\n")
        
        local x = emu:read16(addresses.playerX)
        local y = emu:read16(addresses.playerY)
        local direction = emu:read8(addresses.playerDirection)
        local mapId = emu:read8(addresses.mapId)
        
        debugBuffer:print("  X=" .. (x or "nil") .. ", Y=" .. (y or "nil") .. 
                         ", Dir=" .. (direction or "nil") .. ", Map=" .. (mapId or "nil") .. "\n")
        
        if testAddressSet(addresses) then
            debugBuffer:print("Address set " .. i .. " appears to work\n")
            return addresses
        end
    end
    
    -- If none work, return the first set as a fallback
    debugBuffer:print("No address set validated, using first set as fallback\n")
    return fallbackAddresses[1] or {}
end

-- Manual memory inspection function (for debugging)
function inspectMemoryAddresses()
    debugBuffer:print("=== Manual Memory Inspection ===\n")
    
    -- Known addresses for different Pokemon Sapphire versions
    local testAddresses = {
        0x02031DBC, -- Common Sapphire address
        0x02024EA4, -- Alternative 1
        0x02037BA8, -- Alternative 2
        0x020013E0, -- Current discovered address
        0x02025734, -- Another possibility
        0x02031E50, -- Another possibility
    }
    
    for i, addr in ipairs(testAddresses) do
        local x = emu:read16(addr)
        local y = emu:read16(addr + 2)
        local dir = emu:read8(addr + 4)
        local map = emu:read8(addr + 6)
        
        debugBuffer:print(string.format("0x%08X: X=%d, Y=%d, Dir=%d, Map=%d\n", 
                         addr, x or -1, y or -1, dir or -1, map or -1))
    end
    
    debugBuffer:print("=== End Inspection ===\n")
end

-- Test if a set of addresses contains valid data
function testAddressSet(addresses)
    -- Try to read values and check if they're reasonable
    local x = emu:read16(addresses.playerX)
    local y = emu:read16(addresses.playerY)
    local direction = emu:read8(addresses.playerDirection)
    local mapId = emu:read8(addresses.mapId)
    
    debugBuffer:print("    Raw values: X=" .. (x or "nil") .. ", Y=" .. (y or "nil") .. 
                     ", Dir=" .. (direction or "nil") .. ", Map=" .. (mapId or "nil") .. "\n")
    
    -- Check if values are within expected ranges
    if x and y and direction and mapId then
        -- More lenient coordinate range for testing
        if x >= 0 and x <= 200 and y >= 0 and y <= 200 then
            -- Enhanced direction validation for both standard and TBL encodings
            if isValidDirection(direction) then
                -- Map ID should be reasonable
                if mapId >= 0 and mapId <= 255 then
                    local dirText = getDirectionText(direction)
                    local encodingType = ""
                    if direction >= 1 and direction <= 4 then
                        encodingType = "Standard"
                    elseif direction >= 0x79 and direction <= 0x7C then
                        encodingType = "TBL"
                    end
                    debugBuffer:print("    Values valid (" .. encodingType .. "): X=" .. x .. ", Y=" .. y .. 
                                     ", Dir=" .. direction .. " (" .. dirText .. "), Map=" .. mapId .. "\n")
                    return true
                else
                    debugBuffer:print("    Invalid map ID: " .. mapId .. "\n")
                end
            else
                debugBuffer:print("    Invalid direction: " .. direction .. " (should be 1-4 or 0x79-0x7C)\n")
            end
        else
            debugBuffer:print("    Invalid coordinates: X=" .. x .. ", Y=" .. y .. " (should be 0-200)\n")
        end
    else
        debugBuffer:print("    Some values are nil\n")
    end
    
    return false
end

-- Debug buffer setup
function setupBuffer()
    debugBuffer = console:createBuffer("Debug")
    debugBuffer:setSize(100, 64)
    debugBuffer:clear()
    debugBuffer:print("Debug buffer initialized\n")
end

-- Direction value to text conversion (game-aware)
function getDirectionText(value)
    if gameConfig and gameConfig.directionEncoding then
        local direction = gameConfig.directionEncoding[value]
        if direction then
            return direction
        end
    end
    
    -- Fallback to Pokemon Red encoding if no game config
    if value == 0 then return "DOWN"
    elseif value == 4 then return "UP"
    elseif value == 8 then return "LEFT"
    elseif value == 12 then return "RIGHT"
    else return "UNKNOWN (" .. value .. ")"
    end
end

-- Read game memory data
function readGameMemory()
    local memoryData = {}
    
    -- Read direction and convert to readable form
    local directionValue = emu:read8(memoryAddresses.playerDirection)
    memoryData.direction = {
        value = directionValue,
        text = getDirectionText(directionValue)
    }
    
    -- Read coordinates
    memoryData.position = {
        x = emu:read8(memoryAddresses.playerX),
        y = emu:read8(memoryAddresses.playerY)
    }
    
    -- Read map ID
    memoryData.mapId = emu:read8(memoryAddresses.mapId)
    
    return memoryData
end

-- Video recording functions
function startVideoRecording(buttonCount)
    -- Create directory if it doesn't exist
    os.execute("mkdir -p \"" .. projectRoot .. "/data/videos\"")
    
    -- Calculate video duration: each button takes ~1 second + 1 second post-wait
    local estimatedDurationSeconds = buttonCount + 1
    
    -- Note: mGBA Lua API doesn't expose video recording functions directly
    -- For now, we'll use enhanced screenshot timing instead
    isRecording = true
    videoStartFrame = emu:currentFrame()
    totalButtonCount = buttonCount
    
    -- Calculate when to take final screenshot (convert seconds to frames at 60fps)
    videoEndFrame = videoStartFrame + (estimatedDurationSeconds * 60)
    
    debugBuffer:print("Started enhanced screenshot capture for " .. buttonCount .. " buttons\n")
    debugBuffer:print("Will capture final screenshot after " .. estimatedDurationSeconds .. " seconds\n")
end

function stopVideoRecording()
    if isRecording then
        -- Instead of video recording, take an enhanced screenshot after the button sequence
        -- Create directory if it doesn't exist
        os.execute("mkdir -p \"" .. projectRoot .. "/data/screenshots\"")
        
        -- Take the screenshot
        emu:screenshot(screenshotPath)
        isRecording = false
        
        -- Read the game memory data
        local memoryData = readGameMemory()
        
        -- Create a data package to send with enhanced screenshot info
        local dataPackage = {
            path = screenshotPath,
            previousPath = previousScreenshotPath,
            direction = memoryData.direction.text,
            x = memoryData.position.x,
            y = memoryData.position.y,
            mapId = memoryData.mapId,
            buttonCount = totalButtonCount
        }
        
        -- Convert to a string format for sending
        local dataString = dataPackage.path .. 
                          "||" .. dataPackage.previousPath .. 
                          "||" .. dataPackage.direction .. 
                          "||" .. dataPackage.x .. 
                          "||" .. dataPackage.y .. 
                          "||" .. dataPackage.mapId .. 
                          "||" .. dataPackage.buttonCount
        
        -- Send enhanced screenshot data to Python controller
        sendMessage("enhanced_screenshot_with_state", dataString)
        
        debugBuffer:print("Enhanced screenshot captured and sent to controller\n")
        debugBuffer:print("Direction: " .. dataPackage.direction .. "\n")
        debugBuffer:print("Position: X=" .. dataPackage.x .. ", Y=" .. dataPackage.y .. "\n")
        debugBuffer:print("Map ID: " .. dataPackage.mapId .. "\n")
        debugBuffer:print("Button count: " .. dataPackage.buttonCount .. "\n")
        
        -- AI service controls timing, no need to set waiting flag
    end
end

-- Legacy screenshot function (keeping for backward compatibility)
function captureAndSendScreenshot()
    -- Create directory if it doesn't exist
    os.execute("mkdir -p \"" .. projectRoot .. "/data/screenshots\"")
    
    -- Create new session timestamp for this before/after pair
    currentSessionTimestamp = os.time()
    local timestampedPath = string.gsub(screenshotPath, "%.png", "_before_" .. currentSessionTimestamp .. ".png")
    
    -- Take the screenshot
    emu:screenshot(timestampedPath)
    
    -- Read the game memory data
    local memoryData = readGameMemory()
    
    -- Create a data package to send with the screenshot
    local dataPackage = {
        path = timestampedPath,
        direction = memoryData.direction.text,
        x = memoryData.position.x,
        y = memoryData.position.y,
        mapId = memoryData.mapId
    }
    
    -- Convert to a string format for sending
    local dataString = dataPackage.path .. 
                      "||" .. dataPackage.direction .. 
                      "||" .. dataPackage.x .. 
                      "||" .. dataPackage.y .. 
                      "||" .. dataPackage.mapId
    
    -- Send combined data to Python controller
    sendMessage("screenshot_with_state", dataString)
    
    debugBuffer:print("BEFORE screenshot captured with game state:\n")
    debugBuffer:print("Path: " .. timestampedPath .. "\n")
    debugBuffer:print("Session timestamp: " .. currentSessionTimestamp .. "\n")
    debugBuffer:print("Direction: " .. dataPackage.direction .. "\n")
    debugBuffer:print("Position: X=" .. dataPackage.x .. ", Y=" .. dataPackage.y .. "\n")
    debugBuffer:print("Map ID: " .. dataPackage.mapId .. "\n")
    
    -- AI service controls timing, no need to set waiting flag
end

function captureAndSendAfterScreenshot()
    -- Create directory if it doesn't exist
    os.execute("mkdir -p \"" .. projectRoot .. "/data/screenshots\"")
    
    -- Take the after screenshot using the same session timestamp
    if not currentSessionTimestamp then
        currentSessionTimestamp = os.time()  -- Fallback if no session timestamp
    end
    local afterScreenshotPath = string.gsub(screenshotPath, "%.png", "_after_" .. currentSessionTimestamp .. ".png")
    emu:screenshot(afterScreenshotPath)
    
    -- Read the game memory data
    local memoryData = readGameMemory()
    
    -- Create a data package to send with the after screenshot
    local dataPackage = {
        path = afterScreenshotPath,
        direction = memoryData.direction.text,
        x = memoryData.position.x,
        y = memoryData.position.y,
        mapId = memoryData.mapId
    }
    
    -- Convert to a string format for sending
    local dataString = dataPackage.path .. 
                      "||" .. dataPackage.direction .. 
                      "||" .. dataPackage.x .. 
                      "||" .. dataPackage.y .. 
                      "||" .. dataPackage.mapId
    
    -- Send combined data to Python controller with special prefix
    sendMessage("after_screenshot_data", dataString)
    
    debugBuffer:print("AFTER screenshot captured with game state:\n")
    debugBuffer:print("Path: " .. afterScreenshotPath .. "\n")
    debugBuffer:print("Session timestamp: " .. currentSessionTimestamp .. "\n")
    debugBuffer:print("Direction: " .. dataPackage.direction .. "\n")
    debugBuffer:print("Position: X=" .. dataPackage.x .. ", Y=" .. dataPackage.y .. "\n")
    debugBuffer:print("Map ID: " .. dataPackage.mapId .. "\n")
end

function sendGameState()
    -- Read the game memory data (no screenshot needed for screen capture mode)
    local memoryData = readGameMemory()
    
    -- Create a data package with just the game state
    local dataPackage = {
        direction = memoryData.direction.text,
        x = memoryData.position.x,
        y = memoryData.position.y,
        mapId = memoryData.mapId
    }
    
    -- Convert to a string format for sending
    local dataString = dataPackage.direction .. 
                      "||" .. dataPackage.x .. 
                      "||" .. dataPackage.y .. 
                      "||" .. dataPackage.mapId
    
    -- Send game state data to Python controller
    sendMessage("state", dataString)
    
    debugBuffer:print("Game state sent for screen capture mode:\n")
    debugBuffer:print("Direction: " .. dataPackage.direction .. "\n")
    debugBuffer:print("Position: X=" .. dataPackage.x .. ", Y=" .. dataPackage.y .. "\n")
    debugBuffer:print("Map ID: " .. dataPackage.mapId .. "\n")
    
    -- Set flag back to waiting for next request
    waitingForRequest = true
end

-- Frame counter to manage key press duration and button queue
function handleKeyPress()
    local currentFrame = emu:currentFrame()
    
    -- Check if we need to stop video recording
    if isRecording and currentFrame >= videoEndFrame then
        stopVideoRecording()
        return
    end
    
    -- If we're in a separation period (waiting between button presses)
    if inSeparationPeriod then
        local separationFramesPassed = currentFrame - separationStartFrame
        if separationFramesPassed >= buttonSeparationFrames then
            -- Separation period complete, process next button
            inSeparationPeriod = false
            if #buttonQueue > 0 then
                local nextButton = table.remove(buttonQueue, 1)
                local nextDuration = table.remove(durationQueue, 1) or defaultKeyPressFrames
                currentKeyIndex = nextButton
                currentKeyDuration = nextDuration
                keyPressStartFrame = currentFrame
                emu:addKey(nextButton)
                local keyNames = { "A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L" }
                debugBuffer:print("AI pressing next queued button: " .. keyNames[nextButton + 1] .. 
                                 " (duration: " .. nextDuration .. " frames, after " .. separationFramesPassed .. " frame separation)\n")
            else
                -- All buttons processed, start post-sequence wait
                debugBuffer:print("All buttons processed, starting post-sequence wait\n")
                -- Video will be stopped when videoEndFrame is reached
            end
        end
        return
    end
    
    -- If we're currently pressing a key
    if currentKeyIndex ~= nil then
        local framesPassed = currentFrame - keyPressStartFrame
        
        if framesPassed < currentKeyDuration then
            -- Keep pressing the key
            emu:addKey(currentKeyIndex)
        else
            -- Release the key after sufficient frames
            emu:clearKeys(0x3FF)
            local keyNames = { "A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L" }
            debugBuffer:print("Released " .. keyNames[currentKeyIndex + 1] .. " after " .. framesPassed .. " frames (duration: " .. currentKeyDuration .. ")\n")
            currentKeyIndex = nil
            currentKeyDuration = defaultKeyPressFrames
            
            -- Check if there are more buttons in the queue
            if #buttonQueue > 0 then
                -- Start separation period before next button
                inSeparationPeriod = true
                separationStartFrame = currentFrame
                debugBuffer:print("Starting " .. buttonSeparationFrames .. " frame separation before next button\n")
            else
                -- All buttons processed, video recording will continue for post-sequence wait
                debugBuffer:print("All buttons processed, waiting for video recording to complete\n")
            end
        end
    end
end

-- Socket management functions
function sendMessage(messageType, content)
    if statusSocket then
        statusSocket:send(messageType .. "||" .. content .. "\n")
    end
end

function socketReceived()
    local data, err = statusSocket:receive(1024)
    
    if data then
        -- Trim whitespace
        data = data:gsub("^%s*(.-)%s*$", "%1")
        debugBuffer:print("Received from AI controller: '" .. data .. "'\n")
        
        -- Process different command types
        if data == "request_screenshot" then
            debugBuffer:print("Screenshot requested by controller\n")
            -- Always respond to screenshot requests if game is configured (AI service controls timing)
            if gameConfigReceived then
                captureAndSendScreenshot()
            else
                debugBuffer:print("Cannot take screenshot: Game not configured yet\n")
            end
        elseif data == "request_after_screenshot" then
            debugBuffer:print("After screenshot requested by controller\n")
            -- Capture after screenshot if game is configured
            if gameConfigReceived then
                captureAndSendAfterScreenshot()
            else
                debugBuffer:print("Cannot take after screenshot: Game not configured yet\n")
            end
        elseif data == "request_state" then
            debugBuffer:print("Game state requested by controller (screen capture mode)\n")
            -- Only send state if we're waiting for a request and game is configured
            if waitingForRequest and gameConfigReceived then
                waitingForRequest = false
                sendGameState()
            elseif not gameConfigReceived then
                debugBuffer:print("Cannot send state: Game not configured yet\n")
            end
        elseif string.find(data, "game_config||") then
            -- Handle game configuration from Python service
            local configStart = string.find(data, "||")
            if configStart then
                -- Extract just the config part, stop at any other commands
                local configString = string.sub(data, configStart + 2)
                
                -- Check if there are other commands concatenated (like request_screenshot)
                local nextCommand = string.find(configString, "request_screenshot")
                if nextCommand then
                    configString = string.sub(configString, 1, nextCommand - 1)
                    debugBuffer:print("Found concatenated message, extracting config only\n")
                end
                
                debugBuffer:print("Received game configuration\n")
                debugBuffer:print("Config length: " .. string.len(configString) .. " characters\n")
                
                if handleGameConfig(configString) then
                    debugBuffer:print("Game configuration loaded successfully\n")
                    -- Notify Python that we're ready
                    sendMessage("config_loaded", "true")
                else
                    debugBuffer:print("Failed to load game configuration\n")
                    sendMessage("config_error", "Failed to parse configuration")
                end
            end
        else
            -- Assume it's a button command if not a screenshot request
            -- Handle both single button and comma-separated multiple buttons with optional durations
            local buttonCodes = {}
            local buttonDurations = {}
            
            -- Check if data contains duration information (format: "buttons|durations")
            local pipePos = string.find(data, "|")
            local buttonData = data
            local durationData = nil
            
            if pipePos then
                buttonData = string.sub(data, 1, pipePos - 1)
                durationData = string.sub(data, pipePos + 1)
            end
            
            -- Parse button codes
            if string.find(buttonData, ",") then
                for buttonStr in string.gmatch(buttonData, "([^,]+)") do
                    local buttonCode = tonumber(buttonStr)
                    if buttonCode and buttonCode >= 0 and buttonCode <= 9 then
                        table.insert(buttonCodes, buttonCode)
                    end
                end
            else
                -- Single button
                local buttonCode = tonumber(buttonData)
                if buttonCode and buttonCode >= 0 and buttonCode <= 9 then
                    table.insert(buttonCodes, buttonCode)
                end
            end
            
            -- Parse duration data if present
            if durationData then
                if string.find(durationData, ",") then
                    for durationStr in string.gmatch(durationData, "([^,]+)") do
                        local duration = tonumber(durationStr)
                        if duration and duration >= 1 and duration <= 180 then
                            table.insert(buttonDurations, duration)
                        else
                            table.insert(buttonDurations, defaultKeyPressFrames)
                        end
                    end
                else
                    -- Single duration
                    local duration = tonumber(durationData)
                    if duration and duration >= 1 and duration <= 180 then
                        table.insert(buttonDurations, duration)
                    else
                        table.insert(buttonDurations, defaultKeyPressFrames)
                    end
                end
            end
            
            if #buttonCodes > 0 then
                local keyNames = { "A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L" }
                
                -- Save current screenshot as previous before processing buttons
                if waitingForRequest then
                    emu:screenshot(previousScreenshotPath)
                    debugBuffer:print("Saved previous screenshot\n")
                end
                
                -- Clear existing key presses and button queue
                emu:clearKeys(0x3FF)
                buttonQueue = {}
                durationQueue = {}
                
                -- Start video recording for the button sequence
                startVideoRecording(#buttonCodes)
                
                -- Set up the first button and its duration
                currentKeyIndex = buttonCodes[1]
                currentKeyDuration = buttonDurations[1] or defaultKeyPressFrames
                keyPressStartFrame = emu:currentFrame()
                
                -- Add remaining buttons and durations to queues
                for i = 2, #buttonCodes do
                    table.insert(buttonQueue, buttonCodes[i])
                    table.insert(durationQueue, buttonDurations[i] or defaultKeyPressFrames)
                end
                
                -- Press the first key
                emu:addKey(currentKeyIndex)
                
                -- Log what we're doing
                local buttonNames = {}
                local durationStrings = {}
                for i, code in ipairs(buttonCodes) do
                    table.insert(buttonNames, keyNames[code + 1])
                    table.insert(durationStrings, tostring(buttonDurations[i] or defaultKeyPressFrames))
                end
                debugBuffer:print("AI pressing buttons in sequence: " .. table.concat(buttonNames, ", ") .. 
                                 " (durations: " .. table.concat(durationStrings, ", ") .. " frames)\n")
            else
                debugBuffer:print("Invalid button data received: '" .. data .. "'\n")
                -- Notify we're ready for next input even if this was invalid
                waitingForRequest = true
                sendMessage("ready", "true")
            end
        end
    elseif err ~= socket.ERRORS.AGAIN then
        debugBuffer:print("Socket error: " .. err .. "\n")
        stopSocket()
    end
end

function socketError(err)
    debugBuffer:print("Socket error: " .. err .. "\n")
    stopSocket()
end

function stopSocket()
    if not statusSocket then return end
    debugBuffer:print("Closing socket connection\n")
    statusSocket:close()
    statusSocket = nil
end

function startSocket()
    debugBuffer:print("Connecting to controller at 127.0.0.1:8888...\n")
    statusSocket = socket.tcp()
    
    if not statusSocket then
        debugBuffer:print("Failed to create socket\n")
        return
    end
    
    -- Add callbacks
    statusSocket:add("received", socketReceived)
    statusSocket:add("error", socketError)
    
    -- Connect to the controller
    if statusSocket:connect("127.0.0.1", 8888) then
        debugBuffer:print("Successfully connected to controller\n")
        -- Notify controller we're ready for first instruction
        sendMessage("ready", "true")
        waitingForRequest = true
    else
        debugBuffer:print("Failed to connect to controller\n")
        stopSocket()
    end
end

-- Add callbacks to run our functions
callbacks:add("start", setupBuffer)
callbacks:add("start", waitForGameConfig)  -- Wait for game config from Python
callbacks:add("start", startSocket)
callbacks:add("frame", handleKeyPress)

-- Initialize on script load
if emu then
    setupBuffer()
    waitForGameConfig()  -- Wait for configuration from Python service
    startSocket()
    
    -- Create directory on startup
    os.execute("mkdir -p \"" .. projectRoot .. "/data/screenshots\"")
    debugBuffer:print("Created screenshot directories\n")
end