# Base Game Template

This directory serves as a template for creating new game modules in the LLM Game AI system.

## Creating a New Game Module

To create a new game module:

1. **Copy this directory** to `games/your_game_name/`

2. **Create game_info.py** with game metadata:
```python
GAME_INFO = {
    'name': 'your_game_name',
    'display_name': 'Your Game Name',
    'description': 'Description of your game',
    'version': '1.0',
    'platform': 'Game Boy Advance',  # or other platform
    'emulator': 'mGBA',  # or other emulator
    'supported_features': [
        'screenshot_analysis',
        'button_sequences',
        'memory_reading',  # if applicable
        'knowledge_system',
        'dynamic_prompts'
    ],
    'requirements': {
        'emulator': 'mGBA with Lua scripting support',
        'rom': 'Your Game ROM file',
        'api_keys': ['google_gemini']  # or other providers
    }
}
```

3. **Implement the required modules**:
   - `game_engine.py` - Inherit from `BaseGameEngine`
   - `knowledge_system.py` - Inherit from `BaseKnowledgeSystem`
   - `prompt_template.py` - Inherit from `BasePromptTemplate`
   - `controller.py` - Inherit from `BaseGameController`
   - `llm_client.py` - LLM client implementation (can reuse existing ones)

4. **Update configuration** to use your game:
```json
{
    "game": "your_game_name",
    ...
}
```

## Required Implementations

### GameEngine
- Button mapping for your platform
- Game state parsing from emulator data
- Map/location naming
- Navigation guidance
- Game-specific objectives

### KnowledgeSystem
- Game-specific goals and objectives
- Context generation for your game
- Navigation advice
- Progress analysis
- Action suggestions

### PromptTemplate
- Game-specific prompt template
- Available tools/functions for your game
- Context variables
- System messages

### Controller
- Game-specific tool call handling
- Client communication protocol
- Game state management
- Integration with emulator

## Testing Your Game Module

1. Start the system with your game:
```bash
python game_controller.py --game your_game_name --config config.json
```

2. List available games to verify registration:
```bash
python game_controller.py --list-games
```

3. Test with debug mode for troubleshooting:
```bash
python game_controller.py --game your_game_name --config config.json --debug
```

## Example Games

See the `pokemon_red` module for a complete implementation example.