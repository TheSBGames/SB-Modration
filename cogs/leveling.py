import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from datetime import datetime, timedelta
import logging
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
import math

logger = logging.getLogger(__name__)

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}  # user_id: last_xp_time
        self.voice_tracking = {}  # user_id: join_time
    
    async def get_leveling_settings(self, guild_id):
        """Get leveling settings for a guild"""
        guild_settings = await self.bot.get_guild_settings(guild_id)
        return guild_settings.get('leveling_settings', {
            'enabled': True,
            'xp_per_message': 15,
            'xp_per_minute_voice': 10,
            'level_up_channel': None,
            'level_roles': {},  # level: role_id
            'xp_multiplier': 1.0,
            'ignored_channels': [],
            'ignored_roles': []
        })
    
    async def update_leveling_settings(self, guild_id, settings):
        """Update leveling settings for a guild"""
        await self.bot.update_guild_settings(guild_id, {'leveling_settings': settings})
    
    def calculate_level(self, xp):
        """Calculate level from XP using a formula"""
        # Formula: level = floor(sqrt(xp / 100))
        return int(math.sqrt(xp / 100))
    
    def calculate_xp_for_level(self, level):
        """Calculate XP required for a specific level"""
        return level * level * 100
    
    async def get_user_data(self, guild_id, user_id):
        """Get user's leveling data"""
        user_data = await self.bot.db.user_levels.find_one({
            "guild_id": str(guild_id),
            "user_id": str(user_id)
        })
        
        if not user_data:
            # Create new user data
            user_data = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "xp": 0,
                "level": 0,
                "total_messages": 0,
                "voice_time": 0,
                "last_message": None,
                "created_at": datetime.utcnow()
            }
            await self.bot.db.user_levels.insert_one(user_data)
        
        return user_data
    
    async def add_xp(self, guild_id, user_id, xp_amount, source="message"):
        """Add XP to a user and check for level up"""
        user_data = await self.get_user_data(guild_id, user_id)
        
        old_level = user_data['level']
        new_xp = user_data['xp'] + xp_amount
        new_level = self.calculate_level(new_xp)
        
        # Update user data
        update_data = {
            "xp": new_xp,
            "level": new_level,
            "last_message": datetime.utcnow()
        }
        
        if source == "message":
            update_data["total_messages"] = user_data.get('total_messages', 0) + 1
        elif source == "voice":
            update_data["voice_time"] = user_data.get('voice_time', 0) + 1
        
        await self.bot.db.user_levels.update_one(
            {"guild_id": str(guild_id), "user_id": str(user_id)},
            {"$set": update_data}
        )
        
        # Check for level up
        if new_level > old_level:
            await self.handle_level_up(guild_id, user_id, old_level, new_level)
        
        return new_level > old_level
    
    async def handle_level_up(self, guild_id, user_id, old_level, new_level):
        """Handle level up events"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            user = guild.get_member(user_id)
            if not user:
                return
            
            leveling_settings = await self.get_leveling_settings(guild_id)
            
            # Send level up message
            level_up_channel_id = leveling_settings.get('level_up_channel')
            if level_up_channel_id:
                channel = guild.get_channel(int(level_up_channel_id))
            else:
                # Try to find a general channel
                channel = discord.utils.get(guild.text_channels, name='general') or guild.system_channel
            
            if channel:
                embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=f"{user.mention} has reached **Level {new_level}**!",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
                
                try:
                    await channel.send(embed=embed)
                except:
                    pass  # Channel might not have send permissions
            
            # Handle level roles
            level_roles = leveling_settings.get('level_roles', {})
            for level_req, role_id in level_roles.items():
                try:
                    level_req = int(level_req)
                    if new_level >= level_req and old_level < level_req:
                        role = guild.get_role(int(role_id))
                        if role and role not in user.roles:
                            await user.add_roles(role, reason=f"Level up to {new_level}")
                except:
                    continue
            
            # Log level up
            await self.bot.db.level_logs.insert_one({
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "old_level": old_level,
                "new_level": new_level,
                "timestamp": datetime.utcnow()
            })
            
        except Exception as e:
            logger.error(f"Error handling level up: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle XP gain from messages"""
        if message.author.bot or not message.guild:
            return
        
        guild_id = message.guild.id
        user_id = message.author.id
        
        # Get leveling settings
        leveling_settings = await self.get_leveling_settings(guild_id)
        
        if not leveling_settings.get('enabled', True):
            return
        
        # Check ignored channels
        ignored_channels = leveling_settings.get('ignored_channels', [])
        if str(message.channel.id) in ignored_channels:
            return
        
        # Check ignored roles
        ignored_roles = leveling_settings.get('ignored_roles', [])
        if any(str(role.id) in ignored_roles for role in message.author.roles):
            return
        
        # Check cooldown (prevent spam)
        now = datetime.utcnow()
        cooldown_key = f"{guild_id}_{user_id}"
        
        if cooldown_key in self.xp_cooldowns:
            last_xp_time = self.xp_cooldowns[cooldown_key]
            if (now - last_xp_time).total_seconds() < 60:  # 1 minute cooldown
                return
        
        self.xp_cooldowns[cooldown_key] = now
        
        # Calculate XP
        base_xp = leveling_settings.get('xp_per_message', 15)
        multiplier = leveling_settings.get('xp_multiplier', 1.0)
        xp_gain = int(random.randint(base_xp - 5, base_xp + 5) * multiplier)
        
        # Add XP
        await self.add_xp(guild_id, user_id, xp_gain, "message")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle XP gain from voice activity"""
        if member.bot:
            return
        
        guild_id = member.guild.id
        user_id = member.id
        
        # Get leveling settings
        leveling_settings = await self.get_leveling_settings(guild_id)
        
        if not leveling_settings.get('enabled', True):
            return
        
        now = datetime.utcnow()
        
        # User joined a voice channel
        if before.channel is None and after.channel is not None:
            self.voice_tracking[user_id] = now
        
        # User left a voice channel
        elif before.channel is not None and after.channel is None:
            if user_id in self.voice_tracking:
                join_time = self.voice_tracking[user_id]
                time_spent = (now - join_time).total_seconds() / 60  # minutes
                
                if time_spent >= 1:  # At least 1 minute
                    xp_per_minute = leveling_settings.get('xp_per_minute_voice', 10)
                    multiplier = leveling_settings.get('xp_multiplier', 1.0)
                    xp_gain = int(time_spent * xp_per_minute * multiplier)
                    
                    await self.add_xp(guild_id, user_id, xp_gain, "voice")
                
                del self.voice_tracking[user_id]
    
    @app_commands.command(name="rank", description="View your or someone's rank")
    @app_commands.describe(user="User to check rank for")
    async def rank(self, interaction: discord.Interaction, user: discord.Member = None):
        target_user = user or interaction.user
        
        if target_user.bot:
            await interaction.response.send_message("❌ Bots don't have ranks!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            user_data = await self.get_user_data(interaction.guild.id, target_user.id)
            
            # Get user's rank in the server
            pipeline = [
                {"$match": {"guild_id": str(interaction.guild.id)}},
                {"$sort": {"xp": -1}},
                {"$group": {
                    "_id": None,
                    "users": {"$push": {"user_id": "$user_id", "xp": "$xp", "level": "$level"}}
                }}
            ]
            
            result = await self.bot.db.user_levels.aggregate(pipeline).to_list(length=1)
            
            rank = 1
            if result and result[0]['users']:
                for i, user_info in enumerate(result[0]['users'], 1):
                    if user_info['user_id'] == str(target_user.id):
                        rank = i
                        break
            
            # Create rank card
            rank_card = await self.create_rank_card(target_user, user_data, rank)
            
            file = discord.File(rank_card, filename="rank.png")
            await interaction.followup.send(file=file)
            
        except Exception as e:
            logger.error(f"Error in rank command: {e}")
            await interaction.followup.send("❌ Error generating rank card.")
    
    async def create_rank_card(self, user, user_data, rank):
        """Create a rank card image"""
        try:
            # Create image
            width, height = 800, 240
            img = Image.new('RGB', (width, height), color=(47, 49, 54))
            draw = ImageDraw.Draw(img)
            
            # Try to load fonts (fallback to default if not available)
            try:
                title_font = ImageFont.truetype("arial.ttf", 36)
                text_font = ImageFont.truetype("arial.ttf", 24)
                small_font = ImageFont.truetype("arial.ttf", 18)
            except:
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Draw background gradient
            for i in range(height):
                r = int(47 + (i / height) * 20)
                g = int(49 + (i / height) * 20)
                b = int(54 + (i / height) * 20)
                draw.line([(0, i), (width, i)], fill=(r, g, b))
            
            # User avatar (placeholder circle)
            avatar_size = 120
            avatar_x, avatar_y = 30, 60
            draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size], 
                        fill=(114, 137, 218), outline=(255, 255, 255), width=3)
            
            # User info
            username = user.display_name[:20]  # Limit length
            draw.text((180, 70), username, fill=(255, 255, 255), font=title_font)
            
            # Level and XP info
            level = user_data['level']
            current_xp = user_data['xp']
            xp_for_current = self.calculate_xp_for_level(level)
            xp_for_next = self.calculate_xp_for_level(level + 1)
            xp_progress = current_xp - xp_for_current
            xp_needed = xp_for_next - xp_for_current
            
            draw.text((180, 120), f"Level {level}", fill=(255, 255, 255), font=text_font)
            draw.text((180, 150), f"Rank #{rank}", fill=(255, 255, 255), font=text_font)
            
            # XP Progress bar
            bar_x, bar_y = 180, 190
            bar_width, bar_height = 400, 20
            
            # Background bar
            draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 
                         fill=(32, 34, 37), outline=(114, 137, 218))
            
            # Progress bar
            if xp_needed > 0:
                progress_width = int((xp_progress / xp_needed) * bar_width)
                draw.rectangle([bar_x, bar_y, bar_x + progress_width, bar_y + bar_height], 
                             fill=(114, 137, 218))
            
            # XP text
            xp_text = f"{xp_progress}/{xp_needed} XP"
            draw.text((bar_x + bar_width + 10, bar_y), xp_text, fill=(255, 255, 255), font=small_font)
            
            # Save to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            logger.error(f"Error creating rank card: {e}")
            # Return a simple text-based fallback
            fallback = io.BytesIO()
            fallback.write(b"Rank card generation failed")
            fallback.seek(0)
            return fallback
    
    @app_commands.command(name="leaderboard", description="View the server leaderboard")
    @app_commands.describe(page="Page number (default: 1)")
    async def leaderboard(self, interaction: discord.Interaction, page: int = 1):
        if page < 1:
            page = 1
        
        await interaction.response.defer()
        
        try:
            # Get top users
            skip = (page - 1) * 10
            users = await self.bot.db.user_levels.find(
                {"guild_id": str(interaction.guild.id)}
            ).sort("xp", -1).skip(skip).limit(10).to_list(length=10)
            
            if not users:
                await interaction.followup.send("❌ No users found on this page!")
                return
            
            embed = discord.Embed(
                title="🏆 Server Leaderboard",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            
            leaderboard_text = ""
            for i, user_data in enumerate(users, start=skip + 1):
                user = interaction.guild.get_member(int(user_data['user_id']))
                if user:
                    username = user.display_name[:20]
                    level = user_data['level']
                    xp = user_data['xp']
                    
                    # Medal emojis for top 3
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"
                    else:
                        medal = f"#{i}"
                    
                    leaderboard_text += f"{medal} **{username}** - Level {level} ({xp:,} XP)\n"
            
            embed.description = leaderboard_text
            embed.set_footer(text=f"Page {page} • Use /leaderboard <page> to view other pages")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await interaction.followup.send("❌ Error generating leaderboard.")
    
    @app_commands.command(name="leveling-setup", description="Setup leveling system")
    @app_commands.describe(
        xp_per_message="XP gained per message",
        xp_per_minute_voice="XP gained per minute in voice",
        level_up_channel="Channel for level up announcements"
    )
    async def leveling_setup(self, interaction: discord.Interaction, xp_per_message: int = None, xp_per_minute_voice: int = None, level_up_channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        leveling_settings = await self.get_leveling_settings(interaction.guild.id)
        
        if xp_per_message is not None:
            if xp_per_message < 1 or xp_per_message > 100:
                await interaction.response.send_message("❌ XP per message must be between 1 and 100!", ephemeral=True)
                return
            leveling_settings['xp_per_message'] = xp_per_message
        
        if xp_per_minute_voice is not None:
            if xp_per_minute_voice < 1 or xp_per_minute_voice > 100:
                await interaction.response.send_message("❌ XP per minute voice must be between 1 and 100!", ephemeral=True)
                return
            leveling_settings['xp_per_minute_voice'] = xp_per_minute_voice
        
        if level_up_channel:
            leveling_settings['level_up_channel'] = str(level_up_channel.id)
        
        await self.update_leveling_settings(interaction.guild.id, leveling_settings)
        
        embed = discord.Embed(
            title="📈 Leveling Setup Complete",
            description="Leveling system has been configured!",
            color=discord.Color.green()
        )
        
        if xp_per_message is not None:
            embed.add_field(name="XP per Message", value=str(xp_per_message), inline=True)
        if xp_per_minute_voice is not None:
            embed.add_field(name="XP per Minute (Voice)", value=str(xp_per_minute_voice), inline=True)
        if level_up_channel:
            embed.add_field(name="Level Up Channel", value=level_up_channel.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leveling-toggle", description="Toggle leveling system on/off")
    async def leveling_toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        leveling_settings = await self.get_leveling_settings(interaction.guild.id)
        leveling_settings['enabled'] = not leveling_settings.get('enabled', True)
        
        await self.update_leveling_settings(interaction.guild.id, leveling_settings)
        
        status = "enabled" if leveling_settings['enabled'] else "disabled"
        color = discord.Color.green() if leveling_settings['enabled'] else discord.Color.red()
        
        embed = discord.Embed(
            title="📈 Leveling System Status",
            description=f"Leveling system has been {status} for this server.",
            color=color
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="level-role", description="Set a role reward for reaching a level")
    @app_commands.describe(level="Level requirement", role="Role to give")
    async def level_role(self, interaction: discord.Interaction, level: int, role: discord.Role):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        if level < 1 or level > 1000:
            await interaction.response.send_message("❌ Level must be between 1 and 1000!", ephemeral=True)
            return
        
        leveling_settings = await self.get_leveling_settings(interaction.guild.id)
        
        if 'level_roles' not in leveling_settings:
            leveling_settings['level_roles'] = {}
        
        leveling_settings['level_roles'][str(level)] = str(role.id)
        
        await self.update_leveling_settings(interaction.guild.id, leveling_settings)
        
        embed = discord.Embed(
            title="📈 Level Role Set",
            description=f"Users who reach **Level {level}** will receive the {role.mention} role!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
