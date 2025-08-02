#!/usr/bin/env python3
"""
Discord Bot Startup Script
Handles graceful startup, error recovery, and automatic restarts
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def run_bot():
    """Run the bot with error handling and auto-restart"""
    from main import bot, main
    
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Starting bot (attempt {retry_count + 1}/{max_retries})")
            await main()
            break  # If we get here, the bot shut down normally
            
        except KeyboardInterrupt:
            logger.info("Bot shutdown requested by user")
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Bot crashed with error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if retry_count < max_retries:
                wait_time = min(60 * retry_count, 300)  # Max 5 minutes
                logger.info(f"Restarting in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("Max retries reached. Bot will not restart automatically.")
                break
    
    # Cleanup
    try:
        if not bot.is_closed():
            await bot.close()
    except:
        pass

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['DISCORD_TOKEN', 'MONGODB_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        return False
    
    return True

def main():
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("Discord Bot Starting Up")
    logger.info(f"Start time: {datetime.now()}")
    logger.info("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run the bot
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
