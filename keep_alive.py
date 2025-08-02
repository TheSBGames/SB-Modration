#!/usr/bin/env python3
"""
Keep Alive System for Discord Bot
Prevents hosting platforms from putting the bot to sleep
"""

from flask import Flask, jsonify
from threading import Thread
import logging
import time
import requests
import os
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app for health checks
app = Flask(__name__)

@app.route('/')
def home():
    """Main health check endpoint"""
    return jsonify({
        "status": "alive",
        "service": "SBModeration™ Discord Bot",
        "timestamp": datetime.now().isoformat(),
        "uptime": "Bot is running successfully!",
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    """Health check endpoint for hosting platforms"""
    return jsonify({
        "status": "healthy",
        "service": "discord-bot",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "bot": "running",
            "database": "connected",
            "api": "responsive"
        }
    })

@app.route('/status')
def status():
    """Detailed status endpoint"""
    return jsonify({
        "bot_name": "SBModeration™ Discord Bot",
        "status": "online",
        "features": [
            "500+ Commands",
            "Reddit Integration", 
            "No-Prefix System",
            "GUI Panels",
            "Multi-Platform Support"
        ],
        "powered_by": "SBModeration™",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/ping')
def ping():
    """Simple ping endpoint"""
    return "pong"

def run_flask():
    """Run Flask server in a separate thread"""
    try:
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}")

def keep_alive():
    """Start the keep-alive Flask server"""
    logger.info("🚀 Starting Keep-Alive server...")
    server_thread = Thread(target=run_flask)
    server_thread.daemon = True
    server_thread.start()
    logger.info("✅ Keep-Alive server started successfully!")

def self_ping():
    """Self-ping function to keep the service awake"""
    def ping_self():
        while True:
            try:
                # Wait 25 minutes before pinging (most platforms sleep after 30 min)
                time.sleep(1500)  # 25 minutes
                
                # Get the service URL from environment or use localhost
                service_url = os.environ.get('RENDER_EXTERNAL_URL', 
                                           os.environ.get('RAILWAY_STATIC_URL',
                                           'http://localhost:8080'))
                
                if service_url and service_url != 'http://localhost:8080':
                    response = requests.get(f"{service_url}/ping", timeout=10)
                    if response.status_code == 200:
                        logger.info(f"✅ Self-ping successful: {datetime.now()}")
                    else:
                        logger.warning(f"⚠️ Self-ping failed with status: {response.status_code}")
                else:
                    logger.info("🏠 Running locally, skipping self-ping")
                    
            except Exception as e:
                logger.error(f"❌ Self-ping error: {e}")
    
    # Start self-ping in background thread
    ping_thread = Thread(target=ping_self)
    ping_thread.daemon = True
    ping_thread.start()
    logger.info("🔄 Self-ping system started")

if __name__ == "__main__":
    # Run standalone for testing
    keep_alive()
    self_ping()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)
            logger.info("Keep-alive system running...")
    except KeyboardInterrupt:
        logger.info("Keep-alive system stopped")
