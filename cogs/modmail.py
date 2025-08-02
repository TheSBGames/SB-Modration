import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ModMail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_modmails = {}  # user_id: channel_id
    
    async def get_modmail_settings(self, guild_id):
        """Get modmail settings for a guild"""
        guild_settings = await self.bot.get_guild_settings(guild_id)
        return guild_settings.get('modmail_settings', {
            'enabled': False,
            'category_id': None,
            'staff_roles': [],
            'log_channel': None,
            'anonymous_staff': False
        })
    
    async def update_modmail_settings(self, guild_id, settings):
        """Update modmail settings for a guild"""
        await self.bot.update_guild_settings(guild_id, {'modmail_settings': settings})
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle modmail messages"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Handle DM messages (user to staff)
        if not message.guild:
            await self.handle_user_dm(message)
            return
        
        # Handle staff replies in modmail channels
        if message.channel.name and message.channel.name.startswith('modmail-'):
            await self.handle_staff_reply(message)
    
    async def handle_user_dm(self, message):
        """Handle DM from user to create/continue modmail"""
        try:
            user_id = message.author.id
            
            # Find which guilds the user shares with the bot and have modmail enabled
            mutual_guilds = []
            for guild in self.bot.guilds:
                if guild.get_member(user_id):
                    modmail_settings = await self.get_modmail_settings(guild.id)
                    if modmail_settings.get('enabled', False):
                        mutual_guilds.append(guild)
            
            if not mutual_guilds:
                embed = discord.Embed(
                    title="❌ ModMail Unavailable",
                    description="ModMail is not enabled in any servers we share.",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed)
                return
            
            # If user has active modmail, continue it
            if user_id in self.active_modmails:
                await self.continue_modmail(message, mutual_guilds[0])
                return
            
            # Create new modmail
            await self.create_modmail(message, mutual_guilds[0])
            
        except Exception as e:
            logger.error(f"Error handling user DM: {e}")
            await message.channel.send("❌ An error occurred while processing your message.")
    
    async def create_modmail(self, message, guild):
        """Create a new modmail thread"""
        try:
            modmail_settings = await self.get_modmail_settings(guild.id)
            
            # Get or create modmail category
            category_id = modmail_settings.get('category_id')
            category = None
            if category_id:
                category = discord.utils.get(guild.categories, id=int(category_id))
            
            if not category:
                category = await guild.create_category("📨 ModMail")
                modmail_settings['category_id'] = str(category.id)
                await self.update_modmail_settings(guild.id, modmail_settings)
            
            # Create modmail channel
            channel_name = f"modmail-{message.author.id}"
            
            # Set permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Add staff roles
            staff_roles = modmail_settings.get('staff_roles', [])
            for role_id in staff_roles:
                role = guild.get_role(int(role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            modmail_channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"ModMail thread for {message.author} ({message.author.id})"
            )
            
            # Save modmail to database
            modmail_data = {
                "guild_id": str(guild.id),
                "user_id": str(message.author.id),
                "channel_id": str(modmail_channel.id),
                "status": "open",
                "created_at": datetime.utcnow(),
                "messages": []
            }
            await self.bot.db.modmails.insert_one(modmail_data)
            
            # Track active modmail
            self.active_modmails[message.author.id] = modmail_channel.id
            
            # Send initial message to modmail channel
            embed = discord.Embed(
                title="📨 New ModMail Thread",
                description=f"**User:** {message.author} ({message.author.id})\n**Account Created:** <t:{int(message.author.created_at.timestamp())}:R>",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            if message.author.avatar:
                embed.set_thumbnail(url=message.author.avatar.url)
            
            # Add user's first message
            embed.add_field(
                name="Initial Message",
                value=message.content[:1000] if message.content else "*No content*",
                inline=False
            )
            
            await modmail_channel.send(embed=embed)
            
            # Handle attachments
            if message.attachments:
                files = []
                for attachment in message.attachments:
                    try:
                        file = await attachment.to_file()
                        files.append(file)
                    except:
                        pass
                
                if files:
                    await modmail_channel.send("**Attachments:**", files=files)
            
            # Confirm to user
            embed = discord.Embed(
                title="✅ ModMail Created",
                description=f"Your message has been sent to the staff of **{guild.name}**.\n\nYou will receive replies here. To close this thread, type `close`.",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)
            
            # Log modmail creation
            await self.log_modmail_event(guild.id, "created", message.author, None, "ModMail thread created")
            
        except Exception as e:
            logger.error(f"Error creating modmail: {e}")
            await message.channel.send("❌ Failed to create modmail thread.")
    
    async def continue_modmail(self, message, guild):
        """Continue existing modmail thread"""
        try:
            user_id = message.author.id
            channel_id = self.active_modmails[user_id]
            channel = guild.get_channel(channel_id)
            
            if not channel:
                # Channel was deleted, remove from active modmails
                del self.active_modmails[user_id]
                await self.create_modmail(message, guild)
                return
            
            # Check for close command
            if message.content.lower().strip() == 'close':
                await self.close_modmail_user(message, channel)
                return
            
            # Forward message to staff
            embed = discord.Embed(
                description=message.content[:2000] if message.content else "*No content*",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(
                name=f"{message.author}",
                icon_url=message.author.avatar.url if message.author.avatar else None
            )
            
            await channel.send(embed=embed)
            
            # Handle attachments
            if message.attachments:
                files = []
                for attachment in message.attachments:
                    try:
                        file = await attachment.to_file()
                        files.append(file)
                    except:
                        pass
                
                if files:
                    await channel.send("**User Attachments:**", files=files)
            
            # Save message to database
            await self.bot.db.modmails.update_one(
                {"channel_id": str(channel_id)},
                {
                    "$push": {
                        "messages": {
                            "author_id": str(message.author.id),
                            "author_name": str(message.author),
                            "content": message.content,
                            "timestamp": datetime.utcnow(),
                            "is_staff": False
                        }
                    }
                }
            )
            
            # React to confirm receipt
            await message.add_reaction("✅")
            
        except Exception as e:
            logger.error(f"Error continuing modmail: {e}")
            await message.channel.send("❌ Error sending message to staff.")
    
    async def handle_staff_reply(self, message):
        """Handle staff reply in modmail channel"""
        try:
            # Get modmail data
            modmail = await self.bot.db.modmails.find_one({
                "channel_id": str(message.channel.id),
                "status": "open"
            })
            
            if not modmail:
                return
            
            user_id = int(modmail['user_id'])
            user = self.bot.get_user(user_id)
            
            if not user:
                await message.channel.send("❌ Could not find the user for this modmail thread.")
                return
            
            # Get modmail settings
            modmail_settings = await self.get_modmail_settings(message.guild.id)
            anonymous_staff = modmail_settings.get('anonymous_staff', False)
            
            # Create embed for user
            embed = discord.Embed(
                description=message.content[:2000] if message.content else "*No content*",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            if anonymous_staff:
                embed.set_author(
                    name=f"Staff from {message.guild.name}",
                    icon_url=message.guild.icon.url if message.guild.icon else None
                )
            else:
                embed.set_author(
                    name=f"{message.author} (Staff)",
                    icon_url=message.author.avatar.url if message.author.avatar else None
                )
            
            # Send to user
            try:
                await user.send(embed=embed)
                
                # Handle attachments
                if message.attachments:
                    files = []
                    for attachment in message.attachments:
                        try:
                            file = await attachment.to_file()
                            files.append(file)
                        except:
                            pass
                    
                    if files:
                        await user.send("**Staff Attachments:**", files=files)
                
                # React to confirm sent
                await message.add_reaction("✅")
                
            except discord.Forbidden:
                await message.channel.send("❌ Could not send message to user (DMs disabled).")
                return
            
            # Save message to database
            await self.bot.db.modmails.update_one(
                {"channel_id": str(message.channel.id)},
                {
                    "$push": {
                        "messages": {
                            "author_id": str(message.author.id),
                            "author_name": str(message.author),
                            "content": message.content,
                            "timestamp": datetime.utcnow(),
                            "is_staff": True
                        }
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling staff reply: {e}")
            await message.channel.send("❌ Error sending reply to user.")
    
    async def close_modmail_user(self, message, channel):
        """Close modmail from user side"""
        try:
            # Update database
            await self.bot.db.modmails.update_one(
                {"channel_id": str(channel.id)},
                {
                    "$set": {
                        "status": "closed",
                        "closed_at": datetime.utcnow(),
                        "closed_by": str(message.author.id)
                    }
                }
            )
            
            # Remove from active modmails
            if message.author.id in self.active_modmails:
                del self.active_modmails[message.author.id]
            
            # Notify staff
            embed = discord.Embed(
                title="📨 ModMail Closed",
                description=f"This modmail thread has been closed by {message.author}.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await channel.send(embed=embed)
            
            # Confirm to user
            embed = discord.Embed(
                title="✅ ModMail Closed",
                description="Your modmail thread has been closed. Thank you for contacting us!",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)
            
            # Delete channel after delay
            await asyncio.sleep(10)
            await channel.delete(reason="ModMail closed by user")
            
            # Log closure
            await self.log_modmail_event(channel.guild.id, "closed", message.author, None, "Closed by user")
            
        except Exception as e:
            logger.error(f"Error closing modmail: {e}")
    
    async def log_modmail_event(self, guild_id, event, user, staff=None, details=None):
        """Log modmail events"""
        try:
            log_data = {
                "guild_id": str(guild_id),
                "event": event,
                "user_id": str(user.id),
                "user_name": str(user),
                "staff_id": str(staff.id) if staff else None,
                "staff_name": str(staff) if staff else None,
                "details": details,
                "timestamp": datetime.utcnow()
            }
            await self.bot.db.modmail_logs.insert_one(log_data)
            
            # Send to log channel if configured
            modmail_settings = await self.get_modmail_settings(guild_id)
            log_channel_id = modmail_settings.get('log_channel')
            
            if log_channel_id:
                channel = self.bot.get_channel(int(log_channel_id))
                if channel:
                    embed = discord.Embed(
                        title=f"📨 ModMail {event.title()}",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
                    if staff:
                        embed.add_field(name="Staff", value=str(staff), inline=True)
                    if details:
                        embed.add_field(name="Details", value=details, inline=False)
                    
                    await channel.send(embed=embed)
                    
        except Exception as e:
            logger.error(f"Failed to log modmail event: {e}")
    
    @app_commands.command(name="modmail-setup", description="Setup modmail system")
    @app_commands.describe(
        category="Category for modmail channels",
        staff_role="Role that can handle modmail",
        log_channel="Channel for modmail logs"
    )
    async def modmail_setup(self, interaction: discord.Interaction, category: discord.CategoryChannel = None, staff_role: discord.Role = None, log_channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        modmail_settings = await self.get_modmail_settings(interaction.guild.id)
        
        if category:
            modmail_settings['category_id'] = str(category.id)
        
        if staff_role:
            if 'staff_roles' not in modmail_settings:
                modmail_settings['staff_roles'] = []
            if str(staff_role.id) not in modmail_settings['staff_roles']:
                modmail_settings['staff_roles'].append(str(staff_role.id))
        
        if log_channel:
            modmail_settings['log_channel'] = str(log_channel.id)
        
        modmail_settings['enabled'] = True
        
        await self.update_modmail_settings(interaction.guild.id, modmail_settings)
        
        embed = discord.Embed(
            title="📨 ModMail Setup Complete",
            description="ModMail system has been configured!",
            color=discord.Color.green()
        )
        
        if category:
            embed.add_field(name="Category", value=category.mention, inline=True)
        if staff_role:
            embed.add_field(name="Staff Role", value=staff_role.mention, inline=True)
        if log_channel:
            embed.add_field(name="Log Channel", value=log_channel.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="modmail-close", description="Close the current modmail thread")
    @app_commands.describe(reason="Reason for closing")
    async def modmail_close(self, interaction: discord.Interaction, reason: str = "No reason provided"):
        if not interaction.channel.name or not interaction.channel.name.startswith('modmail-'):
            await interaction.response.send_message("❌ This is not a modmail channel!", ephemeral=True)
            return
        
        # Check permissions
        modmail_settings = await self.get_modmail_settings(interaction.guild.id)
        staff_roles = modmail_settings.get('staff_roles', [])
        
        has_permission = (
            interaction.user.guild_permissions.manage_channels or
            any(role.id in [int(r) for r in staff_roles] for role in interaction.user.roles)
        )
        
        if not has_permission:
            await interaction.response.send_message("❌ You don't have permission to close modmail threads!", ephemeral=True)
            return
        
        try:
            # Get modmail data
            modmail = await self.bot.db.modmails.find_one({
                "channel_id": str(interaction.channel.id),
                "status": "open"
            })
            
            if not modmail:
                await interaction.response.send_message("❌ This modmail thread is not found in database!", ephemeral=True)
                return
            
            user_id = int(modmail['user_id'])
            user = self.bot.get_user(user_id)
            
            # Update database
            await self.bot.db.modmails.update_one(
                {"channel_id": str(interaction.channel.id)},
                {
                    "$set": {
                        "status": "closed",
                        "closed_at": datetime.utcnow(),
                        "closed_by": str(interaction.user.id),
                        "close_reason": reason
                    }
                }
            )
            
            # Remove from active modmails
            if user_id in self.active_modmails:
                del self.active_modmails[user_id]
            
            # Notify user
            if user:
                try:
                    embed = discord.Embed(
                        title="📨 ModMail Closed",
                        description=f"Your modmail thread in **{interaction.guild.name}** has been closed by staff.",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="Reason", value=reason, inline=False)
                    embed.add_field(name="Staff Member", value=str(interaction.user), inline=True)
                    
                    await user.send(embed=embed)
                except:
                    pass  # User has DMs disabled
            
            # Confirm closure
            embed = discord.Embed(
                title="📨 ModMail Closed",
                description=f"This modmail thread has been closed by {interaction.user.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            # Log closure
            await self.log_modmail_event(interaction.guild.id, "closed", user, interaction.user, reason)
            
            # Delete channel after delay
            await asyncio.sleep(10)
            await interaction.channel.delete(reason=f"ModMail closed by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error closing modmail: {e}")
            await interaction.response.send_message("❌ Error closing modmail thread.", ephemeral=True)
    
    @app_commands.command(name="modmail-toggle", description="Toggle modmail system on/off")
    async def modmail_toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        modmail_settings = await self.get_modmail_settings(interaction.guild.id)
        modmail_settings['enabled'] = not modmail_settings.get('enabled', False)
        
        await self.update_modmail_settings(interaction.guild.id, modmail_settings)
        
        status = "enabled" if modmail_settings['enabled'] else "disabled"
        color = discord.Color.green() if modmail_settings['enabled'] else discord.Color.red()
        
        embed = discord.Embed(
            title="📨 ModMail Status",
            description=f"ModMail has been {status} for this server.",
            color=color
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ModMail(bot))
