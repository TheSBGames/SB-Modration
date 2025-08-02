import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import ast
import textwrap
from contextlib import redirect_stdout
import io
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class EmbedBuilder(discord.ui.Modal, title='Custom Embed Builder'):
    def __init__(self):
        super().__init__()

    title_input = discord.ui.TextInput(
        label='Embed Title',
        placeholder='Enter embed title...',
        required=False,
        max_length=256
    )
    
    description_input = discord.ui.TextInput(
        label='Embed Description',
        placeholder='Enter embed description...',
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=4000
    )
    
    color_input = discord.ui.TextInput(
        label='Embed Color (hex)',
        placeholder='#FF0000 or red, blue, green, etc.',
        required=False,
        max_length=20
    )
    
    footer_input = discord.ui.TextInput(
        label='Footer Text',
        placeholder='Enter footer text...',
        required=False,
        max_length=2048
    )
    
    image_input = discord.ui.TextInput(
        label='Image URL',
        placeholder='https://example.com/image.png',
        required=False,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed()
        
        if self.title_input.value:
            embed.title = self.title_input.value
        
        if self.description_input.value:
            embed.description = self.description_input.value
        
        # Handle color
        if self.color_input.value:
            color_value = self.color_input.value.lower().strip()
            try:
                if color_value.startswith('#'):
                    embed.color = discord.Color(int(color_value[1:], 16))
                elif color_value == 'red':
                    embed.color = discord.Color.red()
                elif color_value == 'blue':
                    embed.color = discord.Color.blue()
                elif color_value == 'green':
                    embed.color = discord.Color.green()
                elif color_value == 'yellow':
                    embed.color = discord.Color.yellow()
                elif color_value == 'purple':
                    embed.color = discord.Color.purple()
                elif color_value == 'orange':
                    embed.color = discord.Color.orange()
                else:
                    embed.color = discord.Color.blue()
            except:
                embed.color = discord.Color.blue()
        
        if self.footer_input.value:
            embed.set_footer(text=self.footer_input.value)
        
        if self.image_input.value:
            try:
                embed.set_image(url=self.image_input.value)
            except:
                pass
        
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
    
    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')
    
    @app_commands.command(name="embed", description="Create a custom embed message")
    async def embed_builder(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need Manage Messages permission!", ephemeral=True)
            return
        
        modal = EmbedBuilder()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="eval", description="Evaluate Python code (Owner only)")
    @app_commands.describe(code="Python code to evaluate")
    async def eval_command(self, interaction: discord.Interaction, code: str):
        # Check if user is bot owner
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        env = {
            'bot': self.bot,
            'interaction': interaction,
            'channel': interaction.channel,
            'author': interaction.user,
            'guild': interaction.guild,
            'message': interaction,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(code)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Compilation Error",
                description=f"```py\n{e.__class__.__name__}: {e}\n```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            embed = discord.Embed(
                title="❌ Execution Error",
                color=discord.Color.red()
            )
            if value:
                embed.add_field(name="Output", value=f"```py\n{value}\n```", inline=False)
            embed.add_field(name="Error", value=f"```py\n{e.__class__.__name__}: {e}\n```", inline=False)
            await interaction.followup.send(embed=embed)
        else:
            value = stdout.getvalue()
            
            if ret is None:
                if value:
                    embed = discord.Embed(
                        title="✅ Evaluation Complete",
                        description=f"```py\n{value}\n```",
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        title="✅ Evaluation Complete",
                        description="No output",
                        color=discord.Color.green()
                    )
            else:
                self._last_result = ret
                embed = discord.Embed(
                    title="✅ Evaluation Complete",
                    color=discord.Color.green()
                )
                if value:
                    embed.add_field(name="Output", value=f"```py\n{value}\n```", inline=False)
                embed.add_field(name="Result", value=f"```py\n{ret}\n```", inline=False)
            
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="reload", description="Reload a cog (Owner only)")
    @app_commands.describe(cog="Name of the cog to reload")
    async def reload_cog(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Try to reload the cog
            await self.bot.reload_extension(f'cogs.{cog}')
            
            embed = discord.Embed(
                title="✅ Cog Reloaded",
                description=f"Successfully reloaded `{cog}` cog.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
        except commands.ExtensionNotLoaded:
            embed = discord.Embed(
                title="❌ Cog Not Loaded",
                description=f"The cog `{cog}` is not currently loaded.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            
        except commands.ExtensionNotFound:
            embed = discord.Embed(
                title="❌ Cog Not Found",
                description=f"The cog `{cog}` was not found.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reload Failed",
                description=f"Failed to reload `{cog}`: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="load", description="Load a cog (Owner only)")
    @app_commands.describe(cog="Name of the cog to load")
    async def load_cog(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            await self.bot.load_extension(f'cogs.{cog}')
            
            embed = discord.Embed(
                title="✅ Cog Loaded",
                description=f"Successfully loaded `{cog}` cog.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
        except commands.ExtensionAlreadyLoaded:
            embed = discord.Embed(
                title="❌ Cog Already Loaded",
                description=f"The cog `{cog}` is already loaded.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            
        except commands.ExtensionNotFound:
            embed = discord.Embed(
                title="❌ Cog Not Found",
                description=f"The cog `{cog}` was not found.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Load Failed",
                description=f"Failed to load `{cog}`: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="unload", description="Unload a cog (Owner only)")
    @app_commands.describe(cog="Name of the cog to unload")
    async def unload_cog(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        # Prevent unloading the admin cog
        if cog.lower() == 'admin':
            await interaction.response.send_message("❌ Cannot unload the admin cog!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            await self.bot.unload_extension(f'cogs.{cog}')
            
            embed = discord.Embed(
                title="✅ Cog Unloaded",
                description=f"Successfully unloaded `{cog}` cog.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
        except commands.ExtensionNotLoaded:
            embed = discord.Embed(
                title="❌ Cog Not Loaded",
                description=f"The cog `{cog}` is not currently loaded.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Unload Failed",
                description=f"Failed to unload `{cog}`: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="cogs", description="List all loaded cogs")
    async def list_cogs(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        loaded_cogs = list(self.bot.extensions.keys())
        
        embed = discord.Embed(
            title="🔧 Loaded Cogs",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if loaded_cogs:
            cog_list = "\n".join([f"• {cog}" for cog in loaded_cogs])
            embed.description = f"```\n{cog_list}\n```"
            embed.add_field(name="Total", value=str(len(loaded_cogs)), inline=True)
        else:
            embed.description = "No cogs are currently loaded."
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="sync", description="Sync slash commands (Owner only)")
    async def sync_commands(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            synced = await self.bot.tree.sync()
            
            embed = discord.Embed(
                title="✅ Commands Synced",
                description=f"Successfully synced {len(synced)} slash commands.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Sync Failed",
                description=f"Failed to sync commands: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="presence", description="Change bot presence (Owner only)")
    @app_commands.describe(
        status="Bot status",
        activity_type="Type of activity",
        activity_name="Activity name"
    )
    @app_commands.choices(status=[
        app_commands.Choice(name="Online", value="online"),
        app_commands.Choice(name="Idle", value="idle"),
        app_commands.Choice(name="Do Not Disturb", value="dnd"),
        app_commands.Choice(name="Invisible", value="invisible")
    ])
    @app_commands.choices(activity_type=[
        app_commands.Choice(name="Playing", value="playing"),
        app_commands.Choice(name="Streaming", value="streaming"),
        app_commands.Choice(name="Listening", value="listening"),
        app_commands.Choice(name="Watching", value="watching"),
        app_commands.Choice(name="Competing", value="competing")
    ])
    async def change_presence(self, interaction: discord.Interaction, status: str = None, activity_type: str = None, activity_name: str = None):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        # Convert status string to discord.Status
        status_map = {
            'online': discord.Status.online,
            'idle': discord.Status.idle,
            'dnd': discord.Status.dnd,
            'invisible': discord.Status.invisible
        }
        
        # Convert activity type string to discord.ActivityType
        activity_map = {
            'playing': discord.ActivityType.playing,
            'streaming': discord.ActivityType.streaming,
            'listening': discord.ActivityType.listening,
            'watching': discord.ActivityType.watching,
            'competing': discord.ActivityType.competing
        }
        
        new_status = status_map.get(status, discord.Status.online) if status else discord.Status.online
        activity = None
        
        if activity_type and activity_name:
            activity = discord.Activity(
                type=activity_map.get(activity_type, discord.ActivityType.playing),
                name=activity_name
            )
        
        try:
            await self.bot.change_presence(status=new_status, activity=activity)
            
            embed = discord.Embed(
                title="✅ Presence Updated",
                color=discord.Color.green()
            )
            embed.add_field(name="Status", value=status or "online", inline=True)
            if activity:
                embed.add_field(name="Activity", value=f"{activity_type.title()} {activity_name}", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Presence Update Failed",
                description=f"Failed to update presence: {e}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="shutdown", description="Shutdown the bot (Owner only)")
    async def shutdown_bot(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔴 Bot Shutdown",
            description="Bot is shutting down...",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Shutdown initiated by {interaction.user}")
        
        await interaction.response.send_message(embed=embed)
        
        # Close database connection
        if self.bot.db_client:
            self.bot.db_client.close()
        
        # Close the bot
        await self.bot.close()
    
    @app_commands.command(name="guilds", description="List all guilds the bot is in (Owner only)")
    async def list_guilds(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        guilds = self.bot.guilds
        
        embed = discord.Embed(
            title="🏰 Bot Guilds",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if guilds:
            guild_list = []
            for guild in guilds[:20]:  # Limit to 20 guilds to avoid embed limits
                member_count = guild.member_count
                guild_list.append(f"**{guild.name}** ({guild.id})\n└ Members: {member_count}")
            
            embed.description = "\n\n".join(guild_list)
            embed.add_field(name="Total Guilds", value=str(len(guilds)), inline=True)
            
            total_members = sum(guild.member_count for guild in guilds)
            embed.add_field(name="Total Members", value=str(total_members), inline=True)
            
            if len(guilds) > 20:
                embed.set_footer(text=f"Showing 20 of {len(guilds)} guilds")
        else:
            embed.description = "Bot is not in any guilds."
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leave-guild", description="Leave a guild (Owner only)")
    @app_commands.describe(guild_id="ID of the guild to leave")
    async def leave_guild(self, interaction: discord.Interaction, guild_id: str):
        if interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ This command is restricted to bot owners only!", ephemeral=True)
            return
        
        try:
            guild_id = int(guild_id)
            guild = self.bot.get_guild(guild_id)
            
            if not guild:
                await interaction.response.send_message("❌ Guild not found!", ephemeral=True)
                return
            
            guild_name = guild.name
            await guild.leave()
            
            embed = discord.Embed(
                title="✅ Left Guild",
                description=f"Successfully left **{guild_name}** ({guild_id})",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid guild ID!", ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Leave Guild",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="bot-stats", description="View bot statistics")
    async def bot_stats(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild and interaction.user.id not in self.bot.config.get('owner_ids', []):
            await interaction.response.send_message("❌ You need Manage Server permission or be a bot owner!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Basic stats
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Users", value=str(len(self.bot.users)), inline=True)
        embed.add_field(name="Channels", value=str(len(list(self.bot.get_all_channels()))), inline=True)
        
        # Command stats
        embed.add_field(name="Slash Commands", value=str(len(self.bot.tree.get_commands())), inline=True)
        embed.add_field(name="Loaded Cogs", value=str(len(self.bot.extensions)), inline=True)
        
        # Bot info
        embed.add_field(name="Bot Version", value="1.0.0", inline=True)
        embed.add_field(name="Discord.py Version", value=discord.__version__, inline=True)
        embed.add_field(name="Python Version", value="3.8+", inline=True)
        
        # Uptime (you'd need to track this)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
