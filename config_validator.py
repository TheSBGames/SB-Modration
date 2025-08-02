#!/usr/bin/env python3
"""
Configuration Validator
Validates bot configuration and API keys before startup
"""

import os
import asyncio
import aiohttp
import logging
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import discord

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_required_env_vars(self):
        """Validate required environment variables"""
        required_vars = {
            'DISCORD_TOKEN': 'Discord Bot Token',
            'MONGODB_URL': 'MongoDB Connection URL'
        }
        
        for var, description in required_vars.items():
            if not os.getenv(var):
                self.errors.append(f"Missing required environment variable: {var} ({description})")
    
    def validate_optional_env_vars(self):
        """Validate optional environment variables and warn if missing"""
        optional_vars = {
            'OPENAI_API_KEY': 'OpenAI API Key (required for ChatGPT features)',
            'SPOTIFY_CLIENT_ID': 'Spotify Client ID (required for music metadata)',
            'SPOTIFY_CLIENT_SECRET': 'Spotify Client Secret (required for music metadata)',
            'WEATHER_API_KEY': 'Weather API Key (required for weather commands)',
            'OWNER_IDS': 'Bot Owner IDs (required for admin commands)'
        }
        
        for var, description in optional_vars.items():
            if not os.getenv(var):
                self.warnings.append(f"Optional environment variable not set: {var} ({description})")
    
    async def validate_discord_token(self):
        """Validate Discord bot token"""
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            return
        
        try:
            # Create a temporary bot instance to test the token
            intents = discord.Intents.default()
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                logger.info(f"Discord token validated successfully! Bot: {client.user}")
                await client.close()
            
            await client.start(token)
            
        except discord.LoginFailure:
            self.errors.append("Invalid Discord bot token")
        except Exception as e:
            self.errors.append(f"Error validating Discord token: {e}")
    
    async def validate_mongodb_connection(self):
        """Validate MongoDB connection"""
        mongo_url = os.getenv('MONGODB_URL')
        if not mongo_url:
            return
        
        try:
            client = AsyncIOMotorClient(mongo_url)
            # Test connection
            await client.admin.command('ping')
            server_info = await client.server_info()
            logger.info(f"MongoDB connection validated! Version: {server_info['version']}")
            client.close()
            
        except Exception as e:
            self.errors.append(f"MongoDB connection failed: {e}")
    
    async def validate_openai_api(self):
        """Validate OpenAI API key"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
                
                async with session.get('https://api.openai.com/v1/models', headers=headers) as response:
                    if response.status == 200:
                        logger.info("OpenAI API key validated successfully!")
                    else:
                        self.errors.append(f"OpenAI API validation failed: {response.status}")
                        
        except Exception as e:
            self.errors.append(f"Error validating OpenAI API: {e}")
    
    async def validate_spotify_api(self):
        """Validate Spotify API credentials"""
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            return
        
        try:
            import base64
            
            # Encode credentials
            credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Basic {credentials}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                data = {'grant_type': 'client_credentials'}
                
                async with session.post('https://accounts.spotify.com/api/token', headers=headers, data=data) as response:
                    if response.status == 200:
                        logger.info("Spotify API credentials validated successfully!")
                    else:
                        self.errors.append(f"Spotify API validation failed: {response.status}")
                        
        except Exception as e:
            self.errors.append(f"Error validating Spotify API: {e}")
    
    async def validate_weather_api(self):
        """Validate Weather API key"""
        api_key = os.getenv('WEATHER_API_KEY')
        if not api_key:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://api.openweathermap.org/data/2.5/weather?q=London&appid={api_key}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        logger.info("Weather API key validated successfully!")
                    else:
                        self.errors.append(f"Weather API validation failed: {response.status}")
                        
        except Exception as e:
            self.errors.append(f"Error validating Weather API: {e}")
    
    def validate_owner_ids(self):
        """Validate owner IDs format"""
        owner_ids = os.getenv('OWNER_IDS')
        if not owner_ids:
            return
        
        try:
            ids = [int(id.strip()) for id in owner_ids.split(',') if id.strip()]
            if not ids:
                self.warnings.append("OWNER_IDS is set but contains no valid IDs")
            else:
                logger.info(f"Found {len(ids)} owner ID(s)")
                
        except ValueError:
            self.errors.append("OWNER_IDS contains invalid ID format (must be comma-separated integers)")
    
    async def run_all_validations(self):
        """Run all validation checks"""
        logger.info("Starting configuration validation...")
        
        # Basic validation
        self.validate_required_env_vars()
        self.validate_optional_env_vars()
        self.validate_owner_ids()
        
        # API validations (only if keys are present)
        validation_tasks = []
        
        if os.getenv('DISCORD_TOKEN'):
            validation_tasks.append(self.validate_discord_token())
        
        if os.getenv('MONGODB_URL'):
            validation_tasks.append(self.validate_mongodb_connection())
        
        if os.getenv('OPENAI_API_KEY'):
            validation_tasks.append(self.validate_openai_api())
        
        if os.getenv('SPOTIFY_CLIENT_ID') and os.getenv('SPOTIFY_CLIENT_SECRET'):
            validation_tasks.append(self.validate_spotify_api())
        
        if os.getenv('WEATHER_API_KEY'):
            validation_tasks.append(self.validate_weather_api())
        
        # Run API validations concurrently
        if validation_tasks:
            await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Report results
        self.report_results()
        
        return len(self.errors) == 0
    
    def report_results(self):
        """Report validation results"""
        logger.info("=" * 50)
        logger.info("Configuration Validation Results")
        logger.info("=" * 50)
        
        if self.errors:
            logger.error(f"Found {len(self.errors)} error(s):")
            for error in self.errors:
                logger.error(f"  ❌ {error}")
        
        if self.warnings:
            logger.warning(f"Found {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                logger.warning(f"  ⚠️  {warning}")
        
        if not self.errors and not self.warnings:
            logger.info("✅ All validations passed!")
        elif not self.errors:
            logger.info("✅ All critical validations passed (warnings can be ignored)")
        else:
            logger.error("❌ Configuration validation failed!")
        
        logger.info("=" * 50)

async def main():
    """Main validation function"""
    validator = ConfigValidator()
    success = await validator.run_all_validations()
    
    if not success:
        logger.error("Please fix the configuration errors before starting the bot.")
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
