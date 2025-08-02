# 🚀 Discord Bot Deployment Guide

This guide covers multiple deployment options for your comprehensive Discord bot.

## 📋 Prerequisites

Before deploying, ensure you have:
- Discord Bot Token
- MongoDB database (local or Atlas)
- OpenAI API Key (for ChatGPT features)
- Spotify API credentials (optional, for music metadata)
- Weather API key (optional, for weather commands)

## 🔧 Quick Setup

### 1. Configuration Validation
Run the configuration validator to check your setup:
```bash
python config_validator.py
```

### 2. Database Setup
Initialize the MongoDB database with proper indexes:
```bash
python setup_database.py
```

### 3. Start the Bot
Use the enhanced startup script:
```bash
python run.py
```

## 🐳 Docker Deployment (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- `.env` file configured with your API keys

### Steps

1. **Clone the repository and navigate to the directory**
2. **Configure your `.env` file** with all required API keys
3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

This will start:
- Discord Bot
- MongoDB database
- Lavalink music server
- Redis cache

### Docker Commands
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f discord-bot

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## 🖥️ Local Development

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup MongoDB
- Install MongoDB locally or use MongoDB Atlas
- Update `MONGODB_URL` in your `.env` file

### 3. Setup Lavalink (for music features)
- Download Lavalink JAR from [GitHub](https://github.com/freyacodes/Lavalink/releases)
- Use the provided `lavalink/application.yml` configuration
- Start Lavalink: `java -jar Lavalink.jar`

### 4. Run the Bot
```bash
python run.py
```

## ☁️ Cloud Deployment

### Heroku Deployment

1. **Create a Heroku app**
2. **Add buildpacks**:
   ```bash
   heroku buildpacks:add heroku/python
   ```

3. **Set environment variables**:
   ```bash
   heroku config:set DISCORD_TOKEN=your_token_here
   heroku config:set MONGODB_URL=your_mongodb_url
   # Add other environment variables
   ```

4. **Deploy**:
   ```bash
   git push heroku main
   ```

### Railway Deployment

1. **Connect your GitHub repository to Railway**
2. **Set environment variables** in Railway dashboard
3. **Deploy automatically** on git push

### DigitalOcean App Platform

1. **Create a new app** from your GitHub repository
2. **Configure environment variables**
3. **Set build and run commands**:
   - Build: `pip install -r requirements.txt`
   - Run: `python run.py`

## 🗄️ Database Options

### MongoDB Atlas (Cloud)
1. Create a free cluster at [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Get connection string
3. Update `MONGODB_URL` in `.env`

### Local MongoDB
1. Install MongoDB Community Edition
2. Start MongoDB service
3. Use `mongodb://localhost:27017` as connection URL

### Docker MongoDB
Included in the `docker-compose.yml` file - no additional setup needed.

## 🎵 Music Server Setup

### Lavalink Options

#### Option 1: Docker (Included)
The `docker-compose.yml` includes Lavalink - no additional setup needed.

#### Option 2: Local Lavalink
1. Download Lavalink JAR
2. Use provided `lavalink/application.yml`
3. Start: `java -jar Lavalink.jar`

#### Option 3: Hosted Lavalink
Use a hosted Lavalink service and update connection details in `.env`.

## 🔒 Security Best Practices

### Environment Variables
- Never commit `.env` files to version control
- Use strong, unique passwords
- Rotate API keys regularly

### Bot Permissions
Grant only necessary permissions:
- **Essential**: Send Messages, Use Slash Commands, Read Message History
- **Moderation**: Manage Messages, Kick Members, Ban Members, Manage Roles
- **Music**: Connect, Speak
- **Advanced**: Administrator (for full functionality)

### Database Security
- Use authentication for MongoDB
- Restrict database access by IP
- Enable SSL/TLS connections

## 📊 Monitoring and Logging

### Log Files
- Bot logs are saved to `bot.log`
- Docker logs: `docker-compose logs -f discord-bot`

### Health Checks
The bot includes health checks for:
- Database connectivity
- API availability
- Service status

### Monitoring Commands
Use admin commands to monitor bot status:
- `/bot-stats` - View bot statistics
- `/guilds` - List all guilds
- `/cogs` - View loaded modules

## 🔄 Updates and Maintenance

### Updating the Bot
1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Update dependencies**:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. **Restart services**:
   ```bash
   # Docker
   docker-compose restart discord-bot
   
   # Local
   # Stop and restart run.py
   ```

### Database Migrations
Run database setup after updates:
```bash
python setup_database.py
```

### Backup Strategy
- **Database**: Regular MongoDB backups
- **Configuration**: Version control for code
- **Logs**: Archive important logs

## 🐛 Troubleshooting

### Common Issues

#### Bot Won't Start
1. Check `.env` file configuration
2. Validate API keys with `python config_validator.py`
3. Check MongoDB connectivity
4. Review logs for specific errors

#### Commands Not Working
1. Ensure bot has necessary permissions
2. Check if slash commands are synced: `/sync`
3. Verify guild-specific settings

#### Music Not Working
1. Check Lavalink server status
2. Verify Lavalink connection settings
3. Ensure bot has voice permissions

#### Database Issues
1. Check MongoDB connection
2. Verify database indexes: `python setup_database.py`
3. Check disk space and memory

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL=DEBUG
```

### Getting Help
1. Check bot logs for error messages
2. Verify all API keys are valid
3. Ensure all services are running
4. Check Discord API status

## 📈 Scaling

### Horizontal Scaling
- Use multiple bot instances with different tokens
- Implement sharding for large bots (10,000+ guilds)
- Load balance across multiple servers

### Vertical Scaling
- Increase server resources (CPU, RAM)
- Optimize database queries
- Use Redis for caching

### Performance Optimization
- Monitor memory usage
- Optimize database indexes
- Use connection pooling
- Implement rate limiting

## 🔐 Production Checklist

Before going live:
- [ ] All API keys configured and validated
- [ ] Database properly set up with indexes
- [ ] Bot permissions configured correctly
- [ ] Monitoring and logging enabled
- [ ] Backup strategy implemented
- [ ] Security best practices followed
- [ ] Health checks working
- [ ] Documentation updated
- [ ] Testing completed in development environment

---

**Need help?** Check the troubleshooting section or review the bot logs for specific error messages.
