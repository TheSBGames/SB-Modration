import discord
from discord.ext import commands
from discord import app_commands
import openai
import asyncio
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class ChatGPT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai_client = None
        self.conversation_history = {}
        self.setup_openai()
    
    def setup_openai(self):
        """Setup OpenAI client"""
        try:
            api_key = self.bot.config.get('openai_api_key')
            if api_key:
                self.openai_client = openai.AsyncOpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully!")
            else:
                logger.warning("OpenAI API key not found in configuration!")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    
    async def get_guild_ai_settings(self, guild_id):
        """Get AI settings for a guild"""
        guild_settings = await self.bot.get_guild_settings(guild_id)
        return guild_settings.get('ai_settings', {
            'enabled': False,
            'model': 'gpt-3.5-turbo',
            'max_tokens': 1000,
            'temperature': 0.7,
            'enabled_channels': [],
            'dm_enabled': True,
            'system_prompt': 'You are a helpful Discord bot assistant. Be concise and friendly.'
        })
    
    async def update_guild_ai_settings(self, guild_id, settings):
        """Update AI settings for a guild"""
        await self.bot.update_guild_settings(guild_id, {'ai_settings': settings})
    
    def get_conversation_key(self, user_id, channel_id=None):
        """Get conversation key for history tracking"""
        if channel_id:
            return f"{user_id}_{channel_id}"
        return str(user_id)
    
    async def get_ai_response(self, messages, model='gpt-3.5-turbo', max_tokens=1000, temperature=0.7):
        """Get response from OpenAI API"""
        if not self.openai_client:
            return "❌ OpenAI API is not configured. Please set up your API key."
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"❌ Error generating response: {str(e)}"
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle AI chat in enabled channels"""
        if message.author.bot:
            return
        
        # Handle DMs
        if not message.guild:
            await self.handle_dm_chat(message)
            return
        
        # Handle guild messages
        ai_settings = await self.get_guild_ai_settings(message.guild.id)
        
        if not ai_settings.get('enabled', False):
            return
        
        # Check if channel is enabled for AI
        enabled_channels = ai_settings.get('enabled_channels', [])
        if str(message.channel.id) not in enabled_channels:
            return
        
        # Check if bot is mentioned or replied to
        if self.bot.user not in message.mentions and not (
            message.reference and message.reference.resolved and 
            message.reference.resolved.author == self.bot.user
        ):
            return
        
        await self.handle_ai_chat(message, ai_settings)
    
    async def handle_dm_chat(self, message):
        """Handle AI chat in DMs"""
        try:
            # Get user's preferred settings (you could store per-user preferences)
            ai_settings = {
                'model': 'gpt-3.5-turbo',
                'max_tokens': 1000,
                'temperature': 0.7,
                'system_prompt': 'You are a helpful Discord bot assistant. Be concise and friendly.'
            }
            
            await self.handle_ai_chat(message, ai_settings, is_dm=True)
        except Exception as e:
            logger.error(f"Error handling DM chat: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your message.")
    
    async def handle_ai_chat(self, message, ai_settings, is_dm=False):
        """Handle AI chat conversation"""
        try:
            async with message.channel.typing():
                # Get conversation history
                conv_key = self.get_conversation_key(
                    message.author.id, 
                    None if is_dm else message.channel.id
                )
                
                if conv_key not in self.conversation_history:
                    self.conversation_history[conv_key] = []
                
                # Add system prompt if this is the start of conversation
                messages = []
                if not self.conversation_history[conv_key]:
                    messages.append({
                        "role": "system",
                        "content": ai_settings.get('system_prompt', 'You are a helpful Discord bot assistant.')
                    })
                
                # Add conversation history (last 10 messages to stay within token limits)
                messages.extend(self.conversation_history[conv_key][-10:])
                
                # Clean message content (remove mentions)
                clean_content = message.content
                for mention in message.mentions:
                    clean_content = clean_content.replace(f'<@{mention.id}>', f'@{mention.display_name}')
                    clean_content = clean_content.replace(f'<@!{mention.id}>', f'@{mention.display_name}')
                
                # Add current message
                messages.append({
                    "role": "user",
                    "content": clean_content
                })
                
                # Get AI response
                response = await self.get_ai_response(
                    messages,
                    model=ai_settings.get('model', 'gpt-3.5-turbo'),
                    max_tokens=ai_settings.get('max_tokens', 1000),
                    temperature=ai_settings.get('temperature', 0.7)
                )
                
                # Update conversation history
                self.conversation_history[conv_key].append({
                    "role": "user",
                    "content": clean_content
                })
                self.conversation_history[conv_key].append({
                    "role": "assistant",
                    "content": response
                })
                
                # Keep only last 20 messages in history
                if len(self.conversation_history[conv_key]) > 20:
                    self.conversation_history[conv_key] = self.conversation_history[conv_key][-20:]
                
                # Split long responses
                if len(response) > 2000:
                    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                    for chunk in chunks:
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(response)
                
                # Log the interaction
                await self.log_ai_interaction(message, response, ai_settings.get('model', 'gpt-3.5-turbo'))
                
        except Exception as e:
            logger.error(f"Error in AI chat: {e}")
            await message.channel.send("❌ Sorry, I encountered an error processing your message.")
    
    async def log_ai_interaction(self, message, response, model):
        """Log AI interactions to database"""
        try:
            log_data = {
                "guild_id": str(message.guild.id) if message.guild else None,
                "channel_id": str(message.channel.id),
                "user_id": str(message.author.id),
                "user_message": message.content,
                "ai_response": response,
                "model": model,
                "timestamp": datetime.utcnow()
            }
            await self.bot.db.ai_interactions.insert_one(log_data)
        except Exception as e:
            logger.error(f"Failed to log AI interaction: {e}")
    
    @app_commands.command(name="ai", description="Chat with AI using a specific prompt")
    @app_commands.describe(prompt="Your message to the AI")
    async def ai_chat(self, interaction: discord.Interaction, prompt: str):
        if not self.openai_client:
            await interaction.response.send_message("❌ OpenAI API is not configured!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Get guild AI settings
            ai_settings = await self.get_guild_ai_settings(interaction.guild.id)
            
            messages = [
                {
                    "role": "system",
                    "content": ai_settings.get('system_prompt', 'You are a helpful Discord bot assistant.')
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self.get_ai_response(
                messages,
                model=ai_settings.get('model', 'gpt-3.5-turbo'),
                max_tokens=ai_settings.get('max_tokens', 1000),
                temperature=ai_settings.get('temperature', 0.7)
            )
            
            # Create embed for response
            embed = discord.Embed(
                title="🤖 AI Response",
                description=response[:4000],  # Discord embed limit
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Model: {ai_settings.get('model', 'gpt-3.5-turbo')}")
            
            await interaction.followup.send(embed=embed)
            
            # Log the interaction
            await self.log_ai_interaction(interaction, response, ai_settings.get('model', 'gpt-3.5-turbo'))
            
        except Exception as e:
            logger.error(f"Error in AI command: {e}")
            await interaction.followup.send("❌ Error generating AI response.")
    
    @app_commands.command(name="ai-setup", description="Configure AI settings for this server")
    @app_commands.describe(
        model="AI model to use",
        channel="Channel to enable AI chat in",
        system_prompt="Custom system prompt for the AI"
    )
    @app_commands.choices(model=[
        app_commands.Choice(name="GPT-3.5 Turbo", value="gpt-3.5-turbo"),
        app_commands.Choice(name="GPT-4", value="gpt-4"),
        app_commands.Choice(name="GPT-4 Turbo", value="gpt-4-turbo-preview")
    ])
    async def ai_setup(self, interaction: discord.Interaction, model: str = None, channel: discord.TextChannel = None, system_prompt: str = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        ai_settings = await self.get_guild_ai_settings(interaction.guild.id)
        
        if model:
            ai_settings['model'] = model
        
        if channel:
            if 'enabled_channels' not in ai_settings:
                ai_settings['enabled_channels'] = []
            
            channel_id = str(channel.id)
            if channel_id not in ai_settings['enabled_channels']:
                ai_settings['enabled_channels'].append(channel_id)
        
        if system_prompt:
            ai_settings['system_prompt'] = system_prompt
        
        ai_settings['enabled'] = True
        
        await self.update_guild_ai_settings(interaction.guild.id, ai_settings)
        
        embed = discord.Embed(
            title="🤖 AI Setup Complete",
            description="AI chat has been configured for this server!",
            color=discord.Color.green()
        )
        
        if model:
            embed.add_field(name="Model", value=model, inline=True)
        if channel:
            embed.add_field(name="Enabled Channel", value=channel.mention, inline=True)
        if system_prompt:
            embed.add_field(name="System Prompt", value=system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ai-toggle", description="Toggle AI chat on/off for this server")
    async def ai_toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        ai_settings = await self.get_guild_ai_settings(interaction.guild.id)
        ai_settings['enabled'] = not ai_settings.get('enabled', False)
        
        await self.update_guild_ai_settings(interaction.guild.id, ai_settings)
        
        status = "enabled" if ai_settings['enabled'] else "disabled"
        color = discord.Color.green() if ai_settings['enabled'] else discord.Color.red()
        
        embed = discord.Embed(
            title="🤖 AI Chat Status",
            description=f"AI chat has been {status} for this server.",
            color=color
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ai-channels", description="Manage AI-enabled channels")
    @app_commands.describe(
        action="Add or remove channel",
        channel="Channel to add/remove"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
        app_commands.Choice(name="List", value="list")
    ])
    async def ai_channels(self, interaction: discord.Interaction, action: str, channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        ai_settings = await self.get_guild_ai_settings(interaction.guild.id)
        
        if action == "list":
            enabled_channels = ai_settings.get('enabled_channels', [])
            if not enabled_channels:
                await interaction.response.send_message("❌ No channels are enabled for AI chat!", ephemeral=True)
                return
            
            channel_mentions = []
            for channel_id in enabled_channels:
                ch = interaction.guild.get_channel(int(channel_id))
                if ch:
                    channel_mentions.append(ch.mention)
            
            embed = discord.Embed(
                title="🤖 AI-Enabled Channels",
                description="\n".join(channel_mentions) if channel_mentions else "No valid channels found",
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed)
            return
        
        if not channel:
            await interaction.response.send_message("❌ Please specify a channel!", ephemeral=True)
            return
        
        if 'enabled_channels' not in ai_settings:
            ai_settings['enabled_channels'] = []
        
        channel_id = str(channel.id)
        
        if action == "add":
            if channel_id not in ai_settings['enabled_channels']:
                ai_settings['enabled_channels'].append(channel_id)
                await self.update_guild_ai_settings(interaction.guild.id, ai_settings)
                await interaction.response.send_message(f"✅ Added {channel.mention} to AI-enabled channels!")
            else:
                await interaction.response.send_message(f"❌ {channel.mention} is already AI-enabled!", ephemeral=True)
        
        elif action == "remove":
            if channel_id in ai_settings['enabled_channels']:
                ai_settings['enabled_channels'].remove(channel_id)
                await self.update_guild_ai_settings(interaction.guild.id, ai_settings)
                await interaction.response.send_message(f"✅ Removed {channel.mention} from AI-enabled channels!")
            else:
                await interaction.response.send_message(f"❌ {channel.mention} is not AI-enabled!", ephemeral=True)
    
    @app_commands.command(name="clear-conversation", description="Clear your conversation history with the AI")
    async def clear_conversation(self, interaction: discord.Interaction):
        conv_key = self.get_conversation_key(interaction.user.id, interaction.channel.id)
        
        if conv_key in self.conversation_history:
            del self.conversation_history[conv_key]
            await interaction.response.send_message("✅ Your conversation history has been cleared!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No conversation history found!", ephemeral=True)
    
    @app_commands.command(name="ai-stats", description="View AI usage statistics")
    async def ai_stats(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        try:
            # Get stats from database
            total_interactions = await self.bot.db.ai_interactions.count_documents({
                "guild_id": str(interaction.guild.id)
            })
            
            # Get interactions from last 24 hours
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_interactions = await self.bot.db.ai_interactions.count_documents({
                "guild_id": str(interaction.guild.id),
                "timestamp": {"$gte": yesterday}
            })
            
            # Get top users
            pipeline = [
                {"$match": {"guild_id": str(interaction.guild.id)}},
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]
            
            top_users = await self.bot.db.ai_interactions.aggregate(pipeline).to_list(length=5)
            
            embed = discord.Embed(
                title="🤖 AI Usage Statistics",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Total Interactions", value=str(total_interactions), inline=True)
            embed.add_field(name="Last 24 Hours", value=str(recent_interactions), inline=True)
            embed.add_field(name="Active Conversations", value=str(len(self.conversation_history)), inline=True)
            
            if top_users:
                top_users_text = []
                for i, user_data in enumerate(top_users, 1):
                    user = interaction.guild.get_member(int(user_data['_id']))
                    user_name = user.display_name if user else "Unknown User"
                    top_users_text.append(f"{i}. {user_name}: {user_data['count']} interactions")
                
                embed.add_field(
                    name="Top Users",
                    value="\n".join(top_users_text),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting AI stats: {e}")
            await interaction.response.send_message("❌ Error retrieving AI statistics.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChatGPT(bot))
