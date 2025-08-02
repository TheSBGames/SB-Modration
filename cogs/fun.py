import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import asyncio
from datetime import datetime
import logging
import json
import re
import json
import requests
from PIL import Image, ImageDraw, ImageFont
import io

logger = logging.getLogger(__name__)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        asyncio.create_task(self.session.close())
    
    @app_commands.command(name="meme", description="Get a random meme")
    async def meme(self, interaction: discord.Interaction, subreddit: str = None):
        """Get a random meme from Reddit"""
        try:
            # Popular meme subreddits
            meme_subreddits = [
                'memes', 'dankmemes', 'wholesomememes', 'memeeconomy', 
                'PrequelMemes', 'HistoryMemes', 'ProgrammerHumor', 'gaming',
                'funny', 'me_irl', 'meirl', 'AdviceAnimals', 'MemeTemplatesOfficial'
            ]
            
            chosen_subreddit = subreddit if subreddit else random.choice(meme_subreddits)
            
            async with aiohttp.ClientSession() as session:
                # Try Reddit JSON API first
                reddit_url = f'https://www.reddit.com/r/{chosen_subreddit}/hot.json?limit=50'
                headers = {'User-Agent': 'Discord Bot Meme Fetcher 1.0'}
                
                async with session.get(reddit_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = data['data']['children']
                        
                        # Filter for image posts
                        image_posts = []
                        for post in posts:
                            post_data = post['data']
                            if not post_data.get('is_self', True) and not post_data.get('over_18', False):
                                url = post_data.get('url', '')
                                if any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']) or 'i.redd.it' in url or 'i.imgur.com' in url:
                                    image_posts.append(post_data)
                        
                        if image_posts:
                            meme_post = random.choice(image_posts)
                            
                            embed = discord.Embed(
                                title=meme_post['title'][:256],
                                url=f"https://reddit.com{meme_post['permalink']}",
                                color=discord.Color.orange()
                            )
                            embed.set_image(url=meme_post['url'])
                            embed.set_footer(text=f"👍 {meme_post['ups']} | 💬 {meme_post['num_comments']} | r/{chosen_subreddit} • Powered By SBModeration™")
                            
                            await interaction.response.send_message(embed=embed)
                            return
                
                # Fallback to meme API
                async with session.get('https://meme-api.herokuapp.com/gimme') as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        embed = discord.Embed(
                            title=data['title'],
                            url=data['postLink'],
                            color=discord.Color.orange()
                        )
                        embed.set_image(url=data['url'])
                        embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']} • Powered By SBModeration™")
                        
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message("❌ Couldn't fetch a meme right now!", ephemeral=True)
                        
        except Exception as e:
            logger.error(f"Error in meme command: {e}")
            await interaction.response.send_message("❌ An error occurred while fetching meme!", ephemeral=True)
    
    @app_commands.command(name="roast", description="Get a savage roast from Reddit")
    async def roast(self, interaction: discord.Interaction, target: discord.Member = None):
        """Get a random roast from Reddit roast subreddits"""
        try:
            # Popular roast subreddits
            roast_subreddits = [
                'RoastMe', 'rareinsults', 'clevercomebacks', 'MurderedByWords',
                'insults', 'roasts', 'savageroasts', 'BrandNewSentence'
            ]
            
            chosen_subreddit = random.choice(roast_subreddits)
            
            async with aiohttp.ClientSession() as session:
                reddit_url = f'https://www.reddit.com/r/{chosen_subreddit}/hot.json?limit=100'
                headers = {'User-Agent': 'Discord Bot Roast Fetcher 1.0'}
                
                async with session.get(reddit_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = data['data']['children']
                        
                        # Filter for text posts or posts with good titles
                        good_posts = []
                        for post in posts:
                            post_data = post['data']
                            if not post_data.get('over_18', False) and post_data.get('ups', 0) > 10:
                                title = post_data.get('title', '')
                                selftext = post_data.get('selftext', '')
                                if len(title) > 20 or len(selftext) > 20:
                                    good_posts.append(post_data)
                        
                        if good_posts:
                            roast_post = random.choice(good_posts)
                            
                            # Create roast content
                            roast_title = roast_post['title']
                            roast_content = roast_post.get('selftext', '')
                            
                            if target:
                                roast_text = f"{target.mention}, here's a roast for you:\n\n**{roast_title}**"
                                if roast_content and len(roast_content) < 1000:
                                    roast_text += f"\n\n{roast_content}"
                            else:
                                roast_text = f"**{roast_title}**"
                                if roast_content and len(roast_content) < 1000:
                                    roast_text += f"\n\n{roast_content}"
                            
                            embed = discord.Embed(
                                title="🔥 Savage Roast",
                                description=roast_text[:2000],
                                url=f"https://reddit.com{roast_post['permalink']}",
                                color=discord.Color.red()
                            )
                            embed.set_footer(text=f"👍 {roast_post['ups']} | 💬 {roast_post['num_comments']} | r/{chosen_subreddit} • Powered By SBModeration™")
                            
                            await interaction.response.send_message(embed=embed)
                            return
                
                # Fallback roasts if Reddit fails
                fallback_roasts = [
                    "I'd roast you, but my mom said I'm not allowed to burn trash.",
                    "You're like a software update. Whenever I see you, I think 'not now'.",
                    "I'm not saying you're stupid, but you have bad luck thinking.",
                    "You bring everyone so much joy... when you leave the room.",
                    "I'd explain it to you, but I don't have any crayons with me.",
                    "You're not pretty enough to be this dumb.",
                    "If I wanted to kill myself, I'd climb your ego and jump to your IQ.",
                    "You're the reason God created the middle finger."
                ]
                
                roast_text = random.choice(fallback_roasts)
                if target:
                    roast_text = f"{target.mention} {roast_text}"
                
                embed = discord.Embed(
                    title="🔥 Roast",
                    description=roast_text,
                    color=discord.Color.red()
                )
                
                await interaction.response.send_message(embed=embed)
                        
        except Exception as e:
            logger.error(f"Error in roast command: {e}")
            await interaction.response.send_message("❌ An error occurred while fetching roast!", ephemeral=True)

    @app_commands.command(name="joke", description="Get a random joke")
    async def joke(self, interaction: discord.Interaction):
        """Get a random joke"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://official-joke-api.appspot.com/random_joke') as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        embed = discord.Embed(
                            title="😂 Random Joke",
                            description=f"{data['setup']}\n\n||{data['punchline']}||",
                            color=discord.Color.gold()
                        )
                        
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message("❌ Couldn't fetch a joke right now!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in joke command: {e}")
            await interaction.response.send_message("❌ An error occurred while fetching joke!", ephemeral=True)
    
    @app_commands.command(name="say", description="Make the bot say something")
    @app_commands.describe(message="Message to say", channel="Channel to send to")
    async def say(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need Manage Messages permission!", ephemeral=True)
            return
        
        target_channel = channel or interaction.channel
        
        try:
            await target_channel.send(message)
            
            if channel and channel != interaction.channel:
                await interaction.response.send_message(f"✅ Message sent to {channel.mention}!", ephemeral=True)
            else:
                await interaction.response.send_message("✅ Message sent!", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send message: {e}", ephemeral=True)
    
    @app_commands.command(name="avatar", description="Get user's avatar")
    @app_commands.describe(user="User to get avatar of")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None):
        target_user = user or interaction.user
        
        embed = discord.Embed(
            title=f"{target_user.display_name}'s Avatar",
            color=target_user.color or discord.Color.blue()
        )
        
        if target_user.avatar:
            embed.set_image(url=target_user.avatar.url)
            embed.add_field(
                name="Download Links",
                value=f"[PNG]({target_user.avatar.replace(format='png').url}) | "
                      f"[JPG]({target_user.avatar.replace(format='jpg').url}) | "
                      f"[WEBP]({target_user.avatar.replace(format='webp').url})",
                inline=False
            )
        else:
            embed.description = "This user has no custom avatar."
            embed.set_image(url=target_user.default_avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="userinfo", description="Get information about a user")
    @app_commands.describe(user="User to get info about")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        target_user = user or interaction.user
        
        embed = discord.Embed(
            title="👤 User Information",
            color=target_user.color or discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if target_user.avatar:
            embed.set_thumbnail(url=target_user.avatar.url)
        
        # Basic info
        embed.add_field(name="Username", value=str(target_user), inline=True)
        embed.add_field(name="Display Name", value=target_user.display_name, inline=True)
        embed.add_field(name="User ID", value=target_user.id, inline=True)
        
        # Dates
        embed.add_field(
            name="Account Created",
            value=f"<t:{int(target_user.created_at.timestamp())}:F>\n<t:{int(target_user.created_at.timestamp())}:R>",
            inline=True
        )
        embed.add_field(
            name="Joined Server",
            value=f"<t:{int(target_user.joined_at.timestamp())}:F>\n<t:{int(target_user.joined_at.timestamp())}:R>",
            inline=True
        )
        
        # Status and activity
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡",
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚫"
        }
        embed.add_field(
            name="Status",
            value=f"{status_emoji.get(target_user.status, '⚫')} {target_user.status.name.title()}",
            inline=True
        )
        
        # Roles
        if len(target_user.roles) > 1:
            roles = [role.mention for role in target_user.roles[1:]]  # Skip @everyone
            roles_text = ", ".join(roles[:10])  # Limit to 10 roles
            if len(target_user.roles) > 11:
                roles_text += f" and {len(target_user.roles) - 11} more..."
            embed.add_field(name=f"Roles ({len(target_user.roles) - 1})", value=roles_text, inline=False)
        
        # Permissions
        key_perms = []
        if target_user.guild_permissions.administrator:
            key_perms.append("Administrator")
        elif target_user.guild_permissions.manage_guild:
            key_perms.append("Manage Server")
        elif target_user.guild_permissions.manage_channels:
            key_perms.append("Manage Channels")
        elif target_user.guild_permissions.manage_messages:
            key_perms.append("Manage Messages")
        elif target_user.guild_permissions.kick_members:
            key_perms.append("Kick Members")
        elif target_user.guild_permissions.ban_members:
            key_perms.append("Ban Members")
        
        if key_perms:
            embed.add_field(name="Key Permissions", value=", ".join(key_perms), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="serverinfo", description="Get information about the server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        embed = discord.Embed(
            title="🏰 Server Information",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(name="Server Name", value=guild.name, inline=True)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        
        # Dates
        embed.add_field(
            name="Created",
            value=f"<t:{int(guild.created_at.timestamp())}:F>\n<t:{int(guild.created_at.timestamp())}:R>",
            inline=True
        )
        
        # Member counts
        total_members = guild.member_count
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
        bot_count = sum(1 for member in guild.members if member.bot)
        
        embed.add_field(
            name="Members",
            value=f"Total: {total_members}\nOnline: {online_members}\nBots: {bot_count}",
            inline=True
        )
        
        # Channels
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed.add_field(
            name="Channels",
            value=f"Text: {text_channels}\nVoice: {voice_channels}\nCategories: {categories}",
            inline=True
        )
        
        # Other info
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Emojis", value=f"{len(guild.emojis)}/{guild.emoji_limit}", inline=True)
        embed.add_field(name="Boost Level", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
        
        # Features
        features = []
        if guild.features:
            feature_names = {
                'COMMUNITY': 'Community Server',
                'VERIFIED': 'Verified',
                'PARTNERED': 'Partnered',
                'DISCOVERABLE': 'Discoverable',
                'VANITY_URL': 'Vanity URL',
                'BANNER': 'Banner',
                'ANIMATED_ICON': 'Animated Icon'
            }
            
            for feature in guild.features:
                if feature in feature_names:
                    features.append(feature_names[feature])
        
        if features:
            embed.add_field(name="Features", value=", ".join(features), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="poll", description="Create a poll")
    @app_commands.describe(
        question="Poll question",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)"
    )
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None, option5: str = None):
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)
        if option5:
            options.append(option5)
        
        if len(options) > 5:
            await interaction.response.send_message("❌ Maximum 5 options allowed!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
        
        poll_text = ""
        for i, option in enumerate(options):
            poll_text += f"{reactions[i]} {option}\n"
        
        embed.add_field(name="Options", value=poll_text, inline=False)
        embed.set_footer(text=f"Poll by {interaction.user}")
        
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        # Add reactions
        for i in range(len(options)):
            await message.add_reaction(reactions[i])
    
    @app_commands.command(name="weather", description="Get weather information")
    @app_commands.describe(location="City name or location")
    async def weather(self, interaction: discord.Interaction, location: str):
        api_key = self.bot.config.get('weather_api_key')
        if not api_key:
            await interaction.response.send_message("❌ Weather API key not configured!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    embed = discord.Embed(
                        title=f"🌤️ Weather in {data['name']}, {data['sys']['country']}",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Main weather info
                    temp = data['main']['temp']
                    feels_like = data['main']['feels_like']
                    humidity = data['main']['humidity']
                    pressure = data['main']['pressure']
                    
                    weather_desc = data['weather'][0]['description'].title()
                    weather_icon = data['weather'][0]['icon']
                    
                    embed.add_field(name="Temperature", value=f"{temp}°C (feels like {feels_like}°C)", inline=True)
                    embed.add_field(name="Condition", value=weather_desc, inline=True)
                    embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
                    embed.add_field(name="Pressure", value=f"{pressure} hPa", inline=True)
                    
                    if 'wind' in data:
                        wind_speed = data['wind']['speed']
                        embed.add_field(name="Wind Speed", value=f"{wind_speed} m/s", inline=True)
                    
                    if 'visibility' in data:
                        visibility = data['visibility'] / 1000
                        embed.add_field(name="Visibility", value=f"{visibility} km", inline=True)
                    
                    # Weather icon
                    embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{weather_icon}@2x.png")
                    
                    await interaction.followup.send(embed=embed)
                    
                elif response.status == 404:
                    await interaction.followup.send("❌ Location not found!")
                else:
                    await interaction.followup.send("❌ Failed to fetch weather data!")
                    
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            await interaction.followup.send("❌ Error fetching weather data.")
    
    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="Your question for the 8-ball")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain", "It is decidedly so", "Without a doubt", "Yes definitely",
            "You may rely on it", "As I see it, yes", "Most likely", "Outlook good",
            "Yes", "Signs point to yes", "Reply hazy, try again", "Ask again later",
            "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
            "Don't count on it", "My reply is no", "My sources say no",
            "Outlook not so good", "Very doubtful"
        ]
        
        response = random.choice(responses)
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"*{response}*", inline=False)
        embed.set_footer(text=f"Asked by {interaction.user}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙" if result == "Heads" else "🪙"
        
        embed = discord.Embed(
            title=f"{emoji} Coin Flip",
            description=f"The coin landed on **{result}**!",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="dice", description="Roll dice")
    @app_commands.describe(sides="Number of sides on the dice (default: 6)", count="Number of dice to roll (default: 1)")
    async def dice(self, interaction: discord.Interaction, sides: int = 6, count: int = 1):
        if sides < 2 or sides > 100:
            await interaction.response.send_message("❌ Dice must have between 2 and 100 sides!", ephemeral=True)
            return
        
        if count < 1 or count > 10:
            await interaction.response.send_message("❌ You can roll between 1 and 10 dice!", ephemeral=True)
            return
        
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        
        embed = discord.Embed(
            title="🎲 Dice Roll",
            color=discord.Color.green()
        )
        
        if count == 1:
            embed.description = f"You rolled a **{rolls[0]}** on a {sides}-sided die!"
        else:
            rolls_text = ", ".join(map(str, rolls))
            embed.add_field(name="Individual Rolls", value=rolls_text, inline=False)
            embed.add_field(name="Total", value=str(total), inline=True)
            embed.add_field(name="Average", value=f"{total/count:.1f}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="choose", description="Choose randomly from a list of options")
    @app_commands.describe(options="Options separated by commas")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [choice.strip() for choice in options.split(',') if choice.strip()]
        
        if len(choices) < 2:
            await interaction.response.send_message("❌ Please provide at least 2 options separated by commas!", ephemeral=True)
            return
        
        if len(choices) > 20:
            await interaction.response.send_message("❌ Maximum 20 options allowed!", ephemeral=True)
            return
        
        chosen = random.choice(choices)
        
        embed = discord.Embed(
            title="🎯 Random Choice",
            description=f"I choose: **{chosen}**",
            color=discord.Color.random()
        )
        embed.add_field(name="Options", value=", ".join(choices), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="joke", description="Get a random joke")
    async def joke(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            async with self.session.get('https://official-joke-api.appspot.com/random_joke') as response:
                if response.status == 200:
                    data = await response.json()
                    
                    embed = discord.Embed(
                        title="😂 Random Joke",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Setup", value=data['setup'], inline=False)
                    embed.add_field(name="Punchline", value=data['punchline'], inline=False)
                    
                    await interaction.followup.send(embed=embed)
                else:
                    # Fallback jokes
                    jokes = [
                        ("Why don't scientists trust atoms?", "Because they make up everything!"),
                        ("Why did the scarecrow win an award?", "He was outstanding in his field!"),
                        ("Why don't eggs tell jokes?", "They'd crack each other up!"),
                        ("What do you call a fake noodle?", "An impasta!"),
                        ("Why did the math book look so sad?", "Because it had too many problems!")
                    ]
                    
                    setup, punchline = random.choice(jokes)
                    
                    embed = discord.Embed(
                        title="😂 Random Joke",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Setup", value=setup, inline=False)
                    embed.add_field(name="Punchline", value=punchline, inline=False)
                    
                    await interaction.followup.send(embed=embed)
                    
        except Exception as e:
            logger.error(f"Error fetching joke: {e}")
            await interaction.followup.send("❌ Error fetching joke.")

async def setup(bot):
    await bot.add_cog(Fun(bot))
