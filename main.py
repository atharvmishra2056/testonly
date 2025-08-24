import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, InputText
import os
from flask import Flask
from threading import Thread
import random
import string
import asyncio
import time
import json
import aiohttp
import datetime
import pytz
from collections import defaultdict
import sqlite3
from typing import Optional, Union, List, Dict, Any
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests
import re
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

GUILD_ID = 1377883327771574372
VERIFY_CHANNEL_ID = 1377883328526680065
LOG_CHANNEL_ID = 1377883329755611280
WELCOME_CHANNEL_ID = 1387419489586380972
SERVICE_CHANNEL_ID = 1387386391800975390
GENERAL_CHANNEL_ID = 1377883329503821841
TICKET_CHANNEL_ID = 1387390000000000000  # Example ID
STARBOARD_CHANNEL_ID = 1387390000000000001  # Example ID
SUGGESTION_CHANNEL_ID = 1387390000000000002  # Example ID
GIVEAWAY_CHANNEL_ID = 1387390000000000003  # Example ID
LEVEL_CHANNEL_ID = 1387390000000000004  # Example ID
ECONOMY_CHANNEL_ID = 1387390000000000005  # Example ID
MUSIC_CHANNEL_ID = 1387390000000000006  # Example ID
MOD_LOG_CHANNEL_ID = 1387390000000000007  # Example ID
VOICE_LOG_CHANNEL_ID = 1387390000000000008  # Example ID
MEMBER_LOG_CHANNEL_ID = 1387390000000000009  # Example ID
MESSAGE_LOG_CHANNEL_ID = 1387390000000000010  # Example ID

MOD_ROLE_NAME = "Moderator"
MEMBER_ROLE_NAME = "KuzzMember"
ACTIVE_MEMBER_ROLE_NAME = "Active Member"
ADMIN_ROLE_NAME = "Admin"
STAFF_ROLE_NAME = "Staff"
VIP_ROLE_NAME = "VIP"
MUTED_ROLE_NAME = "Muted"
DJ_ROLE_NAME = "DJ"

BAD_WORDS = ["fuck", "nigga", "shit", "asshole", "bitch", "cunt", "whore", "slut", "retard"]
CAPTCHA_TIMEOUT = 180
BUTTON_COOLDOWN = 5
XP_COOLDOWN = 60
XP_PER_MESSAGE = 5
XP_FOR_ACTIVE_ROLE = 100
MAX_WARNINGS = 3
MUSIC_VOLUME = 0.5
DEFAULT_PREFIX = "/"

SERVICE_ROLES = {
    "facebook":  ["Facebook",  "<:Facebook:1387750761181610054>", 1387742165681180754],
    "discord":   ["Discord",   "<:discord_new:1387781149723463790>", 1387742348175216720],
    "instagram": ["Instagram", "<:instagram:1387473397553958923>", 1387735712874500096],
    "twitter":   ["Twitter",   "<:twitter:1387750022980042962>", 1387756089864486942],
    "tiktok":    ["TikTok",    "<:ticktock:1387750017242103900>", 1387756237566906488],
    "twitch":    ["Twitch",    "<:twitch:1387750756400107591>", 1387756062169366718],
    "snapchat":  ["Snapchat",  "<:snapchat:1387750764344250458>", 1387755991243952229],
    "youtube":   ["YouTube",   "<:Youtube:1387754175613370368>", 1387742474533077084],
    "spotify":   ["Spotify",   "<:Spotify:1387754178478346343>", 1387756124165505065],
}

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    
    # User data
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY,
                 xp INTEGER DEFAULT 0,
                 level INTEGER DEFAULT 1,
                 balance INTEGER DEFAULT 0,
                 daily_last_claimed TEXT,
                 warnings INTEGER DEFAULT 0,
                 muted_until TEXT,
                 timezone TEXT DEFAULT 'UTC')''')
    
    # Economy
    c.execute('''CREATE TABLE IF NOT EXISTS shop (
                 item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 price INTEGER NOT NULL,
                 description TEXT,
                 role_id INTEGER)''')
    
    # Tickets
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
                 ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 channel_id INTEGER NOT NULL,
                 created_at TEXT NOT NULL,
                 closed_by INTEGER,
                 closed_at TEXT)''')
    
    # Giveaways
    c.execute('''CREATE TABLE IF NOT EXISTS giveaways (
                 giveaway_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 channel_id INTEGER NOT NULL,
                 message_id INTEGER NOT NULL,
                 prize TEXT NOT NULL,
                 winners INTEGER NOT NULL,
                 ends_at TEXT NOT NULL,
                 hosted_by INTEGER NOT NULL,
                 ended INTEGER DEFAULT 0)''')
    
    # Suggestions
    c.execute('''CREATE TABLE IF NOT EXISTS suggestions (
                 suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 content TEXT NOT NULL,
                 status TEXT DEFAULT 'pending',
                 created_at TEXT NOT NULL,
                 reviewed_by INTEGER,
                 reviewed_at TEXT)''')
    
    # Custom commands
    c.execute('''CREATE TABLE IF NOT EXISTS custom_commands (
                 command_name TEXT PRIMARY KEY,
                 response TEXT NOT NULL,
                 created_by INTEGER NOT NULL,
                 created_at TEXT NOT NULL)''')
    
    # Invite tracking
    c.execute('''CREATE TABLE IF NOT EXISTS invites (
                 inviter_id INTEGER NOT NULL,
                 invitee_id INTEGER NOT NULL,
                 invite_code TEXT NOT NULL,
                 created_at TEXT NOT NULL,
                 PRIMARY KEY (invitee_id))''')
    
    # Starboard
    c.execute('''CREATE TABLE IF NOT EXISTS starboard (
                 message_id INTEGER PRIMARY KEY,
                 channel_id INTEGER NOT NULL,
                 author_id INTEGER NOT NULL,
                 content TEXT NOT NULL,
                 star_count INTEGER DEFAULT 0,
                 starred_by TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# --- KEEP ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "KuzzBot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.voice_states = True
intents.reactions = True
intents.guilds = True
intents.emojis = True
intents.integrations = True
intents.webhooks = True
intents.invites = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(DEFAULT_PREFIX),
    intents=intents,
    case_insensitive=True,
    help_command=None,
    strip_after_prefix=True
)

# --- IN-MEMORY DATA ---
captcha_sessions = {}
button_cooldowns = {}
xp_data = {}
giveaways = {}
active_giveaways = {}
ticket_channels = {}
music_queues = {}
now_playing_messages = {}
auto_responders = {}
reaction_roles = {}
invite_codes = {}
starboard_messages = {}
temp_voice_channels = {}
user_timezones = {}
custom_commands_cache = {}
shop_items = []
anti_spam = defaultdict(lambda: {"count": 0, "last_message": 0})
auto_moderation_rules = {}
reminder_tasks = {}

AUTO_ROLE_ENABLED = False
MUSIC_ENABLED = True
LEVEL_UP_MESSAGES_ENABLED = True
WELCOME_DM_ENABLED = True
ANTI_SPAM_ENABLED = True
AUTO_MOD_ENABLED = True
STARBOARD_ENABLED = True
SUGGESTION_ENABLED = True
TICKET_ENABLED = True
GIVEAWAY_ENABLED = True
ECONOMY_ENABLED = True

# --- MODALS & VIEWS ---
class CaptchaModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="🔒 CAPTCHA Verification")
        self.user_id = user_id
        self.add_item(InputText(label="Enter the CAPTCHA Code", placeholder="Case-sensitive code...", style=discord.InputTextStyle.short, required=True))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user_input = self.children[0].value
        correct_code = captcha_sessions.get(self.user_id)
        
        captcha_sessions.pop(self.user_id, None)

        if not correct_code or user_input != correct_code:
            await interaction.followup.send("❌ Incorrect CAPTCHA. Please try again.", ephemeral=True)
            return

        member = interaction.user
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
        
        if not role:
            await interaction.followup.send("Verification role not found on the server. Please contact an admin.", ephemeral=True)
            return
            
        if role in member.roles:
            await interaction.followup.send("You are already verified!", ephemeral=True)
            return

        try:
            await member.add_roles(role)
            
            verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
            if verify_channel:
                await verify_channel.set_permissions(member, view_channel=False)
            
            welcome_embed = discord.Embed(
                title="🎉 Welcome to KuzzMarket!",
                description=f"Congratulations, {member.mention}! You are verified. Head over to <#{GENERAL_CHANNEL_ID}>.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=welcome_embed, ephemeral=True)
            
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(title="✅ Verification Log", color=discord.Color.green())
                log_embed.add_field(name="User", value=f"{member.name} ({member.id})", inline=False)
                log_embed.add_field(name="Role Granted", value=role.name, inline=False)
                log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                await log_channel.send(embed=log_embed)
                
        except discord.Forbidden:
            await interaction.followup.send("I don't have permissions to assign roles. Please contact an admin.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)
            logger.error(f"Error during verification for {member.id}: {e}")

class OpenCaptchaModalView(View):
    def __init__(self, user_id):
        super().__init__(timeout=CAPTCHA_TIMEOUT)
        self.user_id = user_id

    @discord.ui.button(label="Enter Code", style=discord.ButtonStyle.blurple)
    async def open_modal_button(self, button: Button, interaction: discord.Interaction):
        modal = CaptchaModal(user_id=self.user_id)
        await interaction.response.send_modal(modal)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify Now", style=discord.ButtonStyle.green, custom_id="verify_kuzz_v5")
    async def verify_button(self, button: Button, interaction: discord.Interaction):
        member = interaction.user
        
        last_click = button_cooldowns.get(member.id, 0)
        if time.time() < last_click + BUTTON_COOLDOWN:
            await interaction.response.send_message("Please wait a few seconds before trying again.", ephemeral=True, delete_after=5)
            return
        button_cooldowns[member.id] = time.time()

        captcha_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        captcha_sessions[member.id] = captcha_code
        
        embed = discord.Embed(
            title="Your CAPTCHA Code Is:",
            description=f"**{captcha_code}**",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Click 'Enter Code' below. You have {CAPTCHA_TIMEOUT} seconds.")

        await interaction.response.send_message(
            embed=embed,
            view=OpenCaptchaModalView(user_id=member.id),
            ephemeral=True
        )

class ServiceView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for service_name, details in SERVICE_ROLES.items():
            label, emoji, role_id = details
            button = Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"service_role_{service_name}"
            )
            button.callback = self.service_button_callback
            self.add_item(button)

    async def service_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        service_name = interaction.data['custom_id'].split('_')[-1]
        
        if service_name not in SERVICE_ROLES:
            await interaction.followup.send("Error: This button is misconfigured.", ephemeral=True)
            return
            
        role_id = SERVICE_ROLES[service_name][2]
        role = interaction.guild.get_role(role_id)
        member = interaction.user

        if not role:
            await interaction.followup.send(f"The '{SERVICE_ROLES[service_name][0]}' role was not found. Please contact an admin.", ephemeral=True)
            return

        if role in member.roles:
            await member.remove_roles(role)
            await interaction.followup.send(f"Removed the **{role.name}** role.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.followup.send(f"You've been given the **{role.name}** role!", ephemeral=True)

class TicketModal(Modal):
    def __init__(self):
        super().__init__(title="Create a Ticket")
        self.add_item(InputText(label="Subject", placeholder="Brief description of your issue", style=discord.InputTextStyle.short, required=True))
        self.add_item(InputText(label="Details", placeholder="Provide more details about your issue", style=discord.InputTextStyle.paragraph, required=True))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        subject = self.children[0].value
        details = self.children[1].value
        user = interaction.user
        guild = interaction.guild
        
        # Create ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        ticket_number = len(ticket_channels) + 1
        channel_name = f"ticket-{ticket_number}-{user.name}"
        
        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=discord.utils.get(guild.categories, name="TICKETS")
            )
            
            ticket_channels[user.id] = ticket_channel.id
            
            # Save to database
            conn = sqlite3.connect('kuzzbot.db')
            c = conn.cursor()
            c.execute('''INSERT INTO tickets (user_id, channel_id, created_at)
                         VALUES (?, ?, ?)''', 
                      (user.id, ticket_channel.id, datetime.datetime.now().isoformat()))
            conn.commit()
            conn.close()
            
            # Send ticket message
            embed = discord.Embed(
                title=f"Ticket #{ticket_number}",
                description=f"**Subject:** {subject}\n\n**Details:** {details}",
                color=discord.Color.blue()
            )
            embed.set_author(name=f"{user.name} ({user.id})", icon_url=user.display_avatar.url)
            embed.set_footer(text="Use the buttons below to manage this ticket")
            
            view = TicketView(user.id, ticket_channel.id)
            await ticket_channel.send(content=f"{staff_role.mention if staff_role else '@Staff'}", embed=embed, view=view)
            
            await interaction.followup.send(f"✅ Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
            
            # Log ticket creation
            log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(title="🎫 Ticket Created", color=discord.Color.green())
                log_embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=False)
                log_embed.add_field(name="Channel", value=ticket_channel.mention, inline=False)
                log_embed.add_field(name="Subject", value=subject, inline=False)
                log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                await log_channel.send(embed=log_embed)
                
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to create channels. Please contact an admin.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {e}", ephemeral=True)
            logger.error(f"Error creating ticket for {user.id}: {e}")

class TicketView(View):
    def __init__(self, user_id, channel_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.channel_id = channel_id

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, button: Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        channel = interaction.channel
        user = interaction.guild.get_member(self.user_id)
        
        # Update database
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        c.execute('''UPDATE tickets 
                     SET closed_by = ?, closed_at = ?
                     WHERE channel_id = ?''', 
                  (interaction.user.id, datetime.datetime.now().isoformat(), self.channel_id))
        conn.commit()
        conn.close()
        
        # Remove from active tickets
        if self.user_id in ticket_channels:
            del ticket_channels[self.user_id]
        
        # Send confirmation
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"This ticket has been closed by {interaction.user.mention}",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
        
        # Notify user via DM
        if user and WELCOME_DM_ENABLED:
            try:
                dm_embed = discord.Embed(
                    title="Your Ticket Has Been Closed",
                    description=f"Your ticket in {interaction.guild.name} has been closed by {interaction.user.name}",
                    color=discord.Color.orange()
                )
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
        
        # Log ticket closure
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🎫 Ticket Closed", color=discord.Color.red())
            log_embed.add_field(name="User", value=f"{user.mention if user else 'Unknown'} ({self.user_id})", inline=False)
            log_embed.add_field(name="Closed By", value=interaction.user.mention, inline=False)
            log_embed.add_field(name="Channel", value=channel.mention, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
        
        # Schedule channel deletion
        await asyncio.sleep(5)
        try:
            await channel.delete()
        except discord.Forbidden:
            pass

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_ticket")
    async def claim_ticket(self, button: Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.followup.send("❌ You don't have permission to claim tickets.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Ticket Claimed",
            description=f"This ticket has been claimed by {interaction.user.mention}",
            color=discord.Color.green()
        )
        await interaction.channel.send(embed=embed)
        
        # Log ticket claim
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🎫 Ticket Claimed", color=discord.Color.green())
            log_embed.add_field(name="Claimed By", value=interaction.user.mention, inline=False)
            log_embed.add_field(name="Channel", value=interaction.channel.mention, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)

class GiveawayView(View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Join Giveaway", style=discord.ButtonStyle.green, custom_id=f"giveaway_join_{giveaway_id}")
    async def join_giveaway(self, button: Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        
        # Check if user already joined
        c.execute('''SELECT 1 FROM giveaway_entries 
                     WHERE giveaway_id = ? AND user_id = ?''', 
                  (self.giveaway_id, user_id))
        
        if c.fetchone():
            await interaction.followup.send("You have already joined this giveaway!", ephemeral=True)
            conn.close()
            return
        
        # Add entry
        c.execute('''INSERT INTO giveaway_entries (giveaway_id, user_id)
                     VALUES (?, ?)''', 
                  (self.giveaway_id, user_id))
        conn.commit()
        conn.close()
        
        await interaction.followup.send("✅ You have successfully joined the giveaway!", ephemeral=True)
        
        # Update giveaway message
        await update_giveaway_message(self.giveaway_id)

class SuggestionView(View):
    def __init__(self, suggestion_id):
        super().__init__(timeout=None)
        self.suggestion_id = suggestion_id

    @discord.ui.button(label="👍 Upvote", style=discord.ButtonStyle.green, custom_id=f"suggestion_upvote_{suggestion_id}")
    async def upvote_suggestion(self, button: Button, interaction: discord.Interaction):
        await self.vote_suggestion(interaction, 1)

    @discord.ui.button(label="👎 Downvote", style=discord.ButtonStyle.red, custom_id=f"suggestion_downvote_{suggestion_id}")
    async def downvote_suggestion(self, button: Button, interaction: discord.Interaction):
        await self.vote_suggestion(interaction, -1)

    async def vote_suggestion(self, interaction: discord.Interaction, vote_type):
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        
        # Check if user already voted
        c.execute('''SELECT vote_type FROM suggestion_votes 
                     WHERE suggestion_id = ? AND user_id = ?''', 
                  (self.suggestion_id, user_id))
        
        existing_vote = c.fetchone()
        
        if existing_vote:
            if existing_vote[0] == vote_type:
                await interaction.followup.send("You have already voted this way!", ephemeral=True)
                conn.close()
                return
            else:
                # Update vote
                c.execute('''UPDATE suggestion_votes 
                             SET vote_type = ?
                             WHERE suggestion_id = ? AND user_id = ?''', 
                          (vote_type, self.suggestion_id, user_id))
        else:
            # Add new vote
            c.execute('''INSERT INTO suggestion_votes (suggestion_id, user_id, vote_type)
                         VALUES (?, ?, ?)''', 
                      (self.suggestion_id, user_id, vote_type))
        
        conn.commit()
        conn.close()
        
        await interaction.followup.send("✅ Your vote has been recorded!", ephemeral=True)
        
        # Update suggestion message
        await update_suggestion_message(self.suggestion_id)

class MusicView(View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red, custom_id="music_stop")
    async def stop_music(self, button: Button, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            music_queues.pop(self.guild_id, None)
            await interaction.response.send_message("⏹️ Music stopped.", ephemeral=True)
        else:
            await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary, custom_id="music_pause")
    async def pause_music(self, button: Button, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ Music paused.", ephemeral=True)
        else:
            await interaction.response.send_message("No music is currently playing.", ephemeral=True)

    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.green, custom_id="music_resume")
    async def resume_music(self, button: Button, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("▶️ Music resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("No music is currently paused.", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.primary, custom_id="music_skip")
    async def skip_music(self, button: Button, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped to next song.", ephemeral=True)
            # The next song will play automatically in the after callback
        else:
            await interaction.response.send_message("No music is currently playing.", ephemeral=True)

    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, custom_id="music_shuffle")
    async def shuffle_music(self, button: Button, interaction: discord.Interaction):
        if self.guild_id in music_queues and len(music_queues[self.guild_id]) > 1:
            random.shuffle(music_queues[self.guild_id])
            await interaction.response.send_message("🔀 Queue shuffled.", ephemeral=True)
        else:
            await interaction.response.send_message("Not enough songs in the queue to shuffle.", ephemeral=True)

class PollView(View):
    def __init__(self, poll_id, options):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        
        for i, option in enumerate(options):
            button = Button(
                label=option,
                style=discord.ButtonStyle.primary,
                custom_id=f"poll_vote_{poll_id}_{i}"
            )
            button.callback = self.vote_callback
            self.add_item(button)

    async def vote_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        option_index = int(interaction.data['custom_id'].split('_')[-1])
        
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        
        # Check if user already voted
        c.execute('''SELECT option_index FROM poll_votes 
                     WHERE poll_id = ? AND user_id = ?''', 
                  (self.poll_id, user_id))
        
        existing_vote = c.fetchone()
        
        if existing_vote:
            if existing_vote[0] == option_index:
                await interaction.followup.send("You have already voted for this option!", ephemeral=True)
                conn.close()
                return
            else:
                # Update vote
                c.execute('''UPDATE poll_votes 
                             SET option_index = ?
                             WHERE poll_id = ? AND user_id = ?''', 
                          (option_index, self.poll_id, user_id))
        else:
            # Add new vote
            c.execute('''INSERT INTO poll_votes (poll_id, user_id, option_index)
                         VALUES (?, ?, ?)''', 
                      (self.poll_id, user_id, option_index))
        
        conn.commit()
        conn.close()
        
        await interaction.followup.send("✅ Your vote has been recorded!", ephemeral=True)
        
        # Update poll message
        await update_poll_message(self.poll_id)

# --- HELPER FUNCTIONS ---
async def send_verify_logic(ctx_or_interaction):
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if not channel:
        response_message = "❌ Verify channel not found!"
        if isinstance(ctx_or_interaction, discord.ApplicationContext):
            await ctx_or_interaction.followup.send(response_message, ephemeral=True)
        else:
            await ctx_or_interaction.send(response_message)
        return

    async for message in channel.history(limit=10):
        if message.author == bot.user:
            await message.delete()

    embed = discord.Embed(
        title="✅ Server Verification",
        description="Welcome to KuzzMarket!\n\nClick the button below to prove you are human and gain access to the server.",
        color=discord.Color.green()
    )
    embed.set_footer(text="KuzzMarket - Powered by KuzzBot")
    await channel.send(embed=embed, view=VerifyView())

    response_message = "✅ Verification message sent successfully!"
    if isinstance(ctx_or_interaction, discord.ApplicationContext):
        await ctx_or_interaction.followup.send(response_message, ephemeral=True)
    else:
        await ctx_or_interaction.send(response_message)

async def send_services_logic(ctx_or_interaction):
    channel = bot.get_channel(SERVICE_CHANNEL_ID)
    if not channel:
        response_message = "❌ Service channel not found or bot lacks permissions!"
        if isinstance(ctx_or_interaction, discord.ApplicationContext):
            await ctx_or_interaction.followup.send(response_message, ephemeral=True)
        else:
            await ctx_or_interaction.send(response_message)
        return

    async for message in channel.history(limit=10):
        if message.author == bot.user:
            await message.delete()

    embed = discord.Embed(
        title="🛒 Service & Platform Roles",
        description="Click the buttons below to assign yourself roles for the services you are interested in. This will give you access to related channels.\n\n_Clicking a button again will remove the role._",
        color=discord.Color.gold()
    )
    await channel.send(embed=embed, view=ServiceView())

    response_message = "✅ Service role message sent to the service channel!"
    if isinstance(ctx_or_interaction, discord.ApplicationContext):
        await ctx_or_interaction.followup.send(response_message, ephemeral=True)
    else:
        await ctx_or_interaction.send(response_message)

async def update_giveaway_message(giveaway_id):
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    
    # Get giveaway details
    c.execute('''SELECT g.message_id, g.channel_id, g.prize, g.winners, g.ends_at, g.ended
                 FROM giveaways g
                 WHERE g.giveaway_id = ?''', (giveaway_id,))
    giveaway = c.fetchone()
    
    if not giveaway:
        conn.close()
        return
    
    message_id, channel_id, prize, winners, ends_at, ended = giveaway
    
    # Get entry count
    c.execute('''SELECT COUNT(*) FROM giveaway_entries 
                 WHERE giveaway_id = ?''', (giveaway_id,))
    entry_count = c.fetchone()[0]
    
    conn.close()
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        embed = message.embeds[0]
        embed.description = f"🎁 **Prize:** {prize}\n👥 **Winners:** {winners}\n🎫 **Entries:** {entry_count}\n⏰ **Ends:** <t:{int(datetime.datetime.fromisoformat(ends_at).timestamp()}:R>"
        
        if ended:
            embed.title = "🎉 GIVEAWAY ENDED"
            embed.color = discord.Color.red()
        else:
            embed.title = "🎉 GIVEAWAY"
            embed.color = discord.Color.blue()
        
        await message.edit(embed=embed)
    except discord.NotFound:
        pass

async def update_suggestion_message(suggestion_id):
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    
    # Get suggestion details
    c.execute('''SELECT s.message_id, s.channel_id, s.content, s.status
                 FROM suggestions s
                 WHERE s.suggestion_id = ?''', (suggestion_id,))
    suggestion = c.fetchone()
    
    if not suggestion:
        conn.close()
        return
    
    message_id, channel_id, content, status = suggestion
    
    # Get vote counts
    c.execute('''SELECT 
                 SUM(CASE WHEN vote_type = 1 THEN 1 ELSE 0 END) as upvotes,
                 SUM(CASE WHEN vote_type = -1 THEN 1 ELSE 0 END) as downvotes
                 FROM suggestion_votes 
                 WHERE suggestion_id = ?''', (suggestion_id,))
    votes = c.fetchone()
    upvotes, downvotes = votes if votes else (0, 0)
    
    conn.close()
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        embed = message.embeds[0]
        embed.description = content
        embed.add_field(name="Status", value=status.title(), inline=False)
        embed.add_field(name="Votes", value=f"👍 {upvotes} | 👎 {downvotes}", inline=False)
        
        if status == "approved":
            embed.color = discord.Color.green()
        elif status == "rejected":
            embed.color = discord.Color.red()
        else:
            embed.color = discord.Color.blue()
        
        await message.edit(embed=embed)
    except discord.NotFound:
        pass

async def update_poll_message(poll_id):
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    
    # Get poll details
    c.execute('''SELECT p.message_id, p.channel_id, p.question, p.options
                 FROM polls p
                 WHERE p.poll_id = ?''', (poll_id,))
    poll = c.fetchone()
    
    if not poll:
        conn.close()
        return
    
    message_id, channel_id, question, options_json = poll
    options = json.loads(options_json)
    
    # Get vote counts
    c.execute('''SELECT option_index, COUNT(*) 
                 FROM poll_votes 
                 WHERE poll_id = ?
                 GROUP BY option_index''', (poll_id,))
    vote_counts = dict(c.fetchall())
    
    total_votes = sum(vote_counts.values())
    
    conn.close()
    
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        embed = discord.Embed(
            title=f"📊 Poll: {question}",
            color=discord.Color.blue()
        )
        
        for i, option in enumerate(options):
            votes = vote_counts.get(i, 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            embed.add_field(
                name=option,
                value=f"{votes} votes ({percentage:.1f}%)",
                inline=False
            )
        
        embed.set_footer(text=f"Total votes: {total_votes}")
        
        await message.edit(embed=embed)
    except discord.NotFound:
        pass

async def play_music(guild_id, voice_channel, song):
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    
    music_queues[guild_id].append(song)
    
    if not voice_channel.guild.voice_client or not voice_channel.guild.voice_client.is_playing():
        await play_next_song(guild_id)

async def play_next_song(guild_id):
    if guild_id not in music_queues or not music_queues[guild_id]:
        return
    
    song = music_queues[guild_id].pop(0)
    
    voice_client = bot.get_guild(guild_id).voice_client
    
    # Download and play song
    # This is a simplified version - in a real bot, you'd use a music library like wavelink
    try:
        # Simulate playing a song
        await asyncio.sleep(song['duration'])
        
        if guild_id in music_queues and music_queues[guild_id]:
            await play_next_song(guild_id)
    except Exception as e:
        logger.error(f"Error playing music: {e}")

def get_level(xp):
    return int((xp / 100) ** 0.5)

def get_xp_for_level(level):
    return level ** 2 * 100

async def create_level_card(user, level, xp, next_level_xp):
    # Create a level card image
    img = Image.new('RGB', (800, 200), color=(36, 39, 49))
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", 40)
        info_font = ImageFont.truetype("arial.ttf", 24)
        progress_font = ImageFont.truetype("arial.ttf", 20)
    except:
        title_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        progress_font = ImageFont.load_default()
    
    # Draw user info
    draw.text((20, 20), f"{user.name}'s Level", fill=(255, 255, 255), font=title_font)
    draw.text((20, 80), f"Level: {level}", fill=(255, 255, 255), font=info_font)
    draw.text((20, 120), f"XP: {xp}/{next_level_xp}", fill=(255, 255, 255), font=info_font)
    
    # Draw progress bar
    progress = min(xp / next_level_xp, 1.0)
    bar_width = 600
    bar_height = 30
    bar_x = 20
    bar_y = 160
    
    # Background
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(58, 61, 73))
    
    # Progress
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_width * progress), bar_y + bar_height], fill=(76, 175, 80))
    
    # Progress text
    progress_text = f"{progress * 100:.1f}%"
    text_width, text_height = progress_font.getsize(progress_text)
    draw.text((bar_x + bar_width // 2 - text_width // 2, bar_y + bar_height // 2 - text_height // 2), 
              progress_text, fill=(255, 255, 255), font=progress_font)
    
    # Save to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return discord.File(img_bytes, filename='level_card.png')

async def send_welcome_message(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return
    
    # Create welcome embed
    embed = discord.Embed(
        title="🎉 Welcome to KuzzMarket!",
        description=f"Hello {member.mention}, welcome to our community!\n\n"
                   f"Please verify yourself in <#{VERIFY_CHANNEL_ID}> to gain access to the server.",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Member #{len(member.guild.members)}")
    
    await channel.send(embed=embed)
    
    # Send DM if enabled
    if WELCOME_DM_ENABLED:
        try:
            dm_embed = discord.Embed(
                title="Welcome to KuzzMarket!",
                description=f"Hello {member.name}, thank you for joining our server!\n\n"
                           f"Please complete the verification process to gain full access to the server.",
                color=discord.Color.blue()
            )
            dm_embed.add_field(
                name="Verification Steps",
                value="1. Go to the verification channel\n"
                      "2. Click the verify button\n"
                      "3. Complete the CAPTCHA\n"
                      "4. Enjoy the server!",
                inline=False
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

async def send_leave_message(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return
    
    embed = discord.Embed(
        title="👋 Member Left",
        description=f"{member.name} has left the server.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await channel.send(embed=embed)

async def log_message_edit(message, before, after):
    channel = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
    if not channel:
        return
    
    embed = discord.Embed(
        title="✏️ Message Edited",
        color=discord.Color.orange()
    )
    embed.set_author(name=f"{message.author.name} ({message.author.id})", icon_url=message.author.display_avatar.url)
    embed.add_field(name="Channel", value=message.channel.mention, inline=False)
    embed.add_field(name="Before", value=before.content[:1024] or "No content", inline=False)
    embed.add_field(name="After", value=after.content[:1024] or "No content", inline=False)
    embed.set_footer(text=f"Message ID: {message.id} | Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    await channel.send(embed=embed)

async def log_message_delete(message):
    channel = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
    if not channel:
        return
    
    embed = discord.Embed(
        title="🗑️ Message Deleted",
        color=discord.Color.red()
    )
    embed.set_author(name=f"{message.author.name} ({message.author.id})", icon_url=message.author.display_avatar.url)
    embed.add_field(name="Channel", value=message.channel.mention, inline=False)
    embed.add_field(name="Content", value=message.content[:1024] or "No content", inline=False)
    embed.set_footer(text=f"Message ID: {message.id} | Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    await channel.send(embed=embed)

async def log_member_join(member):
    channel = bot.get_channel(MEMBER_LOG_CHANNEL_ID)
    if not channel:
        return
    
    embed = discord.Embed(
        title="➕ Member Joined",
        description=f"{member.mention} joined the server.",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.set_footer(text=f"Member ID: {member.id} | Server Members: {len(member.guild.members)}")
    
    await channel.send(embed=embed)

async def log_member_leave(member):
    channel = bot.get_channel(MEMBER_LOG_CHANNEL_ID)
    if not channel:
        return
    
    embed = discord.Embed(
        title="➖ Member Left",
        description=f"{member.mention} left the server.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Roles", value=", ".join([role.mention for role in member.roles[:3]]), inline=True)
    embed.set_footer(text=f"Member ID: {member.id} | Server Members: {len(member.guild.members)}")
    
    await channel.send(embed=embed)

async def log_role_update(member, before, after):
    channel = bot.get_channel(MEMBER_LOG_CHANNEL_ID)
    if not channel:
        return
    
    added_roles = [role for role in after if role not in before]
    removed_roles = [role for role in before if role not in after]
    
    if not added_roles and not removed_roles:
        return
    
    embed = discord.Embed(
        title="🔘 Roles Updated",
        description=f"{member.mention}'s roles have been updated.",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    
    if added_roles:
        embed.add_field(name="Added Roles", value=", ".join([role.mention for role in added_roles]), inline=False)
    
    if removed_roles:
        embed.add_field(name="Removed Roles", value=", ".join([role.mention for role in removed_roles]), inline=False)
    
    embed.set_footer(text=f"Member ID: {member.id} | Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    await channel.send(embed=embed)

async def log_voice_state_update(member, before, after):
    channel = bot.get_channel(VOICE_LOG_CHANNEL_ID)
    if not channel:
        return
    
    # Check if the member joined/left a channel
    if before.channel != after.channel:
        if after.channel:
            # Joined a channel
            embed = discord.Embed(
                title="🔊 Voice Channel Joined",
                description=f"{member.mention} joined {after.channel.mention}",
                color=discord.Color.green()
            )
        else:
            # Left a channel
            embed = discord.Embed(
                title="🔇 Voice Channel Left",
                description=f"{member.mention} left {before.channel.mention}",
                color=discord.Color.red()
            )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member ID: {member.id} | Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        await channel.send(embed=embed)
    
    # Check if the member was muted/deafened
    if before.mute != after.mute or before.deaf != after.deaf:
        embed = discord.Embed(
            title="🔇 Voice State Updated",
            description=f"{member.mention}'s voice state was updated.",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        if before.mute != after.mute:
            embed.add_field(name="Muted", value="Yes" if after.mute else "No", inline=True)
        
        if before.deaf != after.deaf:
            embed.add_field(name="Deafened", value="Yes" if after.deaf else "No", inline=True)
        
        embed.set_footer(text=f"Member ID: {member.id} | Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        await channel.send(embed=embed)

async def check_giveaways():
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    
    # Get active giveaways that have ended
    c.execute('''SELECT giveaway_id, channel_id, message_id, prize, winners, hosted_by
                 FROM giveaways
                 WHERE ended = 0 AND ends_at <= ?''', 
              (datetime.datetime.now().isoformat(),))
    
    ended_giveaways = c.fetchall()
    
    for giveaway in ended_giveaways:
        giveaway_id, channel_id, message_id, prize, winners, hosted_by = giveaway
        
        # Get entries
        c.execute('''SELECT user_id FROM giveaway_entries 
                     WHERE giveaway_id = ?''', (giveaway_id,))
        entries = [row[0] for row in c.fetchall()]
        
        if not entries:
            # No entries, end the giveaway
            c.execute('''UPDATE giveaways SET ended = 1 WHERE giveaway_id = ?''', (giveaway_id,))
            conn.commit()
            continue
        
        # Select winners
        winner_count = min(winners, len(entries))
        winners_list = random.sample(entries, winner_count)
        
        # Mark giveaway as ended
        c.execute('''UPDATE giveaways SET ended = 1 WHERE giveaway_id = ?''', (giveaway_id,))
        conn.commit()
        
        # Get channel and message
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        
        try:
            message = await channel.fetch_message(message_id)
            
            # Update message
            embed = message.embeds[0]
            embed.title = "🎉 GIVEAWAY ENDED"
            embed.color = discord.Color.red()
            embed.description = f"🎁 **Prize:** {prize}\n👥 **Winners:** {winners}\n🎫 **Entries:** {len(entries)}"
            
            # Add winners field
            winners_mentions = []
            for winner_id in winners_list:
                winner = channel.guild.get_member(winner_id)
                if winner:
                    winners_mentions.append(winner.mention)
            
            if winners_mentions:
                embed.add_field(name="Winners", value="\n".join(winners_mentions), inline=False)
            
            await message.edit(embed=embed)
            
            # Announce winners
            winners_text = ", ".join(winners_mentions) if winners_mentions else "No valid winners"
            await channel.send(f"🎉 Congratulations to {winners_text} for winning the **{prize}** giveaway!")
            
            # DM winners
            for winner_id in winners_list:
                winner = channel.guild.get_member(winner_id)
                if winner:
                    try:
                        dm_embed = discord.Embed(
                            title="🎉 You Won a Giveaway!",
                            description=f"Congratulations! You won the **{prize}** giveaway in {channel.guild.name}!",
                            color=discord.Color.green()
                        )
                        await winner.send(embed=dm_embed)
                    except discord.Forbidden:
                        pass
            
            # Log giveaway end
            log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(title="🎉 Giveaway Ended", color=discord.Color.green())
                log_embed.add_field(name="Prize", value=prize, inline=False)
                log_embed.add_field(name="Winners", value=", ".join(winners_mentions) if winners_mentions else "None", inline=False)
                log_embed.add_field(name="Entries", value=str(len(entries)), inline=False)
                log_embed.set_footer(text=f"Giveaway ID: {giveaway_id} | Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                await log_channel.send(embed=log_embed)
                
        except discord.NotFound:
            pass
    
    conn.close()

async def check_reminders():
    current_time = datetime.datetime.now()
    
    # Create a copy of the reminders to avoid modifying during iteration
    reminders_to_remove = []
    
    for reminder_id, reminder in reminder_tasks.items():
        if reminder['time'] <= current_time:
            # Send reminder
            user = bot.get_user(reminder['user_id'])
            if user:
                try:
                    embed = discord.Embed(
                        title="⏰ Reminder",
                        description=reminder['message'],
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text=f"Set at: {reminder['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                    await user.send(embed=embed)
                except discord.Forbidden:
                    pass
            
            reminders_to_remove.append(reminder_id)
    
    # Remove completed reminders
    for reminder_id in reminders_to_remove:
        del reminder_tasks[reminder_id]

async def check_mutes():
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    
    # Get users who should be unmuted
    c.execute('''SELECT user_id FROM users 
                 WHERE muted_until IS NOT NULL AND muted_until <= ?''', 
              (datetime.datetime.now().isoformat(),))
    
    muted_users = [row[0] for row in c.fetchall()]
    
    for user_id in muted_users:
        # Get guild
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            continue
        
        member = guild.get_member(user_id)
        if not member:
            continue
        
        # Remove muted role
        muted_role = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
        if muted_role and muted_role in member.roles:
            try:
                await member.remove_roles(muted_role)
                
                # Update database
                c.execute('''UPDATE users SET muted_until = NULL WHERE user_id = ?''', (user_id,))
                conn.commit()
                
                # Notify user
                try:
                    await member.send("Your mute has expired. You can now speak in the server again.")
                except discord.Forbidden:
                    pass
                
                # Log unmute
                log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(title="🔇 Automatic Unmute", color=discord.Color.green())
                    log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
                    log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    await log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                pass
    
    conn.close()

# --- TASKS ---
@tasks.loop(seconds=60)
async def giveaway_checker():
    await check_giveaways()

@tasks.loop(seconds=30)
async def reminder_checker():
    await check_reminders()

@tasks.loop(seconds=60)
async def mute_checker():
    await check_mutes()

@tasks.loop(minutes=5)
async def update_presence():
    activities = [
        discord.Game(name="KuzzMarket | /help"),
        discord.Streaming(name="KuzzMarket", url="https://twitch.tv/kuzzmarket"),
        discord.Activity(type=discord.ActivityType.listening, name="music"),
        discord.Activity(type=discord.ActivityType.watching, name="the server grow")
    ]
    activity = random.choice(activities)
    await bot.change_presence(activity=activity)

# --- BOT EVENTS ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    logger.info(f'Bot started as {bot.user}')
    
    # Initialize database tables
    init_db()
    
    # Load shop items
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM shop''')
    shop_items.extend(c.fetchall())
    conn.close()
    
    # Load custom commands
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT command_name, response FROM custom_commands''')
    for row in c.fetchall():
        custom_commands_cache[row[0]] = row[1]
    conn.close()
    
    # Load auto responders
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT trigger_word, response FROM auto_responders''')
    for row in c.fetchall():
        auto_responders[row[0]] = row[1]
    conn.close()
    
    # Load reaction roles
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT message_id, emoji, role_id FROM reaction_roles''')
    for row in c.fetchall():
        message_id, emoji, role_id = row
        if message_id not in reaction_roles:
            reaction_roles[message_id] = {}
        reaction_roles[message_id][emoji] = role_id
    conn.close()
    
    # Start tasks
    giveaway_checker.start()
    reminder_checker.start()
    mute_checker.start()
    update_presence.start()
    
    # Add persistent views
    bot.add_view(VerifyView())
    bot.add_view(ServiceView())
    
    # Sync commands
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    
    print("Bot is ready!")

@bot.event
async def on_member_join(member):
    # Send welcome message
    await send_welcome_message(member)
    
    # Log member join
    await log_member_join(member)
    
    # Track invite
    if member.guild.id == GUILD_ID:
        invites = await member.guild.invites()
        for invite in invites:
            if invite.code in invite_codes and invite_codes[invite.code] < invite.uses:
                # This invite was used
                inviter = invite.inviter
                if inviter:
                    # Save to database
                    conn = sqlite3.connect('kuzzbot.db')
                    c = conn.cursor()
                    c.execute('''INSERT INTO invites (inviter_id, invitee_id, invite_code, created_at)
                                 VALUES (?, ?, ?, ?)''', 
                              (inviter.id, member.id, invite.code, datetime.datetime.now().isoformat()))
                    conn.commit()
                    conn.close()
                    
                    # Log invite
                    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(title="📨 Invite Used", color=discord.Color.green())
                        log_embed.add_field(name="Inviter", value=f"{inviter.mention} ({inviter.id})", inline=False)
                        log_embed.add_field(name="Invitee", value=f"{member.mention} ({member.id})", inline=False)
                        log_embed.add_field(name="Invite Code", value=invite.code, inline=False)
                        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                        await log_channel.send(embed=log_embed)
                break
    
    # Auto role if enabled
    if AUTO_ROLE_ENABLED:
        guild = bot.get_guild(GUILD_ID)
        role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
        if role and role not in member.roles:
            try:
                await member.add_roles(role)
                
                # Send welcome message in general
                general_channel = bot.get_channel(GENERAL_CHANNEL_ID)
                if general_channel:
                    await general_channel.send(f"🎉 Welcome {member.mention} to KuzzMarket! You have been automatically assigned the {role.name} role!")
                
                # Log auto role
                log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(title="🤖 Auto Role Applied", color=discord.Color.blue())
                    log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
                    log_embed.add_field(name="Role", value=role.name, inline=False)
                    log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    await log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                logger.error(f"Could not assign {MEMBER_ROLE_NAME} role to {member.name} due to permissions.")

@bot.event
async def on_member_remove(member):
    # Send leave message
    await send_leave_message(member)
    
    # Log member leave
    await log_member_leave(member)

@bot.event
async def on_message_edit(before, after):
    # Log message edit
    if before.author.bot:
        return
    
    await log_message_edit(after, before, after)

@bot.event
async def on_message_delete(message):
    # Log message delete
    if message.author.bot:
        return
    
    await log_message_delete(message)

@bot.event
async def on_member_update(before, after):
    # Log role updates
    if before.roles != after.roles:
        await log_role_update(after, before, after)

@bot.event
async def on_voice_state_update(member, before, after):
    # Log voice state updates
    await log_voice_state_update(member, before, after)
    
    # Handle temporary voice channels
    if after.channel and after.channel.name.startswith("🔊 Join to Create"):
        # Create a temporary voice channel
        guild = after.channel.guild
        category = after.channel.category
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True, speak=True),
            member: discord.PermissionOverwrite(connect=True, speak=True, manage_channels=True)
        }
        
        temp_channel = await guild.create_voice_channel(
            name=f"🔊 {member.display_name}'s Channel",
            category=category,
            overwrites=overwrites
        )
        
        # Move member to the new channel
        await member.move_to(temp_channel)
        
        # Store channel info
        temp_voice_channels[temp_channel.id] = {
            "owner_id": member.id,
            "created_at": datetime.datetime.now()
        }
        
        # Log channel creation
        log_channel = bot.get_channel(VOICE_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🔊 Temporary Voice Channel Created", color=discord.Color.green())
            log_embed.add_field(name="Owner", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Channel", value=temp_channel.mention, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
    
    # Check if a temporary voice channel should be deleted
    if before.channel and before.channel.id in temp_voice_channels:
        # Check if the channel is empty
        if len(before.channel.members) == 0:
            # Delete the channel
            await before.channel.delete()
            
            # Remove from tracking
            del temp_voice_channels[before.channel.id]
            
            # Log channel deletion
            log_channel = bot.get_channel(VOICE_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(title="🔊 Temporary Voice Channel Deleted", color=discord.Color.red())
                log_embed.add_field(name="Channel", value=before.channel.name, inline=False)
                log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                await log_channel.send(embed=log_embed)

@bot.event
async def on_reaction_add(reaction, user):
    # Handle reaction roles
    if reaction.message.id in reaction_roles:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles[reaction.message.id]:
            role_id = reaction_roles[reaction.message.id][emoji_str]
            role = reaction.message.guild.get_role(role_id)
            
            if role and role not in user.roles:
                try:
                    await user.add_roles(role)
                    
                    # Notify user
                    try:
                        await user.send(f"You have been given the {role.name} role!")
                    except discord.Forbidden:
                        pass
                except discord.Forbidden:
                    pass
    
    # Handle starboard
    if STARBOARD_ENABLED and str(reaction.emoji) == "⭐":
        if reaction.count >= 5:  # Minimum stars to add to starboard
            starboard_channel = bot.get_channel(STARBOARD_CHANNEL_ID)
            if not starboard_channel:
                return
            
            # Check if message is already in starboard
            conn = sqlite3.connect('kuzzbot.db')
            c = conn.cursor()
            c.execute('''SELECT 1 FROM starboard WHERE message_id = ?''', (reaction.message.id,))
            if c.fetchone():
                conn.close()
                return
            
            # Add to starboard
            embed = discord.Embed(
                description=reaction.message.content,
                color=discord.Color.gold(),
                timestamp=reaction.message.created_at
            )
            embed.set_author(name=f"{reaction.message.author.name}", icon_url=reaction.message.author.display_avatar.url)
            embed.add_field(name="Source", value=f"[Jump to message]({reaction.message.jump_url})", inline=False)
            embed.set_footer(text=f"⭐ {reaction.count} stars")
            
            if reaction.message.attachments:
                embed.set_image(url=reaction.message.attachments[0].url)
            
            starboard_message = await starboard_channel.send(embed=embed)
            
            # Save to database
            c.execute('''INSERT INTO starboard (message_id, channel_id, author_id, content, star_count, starred_by)
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (reaction.message.id, reaction.message.channel.id, reaction.message.author.id, 
                       reaction.message.content, reaction.count, str(reaction.message.id)))
            conn.commit()
            conn.close()

@bot.event
async def on_reaction_remove(reaction, user):
    # Handle reaction roles
    if reaction.message.id in reaction_roles:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles[reaction.message.id]:
            role_id = reaction_roles[reaction.message.id][emoji_str]
            role = reaction.message.guild.get_role(role_id)
            
            if role and role in user.roles:
                try:
                    await user.remove_roles(role)
                    
                    # Notify user
                    try:
                        await user.send(f"The {role.name} role has been removed from you.")
                    except discord.Forbidden:
                        pass
                except discord.Forbidden:
                    pass

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
    
    # Auto moderation
    if AUTO_MOD_ENABLED:
        content = message.content.lower()
        
        # Bad words filter
        if any(word in content for word in BAD_WORDS):
            try:
                await message.delete()
                await message.author.send(f"Your message in **{message.guild.name}** was deleted for using inappropriate language. Please adhere to the server rules.")
                
                # Log moderation action
                log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(title="🚫 Bad Word Filter", color=discord.Color.red())
                    log_embed.add_field(name="User", value=f"{message.author.mention} ({message.author.id})", inline=False)
                    log_embed.add_field(name="Channel", value=message.channel.mention, inline=False)
                    log_embed.add_field(name="Content", value=message.content[:1024], inline=False)
                    log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    await log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                logger.error(f"Could not delete message or DM user {message.author.name} due to permissions.")
            except Exception as e:
                logger.error(f"Error in auto-moderation: {e}")
            return
        
        # Anti-spam
        if ANTI_SPAM_ENABLED:
            user_id = message.author.id
            current_time = time.time()
            
            if user_id in anti_spam:
                if current_time - anti_spam[user_id]["last_message"] < 5:
                    anti_spam[user_id]["count"] += 1
                    if anti_spam[user_id]["count"] >= 5:
                        # Mute the user
                        muted_role = discord.utils.get(message.guild.roles, name=MUTED_ROLE_NAME)
                        if muted_role and muted_role not in message.author.roles:
                            try:
                                await message.author.add_roles(muted_role)
                                
                                # Set mute duration
                                mute_duration = datetime.timedelta(minutes=10)
                                mute_until = datetime.datetime.now() + mute_duration
                                
                                # Update database
                                conn = sqlite3.connect('kuzzbot.db')
                                c = conn.cursor()
                                c.execute('''UPDATE users SET muted_until = ? WHERE user_id = ?''', 
                                          (mute_until.isoformat(), user_id))
                                conn.commit()
                                conn.close()
                                
                                # Notify user
                                try:
                                    await message.author.send(f"You have been muted for spamming. The mute will expire in 10 minutes.")
                                except discord.Forbidden:
                                    pass
                                
                                # Log mute
                                log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                                if log_channel:
                                    log_embed = discord.Embed(title="🔇 Anti-Spam Mute", color=discord.Color.red())
                                    log_embed.add_field(name="User", value=f"{message.author.mention} ({message.author.id})", inline=False)
                                    log_embed.add_field(name="Duration", value="10 minutes", inline=False)
                                    log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                                    await log_channel.send(embed=log_embed)
                                    
                            except discord.Forbidden:
                                pass
                else:
                    anti_spam[user_id]["count"] = 1
                    anti_spam[user_id]["last_message"] = current_time
            else:
                anti_spam[user_id] = {"count": 1, "last_message": current_time}
    
    # Auto responders
    for trigger, response in auto_responders.items():
        if trigger.lower() in message.content.lower():
            await message.channel.send(response)
            break
    
    # Custom commands
    if message.content.startswith(DEFAULT_PREFIX):
        command_name = message.content[len(DEFAULT_PREFIX):].split()[0].lower()
        if command_name in custom_commands_cache:
            await message.channel.send(custom_commands_cache[command_name])
            return
    
    # XP system
    user_id_str = str(message.author.id)
    current_time = time.time()
    
    if user_id_str not in xp_data:
        xp_data[user_id_str] = {'xp': 0, 'last_message_time': 0}
        
    if current_time - xp_data[user_id_str]['last_message_time'] > XP_COOLDOWN:
        xp_data[user_id_str]['xp'] += XP_PER_MESSAGE
        xp_data[user_id_str]['last_message_time'] = current_time
        
        # Update database
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users (user_id, xp) VALUES (?, COALESCE((SELECT xp FROM users WHERE user_id = ?), 0) + ?)''', 
                  (message.author.id, message.author.id, XP_PER_MESSAGE))
        conn.commit()
        conn.close()
        
        # Check for level up
        new_level = get_level(xp_data[user_id_str]['xp'])
        old_level = get_level(xp_data[user_id_str]['xp'] - XP_PER_MESSAGE)
        
        if new_level > old_level:
            # Level up!
            if LEVEL_UP_MESSAGES_ENABLED:
                level_channel = bot.get_channel(LEVEL_CHANNEL_ID)
                if level_channel:
                    embed = discord.Embed(
                        title="🎉 Level Up!",
                        description=f"Congratulations {message.author.mention}! You've reached level {new_level}!",
                        color=discord.Color.green()
                    )
                    await level_channel.send(embed=embed)
            
            # Check for active member role
            if new_level >= 5 and xp_data[user_id_str]['xp'] >= XP_FOR_ACTIVE_ROLE:
                role = discord.utils.get(message.guild.roles, name=ACTIVE_MEMBER_ROLE_NAME)
                if role and role not in message.author.roles:
                    try:
                        await message.author.add_roles(role)
                        
                        # Notify user
                        try:
                            await message.author.send(f"Congratulations! You've earned the {role.name} role for being active!")
                        except discord.Forbidden:
                            pass
                        
                        # Log role assignment
                        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                        if log_channel:
                            log_embed = discord.Embed(title="🌟 Active Member Role Earned", color=discord.Color.green())
                            log_embed.add_field(name="User", value=f"{message.author.mention} ({message.author.id})", inline=False)
                            log_embed.add_field(name="Level", value=str(new_level), inline=False)
                            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                            await log_channel.send(embed=log_embed)
                            
                    except discord.Forbidden:
                        pass
    
    # Process commands
    await bot.process_commands(message)

# --- COMMANDS ---
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.slash_command(name="ping", description="Checks the bot's latency.", guild_ids=[GUILD_ID])
async def ping_slash(ctx: discord.ApplicationContext):
    await ctx.respond(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms", ephemeral=True)

@bot.slash_command(name="sendverify", description="Sends the verification panel to the verify channel.", guild_ids=[GUILD_ID])
@commands.has_permissions(administrator=True)
async def send_verify_slash(ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    await send_verify_logic(ctx)

@bot.command(name="sendverify")
@commands.has_permissions(administrator=True)
async def send_verify_prefix(ctx: commands.Context):
    await send_verify_logic(ctx)

@bot.slash_command(name="sendservices", description="Sends the service role panel to the service channel.", guild_ids=[GUILD_ID])
@commands.has_permissions(administrator=True)
async def send_services_slash(ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    await send_services_logic(ctx)

@bot.command(name="sendservices")
@commands.has_permissions(administrator=True)
async def send_services_prefix(ctx: commands.Context):
    await send_services_logic(ctx)

@bot.command(name="ok")
@commands.has_permissions(administrator=True)
async def ok(ctx):
    global AUTO_ROLE_ENABLED
    AUTO_ROLE_ENABLED = True
    await ctx.send("✅ Auto role feature enabled! New members will now automatically get the KuzzMember role.")

@bot.command(name="nok")
@commands.has_permissions(administrator=True)
async def nok(ctx):
    global AUTO_ROLE_ENABLED
    AUTO_ROLE_ENABLED = False
    await ctx.send("✅ Auto role feature disabled! New members will no longer get the KuzzMember role automatically.")

@bot.slash_command(name="ok", description="Enable auto role for new members (Admins only)", guild_ids=[GUILD_ID])
@commands.has_permissions(administrator=True)
async def ok_slash(ctx: discord.ApplicationContext):
    global AUTO_ROLE_ENABLED
    AUTO_ROLE_ENABLED = True
    await ctx.respond("✅ Auto role feature enabled! New members will now automatically get the KuzzMember role.", ephemeral=True)

@bot.slash_command(name="nok", description="Disable auto role for new members (Admins only)", guild_ids=[GUILD_ID])
@commands.has_permissions(administrator=True)
async def nok_slash(ctx: discord.ApplicationContext):
    global AUTO_ROLE_ENABLED
    AUTO_ROLE_ENABLED = False
    await ctx.respond("✅ Auto role feature disabled! New members will no longer get the KuzzMember role automatically.", ephemeral=True)

# Moderation Commands
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"{member.mention} has been kicked from the server.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Kicked by {ctx.author.name}")
        await ctx.send(embed=embed)
        
        # Log kick
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.red())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
            
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick this member.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@bot.slash_command(name="kick", description="Kick a member from the server.", guild_ids=[GUILD_ID])
@commands.has_permissions(kick_members=True)
async def kick_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to kick"), 
                    reason: discord.Option(str, "Reason for kicking", default="No reason provided")):
    try:
        await member.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"{member.mention} has been kicked from the server.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Kicked by {ctx.author.name}")
        await ctx.respond(embed=embed)
        
        # Log kick
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.red())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
            
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to kick this member.", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"❌ An error occurred: {e}", ephemeral=True)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.ban(reason=reason)
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} has been banned from the server.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Banned by {ctx.author.name}")
        await ctx.send(embed=embed)
        
        # Log ban
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
            
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this member.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@bot.slash_command(name="ban", description="Ban a member from the server.", guild_ids=[GUILD_ID])
@commands.has_permissions(ban_members=True)
async def ban_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to ban"), 
                   reason: discord.Option(str, "Reason for banning", default="No reason provided")):
    try:
        await member.ban(reason=reason)
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} has been banned from the server.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Banned by {ctx.author.name}")
        await ctx.respond(embed=embed)
        
        # Log ban
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
            
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to ban this member.", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"❌ An error occurred: {e}", ephemeral=True)

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: int = 10, *, reason="No reason provided"):
    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if not muted_role:
        await ctx.send("❌ Muted role not found. Please create a role named 'Muted'.")
        return
    
    if muted_role in member.roles:
        await ctx.send("❌ This member is already muted.")
        return
    
    try:
        await member.add_roles(muted_role)
        
        # Set mute duration
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=duration)
        
        # Update database
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        c.execute('''UPDATE users SET muted_until = ? WHERE user_id = ?''', 
                  (mute_until.isoformat(), member.id))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="🔇 Member Muted",
            description=f"{member.mention} has been muted for {duration} minutes.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Muted by {ctx.author.name}")
        await ctx.send(embed=embed)
        
        # Log mute
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.orange())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
            log_embed.add_field(name="Duration", value=f"{duration} minutes", inline=False)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
            
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to mute this member.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@bot.slash_command(name="mute", description="Mute a member for a specified duration.", guild_ids=[GUILD_ID])
@commands.has_permissions(moderate_members=True)
async def mute_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to mute"), 
                    duration: discord.Option(int, "Duration in minutes", default=10),
                    reason: discord.Option(str, "Reason for muting", default="No reason provided")):
    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if not muted_role:
        await ctx.respond("❌ Muted role not found. Please create a role named 'Muted'.", ephemeral=True)
        return
    
    if muted_role in member.roles:
        await ctx.respond("❌ This member is already muted.", ephemeral=True)
        return
    
    try:
        await member.add_roles(muted_role)
        
        # Set mute duration
        mute_until = datetime.datetime.now() + datetime.timedelta(minutes=duration)
        
        # Update database
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        c.execute('''UPDATE users SET muted_until = ? WHERE user_id = ?''', 
                  (mute_until.isoformat(), member.id))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="🔇 Member Muted",
            description=f"{member.mention} has been muted for {duration} minutes.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Muted by {ctx.author.name}")
        await ctx.respond(embed=embed)
        
        # Log mute
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.orange())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
            log_embed.add_field(name="Duration", value=f"{duration} minutes", inline=False)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
            
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to mute this member.", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"❌ An error occurred: {e}", ephemeral=True)

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if not muted_role:
        await ctx.send("❌ Muted role not found. Please create a role named 'Muted'.")
        return
    
    if muted_role not in member.roles:
        await ctx.send("❌ This member is not muted.")
        return
    
    try:
        await member.remove_roles(muted_role)
        
        # Update database
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        c.execute('''UPDATE users SET muted_until = NULL WHERE user_id = ?''', (member.id,))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="🔊 Member Unmuted",
            description=f"{member.mention} has been unmuted.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Unmuted by {ctx.author.name}")
        await ctx.send(embed=embed)
        
        # Log unmute
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
            
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unmute this member.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@bot.slash_command(name="unmute", description="Unmute a member.", guild_ids=[GUILD_ID])
@commands.has_permissions(moderate_members=True)
async def unmute_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to unmute")):
    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if not muted_role:
        await ctx.respond("❌ Muted role not found. Please create a role named 'Muted'.", ephemeral=True)
        return
    
    if muted_role not in member.roles:
        await ctx.respond("❌ This member is not muted.", ephemeral=True)
        return
    
    try:
        await member.remove_roles(muted_role)
        
        # Update database
        conn = sqlite3.connect('kuzzbot.db')
        c = conn.cursor()
        c.execute('''UPDATE users SET muted_until = NULL WHERE user_id = ?''', (member.id,))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="🔊 Member Unmuted",
            description=f"{member.mention} has been unmuted.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Unmuted by {ctx.author.name}")
        await ctx.respond(embed=embed)
        
        # Log unmute
        log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
            log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=log_embed)
            
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to unmute this member.", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"❌ An error occurred: {e}", ephemeral=True)

@bot.command(name="warn")
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    # Get current warnings
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT warnings FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    
    if result:
        warnings = result[0] + 1
        c.execute('''UPDATE users SET warnings = ? WHERE user_id = ?''', (warnings, member.id))
    else:
        warnings = 1
        c.execute('''INSERT INTO users (user_id, warnings) VALUES (?, ?)''', (member.id, warnings))
    
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="⚠️ Member Warned",
        description=f"{member.mention} has been warned.",
        color=discord.Color.orange()
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Total Warnings", value=f"{warnings}/{MAX_WARNINGS}", inline=False)
    embed.set_footer(text=f"Warned by {ctx.author.name}")
    await ctx.send(embed=embed)
    
    # Notify user
    try:
        dm_embed = discord.Embed(
            title="⚠️ You have been warned",
            description=f"You have been warned in {ctx.guild.name} for: {reason}",
            color=discord.Color.orange()
        )
        dm_embed.add_field(name="Total Warnings", value=f"{warnings}/{MAX_WARNINGS}", inline=False)
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass
    
    # Log warning
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="⚠️ Member Warned", color=discord.Color.orange())
        log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
        log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        log_embed.add_field(name="Total Warnings", value=f"{warnings}/{MAX_WARNINGS}", inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)
    
    # Check for max warnings
    if warnings >= MAX_WARNINGS:
        # Auto mute for 1 hour
        muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
        if muted_role and muted_role not in member.roles:
            try:
                await member.add_roles(muted_role)
                
                # Set mute duration
                mute_until = datetime.datetime.now() + datetime.timedelta(hours=1)
                
                # Update database
                conn = sqlite3.connect('kuzzbot.db')
                c = conn.cursor()
                c.execute('''UPDATE users SET muted_until = ? WHERE user_id = ?''', 
                          (mute_until.isoformat(), member.id))
                conn.commit()
                conn.close()
                
                # Notify user
                try:
                    await member.send("You have reached the maximum number of warnings and have been muted for 1 hour.")
                except discord.Forbidden:
                    pass
                
                # Log auto mute
                log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(title="🔇 Auto Mute (Max Warnings)", color=discord.Color.red())
                    log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
                    log_embed.add_field(name="Duration", value="1 hour", inline=False)
                    log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    await log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                pass

@bot.slash_command(name="warn", description="Warn a member for a rule violation.", guild_ids=[GUILD_ID])
@commands.has_permissions(moderate_members=True)
async def warn_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to warn"), 
                    reason: discord.Option(str, "Reason for warning", default="No reason provided")):
    # Get current warnings
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT warnings FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    
    if result:
        warnings = result[0] + 1
        c.execute('''UPDATE users SET warnings = ? WHERE user_id = ?''', (warnings, member.id))
    else:
        warnings = 1
        c.execute('''INSERT INTO users (user_id, warnings) VALUES (?, ?)''', (member.id, warnings))
    
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="⚠️ Member Warned",
        description=f"{member.mention} has been warned.",
        color=discord.Color.orange()
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Total Warnings", value=f"{warnings}/{MAX_WARNINGS}", inline=False)
    embed.set_footer(text=f"Warned by {ctx.author.name}")
    await ctx.respond(embed=embed)
    
    # Notify user
    try:
        dm_embed = discord.Embed(
            title="⚠️ You have been warned",
            description=f"You have been warned in {ctx.guild.name} for: {reason}",
            color=discord.Color.orange()
        )
        dm_embed.add_field(name="Total Warnings", value=f"{warnings}/{MAX_WARNINGS}", inline=False)
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass
    
    # Log warning
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="⚠️ Member Warned", color=discord.Color.orange())
        log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
        log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        log_embed.add_field(name="Total Warnings", value=f"{warnings}/{MAX_WARNINGS}", inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)
    
    # Check for max warnings
    if warnings >= MAX_WARNINGS:
        # Auto mute for 1 hour
        muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
        if muted_role and muted_role not in member.roles:
            try:
                await member.add_roles(muted_role)
                
                # Set mute duration
                mute_until = datetime.datetime.now() + datetime.timedelta(hours=1)
                
                # Update database
                conn = sqlite3.connect('kuzzbot.db')
                c = conn.cursor()
                c.execute('''UPDATE users SET muted_until = ? WHERE user_id = ?''', 
                          (mute_until.isoformat(), member.id))
                conn.commit()
                conn.close()
                
                # Notify user
                try:
                    await member.send("You have reached the maximum number of warnings and have been muted for 1 hour.")
                except discord.Forbidden:
                    pass
                
                # Log auto mute
                log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(title="🔇 Auto Mute (Max Warnings)", color=discord.Color.red())
                    log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
                    log_embed.add_field(name="Duration", value="1 hour", inline=False)
                    log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    await log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                pass

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    
    # Get warnings
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT warnings FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    conn.close()
    
    warnings = result[0] if result else 0
    
    embed = discord.Embed(
        title="⚠️ Warnings",
        description=f"{member.mention} has {warnings} warnings.",
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Max warnings: {MAX_WARNINGS}")
    await ctx.send(embed=embed)

@bot.slash_command(name="warnings", description="Check a member's warning count.", guild_ids=[GUILD_ID])
async def warnings_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to check", default=None)):
    if not member:
        member = ctx.user
    
    # Get warnings
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT warnings FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    conn.close()
    
    warnings = result[0] if result else 0
    
    embed = discord.Embed(
        title="⚠️ Warnings",
        description=f"{member.mention} has {warnings} warnings.",
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Max warnings: {MAX_WARNINGS}")
    await ctx.respond(embed=embed)

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    if amount < 1 or amount > 100:
        await ctx.send("❌ Please provide a number between 1 and 100.")
        return
    
    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
    
    embed = discord.Embed(
        title="🗑️ Messages Cleared",
        description=f"Deleted {len(deleted) - 1} messages.",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Cleared by {ctx.author.name}")
    
    # Send confirmation message
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(5)
    await msg.delete()
    
    # Log message clear
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="🗑️ Messages Cleared", color=discord.Color.red())
        log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        log_embed.add_field(name="Amount", value=str(len(deleted) - 1), inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)

@bot.slash_command(name="clear", description="Clear a specified number of messages.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_messages=True)
async def clear_slash(ctx: discord.ApplicationContext, amount: discord.Option(int, "Number of messages to clear (1-100)", default=10)):
    if amount < 1 or amount > 100:
        await ctx.respond("❌ Please provide a number between 1 and 100.", ephemeral=True)
        return
    
    deleted = await ctx.channel.purge(limit=amount)
    
    embed = discord.Embed(
        title="🗑️ Messages Cleared",
        description=f"Deleted {len(deleted)} messages.",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Cleared by {ctx.author.name}")
    
    # Send confirmation message
    msg = await ctx.respond(embed=embed)
    await asyncio.sleep(5)
    await msg.delete_original_response()
    
    # Log message clear
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="🗑️ Messages Cleared", color=discord.Color.red())
        log_embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        log_embed.add_field(name="Amount", value=str(len(deleted)), inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)

# Ticket Commands
@bot.command(name="ticket")
async def ticket(ctx):
    if not TICKET_ENABLED:
        await ctx.send("❌ Ticket system is currently disabled.")
        return
    
    modal = TicketModal()
    await ctx.send_modal(modal)

@bot.slash_command(name="ticket", description="Create a support ticket.", guild_ids=[GUILD_ID])
async def ticket_slash(ctx: discord.ApplicationContext):
    if not TICKET_ENABLED:
        await ctx.respond("❌ Ticket system is currently disabled.", ephemeral=True)
        return
    
    modal = TicketModal()
    await ctx.interaction.response.send_modal(modal)

@bot.command(name="close")
@commands.has_permissions(manage_channels=True)
async def close_ticket(ctx):
    if ctx.channel.id not in ticket_channels.values():
        await ctx.send("❌ This is not a ticket channel.")
        return
    
    # Find the ticket owner
    owner_id = None
    for user_id, channel_id in ticket_channels.items():
        if channel_id == ctx.channel.id:
            owner_id = user_id
            break
    
    if not owner_id:
        await ctx.send("❌ Could not find ticket owner.")
        return
    
    # Update database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''UPDATE tickets 
                 SET closed_by = ?, closed_at = ?
                 WHERE channel_id = ?''', 
              (ctx.author.id, datetime.datetime.now().isoformat(), ctx.channel.id))
    conn.commit()
    conn.close()
    
    # Remove from active tickets
    if owner_id in ticket_channels:
        del ticket_channels[owner_id]
    
    # Send confirmation
    embed = discord.Embed(
        title="Ticket Closed",
        description=f"This ticket has been closed by {ctx.author.mention}",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
    
    # Notify user via DM
    user = ctx.guild.get_member(owner_id)
    if user and WELCOME_DM_ENABLED:
        try:
            dm_embed = discord.Embed(
                title="Your Ticket Has Been Closed",
                description=f"Your ticket in {ctx.guild.name} has been closed by {ctx.author.name}",
                color=discord.Color.orange()
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass
    
    # Log ticket closure
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="🎫 Ticket Closed", color=discord.Color.red())
        log_embed.add_field(name="User", value=f"{user.mention if user else 'Unknown'} ({owner_id})", inline=False)
        log_embed.add_field(name="Closed By", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)
    
    # Schedule channel deletion
    await asyncio.sleep(5)
    try:
        await ctx.channel.delete()
    except discord.Forbidden:
        pass

@bot.slash_command(name="close", description="Close the current ticket channel.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_channels=True)
async def close_ticket_slash(ctx: discord.ApplicationContext):
    if ctx.channel.id not in ticket_channels.values():
        await ctx.respond("❌ This is not a ticket channel.", ephemeral=True)
        return
    
    # Find the ticket owner
    owner_id = None
    for user_id, channel_id in ticket_channels.items():
        if channel_id == ctx.channel.id:
            owner_id = user_id
            break
    
    if not owner_id:
        await ctx.respond("❌ Could not find ticket owner.", ephemeral=True)
        return
    
    # Update database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''UPDATE tickets 
                 SET closed_by = ?, closed_at = ?
                 WHERE channel_id = ?''', 
              (ctx.author.id, datetime.datetime.now().isoformat(), ctx.channel.id))
    conn.commit()
    conn.close()
    
    # Remove from active tickets
    if owner_id in ticket_channels:
        del ticket_channels[owner_id]
    
    # Send confirmation
    embed = discord.Embed(
        title="Ticket Closed",
        description=f"This ticket has been closed by {ctx.author.mention}",
        color=discord.Color.red()
    )
    await ctx.respond(embed=embed)
    
    # Notify user via DM
    user = ctx.guild.get_member(owner_id)
    if user and WELCOME_DM_ENABLED:
        try:
            dm_embed = discord.Embed(
                title="Your Ticket Has Been Closed",
                description=f"Your ticket in {ctx.guild.name} has been closed by {ctx.author.name}",
                color=discord.Color.orange()
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass
    
    # Log ticket closure
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="🎫 Ticket Closed", color=discord.Color.red())
        log_embed.add_field(name="User", value=f"{user.mention if user else 'Unknown'} ({owner_id})", inline=False)
        log_embed.add_field(name="Closed By", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)
    
    # Schedule channel deletion
    await asyncio.sleep(5)
    try:
        await ctx.channel.delete()
    except discord.Forbidden:
        pass

@bot.command(name="add")
@commands.has_permissions(manage_channels=True)
async def add_to_ticket(ctx, member: discord.Member):
    if ctx.channel.id not in ticket_channels.values():
        await ctx.send("❌ This is not a ticket channel.")
        return
    
    # Add permissions for the member
    await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
    
    embed = discord.Embed(
        title="Member Added to Ticket",
        description=f"{member.mention} has been added to this ticket.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    
    # Log member addition
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="🎫 Member Added to Ticket", color=discord.Color.green())
        log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        log_embed.add_field(name="Added By", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)

@bot.slash_command(name="add", description="Add a member to the current ticket.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_channels=True)
async def add_to_ticket_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to add")):
    if ctx.channel.id not in ticket_channels.values():
        await ctx.respond("❌ This is not a ticket channel.", ephemeral=True)
        return
    
    # Add permissions for the member
    await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
    
    embed = discord.Embed(
        title="Member Added to Ticket",
        description=f"{member.mention} has been added to this ticket.",
        color=discord.Color.green()
    )
    await ctx.respond(embed=embed)
    
    # Log member addition
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="🎫 Member Added to Ticket", color=discord.Color.green())
        log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        log_embed.add_field(name="Added By", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)

@bot.command(name="remove")
@commands.has_permissions(manage_channels=True)
async def remove_from_ticket(ctx, member: discord.Member):
    if ctx.channel.id not in ticket_channels.values():
        await ctx.send("❌ This is not a ticket channel.")
        return
    
    # Remove permissions for the member
    await ctx.channel.set_permissions(member, overwrite=None)
    
    embed = discord.Embed(
        title="Member Removed from Ticket",
        description=f"{member.mention} has been removed from this ticket.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
    
    # Log member removal
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="🎫 Member Removed from Ticket", color=discord.Color.red())
        log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        log_embed.add_field(name="Removed By", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)

@bot.slash_command(name="remove", description="Remove a member from the current ticket.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_channels=True)
async def remove_from_ticket_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to remove")):
    if ctx.channel.id not in ticket_channels.values():
        await ctx.respond("❌ This is not a ticket channel.", ephemeral=True)
        return
    
    # Remove permissions for the member
    await ctx.channel.set_permissions(member, overwrite=None)
    
    embed = discord.Embed(
        title="Member Removed from Ticket",
        description=f"{member.mention} has been removed from this ticket.",
        color=discord.Color.red()
    )
    await ctx.respond(embed=embed)
    
    # Log member removal
    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if log_channel:
        log_embed = discord.Embed(title="🎫 Member Removed from Ticket", color=discord.Color.red())
        log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        log_embed.add_field(name="Removed By", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        log_embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=log_embed)

# Giveaway Commands
@bot.command(name="giveaway")
@commands.has_permissions(manage_events=True)
async def create_giveaway(ctx, duration: int, winners: int, *, prize: str):
    if not GIVEAWAY_ENABLED:
        await ctx.send("❌ Giveaway system is currently disabled.")
        return
    
    if duration < 1 or duration > 168:  # Max 1 week
        await ctx.send("❌ Duration must be between 1 and 168 hours.")
        return
    
    if winners < 1 or winners > 10:
        await ctx.send("❌ Number of winners must be between 1 and 10.")
        return
    
    # Calculate end time
    end_time = datetime.datetime.now() + datetime.timedelta(hours=duration)
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=f"🎁 **Prize:** {prize}\n👥 **Winners:** {winners}\n🎫 **Entries:** 0\n⏰ **Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.blue()
    )
    embed.set_footer(text="React with 🎉 to enter!")
    
    # Send giveaway message
    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")
    
    # Save to database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO giveaways (channel_id, message_id, prize, winners, ends_at, hosted_by)
                 VALUES (?, ?, ?, ?, ?, ?)''', 
              (ctx.channel.id, message.id, prize, winners, end_time.isoformat(), ctx.author.id))
    conn.commit()
    conn.close()
    
    # Add to active giveaways
    active_giveaways[message.id] = {
        "prize": prize,
        "winners": winners,
        "end_time": end_time,
        "hosted_by": ctx.author.id
    }
    
    await ctx.send("✅ Giveaway created successfully!")

@bot.slash_command(name="giveaway", description="Create a new giveaway.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_events=True)
async def create_giveaway_slash(ctx: discord.ApplicationContext, 
                              duration: discord.Option(int, "Duration in hours (1-168)"),
                              winners: discord.Option(int, "Number of winners (1-10)"),
                              prize: discord.Option(str, "The prize for the giveaway")):
    if not GIVEAWAY_ENABLED:
        await ctx.respond("❌ Giveaway system is currently disabled.", ephemeral=True)
        return
    
    if duration < 1 or duration > 168:  # Max 1 week
        await ctx.respond("❌ Duration must be between 1 and 168 hours.", ephemeral=True)
        return
    
    if winners < 1 or winners > 10:
        await ctx.respond("❌ Number of winners must be between 1 and 10.", ephemeral=True)
        return
    
    # Calculate end time
    end_time = datetime.datetime.now() + datetime.timedelta(hours=duration)
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=f"🎁 **Prize:** {prize}\n👥 **Winners:** {winners}\n🎫 **Entries:** 0\n⏰ **Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.blue()
    )
    embed.set_footer(text="React with 🎉 to enter!")
    
    # Send giveaway message
    message = await ctx.respond(embed=embed)
    message = await message.original_response()
    await message.add_reaction("🎉")
    
    # Save to database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO giveaways (channel_id, message_id, prize, winners, ends_at, hosted_by)
                 VALUES (?, ?, ?, ?, ?, ?)''', 
              (ctx.channel.id, message.id, prize, winners, end_time.isoformat(), ctx.author.id))
    conn.commit()
    conn.close()
    
    # Add to active giveaways
    active_giveaways[message.id] = {
        "prize": prize,
        "winners": winners,
        "end_time": end_time,
        "hosted_by": ctx.author.id
    }
    
    await ctx.followup.send("✅ Giveaway created successfully!", ephemeral=True)

@bot.command(name="reroll")
@commands.has_permissions(manage_events=True)
async def reroll_giveaway(ctx, message_id: int):
    # Get giveaway from database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT prize, winners, channel_id FROM giveaways 
                 WHERE message_id = ? AND ended = 1''', (message_id,))
    giveaway = c.fetchone()
    conn.close()
    
    if not giveaway:
        await ctx.send("❌ Giveaway not found or not ended.")
        return
    
    prize, winners, channel_id = giveaway
    
    # Get entries
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT user_id FROM giveaway_entries 
                 WHERE giveaway_id = (SELECT giveaway_id FROM giveaways WHERE message_id = ?)''', 
              (message_id,))
    entries = [row[0] for row in c.fetchall()]
    conn.close()
    
    if not entries:
        await ctx.send("❌ No entries found for this giveaway.")
        return
    
    # Select new winners
    winner_count = min(winners, len(entries))
    winners_list = random.sample(entries, winner_count)
    
    # Get channel and message
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ Could not find the giveaway channel.")
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        # Announce new winners
        winners_mentions = []
        for winner_id in winners_list:
            winner = channel.guild.get_member(winner_id)
            if winner:
                winners_mentions.append(winner.mention)
        
        if winners_mentions:
            await message.reply(f"🎉 New winners for the **{prize}** giveaway: {', '.join(winners_mentions)}")
            
            # DM winners
            for winner_id in winners_list:
                winner = channel.guild.get_member(winner_id)
                if winner:
                    try:
                        dm_embed = discord.Embed(
                            title="🎉 You Won a Giveaway (Reroll)!",
                            description=f"Congratulations! You won the **{prize}** giveaway in {channel.guild.name}!",
                            color=discord.Color.green()
                        )
                        await winner.send(embed=dm_embed)
                    except discord.Forbidden:
                        pass
        else:
            await message.reply("❌ No valid winners found.")
            
    except discord.NotFound:
        await ctx.send("❌ Could not find the giveaway message.")

@bot.slash_command(name="reroll", description="Reroll winners for a ended giveaway.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_events=True)
async def reroll_giveaway_slash(ctx: discord.ApplicationContext, message_id: discord.Option(str, "The message ID of the giveaway")):
    try:
        message_id = int(message_id)
    except ValueError:
        await ctx.respond("❌ Invalid message ID.", ephemeral=True)
        return
    
    # Get giveaway from database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT prize, winners, channel_id FROM giveaways 
                 WHERE message_id = ? AND ended = 1''', (message_id,))
    giveaway = c.fetchone()
    conn.close()
    
    if not giveaway:
        await ctx.respond("❌ Giveaway not found or not ended.", ephemeral=True)
        return
    
    prize, winners, channel_id = giveaway
    
    # Get entries
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT user_id FROM giveaway_entries 
                 WHERE giveaway_id = (SELECT giveaway_id FROM giveaways WHERE message_id = ?)''', 
              (message_id,))
    entries = [row[0] for row in c.fetchall()]
    conn.close()
    
    if not entries:
        await ctx.respond("❌ No entries found for this giveaway.", ephemeral=True)
        return
    
    # Select new winners
    winner_count = min(winners, len(entries))
    winners_list = random.sample(entries, winner_count)
    
    # Get channel and message
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.respond("❌ Could not find the giveaway channel.", ephemeral=True)
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        # Announce new winners
        winners_mentions = []
        for winner_id in winners_list:
            winner = channel.guild.get_member(winner_id)
            if winner:
                winners_mentions.append(winner.mention)
        
        if winners_mentions:
            await message.reply(f"🎉 New winners for the **{prize}** giveaway: {', '.join(winners_mentions)}")
            
            # DM winners
            for winner_id in winners_list:
                winner = channel.guild.get_member(winner_id)
                if winner:
                    try:
                        dm_embed = discord.Embed(
                            title="🎉 You Won a Giveaway (Reroll)!",
                            description=f"Congratulations! You won the **{prize}** giveaway in {channel.guild.name}!",
                            color=discord.Color.green()
                        )
                        await winner.send(embed=dm_embed)
                    except discord.Forbidden:
                        pass
            
            await ctx.respond("✅ New winners have been selected!", ephemeral=True)
        else:
            await message.reply("❌ No valid winners found.")
            await ctx.respond("❌ No valid winners found.", ephemeral=True)
            
    except discord.NotFound:
        await ctx.respond("❌ Could not find the giveaway message.", ephemeral=True)

# Suggestion Commands
@bot.command(name="suggest")
async def suggest(ctx, *, suggestion: str):
    if not SUGGESTION_ENABLED:
        await ctx.send("❌ Suggestion system is currently disabled.")
        return
    
    # Create suggestion embed
    embed = discord.Embed(
        title="💡 Suggestion",
        description=suggestion,
        color=discord.Color.blue()
    )
    embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Status: Pending | ID: {len(suggestion) + 1}")
    
    # Send suggestion to suggestion channel
    channel = bot.get_channel(SUGGESTION_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Suggestion channel not found.")
        return
    
    message = await channel.send(embed=embed, view=SuggestionView(len(suggestion) + 1))
    
    # Save to database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO suggestions (user_id, content, created_at)
                 VALUES (?, ?, ?)''', 
              (ctx.author.id, suggestion, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await ctx.send("✅ Your suggestion has been submitted!")

@bot.slash_command(name="suggest", description="Submit a suggestion to the server.", guild_ids=[GUILD_ID])
async def suggest_slash(ctx: discord.ApplicationContext, suggestion: discord.Option(str, "Your suggestion")):
    if not SUGGESTION_ENABLED:
        await ctx.respond("❌ Suggestion system is currently disabled.", ephemeral=True)
        return
    
    # Create suggestion embed
    embed = discord.Embed(
        title="💡 Suggestion",
        description=suggestion,
        color=discord.Color.blue()
    )
    embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text="Status: Pending")
    
    # Send suggestion to suggestion channel
    channel = bot.get_channel(SUGGESTION_CHANNEL_ID)
    if not channel:
        await ctx.respond("❌ Suggestion channel not found.", ephemeral=True)
        return
    
    message = await channel.send(embed=embed, view=SuggestionView(message.id))
    
    # Save to database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO suggestions (user_id, content, created_at)
                 VALUES (?, ?, ?)''', 
              (ctx.author.id, suggestion, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    await ctx.respond("✅ Your suggestion has been submitted!", ephemeral=True)

@bot.command(name="approve")
@commands.has_permissions(manage_messages=True)
async def approve_suggestion(ctx, message_id: int):
    # Get suggestion from database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT suggestion_id, user_id, content, channel_id FROM suggestions 
                 WHERE message_id = ? AND status = 'pending' ''', (message_id,))
    suggestion = c.fetchone()
    conn.close()
    
    if not suggestion:
        await ctx.send("❌ Suggestion not found or already processed.")
        return
    
    suggestion_id, user_id, content, channel_id = suggestion
    
    # Update suggestion status
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''UPDATE suggestions 
                 SET status = 'approved', reviewed_by = ?, reviewed_at = ?
                 WHERE suggestion_id = ?''', 
              (ctx.author.id, datetime.datetime.now().isoformat(), suggestion_id))
    conn.commit()
    conn.close()
    
    # Get channel and message
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ Could not find the suggestion channel.")
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        # Update message
        embed = message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"Status: Approved | Reviewed by {ctx.author.name}")
        
        await message.edit(embed=embed)
        
        # Notify user
        user = channel.guild.get_member(user_id)
        if user:
            try:
                dm_embed = discord.Embed(
                    title="💡 Your Suggestion Was Approved",
                    description=f"Your suggestion in {channel.guild.name} has been approved!",
                    color=discord.Color.green()
                )
                dm_embed.add_field(name="Suggestion", value=content[:1024], inline=False)
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
        
        await ctx.send("✅ Suggestion has been approved!")
        
    except discord.NotFound:
        await ctx.send("❌ Could not find the suggestion message.")

@bot.slash_command(name="approve", description="Approve a suggestion.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_messages=True)
async def approve_suggestion_slash(ctx: discord.ApplicationContext, message_id: discord.Option(str, "The message ID of the suggestion")):
    try:
        message_id = int(message_id)
    except ValueError:
        await ctx.respond("❌ Invalid message ID.", ephemeral=True)
        return
    
    # Get suggestion from database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT suggestion_id, user_id, content, channel_id FROM suggestions 
                 WHERE message_id = ? AND status = 'pending' ''', (message_id,))
    suggestion = c.fetchone()
    conn.close()
    
    if not suggestion:
        await ctx.respond("❌ Suggestion not found or already processed.", ephemeral=True)
        return
    
    suggestion_id, user_id, content, channel_id = suggestion
    
    # Update suggestion status
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''UPDATE suggestions 
                 SET status = 'approved', reviewed_by = ?, reviewed_at = ?
                 WHERE suggestion_id = ?''', 
              (ctx.author.id, datetime.datetime.now().isoformat(), suggestion_id))
    conn.commit()
    conn.close()
    
    # Get channel and message
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.respond("❌ Could not find the suggestion channel.", ephemeral=True)
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        # Update message
        embed = message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"Status: Approved | Reviewed by {ctx.author.name}")
        
        await message.edit(embed=embed)
        
        # Notify user
        user = channel.guild.get_member(user_id)
        if user:
            try:
                dm_embed = discord.Embed(
                    title="💡 Your Suggestion Was Approved",
                    description=f"Your suggestion in {channel.guild.name} has been approved!",
                    color=discord.Color.green()
                )
                dm_embed.add_field(name="Suggestion", value=content[:1024], inline=False)
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
        
        await ctx.respond("✅ Suggestion has been approved!", ephemeral=True)
        
    except discord.NotFound:
        await ctx.respond("❌ Could not find the suggestion message.", ephemeral=True)

@bot.command(name="reject")
@commands.has_permissions(manage_messages=True)
async def reject_suggestion(ctx, message_id: int, *, reason: str = "No reason provided"):
    # Get suggestion from database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT suggestion_id, user_id, content, channel_id FROM suggestions 
                 WHERE message_id = ? AND status = 'pending' ''', (message_id,))
    suggestion = c.fetchone()
    conn.close()
    
    if not suggestion:
        await ctx.send("❌ Suggestion not found or already processed.")
        return
    
    suggestion_id, user_id, content, channel_id = suggestion
    
    # Update suggestion status
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''UPDATE suggestions 
                 SET status = 'rejected', reviewed_by = ?, reviewed_at = ?
                 WHERE suggestion_id = ?''', 
              (ctx.author.id, datetime.datetime.now().isoformat(), suggestion_id))
    conn.commit()
    conn.close()
    
    # Get channel and message
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ Could not find the suggestion channel.")
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        # Update message
        embed = message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_footer(text=f"Status: Rejected | Reviewed by {ctx.author.name}")
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await message.edit(embed=embed)
        
        # Notify user
        user = channel.guild.get_member(user_id)
        if user:
            try:
                dm_embed = discord.Embed(
                    title="💡 Your Suggestion Was Rejected",
                    description=f"Your suggestion in {channel.guild.name} has been rejected.",
                    color=discord.Color.red()
                )
                dm_embed.add_field(name="Suggestion", value=content[:1024], inline=False)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
        
        await ctx.send("✅ Suggestion has been rejected!")
        
    except discord.NotFound:
        await ctx.send("❌ Could not find the suggestion message.")

@bot.slash_command(name="reject", description="Reject a suggestion.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_messages=True)
async def reject_suggestion_slash(ctx: discord.ApplicationContext, 
                                message_id: discord.Option(str, "The message ID of the suggestion"),
                                reason: discord.Option(str, "Reason for rejection", default="No reason provided")):
    try:
        message_id = int(message_id)
    except ValueError:
        await ctx.respond("❌ Invalid message ID.", ephemeral=True)
        return
    
    # Get suggestion from database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT suggestion_id, user_id, content, channel_id FROM suggestions 
                 WHERE message_id = ? AND status = 'pending' ''', (message_id,))
    suggestion = c.fetchone()
    conn.close()
    
    if not suggestion:
        await ctx.respond("❌ Suggestion not found or already processed.", ephemeral=True)
        return
    
    suggestion_id, user_id, content, channel_id = suggestion
    
    # Update suggestion status
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''UPDATE suggestions 
                 SET status = 'rejected', reviewed_by = ?, reviewed_at = ?
                 WHERE suggestion_id = ?''', 
              (ctx.author.id, datetime.datetime.now().isoformat(), suggestion_id))
    conn.commit()
    conn.close()
    
    # Get channel and message
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.respond("❌ Could not find the suggestion channel.", ephemeral=True)
        return
    
    try:
        message = await channel.fetch_message(message_id)
        
        # Update message
        embed = message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_footer(text=f"Status: Rejected | Reviewed by {ctx.author.name}")
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await message.edit(embed=embed)
        
        # Notify user
        user = channel.guild.get_member(user_id)
        if user:
            try:
                dm_embed = discord.Embed(
                    title="💡 Your Suggestion Was Rejected",
                    description=f"Your suggestion in {channel.guild.name} has been rejected.",
                    color=discord.Color.red()
                )
                dm_embed.add_field(name="Suggestion", value=content[:1024], inline=False)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass
        
        await ctx.respond("✅ Suggestion has been rejected!", ephemeral=True)
        
    except discord.NotFound:
        await ctx.respond("❌ Could not find the suggestion message.", ephemeral=True)

# Leveling Commands
@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    
    # Get user data
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT xp FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    conn.close()
    
    xp = result[0] if result else 0
    level = get_level(xp)
    next_level_xp = get_xp_for_level(level + 1)
    
    # Create level card
    level_card = await create_level_card(member, level, xp, next_level_xp)
    
    await ctx.send(file=level_card)

@bot.slash_command(name="rank", description="Check your or another member's rank.", guild_ids=[GUILD_ID])
async def rank_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to check", default=None)):
    if not member:
        member = ctx.user
    
    # Get user data
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT xp FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    conn.close()
    
    xp = result[0] if result else 0
    level = get_level(xp)
    next_level_xp = get_xp_for_level(level + 1)
    
    # Create level card
    level_card = await create_level_card(member, level, xp, next_level_xp)
    
    await ctx.respond(file=level_card)

@bot.command(name="leaderboard")
async def leaderboard(ctx, limit: int = 10):
    if limit < 1 or limit > 25:
        await ctx.send("❌ Please provide a number between 1 and 25.")
        return
    
    # Get top users
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT user_id, xp FROM users ORDER BY xp DESC LIMIT ?''', (limit,))
    top_users = c.fetchall()
    conn.close()
    
    # Create leaderboard embed
    embed = discord.Embed(
        title="🏆 XP Leaderboard",
        description=f"Top {limit} members with the most XP",
        color=discord.Color.gold()
    )
    
    for i, (user_id, xp) in enumerate(top_users, 1):
        member = ctx.guild.get_member(user_id)
        if member:
            level = get_level(xp)
            embed.add_field(
                name=f"#{i} {member.display_name}",
                value=f"Level {level} | {xp} XP",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.slash_command(name="leaderboard", description="View the XP leaderboard.", guild_ids=[GUILD_ID])
async def leaderboard_slash(ctx: discord.ApplicationContext, limit: discord.Option(int, "Number of users to show (1-25)", default=10)):
    if limit < 1 or limit > 25:
        await ctx.respond("❌ Please provide a number between 1 and 25.", ephemeral=True)
        return
    
    # Get top users
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT user_id, xp FROM users ORDER BY xp DESC LIMIT ?''', (limit,))
    top_users = c.fetchall()
    conn.close()
    
    # Create leaderboard embed
    embed = discord.Embed(
        title="🏆 XP Leaderboard",
        description=f"Top {limit} members with the most XP",
        color=discord.Color.gold()
    )
    
    for i, (user_id, xp) in enumerate(top_users, 1):
        member = ctx.guild.get_member(user_id)
        if member:
            level = get_level(xp)
            embed.add_field(
                name=f"#{i} {member.display_name}",
                value=f"Level {level} | {xp} XP",
                inline=False
            )
    
    await ctx.respond(embed=embed)

# Economy Commands
@bot.command(name="balance")
async def balance(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    
    # Get user balance
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT balance FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    conn.close()
    
    balance = result[0] if result else 0
    
    embed = discord.Embed(
        title="💰 Balance",
        description=f"{member.mention} has **{balance}** coins.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.slash_command(name="balance", description="Check your or another member's balance.", guild_ids=[GUILD_ID])
async def balance_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to check", default=None)):
    if not member:
        member = ctx.user
    
    # Get user balance
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT balance FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    conn.close()
    
    balance = result[0] if result else 0
    
    embed = discord.Embed(
        title="💰 Balance",
        description=f"{member.mention} has **{balance}** coins.",
        color=discord.Color.gold()
    )
    await ctx.respond(embed=embed)

@bot.command(name="daily")
async def daily(ctx):
    # Check if user can claim daily
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT daily_last_claimed, balance FROM users WHERE user_id = ?''', (ctx.author.id,))
    result = c.fetchone()
    
    if result:
        last_claimed_str, balance = result
        if last_claimed_str:
            last_claimed = datetime.datetime.fromisoformat(last_claimed_str)
            next_claim = last_claimed + datetime.timedelta(days=1)
            
            if datetime.datetime.now() < next_claim:
                time_left = next_claim - datetime.datetime.now()
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await ctx.send(f"❌ You can claim your next daily reward in {hours}h {minutes}m.")
                conn.close()
                return
    
    # Calculate reward
    reward = random.randint(100, 500)
    
    # Update balance and last claimed
    new_balance = balance + reward if result else reward
    c.execute('''INSERT OR REPLACE INTO users (user_id, balance, daily_last_claimed)
                 VALUES (?, ?, ?)''', 
              (ctx.author.id, new_balance, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="🎁 Daily Reward",
        description=f"You have claimed your daily reward of **{reward}** coins!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.slash_command(name="daily", description="Claim your daily reward.", guild_ids=[GUILD_ID])
async def daily_slash(ctx: discord.ApplicationContext):
    # Check if user can claim daily
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT daily_last_claimed, balance FROM users WHERE user_id = ?''', (ctx.user.id,))
    result = c.fetchone()
    
    if result:
        last_claimed_str, balance = result
        if last_claimed_str:
            last_claimed = datetime.datetime.fromisoformat(last_claimed_str)
            next_claim = last_claimed + datetime.timedelta(days=1)
            
            if datetime.datetime.now() < next_claim:
                time_left = next_claim - datetime.datetime.now()
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await ctx.respond(f"❌ You can claim your next daily reward in {hours}h {minutes}m.", ephemeral=True)
                conn.close()
                return
    
    # Calculate reward
    reward = random.randint(100, 500)
    
    # Update balance and last claimed
    new_balance = balance + reward if result else reward
    c.execute('''INSERT OR REPLACE INTO users (user_id, balance, daily_last_claimed)
                 VALUES (?, ?, ?)''', 
              (ctx.user.id, new_balance, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="🎁 Daily Reward",
        description=f"You have claimed your daily reward of **{reward}** coins!",
        color=discord.Color.green()
    )
    await ctx.respond(embed=embed)

@bot.command(name="work")
async def work(ctx):
    # Get user balance
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT balance FROM users WHERE user_id = ?''', (ctx.author.id,))
    result = c.fetchone()
    balance = result[0] if result else 0
    
    # Calculate earnings
    earnings = random.randint(50, 200)
    
    # Update balance
    new_balance = balance + earnings
    c.execute('''INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)''', 
              (ctx.author.id, new_balance))
    conn.commit()
    conn.close()
    
    # Work messages
    work_messages = [
        f"You worked as a programmer and earned **{earnings}** coins!",
        f"You helped someone with their homework and earned **{earnings}** coins!",
        f"You completed a survey and earned **{earnings}** coins!",
        f"You walked dogs and earned **{earnings}** coins!",
        f"You designed a logo and earned **{earnings}** coins!"
    ]
    
    embed = discord.Embed(
        title="💼 Work",
        description=random.choice(work_messages),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.slash_command(name="work", description="Work to earn coins.", guild_ids=[GUILD_ID])
async def work_slash(ctx: discord.ApplicationContext):
    # Get user balance
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT balance FROM users WHERE user_id = ?''', (ctx.user.id,))
    result = c.fetchone()
    balance = result[0] if result else 0
    
    # Calculate earnings
    earnings = random.randint(50, 200)
    
    # Update balance
    new_balance = balance + earnings
    c.execute('''INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)''', 
              (ctx.user.id, new_balance))
    conn.commit()
    conn.close()
    
    # Work messages
    work_messages = [
        f"You worked as a programmer and earned **{earnings}** coins!",
        f"You helped someone with their homework and earned **{earnings}** coins!",
        f"You completed a survey and earned **{earnings}** coins!",
        f"You walked dogs and earned **{earnings}** coins!",
        f"You designed a logo and earned **{earnings}** coins!"
    ]
    
    embed = discord.Embed(
        title="💼 Work",
        description=random.choice(work_messages),
        color=discord.Color.blue()
    )
    await ctx.respond(embed=embed)

@bot.command(name="shop")
async def shop(ctx):
    if not shop_items:
        await ctx.send("❌ The shop is currently empty.")
        return
    
    embed = discord.Embed(
        title="🛒 Shop",
        description="Buy items with your coins!",
        color=discord.Color.purple()
    )
    
    for item in shop_items:
        item_id, name, price, description, role_id = item
        role = ctx.guild.get_role(role_id) if role_id else None
        role_text = f" (Grants {role.mention})" if role else ""
        
        embed.add_field(
            name=f"{name} - {price} coins{role_text}",
            value=description or "No description",
            inline=False
        )
    
    embed.set_footer(text=f"Use /buy <item_id> to purchase an item")
    await ctx.send(embed=embed)

@bot.slash_command(name="shop", description="View the server shop.", guild_ids=[GUILD_ID])
async def shop_slash(ctx: discord.ApplicationContext):
    if not shop_items:
        await ctx.respond("❌ The shop is currently empty.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🛒 Shop",
        description="Buy items with your coins!",
        color=discord.Color.purple()
    )
    
    for item in shop_items:
        item_id, name, price, description, role_id = item
        role = ctx.guild.get_role(role_id) if role_id else None
        role_text = f" (Grants {role.mention})" if role else ""
        
        embed.add_field(
            name=f"{name} - {price} coins{role_text}",
            value=description or "No description",
            inline=False
        )
    
    embed.set_footer(text=f"Use /buy <item_id> to purchase an item")
    await ctx.respond(embed=embed)

@bot.command(name="buy")
async def buy(ctx, item_id: int):
    # Get item from shop
    item = None
    for shop_item in shop_items:
        if shop_item[0] == item_id:
            item = shop_item
            break
    
    if not item:
        await ctx.send("❌ Item not found in the shop.")
        return
    
    _, name, price, description, role_id = item
    
    # Get user balance
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT balance FROM users WHERE user_id = ?''', (ctx.author.id,))
    result = c.fetchone()
    balance = result[0] if result else 0
    
    if balance < price:
        await ctx.send(f"❌ You don't have enough coins to buy {name}. You need {price - balance} more coins.")
        conn.close()
        return
    
    # Process purchase
    new_balance = balance - price
    c.execute('''INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)''', 
              (ctx.author.id, new_balance))
    conn.commit()
    conn.close()
    
    # Grant role if applicable
    if role_id:
        role = ctx.guild.get_role(role_id)
        if role and role not in ctx.author.roles:
            try:
                await ctx.author.add_roles(role)
                await ctx.send(f"✅ You have purchased {name} and received the {role.name} role!")
            except discord.Forbidden:
                await ctx.send(f"✅ You have purchased {name}! (Failed to grant role due to permissions)")
        else:
            await ctx.send(f"✅ You have purchased {name}!")
    else:
        await ctx.send(f"✅ You have purchased {name}!")

@bot.slash_command(name="buy", description="Buy an item from the shop.", guild_ids=[GUILD_ID])
async def buy_slash(ctx: discord.ApplicationContext, item_id: discord.Option(int, "The ID of the item to buy")):
    # Get item from shop
    item = None
    for shop_item in shop_items:
        if shop_item[0] == item_id:
            item = shop_item
            break
    
    if not item:
        await ctx.respond("❌ Item not found in the shop.", ephemeral=True)
        return
    
    _, name, price, description, role_id = item
    
    # Get user balance
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT balance FROM users WHERE user_id = ?''', (ctx.user.id,))
    result = c.fetchone()
    balance = result[0] if result else 0
    
    if balance < price:
        await ctx.respond(f"❌ You don't have enough coins to buy {name}. You need {price - balance} more coins.", ephemeral=True)
        conn.close()
        return
    
    # Process purchase
    new_balance = balance - price
    c.execute('''INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)''', 
              (ctx.user.id, new_balance))
    conn.commit()
    conn.close()
    
    # Grant role if applicable
    if role_id:
        role = ctx.guild.get_role(role_id)
        if role and role not in ctx.user.roles:
            try:
                await ctx.user.add_roles(role)
                await ctx.respond(f"✅ You have purchased {name} and received the {role.name} role!")
            except discord.Forbidden:
                await ctx.respond(f"✅ You have purchased {name}! (Failed to grant role due to permissions)")
        else:
            await ctx.respond(f"✅ You have purchased {name}!")
    else:
        await ctx.respond(f"✅ You have purchased {name}!")

# Utility Commands
@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    
    # Get user data
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT xp, balance, warnings FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    conn.close()
    
    xp = result[0] if result and result[0] else 0
    balance = result[1] if result and result[1] else 0
    warnings = result[2] if result and result[2] else 0
    
    level = get_level(xp)
    
    # Create embed
    embed = discord.Embed(
        title=f"User Information - {member.name}",
        description=f"ID: {member.id}",
        color=member.color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Level", value=str(level), inline=True)
    embed.add_field(name="XP", value=str(xp), inline=True)
    embed.add_field(name="Balance", value=f"{balance} coins", inline=True)
    embed.add_field(name="Warnings", value=f"{warnings}/{MAX_WARNINGS}", inline=True)
    
    if member.activity:
        embed.add_field(name="Activity", value=member.activity.name, inline=False)
    
    if member.roles:
        roles = [role.mention for role in member.roles if role != member.guild.default_role]
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles[:10]), inline=False)
    
    await ctx.send(embed=embed)

@bot.slash_command(name="userinfo", description="Get information about a user.", guild_ids=[GUILD_ID])
async def userinfo_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to get info about", default=None)):
    if not member:
        member = ctx.user
    
    # Get user data
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''SELECT xp, balance, warnings FROM users WHERE user_id = ?''', (member.id,))
    result = c.fetchone()
    conn.close()
    
    xp = result[0] if result and result[0] else 0
    balance = result[1] if result and result[1] else 0
    warnings = result[2] if result and result[2] else 0
    
    level = get_level(xp)
    
    # Create embed
    embed = discord.Embed(
        title=f"User Information - {member.name}",
        description=f"ID: {member.id}",
        color=member.color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Level", value=str(level), inline=True)
    embed.add_field(name="XP", value=str(xp), inline=True)
    embed.add_field(name="Balance", value=f"{balance} coins", inline=True)
    embed.add_field(name="Warnings", value=f"{warnings}/{MAX_WARNINGS}", inline=True)
    
    if member.activity:
        embed.add_field(name="Activity", value=member.activity.name, inline=False)
    
    if member.roles:
        roles = [role.mention for role in member.roles if role != member.guild.default_role]
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles[:10]), inline=False)
    
    await ctx.respond(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    
    # Get member counts
    total_members = guild.member_count
    online_members = len([m for m in guild.members if m.status != discord.Status.offline])
    
    # Get channel counts
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    
    # Create embed
    embed = discord.Embed(
        title=f"Server Information - {guild.name}",
        description=f"ID: {guild.id}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Members", value=f"{total_members} total\n{online_members} online", inline=True)
    embed.add_field(name="Channels", value=f"{text_channels} text\n{voice_channels} voice", inline=True)
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="Emojis", value=str(len(guild.emojis)), inline=True)
    embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
    embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
    
    if guild.description:
        embed.add_field(name="Description", value=guild.description, inline=False)
    
    await ctx.send(embed=embed)

@bot.slash_command(name="serverinfo", description="Get information about the server.", guild_ids=[GUILD_ID])
async def serverinfo_slash(ctx: discord.ApplicationContext):
    guild = ctx.guild
    
    # Get member counts
    total_members = guild.member_count
    online_members = len([m for m in guild.members if m.status != discord.Status.offline])
    
    # Get channel counts
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    
    # Create embed
    embed = discord.Embed(
        title=f"Server Information - {guild.name}",
        description=f"ID: {guild.id}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Members", value=f"{total_members} total\n{online_members} online", inline=True)
    embed.add_field(name="Channels", value=f"{text_channels} text\n{voice_channels} voice", inline=True)
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="Emojis", value=str(len(guild.emojis)), inline=True)
    embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
    embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
    
    if guild.description:
        embed.add_field(name="Description", value=guild.description, inline=False)
    
    await ctx.respond(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    
    embed = discord.Embed(
        title=f"{member.name}'s Avatar",
        color=member.color
    )
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.slash_command(name="avatar", description="Get a user's avatar.", guild_ids=[GUILD_ID])
async def avatar_slash(ctx: discord.ApplicationContext, member: discord.Option(discord.Member, "The member to get the avatar of", default=None)):
    if not member:
        member = ctx.user
    
    embed = discord.Embed(
        title=f"{member.name}'s Avatar",
        color=member.color
    )
    embed.set_image(url=member.display_avatar.url)
    await ctx.respond(embed=embed)

@bot.command(name="invite")
async def invite(ctx):
    embed = discord.Embed(
        title="Invite KuzzBot",
        description="Invite KuzzBot to your server!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Invite Link", value="[Click here to invite](https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands)")
    await ctx.send(embed=embed)

@bot.slash_command(name="invite", description="Get the bot's invite link.", guild_ids=[GUILD_ID])
async def invite_slash(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="Invite KuzzBot",
        description="Invite KuzzBot to your server!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Invite Link", value="[Click here to invite](https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands)")
    await ctx.respond(embed=embed)

@bot.command(name="help")
async def help(ctx, command_name: str = None):
    if command_name:
        # Help for specific command
        command = bot.get_command(command_name)
        if not command:
            await ctx.send(f"❌ Command '{command_name}' not found.")
            return
        
        embed = discord.Embed(
            title=f"Help - {command_name}",
            description=command.help or "No description available.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Usage", value=f"`{DEFAULT_PREFIX}{command_name} {command.signature if command.signature else ''}`")
        await ctx.send(embed=embed)
    else:
        # General help
        embed = discord.Embed(
            title="KuzzBot Help",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )
        
        # Categorize commands
        categories = {
            "Moderation": ["kick", "ban", "mute", "unmute", "warn", "warnings", "clear"],
            "Tickets": ["ticket", "close", "add", "remove"],
            "Giveaways": ["giveaway", "reroll"],
            "Suggestions": ["suggest", "approve", "reject"],
            "Leveling": ["rank", "leaderboard"],
            "Economy": ["balance", "daily", "work", "shop", "buy"],
            "Utility": ["userinfo", "serverinfo", "avatar", "invite", "ping"],
            "Admin": ["sendverify", "sendservices", "ok", "nok"]
        }
        
        for category, commands in categories.items():
            command_list = []
            for cmd_name in commands:
                cmd = bot.get_command(cmd_name)
                if cmd:
                    command_list.append(f"`{DEFAULT_PREFIX}{cmd_name}`")
            
            if command_list:
                embed.add_field(name=category, value="\n".join(command_list), inline=False)
        
        embed.set_footer(text=f"Use {DEFAULT_PREFIX}help <command> for more info on a specific command.")
        await ctx.send(embed=embed)

@bot.slash_command(name="help", description="Get help with commands.", guild_ids=[GUILD_ID])
async def help_slash(ctx: discord.ApplicationContext, command_name: discord.Option(str, "The command to get help for", default=None)):
    if command_name:
        # Help for specific command
        command = bot.get_command(command_name)
        if not command:
            await ctx.respond(f"❌ Command '{command_name}' not found.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Help - {command_name}",
            description=command.help or "No description available.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Usage", value=f"`{DEFAULT_PREFIX}{command_name} {command.signature if command.signature else ''}`")
        await ctx.respond(embed=embed)
    else:
        # General help
        embed = discord.Embed(
            title="KuzzBot Help",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )
        
        # Categorize commands
        categories = {
            "Moderation": ["kick", "ban", "mute", "unmute", "warn", "warnings", "clear"],
            "Tickets": ["ticket", "close", "add", "remove"],
            "Giveaways": ["giveaway", "reroll"],
            "Suggestions": ["suggest", "approve", "reject"],
            "Leveling": ["rank", "leaderboard"],
            "Economy": ["balance", "daily", "work", "shop", "buy"],
            "Utility": ["userinfo", "serverinfo", "avatar", "invite", "ping"],
            "Admin": ["sendverify", "sendservices", "ok", "nok"]
        }
        
        for category, commands in categories.items():
            command_list = []
            for cmd_name in commands:
                cmd = bot.get_command(cmd_name)
                if cmd:
                    command_list.append(f"`{DEFAULT_PREFIX}{cmd_name}`")
            
            if command_list:
                embed.add_field(name=category, value="\n".join(command_list), inline=False)
        
        embed.set_footer(text=f"Use /help <command> for more info on a specific command.")
        await ctx.respond(embed=embed)

# Fun Commands
@bot.command(name="meme")
async def meme(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://meme-api.herokuapp.com/gimme") as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title=data["title"],
                    color=discord.Color.random()
                )
                embed.set_image(url=data["url"])
                embed.set_footer(text=f"👍 {data['ups']} | 💬 {data['postLink']}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to fetch meme.")

@bot.slash_command(name="meme", description="Get a random meme.", guild_ids=[GUILD_ID])
async def meme_slash(ctx: discord.ApplicationContext):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://meme-api.herokuapp.com/gimme") as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title=data["title"],
                    color=discord.Color.random()
                )
                embed.set_image(url=data["url"])
                embed.set_footer(text=f"👍 {data['ups']} | 💬 {data['postLink']}")
                await ctx.respond(embed=embed)
            else:
                await ctx.respond("❌ Failed to fetch meme.", ephemeral=True)

@bot.command(name="joke")
async def joke(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title="😂 Joke",
                    description=f"{data['setup']}\n\n||{data['punchline']}||",
                    color=discord.Color.random()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to fetch joke.")

@bot.slash_command(name="joke", description="Get a random joke.", guild_ids=[GUILD_ID])
async def joke_slash(ctx: discord.ApplicationContext):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title="😂 Joke",
                    description=f"{data['setup']}\n\n||{data['punchline']}||",
                    color=discord.Color.random()
                )
                await ctx.respond(embed=embed)
            else:
                await ctx.respond("❌ Failed to fetch joke.", ephemeral=True)

@bot.command(name="8ball")
async def eight_ball(ctx, *, question: str):
    responses = [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes - definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    
    embed = discord.Embed(
        title="🎱 8 Ball",
        description=f"Question: {question}\n\nAnswer: {random.choice(responses)}",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

@bot.slash_command(name="8ball", description="Ask the magic 8 ball a question.", guild_ids=[GUILD_ID])
async def eight_ball_slash(ctx: discord.ApplicationContext, question: discord.Option(str, "Your question for the 8 ball")):
    responses = [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes - definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    
    embed = discord.Embed(
        title="🎱 8 Ball",
        description=f"Question: {question}\n\nAnswer: {random.choice(responses)}",
        color=discord.Color.purple()
    )
    await ctx.respond(embed=embed)

@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
    if sides < 1 or sides > 100:
        await ctx.send("❌ Please provide a number between 1 and 100.")
        return
    
    result = random.randint(1, sides)
    embed = discord.Embed(
        title="🎲 Dice Roll",
        description=f"You rolled a **{result}** on a {sides}-sided die!",
        color=discord.Color.random()
    )
    await ctx.send(embed=embed)

@bot.slash_command(name="roll", description="Roll a dice with a specified number of sides.", guild_ids=[GUILD_ID])
async def roll_slash(ctx: discord.ApplicationContext, sides: discord.Option(int, "Number of sides on the dice", default=6)):
    if sides < 1 or sides > 100:
        await ctx.respond("❌ Please provide a number between 1 and 100.", ephemeral=True)
        return
    
    result = random.randint(1, sides)
    embed = discord.Embed(
        title="🎲 Dice Roll",
        description=f"You rolled a **{result}** on a {sides}-sided die!",
        color=discord.Color.random()
    )
    await ctx.respond(embed=embed)

@bot.command(name="coinflip")
async def coinflip(ctx):
    result = random.choice(["Heads", "Tails"])
    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=f"The coin landed on **{result}**!",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.slash_command(name="coinflip", description="Flip a coin.", guild_ids=[GUILD_ID])
async def coinflip_slash(ctx: discord.ApplicationContext):
    result = random.choice(["Heads", "Tails"])
    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=f"The coin landed on **{result}**!",
        color=discord.Color.gold()
    )
    await ctx.respond(embed=embed)

# Music Commands (simplified - would need a music library for full functionality)
@bot.command(name="play")
async def play(ctx, *, query: str):
    if not MUSIC_ENABLED:
        await ctx.send("❌ Music system is currently disabled.")
        return
    
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await ctx.send("❌ You need to be in a voice channel to play music.")
        return
    
    # Check if user has DJ role
    dj_role = discord.utils.get(ctx.guild.roles, name=DJ_ROLE_NAME)
    if dj_role and dj_role not in ctx.author.roles:
        await ctx.send(f"❌ You need the {dj_role.name} role to play music.")
        return
    
    # Simulate playing music
    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"**{query}**",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    
    # Send now playing message
    message = await ctx.send(embed=embed)
    now_playing_messages[ctx.guild.id] = message.id
    
    # Add music controls
    view = MusicView(ctx.guild.id)
    await message.edit(view=view)

@bot.slash_command(name="play", description="Play music in a voice channel.", guild_ids=[GUILD_ID])
async def play_slash(ctx: discord.ApplicationContext, query: discord.Option(str, "The song to play")):
    if not MUSIC_ENABLED:
        await ctx.respond("❌ Music system is currently disabled.", ephemeral=True)
        return
    
    voice_channel = ctx.user.voice.channel if ctx.user.voice else None
    if not voice_channel:
        await ctx.respond("❌ You need to be in a voice channel to play music.", ephemeral=True)
        return
    
    # Check if user has DJ role
    dj_role = discord.utils.get(ctx.guild.roles, name=DJ_ROLE_NAME)
    if dj_role and dj_role not in ctx.user.roles:
        await ctx.respond(f"❌ You need the {dj_role.name} role to play music.", ephemeral=True)
        return
    
    # Simulate playing music
    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"**{query}**",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Requested by {ctx.user.name}")
    
    # Send now playing message
    message = await ctx.respond(embed=embed)
    now_playing_messages[ctx.guild.id] = message.id
    
    # Add music controls
    view = MusicView(ctx.guild.id)
    await message.edit(view=view)

# Reminder Commands
@bot.command(name="remind")
async def remind(ctx, time: str, *, message: str):
    # Parse time
    time_units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    try:
        duration = int(time[:-1]) * time_units[time[-1]]
    except (ValueError, KeyError):
        await ctx.send("❌ Invalid time format. Use format like 10s, 5m, 1h, 2d.")
        return
    
    if duration < 10 or duration > 604800:  # Min 10 seconds, max 1 week
        await ctx.send("❌ Time must be between 10 seconds and 1 week.")
        return
    
    # Calculate reminder time
    reminder_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
    
    # Create reminder task
    reminder_id = f"{ctx.author.id}_{int(time.time())}"
    reminder_tasks[reminder_id] = {
        "user_id": ctx.author.id,
        "message": message,
        "time": reminder_time,
        "created_at": datetime.datetime.now()
    }
    
    embed = discord.Embed(
        title="⏰ Reminder Set",
        description=f"I will remind you in {time} about: {message}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.slash_command(name="remind", description="Set a reminder for yourself.", guild_ids=[GUILD_ID])
async def remind_slash(ctx: discord.ApplicationContext, 
                      time: discord.Option(str, "Time duration (e.g., 10s, 5m, 1h, 2d)"),
                      message: discord.Option(str, "The reminder message")):
    # Parse time
    time_units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    try:
        duration = int(time[:-1]) * time_units[time[-1]]
    except (ValueError, KeyError):
        await ctx.respond("❌ Invalid time format. Use format like 10s, 5m, 1h, 2d.", ephemeral=True)
        return
    
    if duration < 10 or duration > 604800:  # Min 10 seconds, max 1 week
        await ctx.respond("❌ Time must be between 10 seconds and 1 week.", ephemeral=True)
        return
    
    # Calculate reminder time
    reminder_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
    
    # Create reminder task
    reminder_id = f"{ctx.user.id}_{int(time.time())}"
    reminder_tasks[reminder_id] = {
        "user_id": ctx.user.id,
        "message": message,
        "time": reminder_time,
        "created_at": datetime.datetime.now()
    }
    
    embed = discord.Embed(
        title="⏰ Reminder Set",
        description=f"I will remind you in {time} about: {message}",
        color=discord.Color.blue()
    )
    await ctx.respond(embed=embed)

# Poll Commands
@bot.command(name="poll")
@commands.has_permissions(manage_messages=True)
async def create_poll(ctx, question: str, *options: str):
    if len(options) < 2 or len(options) > 10:
        await ctx.send("❌ Please provide between 2 and 10 options.")
        return
    
    # Create poll embed
    embed = discord.Embed(
        title=f"📊 Poll: {question}",
        color=discord.Color.blue()
    )
    
    for i, option in enumerate(options):
        embed.add_field(name=f"Option {i+1}", value=option, inline=False)
    
    # Send poll message
    message = await ctx.send(embed=embed)
    
    # Save to database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO polls (message_id, channel_id, question, options)
                 VALUES (?, ?, ?, ?)''', 
              (message.id, ctx.channel.id, question, json.dumps(options)))
    conn.commit()
    conn.close()
    
    # Add poll view
    view = PollView(message.id, options)
    await message.edit(view=view)
    
    await ctx.send("✅ Poll created successfully!")

@bot.slash_command(name="poll", description="Create a poll.", guild_ids=[GUILD_ID])
@commands.has_permissions(manage_messages=True)
async def create_poll_slash(ctx: discord.ApplicationContext, 
                          question: discord.Option(str, "The poll question"),
                          option1: discord.Option(str, "First option"),
                          option2: discord.Option(str, "Second option"),
                          option3: discord.Option(str, "Third option", default=None),
                          option4: discord.Option(str, "Fourth option", default=None),
                          option5: discord.Option(str, "Fifth option", default=None)):
    options = [option1, option2]
    if option3:
        options.append(option3)
    if option4:
        options.append(option4)
    if option5:
        options.append(option5)
    
    if len(options) < 2 or len(options) > 5:
        await ctx.respond("❌ Please provide between 2 and 5 options.", ephemeral=True)
        return
    
    # Create poll embed
    embed = discord.Embed(
        title=f"📊 Poll: {question}",
        color=discord.Color.blue()
    )
    
    for i, option in enumerate(options):
        embed.add_field(name=f"Option {i+1}", value=option, inline=False)
    
    # Send poll message
    message = await ctx.respond(embed=embed)
    message = await message.original_response()
    
    # Save to database
    conn = sqlite3.connect('kuzzbot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO polls (message_id, channel_id, question, options)
                 VALUES (?, ?, ?, ?)''', 
              (message.id, ctx.channel.id, question, json.dumps(options)))
    conn.commit()
    conn.close()
    
    # Add poll view
    view = PollView(message.id, options)
    await message.edit(view=view)
    
    await ctx.followup.send("✅ Poll created successfully!", ephemeral=True)

# --- ERROR HANDLING ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required arguments. Check the command usage with /help.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument. Check the command usage with /help.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        logger.error(f"Error in command {ctx.command}: {error}")
        await ctx.send("❌ An error occurred while executing the command.")

@bot.event
async def on_application_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond("❌ You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.respond("❌ Missing required arguments. Check the command usage with /help.", ephemeral=True)
    elif isinstance(error, commands.BadArgument):
        await ctx.respond("❌ Invalid argument. Check the command usage with /help.", ephemeral=True)
    else:
        logger.error(f"Error in slash command {ctx.command}: {error}")
        await ctx.respond("❌ An error occurred while executing the command.", ephemeral=True)

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    try:
        token = os.environ.get('DISCORD_TOKEN')
        if not token:
            print("ERROR: DISCORD_TOKEN environment variable not found.")
        else:
            keep_alive()
            bot.run(token)
    except Exception as e:
        print(f"CRITICAL ERROR: Could not start the bot. {e}")
        logger.error(f"CRITICAL ERROR: Could not start the bot. {e}")
