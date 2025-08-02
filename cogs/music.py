import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
from datetime import datetime
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import os

logger = logging.getLogger(__name__)

class MusicView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="play_pause")
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        if not player:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        if player.paused:
            await player.pause(False)
            await interaction.response.send_message("▶️ Resumed playback!", ephemeral=True)
        else:
            await player.pause(True)
            await interaction.response.send_message("⏸️ Paused playback!", ephemeral=True)
    
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        if not player:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        await player.skip()
        await interaction.response.send_message("⏭️ Skipped to next track!", ephemeral=True)
    
    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        if not player:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        await player.disconnect()
        await interaction.response.send_message("⏹️ Stopped playback and disconnected!", ephemeral=True)
    
    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="shuffle")
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        if not player or not player.queue:
            await interaction.response.send_message("❌ No songs in queue to shuffle!", ephemeral=True)
            return
        
        player.queue.shuffle()
        await interaction.response.send_message("🔀 Queue shuffled!", ephemeral=True)
    
    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="loop")
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        if not player:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        # Toggle loop mode
        if hasattr(player, 'loop_mode'):
            player.loop_mode = not player.loop_mode
        else:
            player.loop_mode = True
        
        status = "enabled" if player.loop_mode else "disabled"
        await interaction.response.send_message(f"🔁 Loop mode {status}!", ephemeral=True)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spotify = None
        self.setup_spotify()
        self.bot.add_view(MusicView(bot))
    
    def setup_spotify(self):
        """Setup Spotify client for playlist/track info"""
        try:
            client_id = self.bot.config.get('spotify_client_id')
            client_secret = self.bot.config.get('spotify_client_secret')
            
            if client_id and client_secret:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret
                )
                self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                logger.info("Spotify client initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
    
    async def cog_load(self):
        """Setup Wavelink when cog loads"""
        try:
            node = wavelink.Node(
                uri=f"http://{self.bot.config.get('lavalink_host', 'localhost')}:{self.bot.config.get('lavalink_port', 2333)}",
                password=self.bot.config.get('lavalink_password', 'youshallnotpass')
            )
            await wavelink.Pool.connect(client=self.bot, nodes=[node])
            logger.info("Connected to Lavalink successfully!")
        except Exception as e:
            logger.error(f"Failed to connect to Lavalink: {e}")
    
    async def ensure_voice(self, interaction: discord.Interaction):
        """Ensure bot is connected to voice channel"""
        if not interaction.user.voice:
            await interaction.response.send_message("❌ You need to be in a voice channel!", ephemeral=True)
            return False
        
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to connect to voice channel: {e}", ephemeral=True)
                return False
        
        return True
    
    def check_dj_permissions(self, interaction: discord.Interaction):
        """Check if user has DJ permissions"""
        guild_settings = self.bot.guild_settings.get(str(interaction.guild.id), {})
        music_settings = guild_settings.get('music_settings', {})
        dj_role_id = music_settings.get('dj_role')
        
        # Check if user has DJ role or manage channels permission
        if interaction.user.guild_permissions.manage_channels:
            return True
        
        if dj_role_id:
            dj_role = interaction.guild.get_role(int(dj_role_id))
            if dj_role and dj_role in interaction.user.roles:
                return True
        
        return False
    
    @app_commands.command(name="play", description="Play a song or playlist")
    @app_commands.describe(query="Song name, URL, or search query")
    async def play(self, interaction: discord.Interaction, query: str):
        if not await self.ensure_voice(interaction):
            return
        
        await interaction.response.defer()
        
        try:
            player = wavelink.Pool.get_node().get_player(interaction.guild.id)
            
            # Search for tracks
            tracks = await wavelink.Playable.search(query)
            
            if not tracks:
                await interaction.followup.send("❌ No tracks found!")
                return
            
            if isinstance(tracks, wavelink.Playlist):
                # Handle playlist
                for track in tracks.tracks:
                    await player.queue.put_wait(track)
                
                embed = discord.Embed(
                    title="📝 Playlist Added",
                    description=f"Added **{len(tracks.tracks)}** tracks from `{tracks.name}`",
                    color=discord.Color.green()
                )
            else:
                # Handle single track
                track = tracks[0]
                await player.queue.put_wait(track)
                
                embed = discord.Embed(
                    title="🎵 Track Added",
                    description=f"**{track.title}** by {track.author}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Duration", value=f"{track.length // 60000}:{(track.length // 1000) % 60:02d}", inline=True)
                embed.add_field(name="Position in Queue", value=str(len(player.queue)), inline=True)
            
            # Start playing if not already playing
            if not player.playing:
                await player.play(player.queue.get())
            
            view = MusicView(self.bot)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error playing music: {e}")
            await interaction.followup.send(f"❌ Error playing music: {e}")
    
    @app_commands.command(name="pause", description="Pause the current track")
    async def pause(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player or not player.playing:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        await player.pause(True)
        
        embed = discord.Embed(
            title="⏸️ Music Paused",
            description="Playback has been paused.",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="resume", description="Resume the current track")
    async def resume(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player or not player.paused:
            await interaction.response.send_message("❌ Music is not paused!", ephemeral=True)
            return
        
        await player.pause(False)
        
        embed = discord.Embed(
            title="▶️ Music Resumed",
            description="Playback has been resumed.",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player or not player.playing:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        # Check DJ permissions for skip
        if not self.check_dj_permissions(interaction) and len(player.channel.members) > 3:
            await interaction.response.send_message("❌ You need DJ permissions to skip when there are multiple listeners!", ephemeral=True)
            return
        
        await player.skip()
        
        embed = discord.Embed(
            title="⏭️ Track Skipped",
            description="Skipped to the next track.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="stop", description="Stop playback and clear queue")
    async def stop(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        # Check DJ permissions
        if not self.check_dj_permissions(interaction):
            await interaction.response.send_message("❌ You need DJ permissions to stop playback!", ephemeral=True)
            return
        
        await player.disconnect()
        
        embed = discord.Embed(
            title="⏹️ Playback Stopped",
            description="Stopped playback and cleared the queue.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="queue", description="Show the current music queue")
    async def queue(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player or not player.queue:
            await interaction.response.send_message("❌ The queue is empty!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎵 Music Queue",
            color=discord.Color.blue()
        )
        embed.set_footer(text="🎵 Music Player • Powered By SBModeration™")
        
        # Show currently playing
        if player.current:
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{player.current.title}** by {player.current.author}",
                inline=False
            )
        
        # Show next tracks in queue
        queue_list = []
        for i, track in enumerate(list(player.queue)[:10], 1):
            duration = f"{track.length // 60000}:{(track.length // 1000) % 60:02d}"
            queue_list.append(f"`{i}.` **{track.title}** by {track.author} `[{duration}]`")
        
        if queue_list:
            embed.add_field(
                name="📝 Up Next",
                value="\n".join(queue_list),
                inline=False
            )
        
        if len(player.queue) > 10:
            embed.add_field(
                name="📊 Queue Info",
                value=f"Showing 10 of {len(player.queue)} tracks",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="nowplaying", description="Show information about the current track")
    async def nowplaying(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player or not player.current:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        track = player.current
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{track.title}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Artist", value=track.author, inline=True)
        
        # Format duration
        current_pos = player.position // 1000
        total_duration = track.length // 1000
        
        current_time = f"{current_pos // 60}:{current_pos % 60:02d}"
        total_time = f"{total_duration // 60}:{total_duration % 60:02d}"
        
        embed.add_field(name="Duration", value=f"{current_time} / {total_time}", inline=True)
        embed.add_field(name="Volume", value=f"{player.volume}%", inline=True)
        
        # Progress bar
        progress = int((current_pos / total_duration) * 20) if total_duration > 0 else 0
        progress_bar = "█" * progress + "░" * (20 - progress)
        embed.add_field(name="Progress", value=f"`{progress_bar}`", inline=False)
        
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        
        view = MusicView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="volume", description="Set the playback volume")
    @app_commands.describe(volume="Volume level (0-100)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        if volume < 0 or volume > 100:
            await interaction.response.send_message("❌ Volume must be between 0 and 100!", ephemeral=True)
            return
        
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        # Check DJ permissions for volume changes > 50%
        if volume > 50 and not self.check_dj_permissions(interaction):
            await interaction.response.send_message("❌ You need DJ permissions to set volume above 50%!", ephemeral=True)
            return
        
        await player.set_volume(volume)
        
        embed = discord.Embed(
            title="🔊 Volume Changed",
            description=f"Volume set to **{volume}%**",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="shuffle", description="Shuffle the current queue")
    async def shuffle(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player or not player.queue:
            await interaction.response.send_message("❌ No songs in queue to shuffle!", ephemeral=True)
            return
        
        # Check DJ permissions
        if not self.check_dj_permissions(interaction):
            await interaction.response.send_message("❌ You need DJ permissions to shuffle the queue!", ephemeral=True)
            return
        
        player.queue.shuffle()
        
        embed = discord.Embed(
            title="🔀 Queue Shuffled",
            description=f"Shuffled **{len(player.queue)}** tracks in the queue.",
            color=discord.Color.purple()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="clear", description="Clear the music queue")
    async def clear(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player or not player.queue:
            await interaction.response.send_message("❌ The queue is already empty!", ephemeral=True)
            return
        
        # Check DJ permissions
        if not self.check_dj_permissions(interaction):
            await interaction.response.send_message("❌ You need DJ permissions to clear the queue!", ephemeral=True)
            return
        
        queue_size = len(player.queue)
        player.queue.clear()
        
        embed = discord.Embed(
            title="🗑️ Queue Cleared",
            description=f"Removed **{queue_size}** tracks from the queue.",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="lyrics", description="Get lyrics for the current track")
    async def lyrics(self, interaction: discord.Interaction):
        player = wavelink.Pool.get_node().get_player(interaction.guild.id)
        
        if not player or not player.current:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Search for lyrics using the track title and author
            query = f"{player.current.title} {player.current.author}"
            
            # This is a placeholder - you would integrate with a lyrics API
            # like Genius, AZLyrics, or similar
            embed = discord.Embed(
                title="🎤 Lyrics",
                description=f"Lyrics for **{player.current.title}** by {player.current.author}",
                color=discord.Color.purple()
            )
            embed.add_field(
                name="Note",
                value="Lyrics feature requires integration with a lyrics API service.",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error fetching lyrics: {e}")
            await interaction.followup.send("❌ Failed to fetch lyrics.")
    
    @app_commands.command(name="music-setup", description="Setup music system for this server")
    @app_commands.describe(dj_role="Role that gets DJ permissions")
    async def music_setup(self, interaction: discord.Interaction, dj_role: discord.Role = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)
            return
        
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        music_settings = guild_settings.get('music_settings', {})
        
        if dj_role:
            music_settings['dj_role'] = str(dj_role.id)
        
        music_settings['enabled'] = True
        
        await self.bot.update_guild_settings(interaction.guild.id, {'music_settings': music_settings})
        
        embed = discord.Embed(
            title="🎵 Music System Setup",
            description="Music system has been configured!",
            color=discord.Color.green()
        )
        
        if dj_role:
            embed.add_field(name="DJ Role", value=dj_role.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Handle track end events"""
        player = payload.player
        
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)

async def setup(bot):
    await bot.add_cog(Music(bot))
