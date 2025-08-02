import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from keep_alive import keep_alive, self_ping
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        # Database connection
        self.db_client = None
        self.db = None
        
        # Bot configuration
        self.config = {}
        self.guild_settings = {}
        self.no_prefix_users = {}
        
        # Load configuration from environment
        self.load_env_config()
    
    def load_env_config(self):
        """Load bot configuration from environment variables"""
        self.config = {
            'discord_token': os.getenv('DISCORD_TOKEN'),
            'mongodb_url': os.getenv('MONGODB_URL', 'mongodb://localhost:27017'),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'spotify_client_id': os.getenv('SPOTIFY_CLIENT_ID'),
            'spotify_client_secret': os.getenv('SPOTIFY_CLIENT_SECRET'),
            'weather_api_key': os.getenv('WEATHER_API_KEY'),
            'owner_ids': [int(id.strip()) for id in os.getenv('OWNER_IDS', '').split(',') if id.strip()],
            'default_prefix': os.getenv('DEFAULT_PREFIX', '!'),
            'bot_status': os.getenv('BOT_STATUS', 'online'),
            'activity_type': os.getenv('ACTIVITY_TYPE', 'watching'),
            'activity_name': os.getenv('ACTIVITY_NAME', 'over the server | !help'),
            'lavalink_host': os.getenv('LAVALINK_HOST', 'localhost'),
            'lavalink_port': int(os.getenv('LAVALINK_PORT', '2333')),
            'lavalink_password': os.getenv('LAVALINK_PASSWORD', 'youshallnotpass'),
            'db_name': os.getenv('DB_NAME', 'discord_bot')
        }
        
        # Validate required environment variables
        if not self.config['discord_token']:
            logger.error("DISCORD_TOKEN not found in .env file!")
        if not self.config['mongodb_url']:
            logger.error("MONGODB_URL not found in .env file!")
    
    async def get_prefix(self, bot, message):
        """Dynamic prefix handler with no-prefix mode support"""
        if not message.guild:
            return commands.when_mentioned_or("!")(bot, message)
        
        # Check if user has no-prefix permission
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        
        if guild_id in self.no_prefix_users and user_id in self.no_prefix_users[guild_id]:
            # Check if permission is still valid
            perm_data = self.no_prefix_users[guild_id][user_id]
            if perm_data['expires'] > datetime.now().timestamp():
                return commands.when_mentioned_or("!", "")(bot, message)
            else:
                # Remove expired permission
                del self.no_prefix_users[guild_id][user_id]
        
        # Get guild-specific prefix from database
        guild_data = await self.get_guild_settings(guild_id)
        prefix = guild_data.get('prefix', '!')
        
        return commands.when_mentioned_or(prefix)(bot, message)
    
    async def setup_database(self):
        """Initialize MongoDB connection"""
        try:
            mongo_url = self.config.get('mongodb_url', 'mongodb://localhost:27017')
            db_name = self.config.get('db_name', 'discord_bot')
            self.db_client = AsyncIOMotorClient(mongo_url)
            self.db = self.db_client[db_name]
            logger.info(f"Connected to MongoDB successfully! Database: {db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
    
    async def get_guild_settings(self, guild_id):
        """Get guild-specific settings from database"""
        if not self.db:
            return {}
        
        guild_data = await self.db.guilds.find_one({"guild_id": str(guild_id)})
        if not guild_data:
            # Create default settings
            default_settings = {
                "guild_id": str(guild_id),
                "prefix": "!",
                "language": "en",
                "modlog_channel": None,
                "automod_enabled": True,
                "leveling_enabled": True,
                "music_enabled": True,
                "tickets_enabled": True
            }
            await self.db.guilds.insert_one(default_settings)
            return default_settings
        
        return guild_data
    
    async def update_guild_settings(self, guild_id, settings):
        """Update guild settings in database"""
        if not self.db:
            return
        
        await self.db.guilds.update_one(
            {"guild_id": str(guild_id)},
            {"$set": settings},
            upsert=True
        )
    
    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        # Start keep-alive system
        keep_alive()
        self_ping()
        logger.info("🚀 Keep-alive system activated!")
        
        await self.setup_database()
        await self.load_cogs()
        logger.info("Bot setup completed!")
    
    async def load_cogs(self):
        """Load all cogs"""
        cogs_to_load = [
            'cogs.moderation',
            'cogs.tickets',
            'cogs.automod',
            'cogs.music',
            'cogs.chatgpt',
            'cogs.modmail',
            'cogs.fun',
            'cogs.admin',
            'cogs.leveling',
            'cogs.utility'
        ]
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}: {e}")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over the server | !help"
            )
        )
    
    async def on_guild_join(self, guild):
        """Called when bot joins a guild"""
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        
        # Create default guild settings
        await self.get_guild_settings(guild.id)
    
    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
            return
        
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions to execute this command!")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
            return
        
        logger.error(f"Command error in {ctx.command}: {error}")
        await ctx.send("❌ An error occurred while executing the command.")

# Create bot instance
bot = AdvancedBot()

async def main():
    """Main function to run the bot"""
    try:
        # Check if token exists
        token = bot.config.get('discord_token')
        if not token:
            logger.error("Discord token not found in config.json!")
            return
        
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        if bot.db_client:
            bot.db_client.close()

if __name__ == "__main__":
    asyncio.run(main())
