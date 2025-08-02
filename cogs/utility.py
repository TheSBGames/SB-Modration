import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

class NoPrefix(commands.Cog):
    """No Prefix Mode and Multi-language Support"""
    
    def __init__(self, bot):
        self.bot = bot
        self.languages = {
            'en': {
                'name': 'English',
                'help_title': 'Help Menu',
                'help_description': 'Here are all available commands:',
                'permission_denied': 'You don\'t have permission to use this command!',
                'success': 'Success!',
                'error': 'An error occurred!',
                'user_not_found': 'User not found!',
                'invalid_duration': 'Invalid duration format!'
            },
            'es': {
                'name': 'Español',
                'help_title': 'Menú de Ayuda',
                'help_description': 'Aquí están todos los comandos disponibles:',
                'permission_denied': '¡No tienes permiso para usar este comando!',
                'success': '¡Éxito!',
                'error': '¡Ocurrió un error!',
                'user_not_found': '¡Usuario no encontrado!',
                'invalid_duration': '¡Formato de duración inválido!'
            },
            'fr': {
                'name': 'Français',
                'help_title': 'Menu d\'Aide',
                'help_description': 'Voici toutes les commandes disponibles:',
                'permission_denied': 'Vous n\'avez pas la permission d\'utiliser cette commande!',
                'success': 'Succès!',
                'error': 'Une erreur s\'est produite!',
                'user_not_found': 'Utilisateur non trouvé!',
                'invalid_duration': 'Format de durée invalide!'
            },
            'de': {
                'name': 'Deutsch',
                'help_title': 'Hilfe-Menü',
                'help_description': 'Hier sind alle verfügbaren Befehle:',
                'permission_denied': 'Sie haben keine Berechtigung, diesen Befehl zu verwenden!',
                'success': 'Erfolg!',
                'error': 'Ein Fehler ist aufgetreten!',
                'user_not_found': 'Benutzer nicht gefunden!',
                'invalid_duration': 'Ungültiges Dauerformat!'
            }
        }
    
    async def get_user_language(self, user_id, guild_id=None):
        """Get user's preferred language"""
        # Check user preference first
        user_pref = await self.bot.db.user_preferences.find_one({"user_id": str(user_id)})
        if user_pref and 'language' in user_pref:
            return user_pref['language']
        
        # Fall back to guild preference
        if guild_id:
            guild_settings = await self.bot.get_guild_settings(guild_id)
            return guild_settings.get('language', 'en')
        
        return 'en'
    
    def get_text(self, key, language='en'):
        """Get localized text"""
        return self.languages.get(language, self.languages['en']).get(key, self.languages['en'][key])
    
    @app_commands.command(name="np-add", description="Grant no-prefix permission to a user (Owner only)")
    @app_commands.describe(
        user="User to grant no-prefix permission",
        duration="Duration (10m, 1h, 1d, perm for permanent)"
    )
    async def np_add(self, interaction: discord.Interaction, user: discord.Member, duration: str = "10m"):
        # Check if user is bot owner
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        try:
            # Parse duration
            if duration.lower() == "perm":
                expires = datetime.now().timestamp() + (365 * 24 * 60 * 60)  # 1 year from now
                duration_text = "permanent"
            else:
                # Parse time format (e.g., 10m, 1h, 1d)
                import re
                match = re.match(r'(\d+)([mhd])', duration.lower())
                if not match:
                    await interaction.response.send_message("❌ Invalid duration format! Use format like: 10m, 1h, 1d, or 'perm'", ephemeral=True)
                    return
                
                amount, unit = match.groups()
                amount = int(amount)
                
                if unit == 'm':
                    seconds = amount * 60
                    duration_text = f"{amount} minute(s)"
                elif unit == 'h':
                    seconds = amount * 3600
                    duration_text = f"{amount} hour(s)"
                elif unit == 'd':
                    seconds = amount * 86400
                    duration_text = f"{amount} day(s)"
                
                expires = datetime.now().timestamp() + seconds
            
            # Grant no-prefix permission
            guild_id = str(interaction.guild.id)
            user_id = str(user.id)
            
            if guild_id not in self.bot.no_prefix_users:
                self.bot.no_prefix_users[guild_id] = {}
            
            self.bot.no_prefix_users[guild_id][user_id] = {
                'expires': expires,
                'granted_by': str(interaction.user.id),
                'granted_at': datetime.now().timestamp()
            }
            
            # Save to database
            await self.bot.db.no_prefix_permissions.update_one(
                {"guild_id": guild_id, "user_id": user_id},
                {
                    "$set": {
                        "expires": expires,
                        "granted_by": str(interaction.user.id),
                        "granted_at": datetime.now().timestamp()
                    }
                },
                upsert=True
            )
            
            embed = discord.Embed(
                title="✅ No-Prefix Permission Granted",
                description=f"{user.mention} can now use commands without prefix for {duration_text}.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error granting no-prefix permission: {e}")
            await interaction.response.send_message("❌ Error granting no-prefix permission.", ephemeral=True)
    
    @app_commands.command(name="np-remove", description="Remove no-prefix permission from a user (Owner only)")
    @app_commands.describe(user="User to remove no-prefix permission from")
    async def np_remove(self, interaction: discord.Interaction, user: discord.Member):
        # Check if user is bot owner
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        try:
            guild_id = str(interaction.guild.id)
            user_id = str(user.id)
            
            # Remove from memory
            if guild_id in self.bot.no_prefix_users and user_id in self.bot.no_prefix_users[guild_id]:
                del self.bot.no_prefix_users[guild_id][user_id]
            
            # Remove from database
            await self.bot.db.no_prefix_permissions.delete_one({
                "guild_id": guild_id,
                "user_id": user_id
            })
            
            embed = discord.Embed(
                title="✅ No-Prefix Permission Revoked",
                description=f"No-prefix permission has been revoked from {user.mention}.",
                color=discord.Color.orange()
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error revoking no-prefix permission: {e}")
            await interaction.response.send_message("❌ Error revoking no-prefix permission.", ephemeral=True)
    
    @app_commands.command(name="np-list", description="List users with no-prefix permissions (Owner only)")
    async def np_list(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        try:
            guild_id = str(interaction.guild.id)
            users = self.bot.no_prefix_users.get(guild_id, {})
            
            embed = discord.Embed(
                title="No-Prefix Permissions",
                description="Users with no-prefix permissions:",
                color=discord.Color.blue()
            )
            
            for user_id, data in users.items():
                user = interaction.guild.get_member(int(user_id))
                if user:
                    embed.add_field(name=user.name, value=f"Expires: {datetime.fromtimestamp(data['expires'])}", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing no-prefix permissions: {e}")
            await interaction.response.send_message("❌ Error listing no-prefix permissions.", ephemeral=True)
    
    @app_commands.command(name="language", description="Set your preferred language")
    @app_commands.describe(language="Your preferred language")
    @app_commands.choices(language=[
        app_commands.Choice(name="English", value="en"),
        app_commands.Choice(name="Español", value="es"),
        app_commands.Choice(name="Français", value="fr"),
        app_commands.Choice(name="Deutsch", value="de")
    ])
    async def set_language(self, interaction: discord.Interaction, language: str):
        try:
            # Update user preference
            await self.bot.db.user_preferences.update_one(
                {"user_id": str(interaction.user.id)},
                {
                    "$set": {
                        "language": language,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            lang_name = self.languages[language]['name']
            success_text = self.get_text('success', language)
            
            embed = discord.Embed(
                title=f"✅ {success_text}",
                description=f"Your language has been set to **{lang_name}**.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting language: {e}")
            await interaction.response.send_message("❌ Error setting language.", ephemeral=True)
    
    @app_commands.command(name="server-language", description="Set the server's default language")
    @app_commands.describe(language="Server's default language")
    @app_commands.choices(language=[
        app_commands.Choice(name="English", value="en"),
        app_commands.Choice(name="Español", value="es"),
        app_commands.Choice(name="Français", value="fr"),
        app_commands.Choice(name="Deutsch", value="de")
    ])
    async def set_server_language(self, interaction: discord.Interaction, language: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        try:
            # Update guild settings
            await self.bot.update_guild_settings(interaction.guild.id, {'language': language})
            
            lang_name = self.languages[language]['name']
            
            embed = discord.Embed(
                title="✅ Server Language Updated",
                description=f"Server default language has been set to **{lang_name}**.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error setting server language: {e}")
            await interaction.response.send_message("❌ Error setting server language.", ephemeral=True)
    
    @app_commands.command(name="help", description="Show help menu")
    async def help_command(self, interaction: discord.Interaction):
        user_lang = await self.get_user_language(interaction.user.id, interaction.guild.id if interaction.guild else None)
        
        embed = discord.Embed(
            title=self.get_text('help_title', user_lang),
            description=self.get_text('help_description', user_lang),
            color=discord.Color.blue()
        )
        
        # Add command categories
        categories = {
            "🛡️ Moderation": "/ban, /kick, /timeout, /warn, /purge, /lock, /unlock",
            "🎫 Tickets": "/ticket-setup, /ticket-panel, /ticket-add, /ticket-remove",
            "🤖 AutoMod": "/automod, /automod-toggle, /automod-whitelist",
            "🎶 Music": "/play, /pause, /skip, /queue, /volume, /nowplaying",
            "🧠 ChatGPT": "/ai, /ai-setup, /ai-toggle, /clear-conversation",
            "📨 ModMail": "/modmail-setup, /modmail-close, /modmail-toggle",
            "🎉 Fun": "/meme, /joke, /8ball, /poll, /weather, /avatar",
            "⚙️ Admin": "/embed, /eval, /reload, /sync, /presence",
            "📈 Leveling": "/rank, /leaderboard, /leveling-setup, /level-role",
            "🌍 Utility": "/language, /server-language, /no-prefix, /help"
        }
        
        for category, commands in categories.items():
            embed.add_field(name=category, value=commands, inline=False)
        
        embed.set_footer(text="Use /command-name to run a command")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(NoPrefix(bot))
