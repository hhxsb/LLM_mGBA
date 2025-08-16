# Contributing to AI GBA Player

Thank you for your interest in contributing to this universal AI gaming framework! This project enables LLMs to play any Game Boy Advance game through visual understanding and decision-making.

## 🎯 Project Vision

While this framework started with Pokémon Red (based on [martoast/LLM-Pokemon-Red](https://github.com/martoast/LLM-Pokemon-Red)), our goal is to create a universal system that can play any GBA game. The simplified architecture is designed to be:

- **Game-agnostic**: Core systems work with any GBA title
- **Simple to use**: Single Django process with web interface
- **Easy to extend**: Modular design for adding new games
- **Developer-friendly**: Real-time chat interface for monitoring AI

## 🎮 Priority Contribution Areas

### 1. New Game Support (High Priority)
Help expand the framework to support additional GBA games:

**Target Games**:
- 🏃 **Platformers**: Super Mario Advance series, Sonic games
- ⚔️ **Action/Adventure**: The Legend of Zelda: Minish Cap, Metroid series
- 🎖️ **Strategy/RPG**: Fire Emblem series, Final Fantasy Tactics Advance
- 🏁 **Racing**: Mario Kart: Super Circuit, F-Zero series
- 🥊 **Fighting**: Street Fighter Alpha series, Tekken Advance

**What's Needed**:
- Game-specific prompt templates optimized for each game
- Memory address mappings for game state (optional)
- Game-specific knowledge modules
- Testing with different game types

### 2. LLM Provider Support (Medium Priority)
Expand support for different AI providers:

**Current Support**:
- ✅ Google Gemini (primary)
- ✅ OpenAI GPT-4o
- 🔄 Anthropic Claude (basic support)

**Needed**:
- Local model support (Ollama, LM Studio)
- Azure OpenAI integration
- Enhanced Anthropic Claude support
- Model performance benchmarking

### 3. Web Interface Enhancements (Medium Priority)
Improve the Django web interface:

**Current Features**:
- Real-time chat monitoring
- Configuration management
- mGBA launcher integration

**Enhancement Ideas**:
- WebSocket support for true real-time updates
- Game state visualization
- AI decision replay system
- Performance metrics dashboard
- Multi-game session management

### 4. AI Performance Improvements (Medium Priority)
Enhance AI decision-making capabilities:

**Areas for Improvement**:
- Better prompt engineering for different game genres
- Enhanced error recovery strategies
- Adaptive decision timing based on game state
- Memory system for long-term game progress
- Multi-modal input processing (audio + visual)

## 🛠️ Technical Architecture

### Simplified System Overview
```
mGBA Emulator ↔ Lua Script ↔ Socket (Port 8888) ↔ AIGameService ↔ LLM API
                                                         ↓
                                              Django Web Interface
                                           (Real-time Chat Monitoring)
```

### Key Components
- **`ai_gba_player/dashboard/ai_game_service.py`**: Main AI service with socket server
- **`ai_gba_player/dashboard/llm_client.py`**: LLM API client for multiple providers
- **`ai_gba_player/ai_gba_player/simple_views.py`**: Web interface and API endpoints
- **`emulator/script.lua`**: mGBA Lua script for game control
- **`games/pokemon_red/`**: Game-specific modules (template for new games)

## 🚀 Getting Started

### Development Setup
```bash
# 1. Clone and setup
git clone <repository-url>
cd LLM-Pokemon-Red
pip install -r requirements.txt

# 2. Setup database
cd ai_gba_player
python manage.py migrate

# 3. Start development server
python manage.py runserver
```

### Testing Your Changes
```bash
# Test AI service
python test_ai_service.py

# Test Django app
cd ai_gba_player
python manage.py test

# Manual integration test
# 1. Start Django server
# 2. Configure via web interface
# 3. Launch mGBA and load script
# 4. Monitor real-time chat interface
```

## 📝 Contribution Guidelines

### Code Style
- Follow Python PEP 8 style guidelines
- Use type hints where appropriate
- Include docstrings for public methods
- Keep functions focused and small

### Adding New Games
1. **Create game directory**: `games/your_game/`
2. **Implement controller**: Extend base game controller
3. **Create prompts**: Game-specific prompt templates
4. **Add knowledge system**: Game state understanding
5. **Test thoroughly**: Verify AI can play effectively

Example structure:
```
games/your_game/
├── __init__.py
├── controller.py       # Game-specific controller
├── knowledge_system.py # Game state management
└── prompt_template.py  # AI prompts for this game
```

### Adding LLM Providers
1. **Extend LLMClient**: Add new provider method in `dashboard/llm_client.py`
2. **Implement API calls**: Follow existing patterns for error handling
3. **Update configuration**: Add provider options to web interface
4. **Test integration**: Verify tool calling and response parsing

### UI Improvements
1. **Enhance templates**: Update HTML templates in `dashboard/templates/`
2. **Add CSS/JS**: Extend styling in `dashboard/static/`
3. **Create API endpoints**: Add new endpoints in `simple_views.py`
4. **Test responsiveness**: Ensure mobile compatibility

## 🧪 Testing

### Unit Tests
```bash
cd ai_gba_player
python manage.py test
```

### Integration Tests
```bash
# Test AI service communication
python test_ai_service.py

# Test with real mGBA connection
# Start Django server, configure settings, launch mGBA, load script
```

### Game-Specific Testing
When adding new games:
1. Test AI can understand game state
2. Verify appropriate actions are taken
3. Check error recovery works
4. Ensure long-term progress is possible

## 📚 Documentation

### Code Documentation
- Document all public methods and classes
- Include examples for complex functionality
- Update CLAUDE.md for architectural changes
- Keep README.md current with new features

### User Documentation
- Update SETUP.md for new installation steps
- Add troubleshooting for new features
- Create guides for new game integration
- Document configuration options

## 🤝 Pull Request Process

1. **Fork the repository** and create a feature branch
2. **Make your changes** following the contribution guidelines
3. **Test thoroughly** including both unit and integration tests
4. **Update documentation** for any new features or changes
5. **Submit pull request** with clear description of changes

### PR Checklist
- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Changes are tested with real mGBA connection
- [ ] Commit messages are clear and descriptive

## 🐛 Bug Reports

When reporting bugs:
1. **Use GitHub Issues** with clear titles
2. **Include system information**: OS, Python version, mGBA version
3. **Provide reproduction steps**: Exact steps to reproduce the issue
4. **Include logs**: Django console output and error messages
5. **Screenshots**: If UI-related, include screenshots

## 💡 Feature Requests

For new features:
1. **Check existing issues** to avoid duplicates
2. **Describe the use case**: Why is this feature needed?
3. **Propose implementation**: How should it work?
4. **Consider alternatives**: What other approaches were considered?

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Code Review**: Submit PRs for feedback on approaches
- **Architecture Questions**: Discuss major changes in issues first

## 🏆 Recognition

Contributors will be recognized in:
- Repository contributors list
- Release notes for significant contributions
- Special mention for new game integrations

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Ready to contribute?** Start with the [SETUP.md](SETUP.md) guide to get your development environment ready!