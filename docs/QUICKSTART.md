# ⚡ Quick Start Guide - AI GBA Player

Get AI GBA Player running in under 5 minutes!

## 🚀 Fastest Setup

### 1. Prerequisites
- Python 3.11+
- mGBA emulator
- GBA ROM file
- LLM API key (Google Gemini recommended)

### 2. Install & Run
```bash
# Clone and install
git clone <repository-url>
cd LLM-Pokemon-Red
pip install -r requirements.txt

# Setup database
cd ai_gba_player
python manage.py migrate

# Start web interface
python manage.py runserver
```

### 3. Configure (2 minutes)
1. Open **http://localhost:8000**
2. **ROM Configuration**: Set path to your `.gba` file
3. **AI Settings**: Choose "Google Gemini" and enter API key
4. Click **"Save Config"** for both sections

### 4. Launch & Play
1. Click **"Launch mGBA"** (or start mGBA manually)
2. Click **"Reset mGBA Connection"**
3. In mGBA: **Tools → Script Viewer → Load** `emulator/script.lua`
4. **Watch the AI play in real-time chat!** 🎮

## 📱 What You'll See

The chat interface shows:
- 📤 **Screenshots sent to AI** with game position
- 🤖 **AI reasoning and decisions** in real-time
- 🎮 **Button actions** taken by the AI
- 📊 **Connection status** and system health

## 🔧 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| **mGBA won't launch** | Install mGBA or set correct path in configuration |
| **No screenshots** | Ensure ROM is loaded and Lua script is running |
| **AI errors** | Check API key is valid and has quota |
| **Port 8888 busy** | Stop any other AI services running |

## 🎯 Next Steps

- **Try different games**: Any GBA ROM works!
- **Experiment with settings**: Adjust decision cooldown for different speeds
- **Monitor AI decisions**: Watch how it learns and adapts
- **Add new LLM providers**: Try OpenAI or Anthropic

## 📚 Full Documentation

- **[README.md](README.md)**: Complete feature overview
- **[SETUP.md](SETUP.md)**: Detailed installation guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: How to contribute

---

**🎮 Ready to watch AI play GBA games?** 
`cd ai_gba_player && python manage.py runserver` → http://localhost:8000