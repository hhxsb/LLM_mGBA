# 🔍 Pokemon Sapphire Memory Address Debugging Guide

## Current Issue

Your Pokemon Sapphire ROM is being detected correctly, but the memory addresses for player data (position, direction, map) are not accurate. The system found address `0x020013E0` but it's always showing "Direction: UP" and static coordinates.

## 🛠️ **Step-by-Step Debugging Process**

### Step 1: Use the Real-Time Memory Debugger

1. **Load the debug script** in mGBA:
   - Tools > Script Viewer
   - Load: `debug_sapphire_memory_realtime.lua`

2. **The script will show all known Pokemon Sapphire addresses** and monitor them for changes

3. **Move your character around** while watching the debug output:
   - Walk in different directions  
   - Turn to face different directions
   - Enter/exit buildings if possible

4. **Look for addresses that change** - these will be marked with `*** CHANGED ***`

### Step 2: Identify the Correct Address

The correct player data address should show:
- **X/Y coordinates change** when you move the character
- **Direction value changes** when you turn the character (1=DOWN, 2=UP, 3=LEFT, 4=RIGHT)
- **Map ID changes** when you enter new areas

### Step 3: Update the System

Once you find the working address, we can update the fallback addresses in the Python configuration.

## 🔧 **Manual Testing**

If the real-time debugger doesn't work, you can also test manually:

### In mGBA Script Viewer Console:
```lua
-- Test specific addresses manually
local addr = 0x02031DBC  -- Replace with address to test
local x = emu:read16(addr)
local y = emu:read16(addr + 2)  
local dir = emu:read8(addr + 4)
local map = emu:read8(addr + 6)
print("X="..x..", Y="..y..", Dir="..dir..", Map="..map)
```

### Expected Behavior:
- **X and Y should be small numbers** (typically 5-50 for most Pokemon maps)
- **Direction should be 1, 2, 3, or 4** (not 0 or other values)
- **Map ID should be reasonable** (usually 0-100 for most areas)

## 📋 **Known Pokemon Sapphire Addresses to Test**

The debugging script tests these addresses:
- `0x02031DBC` - Most common Sapphire address
- `0x02024EA4` - Alternative version 1  
- `0x02037BA8` - Alternative version 2
- `0x020013E0` - Currently discovered (but seems wrong)
- `0x02025734` - Additional possibility
- `0x02031E50` - Additional possibility

## 🎯 **What to Look For**

### Good Address Signs:
- ✅ Values change when you move
- ✅ Direction shows correct value (1=DOWN, 2=UP, 3=LEFT, 4=RIGHT)
- ✅ Coordinates are reasonable (not 0,0 unless you're actually at origin)
- ✅ Map ID seems reasonable

### Bad Address Signs:
- ❌ Always shows same direction (like "UP")
- ❌ Coordinates never change
- ❌ Direction is always 2 or some fixed value
- ❌ Values are obviously wrong (like 65535 or 0)

## 🔄 **Updated Script Benefits**

The updated `script.lua` now:
1. **Tests fallback addresses first** (more reliable than memory scanning)
2. **Shows detailed debugging info** for each address tested
3. **Provides better validation** of address candidates
4. **Includes memory inspection** to see all known addresses

## 📞 **Next Steps**

1. **Run the debug script** and move your character
2. **Identify which address shows changing values**
3. **Report back the working address** and I'll update the system
4. **Test with the updated configuration**

The debug script will automatically highlight which addresses change when you move, making it easy to identify the correct player data location for your specific Pokemon Sapphire ROM.

## 🎮 **ROM Version Considerations**

Different Pokemon Sapphire ROM versions (US, EU, Japan, different revisions) may have player data at different memory locations. The debugging script tests multiple known addresses to find the one that works for your specific ROM.

Once we identify the correct address for your ROM, the system will work perfectly! 🚀