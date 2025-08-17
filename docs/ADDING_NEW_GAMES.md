# Adding New Games to AI GBA Player

This guide explains how to extend the AI GBA Player system to support additional Game Boy and Game Boy Advance games.

## Architecture Overview

The system uses a 3-step process for game support:
1. **Game Detection** - Identify the ROM based on name/CRC
2. **Configuration** - Define game-specific settings and memory layout
3. **Memory Discovery** - Find or define memory addresses for game state

## Step 1: Add Game Detection

Edit `emulator/script.lua` in the `detectGame()` function (lines 37-74):

```lua
function detectGame()
    local romName = emu:romName() or ""
    local gameName = string.upper(romName)
    
    -- Add your new game detection here
    if string.find(gameName, "YOUR_GAME_NAME") then
        return "your_game_id"
    elseif string.find(gameName, "POKEMON SAPPHIRE") then
        return "pokemon_sapphire"
    -- ... existing games
    end
end
```

**Detection Methods:**
- **ROM Name Pattern**: Most common, matches ROM title
- **CRC32 Hash**: For specific ROM versions
- **Combined**: Both name and CRC for precision

## Step 2: Create Game Configuration

Add to `createGameConfigs()` function (lines 77-144):

```lua
-- Your new game configuration
configs.your_game_id = {
    name = "Your Game Name",
    platform = "Game Boy" or "Game Boy Advance",
    memoryAddresses = {
        -- For Game Boy (static addresses)
        playerDirection = 0xC109,
        playerX = 0xD362,
        playerY = 0xD361,
        mapId = 0xD35E,
        
        -- For GBA (dynamic - set to nil initially)
        -- playerDirection = nil,
        -- playerX = nil,
        -- playerY = nil,
        -- mapId = nil,
    },
    directionEncoding = {
        -- Game Boy style (Pokemon Red/Blue)
        [0] = "DOWN", [4] = "UP", [8] = "LEFT", [12] = "RIGHT"
        
        -- GBA style (Pokemon Ruby/Sapphire/Emerald)
        -- [1] = "DOWN", [2] = "UP", [3] = "LEFT", [4] = "RIGHT"
    },
    memoryType = "static" or "dynamic"
}
```

### Configuration Options

**Platform Types:**
- `"Game Boy"` - Original Game Boy games (static memory)
- `"Game Boy Advance"` - GBA games (usually dynamic memory)

**Memory Types:**
- `"static"` - Fixed memory addresses (Game Boy games)
- `"dynamic"` - Requires memory scanning (most GBA games)

**Direction Encoding:**
- Game Boy: 0=DOWN, 4=UP, 8=LEFT, 12=RIGHT
- GBA: Usually 1=DOWN, 2=UP, 3=LEFT, 4=RIGHT (varies by game)

## Step 3: Implement Memory Discovery (GBA Games Only)

For GBA games with dynamic memory, add to `discoverMemoryAddresses()` function (lines 169-191):

```lua
function discoverMemoryAddresses()
    if currentGame == "your_game_id" then
        local discovered = scanForYourGame()
        if discovered then
            memoryAddresses = discovered
        else
            memoryAddresses = getYourGameFallbackAddresses()
        end
    -- ... existing games
    end
end
```

### Create Fallback Address Function

```lua
function getYourGameFallbackAddresses()
    local possibleAddresses = {
        -- Address set 1 (find these using memory scanning tools)
        {
            playerX = 0x02031ABC,
            playerY = 0x02031ABE,
            playerDirection = 0x02031AC0,
            mapId = 0x02031AC2,
        },
        -- Address set 2 (alternative ROM versions)
        {
            playerX = 0x02024DEF,
            playerY = 0x02024DF1,
            playerDirection = 0x02024DF3,
            mapId = 0x02024DF5,
        }
    }
    
    -- Test each set and return first working one
    for i, addresses in ipairs(possibleAddresses) do
        if testAddressSet(addresses) then
            return addresses
        end
    end
    
    return possibleAddresses[1]  -- Fallback to first set
end
```

## Step 4: Find Memory Addresses

### For Game Boy Games (Static)
Use emulator memory viewers or community documentation to find fixed addresses.

### For GBA Games (Dynamic)
1. **Use the debug script**: Load `debug_sapphire_memory.lua` and modify it for your game
2. **Manual memory scanning**: Use mGBA's memory viewer while playing
3. **Community resources**: Check forums, ROM hacking sites, disassemblies

**Common GBA Memory Regions:**
- `0x02000000 - 0x02040000` - External Work RAM (EWRAM)
- `0x03000000 - 0x03008000` - Internal Work RAM (IWRAM)

### Memory Scanning Tips

**Look for patterns where:**
- X/Y coordinates change when player moves
- Direction value changes when player turns
- Map ID changes when entering new areas
- Values are in reasonable ranges (coordinates: 0-1000, direction: 1-4, map: 0-255)

## Step 5: Test Your Implementation

1. **Load your ROM** in mGBA
2. **Load script.lua** and check debug output for correct detection
3. **Verify memory addresses** show valid values when you move the player
4. **Test with AI GBA Player** to ensure full integration

## Example: Adding Pokemon Crystal

```lua
-- Step 1: Detection
if string.find(gameName, "POKEMON CRYSTAL") then
    return "pokemon_crystal"

-- Step 2: Configuration  
configs.pokemon_crystal = {
    name = "Pokemon Crystal",
    platform = "Game Boy Color",
    memoryAddresses = {
        playerDirection = 0xDCB9,
        playerX = 0xDCB7,
        playerY = 0xDCB8,
        mapId = 0xDCB5,
    },
    directionEncoding = {
        [0] = "DOWN", [4] = "UP", [8] = "LEFT", [12] = "RIGHT"
    },
    memoryType = "static"
}
```

## Troubleshooting

**Game not detected:**
- Check ROM name pattern in debug output
- Try adding CRC32 checking for specific versions

**Invalid memory values:**
- Verify addresses using memory viewer
- Check direction encoding matches game's format
- Ensure coordinate ranges are reasonable

**Dynamic discovery fails:**
- Add more fallback address sets
- Manually scan memory using debug tools
- Check community resources for known addresses

## Resources

- **mGBA Memory Viewer**: Tools > Memory Viewer
- **Community ROM Info**: Datacrystal.romhacking.net
- **Debug Script**: Use `debug_sapphire_memory.lua` as template
- **Pokemon Disassemblies**: github.com/pret/ (for accurate memory maps)

The system is designed to be highly extensible - most games can be added with just configuration changes, no core code modifications needed.