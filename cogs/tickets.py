import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
import logging
import io

logger = logging.getLogger(__name__)

class TicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_ticket_creation(interaction)
    
    async def handle_ticket_creation(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        
        # Check if user already has an open ticket
        existing_ticket = await self.bot.db.tickets.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "status": "open"
        })
        
        if existing_ticket:
            await interaction.response.send_message("❌ You already have an open ticket!", ephemeral=True)
            return
        
        try:
            guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
            ticket_settings = guild_settings.get('ticket_settings', {})
            
            # Get or create ticket category
            category_id = ticket_settings.get('category_id')
            category = None
            if category_id:
                category = discord.utils.get(interaction.guild.categories, id=int(category_id))
            
            if not category:
                # Create default category
                category = await interaction.guild.create_category("🎫 Tickets")
                ticket_settings['category_id'] = str(category.id)
                await self.bot.update_guild_settings(interaction.guild.id, {'ticket_settings': ticket_settings})
            
            # Create ticket channel
            ticket_number = await self.get_next_ticket_number(guild_id)
            channel_name = f"ticket-{ticket_number:04d}"
            
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Add support roles
            support_roles = ticket_settings.get('support_roles', [])
            for role_id in support_roles:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            ticket_channel = await interaction.guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Support ticket for {interaction.user} | Ticket #{ticket_number:04d}"
            )
            
            # Save ticket to database
            ticket_data = {
                "guild_id": guild_id,
                "user_id": user_id,
                "channel_id": str(ticket_channel.id),
                "ticket_number": ticket_number,
                "status": "open",
                "created_at": datetime.utcnow(),
                "messages": []
            }
            await self.bot.db.tickets.insert_one(ticket_data)
            
            # Send welcome message
            embed = discord.Embed(
                title=f"🎫 Ticket #{ticket_number:04d}",
                description=f"Hello {interaction.user.mention}! Thank you for creating a ticket.\n\nPlease describe your issue and our support team will assist you shortly.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="🎆 Ticket System • Powered By SBModeration™\nUse the buttons below to manage this ticket")
            
            view = TicketControlView(self.bot, ticket_number)
            await ticket_channel.send(embed=embed, view=view)
            
            await interaction.response.send_message(f"✅ Ticket created! Please check {ticket_channel.mention}", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            await interaction.response.send_message("❌ Failed to create ticket. Please try again later.", ephemeral=True)
    
    async def get_next_ticket_number(self, guild_id):
        """Get the next ticket number for the guild"""
        last_ticket = await self.bot.db.tickets.find_one(
            {"guild_id": guild_id},
            sort=[("ticket_number", -1)]
        )
        return (last_ticket['ticket_number'] + 1) if last_ticket else 1

class TicketControlView(discord.ui.View):
    def __init__(self, bot, ticket_number):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_number = ticket_number
    
    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        ticket_settings = guild_settings.get('ticket_settings', {})
        support_roles = ticket_settings.get('support_roles', [])
        
        has_permission = (
            interaction.user.guild_permissions.manage_channels or
            any(role.id in [int(r) for r in support_roles] for role in interaction.user.roles)
        )
        
        if not has_permission:
            await interaction.response.send_message("❌ You don't have permission to close tickets!", ephemeral=True)
            return
        
        await self.handle_ticket_close(interaction)
    
    @discord.ui.button(label="📋 Create Transcript", style=discord.ButtonStyle.secondary, custom_id="create_transcript")
    async def create_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            # Generate transcript
            transcript = await self.generate_transcript(interaction.channel)
            
            # Save as file
            transcript_file = discord.File(
                io.StringIO(transcript),
                filename=f"ticket-{self.ticket_number:04d}-transcript.txt"
            )
            
            await interaction.followup.send("📋 Ticket transcript:", file=transcript_file)
            
        except Exception as e:
            logger.error(f"Failed to create transcript: {e}")
            await interaction.followup.send("❌ Failed to create transcript.", ephemeral=True)
    
    async def handle_ticket_close(self, interaction: discord.Interaction):
        try:
            # Update ticket status in database
            await self.bot.db.tickets.update_one(
                {"channel_id": str(interaction.channel.id)},
                {
                    "$set": {
                        "status": "closed",
                        "closed_at": datetime.utcnow(),
                        "closed_by": str(interaction.user.id)
                    }
                }
            )
            
            # Generate and save transcript
            transcript = await self.generate_transcript(interaction.channel)
            
            # Save transcript to database
            await self.bot.db.transcripts.insert_one({
                "guild_id": str(interaction.guild.id),
                "ticket_number": self.ticket_number,
                "transcript": transcript,
                "created_at": datetime.utcnow()
            })
            
            embed = discord.Embed(
                title="🔒 Ticket Closed",
                description=f"This ticket has been closed by {interaction.user.mention}.\nThe channel will be deleted in 10 seconds.",
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Delete channel after delay
            await asyncio.sleep(10)
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Failed to close ticket: {e}")
            await interaction.response.send_message("❌ Failed to close ticket.", ephemeral=True)
    
    async def generate_transcript(self, channel):
        """Generate a text transcript of the ticket"""
        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            content = message.content or "[No text content]"
            
            # Handle attachments
            if message.attachments:
                attachments = ", ".join([att.filename for att in message.attachments])
                content += f" [Attachments: {attachments}]"
            
            # Handle embeds
            if message.embeds:
                content += f" [Embeds: {len(message.embeds)}]"
            
            messages.append(f"[{timestamp}] {message.author}: {content}")
        
        return "\n".join(messages)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Add persistent views
        self.bot.add_view(TicketView(bot))
    
    @app_commands.command(name="ticket-setup", description="Setup ticket system for this server")
    @app_commands.describe(
        category="Category for ticket channels",
        support_role="Role that can manage tickets"
    )
    async def ticket_setup(self, interaction: discord.Interaction, category: discord.CategoryChannel = None, support_role: discord.Role = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to setup tickets!", ephemeral=True)
            return
        
        try:
            guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
            ticket_settings = guild_settings.get('ticket_settings', {})
            
            if category:
                ticket_settings['category_id'] = str(category.id)
            
            if support_role:
                if 'support_roles' not in ticket_settings:
                    ticket_settings['support_roles'] = []
                if str(support_role.id) not in ticket_settings['support_roles']:
                    ticket_settings['support_roles'].append(str(support_role.id))
            
            await self.bot.update_guild_settings(interaction.guild.id, {'ticket_settings': ticket_settings})
            
            embed = discord.Embed(
                title="🎫 Ticket System Setup",
                description="Ticket system has been configured!",
                color=discord.Color.green()
            )
            
            if category:
                embed.add_field(name="Category", value=category.mention, inline=True)
            if support_role:
                embed.add_field(name="Support Role", value=support_role.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to setup tickets: {e}")
            await interaction.response.send_message("❌ Failed to setup ticket system.", ephemeral=True)
    
    @app_commands.command(name="ticket-panel", description="Create a ticket panel")
    @app_commands.describe(
        title="Title for the ticket panel",
        description="Description for the ticket panel"
    )
    async def ticket_panel(self, interaction: discord.Interaction, title: str = "🎫 Support Tickets", description: str = "Click the button below to create a support ticket."):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need Manage Server permission to create ticket panels!", ephemeral=True)
            return
        
        try:
            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blue()
            )
            embed.set_footer(text="Our support team will assist you as soon as possible!")
            
            view = TicketView(self.bot)
            await interaction.response.send_message(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Failed to create ticket panel: {e}")
            await interaction.response.send_message("❌ Failed to create ticket panel.", ephemeral=True)
    
    @app_commands.command(name="ticket-add", description="Add a user to the current ticket")
    @app_commands.describe(user="User to add to the ticket")
    async def ticket_add(self, interaction: discord.Interaction, user: discord.Member):
        # Check if this is a ticket channel
        ticket = await self.bot.db.tickets.find_one({
            "channel_id": str(interaction.channel.id),
            "status": "open"
        })
        
        if not ticket:
            await interaction.response.send_message("❌ This is not a ticket channel!", ephemeral=True)
            return
        
        # Check permissions
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        ticket_settings = guild_settings.get('ticket_settings', {})
        support_roles = ticket_settings.get('support_roles', [])
        
        has_permission = (
            interaction.user.guild_permissions.manage_channels or
            any(role.id in [int(r) for r in support_roles] for role in interaction.user.roles) or
            str(interaction.user.id) == ticket['user_id']
        )
        
        if not has_permission:
            await interaction.response.send_message("❌ You don't have permission to add users to this ticket!", ephemeral=True)
            return
        
        try:
            # Add user to channel
            await interaction.channel.set_permissions(
                user,
                read_messages=True,
                send_messages=True
            )
            
            embed = discord.Embed(
                title="✅ User Added",
                description=f"{user.mention} has been added to this ticket.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to add user to ticket: {e}")
            await interaction.response.send_message("❌ Failed to add user to ticket.", ephemeral=True)
    
    @app_commands.command(name="ticket-remove", description="Remove a user from the current ticket")
    @app_commands.describe(user="User to remove from the ticket")
    async def ticket_remove(self, interaction: discord.Interaction, user: discord.Member):
        # Check if this is a ticket channel
        ticket = await self.bot.db.tickets.find_one({
            "channel_id": str(interaction.channel.id),
            "status": "open"
        })
        
        if not ticket:
            await interaction.response.send_message("❌ This is not a ticket channel!", ephemeral=True)
            return
        
        # Check permissions
        guild_settings = await self.bot.get_guild_settings(interaction.guild.id)
        ticket_settings = guild_settings.get('ticket_settings', {})
        support_roles = ticket_settings.get('support_roles', [])
        
        has_permission = (
            interaction.user.guild_permissions.manage_channels or
            any(role.id in [int(r) for r in support_roles] for role in interaction.user.roles)
        )
        
        if not has_permission:
            await interaction.response.send_message("❌ You don't have permission to remove users from tickets!", ephemeral=True)
            return
        
        # Don't allow removing the ticket owner
        if str(user.id) == ticket['user_id']:
            await interaction.response.send_message("❌ You cannot remove the ticket owner!", ephemeral=True)
            return
        
        try:
            # Remove user from channel
            await interaction.channel.set_permissions(user, overwrite=None)
            
            embed = discord.Embed(
                title="✅ User Removed",
                description=f"{user.mention} has been removed from this ticket.",
                color=discord.Color.orange()
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to remove user from ticket: {e}")
            await interaction.response.send_message("❌ Failed to remove user from ticket.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
