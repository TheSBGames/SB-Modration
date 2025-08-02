# 🤖 Advanced Discord Bot

A comprehensive, feature-rich Discord bot with moderation, entertainment, utility, and AI capabilities.

## ✨ Features

### 🛡️ Moderation System
- **Commands**: Ban, kick, mute, timeout, warn, purge, lock/unlock channels
- **Logging**: Comprehensive moderation logs with database storage
- **Auto-moderation**: Spam, profanity, link, and external app filtering
- **Customizable**: Per-guild settings and bypass roles

### 🎫 Ticket System
- **Fully Customizable**: Per-guild panels with dynamic category assignment
- **Auto Transcripts**: Automatic transcript generation and storage
- **Support Roles**: Role-based access control
- **User-Friendly**: Interactive buttons and easy management

### 🤖 AutoMod
- **Smart Filtering**: Links, spam, profanity, external apps
- **Bypass Roles**: Configure roles that bypass automod
- **GUI Configuration**: Easy setup through interactive menus
- **Progressive Punishment**: Escalating consequences for repeat offenders

### 🎶 Music System
- **Full Featured**: Play, pause, skip, queue, volume control
- **Autoplay**: Continuous music playback
- **Filters & Effects**: Audio filters and volume control
- **DJ Role Control**: Role-based music permissions
- **Lyrics Support**: Integrated lyrics fetching (API required)

### 🧠 ChatGPT Integration
- **Multiple Models**: GPT-3.5, GPT-4, GPT-4-turbo support
- **Multi-channel**: AI chat in designated channels
- **DM Support**: Private AI conversations
- **Command-based**: Direct AI interaction commands
- **Conversation Memory**: Persistent conversation history

### 📨 ModMail System
- **Embed Replies**: Professional staff responses with identity
- **Modmail Logs**: Complete interaction logging
- **Per-guild Config**: Customizable settings per server
- **Anonymous Option**: Staff can reply anonymously

### 🎉 Fun & Utility
- **Entertainment**: Memes, jokes, 8-ball, polls, weather
- **User Info**: Avatar, userinfo, serverinfo commands
- **Interactive**: Dice rolling, coin flips, random choices
- **Weather**: Real-time weather information

### ⚙️ Admin Tools
- **Custom Embeds**: Interactive embed message creator
- **Code Evaluation**: Python code execution (owner only)
- **Cog Management**: Load, unload, reload cogs dynamically
- **Bot Management**: Presence control, guild management

### 📈 Leveling System
- **XP Tracking**: Message and voice activity XP
- **Rank Cards**: Beautiful rank card generation
- **Leaderboards**: Server-wide ranking system
- **Role Rewards**: Automatic role assignment on level up
- **Per-guild Settings**: Customizable XP rates and settings

### 🎯 No Prefix Mode
- **Owner Control**: Grant users permission to use commands without prefix
- **Flexible Duration**: 10 minutes to permanent permissions
- **Database Tracking**: Persistent permission storage

### 🌍 Multi-language Support
- **Dynamic i18n**: Support for English, Spanish, French, German
- **User Preferences**: Individual language settings
- **Guild Defaults**: Server-wide language configuration
- **Fallback System**: Graceful degradation to English

### 🗃️ Database Features
- **MongoDB Integration**: Persistent data storage
- **Per-guild Settings**: Isolated configuration per server
- **User Preferences**: Individual user customization
- **Comprehensive Logging**: All actions logged with timestamps

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8 or higher
- MongoDB database
- Discord Bot Token
- OpenAI API Key (for ChatGPT features)
- Spotify API credentials (for music metadata)
- Weather API key (for weather commands)

### Installation

1. **Clone or download the bot files**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `.env` file and fill in your credentials:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   MONGODB_URL=mongodb://localhost:27017
   OPENAI_API_KEY=your_openai_api_key_here
   SPOTIFY_CLIENT_ID=your_spotify_client_id_here
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
   WEATHER_API_KEY=your_weather_api_key_here
   OWNER_IDS=123456789012345678,987654321098765432
   ```

4. **Setup MongoDB:**
   - Install MongoDB locally or use MongoDB Atlas
   - Update `MONGODB_URL` in your `.env` file

5. **Setup Lavalink (for music features):**
   - Download Lavalink from [GitHub](https://github.com/freyacodes/Lavalink)
   - Configure `application.yml` with your settings
   - Update Lavalink settings in `.env`

6. **Run the bot:**
   ```bash
   python main.py
   ```

### Discord Bot Setup

1. **Create a Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the bot token to your `.env` file

2. **Bot Permissions:**
   - Administrator (recommended for full functionality)
   - Or specific permissions:
     - Manage Server
     - Manage Channels
     - Manage Messages
     - Manage Roles
     - Ban Members
     - Kick Members
     - Moderate Members
     - Send Messages
     - Use Slash Commands
     - Connect to Voice
     - Speak in Voice

3. **Invite the bot:**
   - Use Discord's OAuth2 URL generator
   - Select "bot" and "applications.commands" scopes
   - Select required permissions
   - Invite to your server

## 📋 Commands Overview

### Moderation Commands
- `/ban` - Ban a user from the server
- `/kick` - Kick a user from the server
- `/timeout` - Timeout a user
- `/warn` - Warn a user
- `/warnings` - View user warnings
- `/purge` - Delete multiple messages
- `/lock` - Lock a channel
- `/unlock` - Unlock a channel

### Ticket Commands
- `/ticket-setup` - Configure ticket system
- `/ticket-panel` - Create ticket creation panel
- `/ticket-add` - Add user to ticket
- `/ticket-remove` - Remove user from ticket
- `/modmail-close` - Close current ticket

### AutoMod Commands
- `/automod` - Configure AutoMod settings
- `/automod-toggle` - Toggle AutoMod on/off
- `/automod-whitelist` - Add domain to whitelist

### Music Commands
- `/play` - Play a song or playlist
- `/pause` - Pause current track
- `/resume` - Resume playback
- `/skip` - Skip current track
- `/stop` - Stop playback and disconnect
- `/queue` - View music queue
- `/nowplaying` - Show current track info
- `/volume` - Set playback volume
- `/shuffle` - Shuffle queue
- `/clear` - Clear music queue
- `/lyrics` - Get lyrics for current track

### AI Commands
- `/ai` - Chat with AI
- `/ai-setup` - Configure AI settings
- `/ai-toggle` - Toggle AI chat
- `/ai-channels` - Manage AI-enabled channels
- `/clear-conversation` - Clear AI conversation history

### Fun Commands
- `/meme` - Get a random meme
- `/joke` - Get a random joke
- `/8ball` - Ask the magic 8-ball
- `/poll` - Create a poll
- `/weather` - Get weather information
- `/avatar` - Get user's avatar
- `/userinfo` - Get user information
- `/serverinfo` - Get server information
- `/coinflip` - Flip a coin
- `/dice` - Roll dice
- `/choose` - Choose from options

### Admin Commands (Owner Only)
- `/embed` - Create custom embed
- `/eval` - Evaluate Python code
- `/reload` - Reload a cog
- `/load` - Load a cog
- `/unload` - Unload a cog
- `/sync` - Sync slash commands
- `/presence` - Change bot presence
- `/shutdown` - Shutdown the bot

### Leveling Commands
- `/rank` - View your rank
- `/leaderboard` - View server leaderboard
- `/leveling-setup` - Configure leveling system
- `/leveling-toggle` - Toggle leveling on/off
- `/level-role` - Set role reward for level

### Utility Commands
- `/help` - Show help menu
- `/language` - Set your language preference
- `/server-language` - Set server default language
- `/no-prefix` - Grant no-prefix permissions (Owner only)

## 🔧 Configuration

### Per-Guild Settings
Each server can customize:
- Command prefixes
- Language preferences
- Feature toggles (moderation, music, leveling, etc.)
- Channel configurations
- Role assignments
- AutoMod settings
- Ticket system setup
- AI chat settings

### User Preferences
Users can set:
- Language preferences
- Individual settings that override server defaults

## 🛠️ Development

### Project Structure
```
├── main.py              # Main bot file
├── requirements.txt     # Python dependencies
├── .env                # Environment variables
├── README.md           # This file
└── cogs/               # Bot modules
    ├── moderation.py   # Moderation commands
    ├── tickets.py      # Ticket system
    ├── automod.py      # Auto-moderation
    ├── music.py        # Music system
    ├── chatgpt.py      # AI integration
    ├── modmail.py      # ModMail system
    ├── fun.py          # Fun commands
    ├── admin.py        # Admin tools
    ├── leveling.py     # Leveling system
    └── utility.py      # Utility commands
```

### Adding New Features
1. Create new cog in `cogs/` directory
2. Follow the existing cog structure
3. Add database models if needed
4. Update help command with new commands
5. Test thoroughly before deployment

## 📊 Database Schema

The bot uses MongoDB with the following collections:
- `guilds` - Server settings and configuration
- `users` - User preferences and data
- `modlogs` - Moderation action logs
- `tickets` - Ticket system data
- `transcripts` - Ticket transcripts
- `warnings` - User warnings
- `automod_violations` - AutoMod violation logs
- `modmails` - ModMail conversations
- `user_levels` - Leveling system data
- `ai_interactions` - AI chat logs
- `no_prefix_permissions` - No-prefix permissions

## 🤝 Support

For support, feature requests, or bug reports:
1. Check the documentation above
2. Review the code comments
3. Test in a development environment first
4. Ensure all dependencies are properly installed

## 📝 License

This project is provided as-is for educational and personal use.

## 🙏 Acknowledgments

- Discord.py library
- OpenAI API
- MongoDB
- Lavalink music server
- Various API providers (weather, memes, etc.)

---

**Note**: Remember to keep your API keys and tokens secure. Never commit them to version control!
