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

-- Memory addresses for Pokemon Red (Game Boy)
local memoryAddresses = {
    playerDirection = 0xC109,  -- Direction facing (0:Down, 4:Up, 8:Left, 12:Right)
    playerX = 0xD362,          -- X coordinate on map
    playerY = 0xD361,          -- Y coordinate on map
    mapId = 0xD35E,            -- Current map ID
}

-- Debug buffer setup
function setupBuffer()
    debugBuffer = console:createBuffer("Debug")
    debugBuffer:setSize(100, 64)
    debugBuffer:clear()
    debugBuffer:print("Debug buffer initialized\n")
end

-- Direction value to text conversion
function getDirectionText(value)
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
        
        -- Set flag back to waiting for next request
        waitingForRequest = true
    end
end

-- Legacy screenshot function (keeping for backward compatibility)
function captureAndSendScreenshot()
    -- Create directory if it doesn't exist
    os.execute("mkdir -p \"" .. projectRoot .. "/data/screenshots\"")
    
    -- Take the screenshot
    emu:screenshot(screenshotPath)
    
    -- Read the game memory data
    local memoryData = readGameMemory()
    
    -- Create a data package to send with the screenshot
    local dataPackage = {
        path = screenshotPath,
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
    
    debugBuffer:print("Screenshot captured with game state:\n")
    debugBuffer:print("Direction: " .. dataPackage.direction .. "\n")
    debugBuffer:print("Position: X=" .. dataPackage.x .. ", Y=" .. dataPackage.y .. "\n")
    debugBuffer:print("Map ID: " .. dataPackage.mapId .. "\n")
    
    -- Set flag back to waiting for next request
    waitingForRequest = true
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
            -- Only take screenshot if we're waiting for a request
            if waitingForRequest then
                waitingForRequest = false
                captureAndSendScreenshot()
            end
        elseif data == "request_state" then
            debugBuffer:print("Game state requested by controller (screen capture mode)\n")
            -- Only send state if we're waiting for a request
            if waitingForRequest then
                waitingForRequest = false
                sendGameState()
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
callbacks:add("start", startSocket)
callbacks:add("frame", handleKeyPress)

-- Initialize on script load
if emu then
    setupBuffer()
    startSocket()
    
    -- Create directory on startup
    os.execute("mkdir -p \"" .. projectRoot .. "/data/screenshots\"")
    debugBuffer:print("Created screenshot directories\n")
end