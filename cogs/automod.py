import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
from datetime import datetime, timedelta
import logging
from better_profanity import profanity
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AutoModView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.select(
        placeholder="Configure AutoMod Settings...",
        options=[
            discord.SelectOption(label="🔗 Link Filter", description="Configure link filtering", value="links"),
            discord.SelectOption(label="📢 Spam Filter", description="Configure spam protection", value="spam"),
            discord.SelectOption(label="🤬 Profanity Filter", description="Configure profanity filtering", value="profanity"),
            discord.SelectOption(label="📱 External Apps", description="Configure external app filtering", value="apps"),
            discord.SelectOption(label="👤 Bypass Roles", description="Configure bypass roles", value="bypass"),
        ]
    )
    async def automod_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        value = select.values[0]
        
        if value == "links":
            await self.configure_links(interaction)
        elif value == "spam":
            await self.configure_spam(interaction)
        elif value == "profanity":
            await self.configure_profanity(interaction)
        elif value == "apps":
            await self.configure_apps(interaction)
        elif value == "bypass":
            await self.configure_bypass(interaction)
    
    async def configure_links(self, interaction: discord.Interaction):
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        automod_settings = guild_settings.get('automod_settings', {})
        link_filter = automod_settings.get('link_filter', {})
        
        embed = discord.Embed(
            title="🔗 Link Filter Configuration",
            description="Configure how links are handled in your server.",
            color=discord.Color.blue()
        )
        
        current_status = "✅ Enabled" if link_filter.get('enabled', False) else "❌ Disabled"
        embed.add_field(name="Status", value=current_status, inline=True)
        
        whitelist = link_filter.get('whitelist', [])
        if whitelist:
            embed.add_field(name="Whitelisted Domains", value="\n".join(whitelist[:5]), inline=False)
        
        view = LinkConfigView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def configure_spam(self, interaction: discord.Interaction):
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        automod_settings = guild_settings.get('automod_settings', {})
        spam_filter = automod_settings.get('spam_filter', {})
        
        embed = discord.Embed(
            title="📢 Spam Filter Configuration",
            description="Configure spam protection settings.",
            color=discord.Color.orange()
        )
        
        current_status = "✅ Enabled" if spam_filter.get('enabled', False) else "❌ Disabled"
        embed.add_field(name="Status", value=current_status, inline=True)
        
        max_messages = spam_filter.get('max_messages', 5)
        time_window = spam_filter.get('time_window', 10)
        embed.add_field(name="Limit", value=f"{max_messages} messages in {time_window}s", inline=True)
        
        view = SpamConfigView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class LinkConfigView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @discord.ui.button(label="Toggle Link Filter", style=discord.ButtonStyle.primary)
    async def toggle_links(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        automod_settings = guild_settings.get('automod_settings', {})
        
        if 'link_filter' not in automod_settings:
            automod_settings['link_filter'] = {}
        
        current = automod_settings['link_filter'].get('enabled', False)
        automod_settings['link_filter']['enabled'] = not current
        
        await self.bot.update_guild_settings(interaction.guild.id, {'automod_settings': automod_settings})
        
        status = "enabled" if not current else "disabled"
        await interaction.response.send_message(f"✅ Link filter has been {status}!", ephemeral=True)

class SpamConfigView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @discord.ui.button(label="Toggle Spam Filter", style=discord.ButtonStyle.primary)
    async def toggle_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        automod_settings = guild_settings.get('automod_settings', {})
        
        if 'spam_filter' not in automod_settings:
            automod_settings['spam_filter'] = {'max_messages': 5, 'time_window': 10}
        
        current = automod_settings['spam_filter'].get('enabled', False)
        automod_settings['spam_filter']['enabled'] = not current
        
        await self.bot.update_guild_settings(interaction.guild.id, {'automod_settings': automod_settings})
        
        status = "enabled" if not current else "disabled"
        await interaction.response.send_message(f"✅ Spam filter has been {status}!", ephemeral=True)

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_message_cache = {}  # For spam detection
        self.bot.add_view(AutoModView(bot))
        
        # Initialize profanity filter
        profanity.load_censor_words()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        guild_settings = await self.bot.get_guild_settings(message.guild.id)
        automod_settings = guild_settings.get('automod_settings', {})
        
        if not automod_settings.get('enabled', True):
            return
        
        # Check bypass roles
        bypass_roles = automod_settings.get('bypass_roles', [])
        if any(str(role.id) in bypass_roles for role in message.author.roles):
            return
        
        # Check if user has manage messages permission
        if message.author.guild_permissions.manage_messages:
            return
        
        violations = []
        
        # Link filter
        if await self.check_links(message, automod_settings):
            violations.append("links")
        
        # Spam filter
        if await self.check_spam(message, automod_settings):
            violations.append("spam")
        
        # Profanity filter
        if await self.check_profanity(message, automod_settings):
            violations.append("profanity")
        
        # External apps filter
        if await self.check_external_apps(message, automod_settings):
            violations.append("external_apps")
        
        if violations:
            await self.handle_violations(message, violations, automod_settings)
    
    async def check_links(self, message, automod_settings):
        """Check for unauthorized links"""
        link_filter = automod_settings.get('link_filter', {})
        if not link_filter.get('enabled', False):
            return False
        
        # URL regex pattern
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        urls = url_pattern.findall(message.content)
        if not urls:
            return False
        
        whitelist = link_filter.get('whitelist', [])
        
        for url in urls:
            try:
                domain = urlparse(url).netloc.lower()
                # Remove www. prefix
                domain = domain.replace('www.', '')
                
                if domain not in whitelist:
                    return True
            except:
                return True  # Invalid URL format
        
        return False
    
    async def check_spam(self, message, automod_settings):
        """Check for spam messages"""
        spam_filter = automod_settings.get('spam_filter', {})
        if not spam_filter.get('enabled', False):
            return False
        
        user_id = message.author.id
        guild_id = message.guild.id
        now = datetime.utcnow()
        
        # Initialize cache for guild if not exists
        if guild_id not in self.user_message_cache:
            self.user_message_cache[guild_id] = {}
        
        # Initialize cache for user if not exists
        if user_id not in self.user_message_cache[guild_id]:
            self.user_message_cache[guild_id][user_id] = []
        
        # Add current message timestamp
        self.user_message_cache[guild_id][user_id].append(now)
        
        # Remove old messages outside time window
        time_window = spam_filter.get('time_window', 10)
        cutoff_time = now - timedelta(seconds=time_window)
        
        self.user_message_cache[guild_id][user_id] = [
            timestamp for timestamp in self.user_message_cache[guild_id][user_id]
            if timestamp > cutoff_time
        ]
        
        # Check if user exceeded message limit
        max_messages = spam_filter.get('max_messages', 5)
        return len(self.user_message_cache[guild_id][user_id]) > max_messages
    
    async def check_profanity(self, message, automod_settings):
        """Check for profanity"""
        profanity_filter = automod_settings.get('profanity_filter', {})
        if not profanity_filter.get('enabled', False):
            return False
        
        return profanity.contains_profanity(message.content)
    
    async def check_external_apps(self, message, automod_settings):
        """Check for external app invites (Discord invites, etc.)"""
        apps_filter = automod_settings.get('apps_filter', {})
        if not apps_filter.get('enabled', False):
            return False
        
        # Discord invite pattern
        discord_invite_pattern = re.compile(
            r'(discord\.gg\/|discord\.com\/invite\/|discordapp\.com\/invite\/)[a-zA-Z0-9]+'
        )
        
        return bool(discord_invite_pattern.search(message.content))
    
    async def handle_violations(self, message, violations, automod_settings):
        """Handle automod violations"""
        try:
            # Delete the message
            await message.delete()
            
            # Log the violation
            await self.log_violation(message, violations)
            
            # Send warning to user
            warning_msg = f"⚠️ {message.author.mention}, your message was removed for violating server rules: {', '.join(violations)}"
            
            # Send temporary warning message
            warning = await message.channel.send(warning_msg)
            await asyncio.sleep(5)
            await warning.delete()
            
            # Apply punishment if configured
            await self.apply_punishment(message, violations, automod_settings)
            
        except discord.NotFound:
            pass  # Message already deleted
        except Exception as e:
            logger.error(f"Error handling automod violation: {e}")
    
    async def log_violation(self, message, violations):
        """Log automod violation to database and modlog"""
        try:
            # Save to database
            violation_data = {
                "guild_id": str(message.guild.id),
                "user_id": str(message.author.id),
                "channel_id": str(message.channel.id),
                "violations": violations,
                "message_content": message.content,
                "timestamp": datetime.utcnow()
            }
            await self.bot.db.automod_violations.insert_one(violation_data)
            
            # Send to modlog channel
            guild_settings = await self.bot.get_guild_settings(message.guild.id)
            modlog_channel_id = guild_settings.get('modlog_channel')
            
            if modlog_channel_id:
                channel = self.bot.get_channel(int(modlog_channel_id))
                if channel:
                    embed = discord.Embed(
                        title="🤖 AutoMod Violation",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=message.author.mention, inline=True)
                    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                    embed.add_field(name="Violations", value=", ".join(violations), inline=True)
                    embed.add_field(name="Message Content", value=message.content[:1000], inline=False)
                    
                    await channel.send(embed=embed)
                    
        except Exception as e:
            logger.error(f"Failed to log automod violation: {e}")
    
    async def apply_punishment(self, message, violations, automod_settings):
        """Apply punishment for automod violations"""
        try:
            # Get user's violation count
            violation_count = await self.bot.db.automod_violations.count_documents({
                "guild_id": str(message.guild.id),
                "user_id": str(message.author.id)
            })
            
            # Progressive punishment system
            if violation_count >= 5:
                # Timeout for 1 hour
                timeout_until = datetime.utcnow() + timedelta(hours=1)
                await message.author.timeout(timeout_until, reason="AutoMod: Multiple violations")
            elif violation_count >= 3:
                # Timeout for 10 minutes
                timeout_until = datetime.utcnow() + timedelta(minutes=10)
                await message.author.timeout(timeout_until, reason="AutoMod: Repeated violations")
                
        except Exception as e:
            logger.error(f"Failed to apply automod punishment: {e}")
    
    @app_commands.command(name="automod", description="Configure AutoMod settings")
    async def automod_config(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        automod_settings = guild_settings.get('automod_settings', {})
        
        embed = discord.Embed(
            title="🤖 AutoMod Configuration",
            description="Configure automatic moderation settings for your server.",
            color=discord.Color.blue()
        )
        
        # Status overview
        status = "✅ Enabled" if automod_settings.get('enabled', True) else "❌ Disabled"
        embed.add_field(name="AutoMod Status", value=status, inline=True)
        
        # Individual filter status
        filters = {
            "🔗 Link Filter": automod_settings.get('link_filter', {}).get('enabled', False),
            "📢 Spam Filter": automod_settings.get('spam_filter', {}).get('enabled', False),
            "🤬 Profanity Filter": automod_settings.get('profanity_filter', {}).get('enabled', False),
            "📱 External Apps": automod_settings.get('apps_filter', {}).get('enabled', False)
        }
        
        filter_status = "\n".join([
            f"{name}: {'✅' if enabled else '❌'}"
            for name, enabled in filters.items()
        ])
        embed.add_field(name="Filters", value=filter_status, inline=True)
        
        view = AutoModView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="automod-toggle", description="Toggle AutoMod on/off")
    async def automod_toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        automod_settings = guild_settings.get('automod_settings', {})
        
        current = automod_settings.get('enabled', True)
        automod_settings['enabled'] = not current
        
        await self.bot.update_guild_settings(interaction.guild.id, {'automod_settings': automod_settings})
        
        status = "enabled" if not current else "disabled"
        embed = discord.Embed(
            title="🤖 AutoMod Status Updated",
            description=f"AutoMod has been {status} for this server.",
            color=discord.Color.green() if not current else discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="automod-whitelist", description="Add a domain to the link whitelist")
    @app_commands.describe(domain="Domain to whitelist (e.g., youtube.com)")
    async def automod_whitelist(self, interaction: discord.Interaction, domain: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        automod_settings = guild_settings.get('automod_settings', {})
        
        if 'link_filter' not in automod_settings:
            automod_settings['link_filter'] = {}
        
        if 'whitelist' not in automod_settings['link_filter']:
            automod_settings['link_filter']['whitelist'] = []
        
        domain = domain.lower().replace('www.', '').replace('http://', '').replace('https://', '')
        
        if domain not in automod_settings['link_filter']['whitelist']:
            automod_settings['link_filter']['whitelist'].append(domain)
            await self.bot.update_guild_settings(interaction.guild.id, {'automod_settings': automod_settings})
            
            await interaction.response.send_message(f"✅ Added `{domain}` to the link whitelist!")
        else:
            await interaction.response.send_message(f"❌ `{domain}` is already whitelisted!")

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
