#!/usr/bin/env python3
"""
Database Setup and Migration Script
Sets up MongoDB collections and indexes for optimal performance
"""

import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_database():
    """Setup MongoDB collections and indexes"""
    try:
        # Connect to MongoDB
        mongo_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
        db_name = os.getenv('DB_NAME', 'discord_bot')
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        logger.info(f"Connected to MongoDB: {db_name}")
        
        # Create indexes for better performance
        collections_indexes = {
            'guilds': [
                ('guild_id', 1),  # Unique index on guild_id
            ],
            'user_levels': [
                ('guild_id', 1),
                ('user_id', 1),
                ('xp', -1),  # For leaderboards
                [('guild_id', 1), ('user_id', 1)],  # Compound index
            ],
            'modlogs': [
                ('guild_id', 1),
                ('timestamp', -1),
                ('moderator_id', 1),
                ('target_id', 1),
            ],
            'tickets': [
                ('guild_id', 1),
                ('user_id', 1),
                ('channel_id', 1),
                ('status', 1),
                ('created_at', -1),
            ],
            'warnings': [
                ('guild_id', 1),
                ('user_id', 1),
                ('timestamp', -1),
                [('guild_id', 1), ('user_id', 1)],
            ],
            'automod_violations': [
                ('guild_id', 1),
                ('user_id', 1),
                ('timestamp', -1),
            ],
            'modmails': [
                ('guild_id', 1),
                ('user_id', 1),
                ('channel_id', 1),
                ('status', 1),
            ],
            'ai_interactions': [
                ('guild_id', 1),
                ('user_id', 1),
                ('timestamp', -1),
            ],
            'no_prefix_permissions': [
                ('guild_id', 1),
                ('user_id', 1),
                ('expires', 1),
                [('guild_id', 1), ('user_id', 1)],
            ],
            'user_preferences': [
                ('user_id', 1),  # Unique index
            ],
            'transcripts': [
                ('guild_id', 1),
                ('ticket_number', 1),
                ('created_at', -1),
            ],
            'level_logs': [
                ('guild_id', 1),
                ('user_id', 1),
                ('timestamp', -1),
            ],
            'modmail_logs': [
                ('guild_id', 1),
                ('timestamp', -1),
            ]
        }
        
        # Create collections and indexes
        for collection_name, indexes in collections_indexes.items():
            collection = db[collection_name]
            
            # Create indexes
            for index in indexes:
                if isinstance(index, list):
                    # Compound index
                    await collection.create_index(index)
                    logger.info(f"Created compound index on {collection_name}: {index}")
                else:
                    # Single field index
                    await collection.create_index(index)
                    logger.info(f"Created index on {collection_name}.{index[0] if isinstance(index, tuple) else index}")
        
        # Create unique indexes where needed
        await db.guilds.create_index('guild_id', unique=True)
        await db.user_preferences.create_index('user_id', unique=True)
        await db.no_prefix_permissions.create_index([('guild_id', 1), ('user_id', 1)], unique=True)
        
        logger.info("Database setup completed successfully!")
        
        # Test connection
        server_info = await client.server_info()
        logger.info(f"MongoDB version: {server_info['version']}")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

async def create_default_guild_settings(guild_id):
    """Create default settings for a new guild"""
    default_settings = {
        "guild_id": str(guild_id),
        "prefix": "!",
        "language": "en",
        "modlog_channel": None,
        "automod_enabled": True,
        "leveling_enabled": True,
        "music_enabled": True,
        "tickets_enabled": True,
        "automod_settings": {
            "enabled": True,
            "link_filter": {"enabled": False, "whitelist": []},
            "spam_filter": {"enabled": False, "max_messages": 5, "time_window": 10},
            "profanity_filter": {"enabled": False},
            "apps_filter": {"enabled": False},
            "bypass_roles": []
        },
        "ticket_settings": {
            "enabled": True,
            "category_id": None,
            "support_roles": [],
            "log_channel": None
        },
        "music_settings": {
            "enabled": True,
            "dj_role": None,
            "max_volume": 100
        },
        "leveling_settings": {
            "enabled": True,
            "xp_per_message": 15,
            "xp_per_minute_voice": 10,
            "level_up_channel": None,
            "level_roles": {},
            "xp_multiplier": 1.0,
            "ignored_channels": [],
            "ignored_roles": []
        },
        "ai_settings": {
            "enabled": False,
            "model": "gpt-3.5-turbo",
            "max_tokens": 1000,
            "temperature": 0.7,
            "enabled_channels": [],
            "dm_enabled": True,
            "system_prompt": "You are a helpful Discord bot assistant. Be concise and friendly."
        },
        "modmail_settings": {
            "enabled": False,
            "category_id": None,
            "staff_roles": [],
            "log_channel": None,
            "anonymous_staff": False
        }
    }
    
    return default_settings

if __name__ == "__main__":
    asyncio.run(setup_database())
