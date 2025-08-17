# Testing Pokemon Sapphire Support

## Quick Test Procedure

1. **Start mGBA with Pokemon Sapphire ROM**
2. **Load the updated script.lua** (Tools > Script Viewer > Load script.lua)
3. **Check debug output** for game detection:
   ```
   Detecting game...
   ROM Name: POKEMON SAPPHIRE
   Detected game: Pokemon Sapphire (Game Boy Advance)
   Dynamic memory discovery needed
   ```

4. **Monitor memory discovery process**:
   - First tries memory scanning (may take a few seconds)
   - Falls back to known address sets if scanning fails
   - Should show "Successfully discovered memory addresses" or "Using fallback Sapphire addresses"

5. **Start AI GBA Player**:
   ```bash
   cd ai_gba_player
   python manage.py runserver
   # In another terminal:
   python manage.py start_process unified_service
   ```

## Expected Debug Output

```
Debug buffer initialized
Detecting game...
ROM Name: POKEMON SAPPHIRE VERSION
ROM CRC32: [some number]
Detected game: Pokemon Sapphire (Game Boy Advance)
Dynamic memory discovery needed
Attempting to discover memory addresses...
Scanning memory for player data patterns...
[Either] Successfully discovered memory addresses
[Or] Memory scan failed to find player data
[Or] Using fallback Sapphire addresses
Testing address set 1...
Values seem valid: X=123, Y=456, Dir=1, Map=12
Address set 1 appears to work
```

## Troubleshooting

### If memory discovery fails:
- The system will try 3 different fallback address sets
- Check if coordinates, direction, and map ID values look reasonable
- Direction should be 1-4 (not 0,4,8,12 like Game Boy games)

### If coordinates look wrong:
- May need to add more fallback address sets for your specific ROM version
- Check ROM CRC32 in debug output to identify exact version

### If game state is invalid:
- Try moving the player character and see if values update
- X/Y should change when moving, direction should change when turning

## Adding Support for Your ROM Version

If the current fallback addresses don't work for your specific Sapphire ROM:

1. Note the ROM CRC32 from debug output
2. Add new address set to `getPokemonSapphireFallbackAddresses()` function
3. Test with manual memory scanning tools if needed

The system is designed to be robust and should work with most Pokemon Sapphire versions.