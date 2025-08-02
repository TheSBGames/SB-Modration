import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def log_action(self, guild_id, action, moderator, target, reason=None, duration=None):
        """Log moderation actions to database and modlog channel"""
        try:
            # Save to database
            log_data = {
                "guild_id": str(guild_id),
                "action": action,
                "moderator_id": str(moderator.id),
                "moderator_name": str(moderator),
                "target_id": str(target.id) if hasattr(target, 'id') else None,
                "target_name": str(target),
                "reason": reason,
                "duration": duration,
                "timestamp": datetime.utcnow()
            }
            await self.bot.db.modlogs.insert_one(log_data)
            
            # Send to modlog channel
            guild_settings = await self.bot.get_guild_settings(guild_id)
            modlog_channel_id = guild_settings.get('modlog_channel')
            
            if modlog_channel_id:
                channel = self.bot.get_channel(int(modlog_channel_id))
                if channel:
                    embed = discord.Embed(
                        title=f"🛡️ {action.title()}",
                        color=discord.Color.red() if action in ['ban', 'kick'] else discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                    embed.add_field(name="Target", value=str(target), inline=True)
                    if reason:
                        embed.add_field(name="Reason", value=reason, inline=False)
                    if duration:
                        embed.add_field(name="Duration", value=duration, inline=True)
                    
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to log moderation action: {e}")
    
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="Reason for the ban",
        delete_messages="Days of messages to delete (0-7)"
    )
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided", delete_messages: int = 0):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ You don't have permission to ban members!", ephemeral=True)
            return
        
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ You cannot ban someone with equal or higher role!", ephemeral=True)
            return
        
        try:
            await user.ban(reason=f"{interaction.user}: {reason}", delete_message_days=min(delete_messages, 7))
            await self.log_action(interaction.guild.id, "ban", interaction.user, user, reason)
            
            embed = discord.Embed(
                title="🔨 User Banned",
                description=f"{user.mention} has been banned from the server.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to ban user: {e}", ephemeral=True)
    
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(user="The user to kick", reason="Reason for the kick")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("❌ You don't have permission to kick members!", ephemeral=True)
            return
        
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ You cannot kick someone with equal or higher role!", ephemeral=True)
            return
        
        try:
            await user.kick(reason=f"{interaction.user}: {reason}")
            await self.log_action(interaction.guild.id, "kick", interaction.user, user, reason)
            
            embed = discord.Embed(
                title="👢 User Kicked",
                description=f"{user.mention} has been kicked from the server.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to kick user: {e}", ephemeral=True)
    
    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        user="The user to timeout",
        duration="Duration in minutes",
        reason="Reason for the timeout"
    )
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: int, reason: str = "No reason provided"):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("❌ You don't have permission to timeout members!", ephemeral=True)
            return
        
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ You cannot timeout someone with equal or higher role!", ephemeral=True)
            return
        
        try:
            timeout_until = datetime.utcnow() + timedelta(minutes=duration)
            await user.timeout(timeout_until, reason=f"{interaction.user}: {reason}")
            await self.log_action(interaction.guild.id, "timeout", interaction.user, user, reason, f"{duration} minutes")
            
            embed = discord.Embed(
                title="⏰ User Timed Out",
                description=f"{user.mention} has been timed out for {duration} minutes.",
                color=discord.Color.yellow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to timeout user: {e}", ephemeral=True)
    
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(user="The user to warn", reason="Reason for the warning")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("❌ You don't have permission to warn members!", ephemeral=True)
            return
        
        try:
            # Save warning to database
            warning_data = {
                "guild_id": str(interaction.guild.id),
                "user_id": str(user.id),
                "moderator_id": str(interaction.user.id),
                "reason": reason,
                "timestamp": datetime.utcnow()
            }
            await self.bot.db.warnings.insert_one(warning_data)
            
            # Get total warnings for user
            total_warnings = await self.bot.db.warnings.count_documents({
                "guild_id": str(interaction.guild.id),
                "user_id": str(user.id)
            })
            
            await self.log_action(interaction.guild.id, "warn", interaction.user, user, reason)
            
            embed = discord.Embed(
                title="⚠️ User Warned",
                description=f"{user.mention} has been warned.",
                color=discord.Color.yellow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Total Warnings", value=str(total_warnings), inline=True)
            
            await interaction.response.send_message(embed=embed)
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title=f"⚠️ Warning in {interaction.guild.name}",
                    description=f"You have been warned by {interaction.user}.",
                    color=discord.Color.yellow()
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Total Warnings", value=str(total_warnings), inline=True)
                await user.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to warn user: {e}", ephemeral=True)
    
    @app_commands.command(name="purge", description="Delete multiple messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def purge(self, interaction: discord.Interaction, amount: int):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You don't have permission to manage messages!", ephemeral=True)
            return
        
        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ Amount must be between 1 and 100!", ephemeral=True)
            return
        
        try:
            await interaction.response.defer()
            deleted = await interaction.channel.purge(limit=amount)
            
            await self.log_action(interaction.guild.id, "purge", interaction.user, interaction.channel, f"Deleted {len(deleted)} messages")
            
            embed = discord.Embed(
                title="🧹 Messages Purged",
                description=f"Deleted {len(deleted)} messages from {interaction.channel.mention}.",
                color=discord.Color.green()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            
            # Send confirmation and delete after 5 seconds
            msg = await interaction.followup.send(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
            
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to purge messages: {e}", ephemeral=True)
    
    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.describe(channel="Channel to lock", reason="Reason for locking")
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You don't have permission to manage channels!", ephemeral=True)
            return
        
        channel = channel or interaction.channel
        
        try:
            # Remove send message permission for @everyone
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"{interaction.user}: {reason}")
            
            await self.log_action(interaction.guild.id, "lock", interaction.user, channel, reason)
            
            embed = discord.Embed(
                title="🔒 Channel Locked",
                description=f"{channel.mention} has been locked.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to lock channel: {e}", ephemeral=True)
    
    @app_commands.command(name="unlock", description="Unlock a channel")
    @app_commands.describe(channel="Channel to unlock", reason="Reason for unlocking")
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You don't have permission to manage channels!", ephemeral=True)
            return
        
        channel = channel or interaction.channel
        
        try:
            # Restore send message permission for @everyone
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = None
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"{interaction.user}: {reason}")
            
            await self.log_action(interaction.guild.id, "unlock", interaction.user, channel, reason)
            
            embed = discord.Embed(
                title="🔓 Channel Unlocked",
                description=f"{channel.mention} has been unlocked.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to unlock channel: {e}", ephemeral=True)
    
    @app_commands.command(name="warnings", description="View warnings for a user")
    @app_commands.describe(user="User to check warnings for")
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("❌ You don't have permission to view warnings!", ephemeral=True)
            return
        
        try:
            warnings = await self.bot.db.warnings.find({
                "guild_id": str(interaction.guild.id),
                "user_id": str(user.id)
            }).sort("timestamp", -1).to_list(length=10)
            
            if not warnings:
                embed = discord.Embed(
                    title="⚠️ User Warnings",
                    description=f"{user.mention} has no warnings.",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="⚠️ User Warnings",
                    description=f"{user.mention} has {len(warnings)} warning(s).",
                    color=discord.Color.yellow()
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to fetch warnings: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
