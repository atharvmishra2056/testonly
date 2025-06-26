import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import os
from flask import Flask
from threading import Thread
import random
import string
import asyncio

# --- CONFIGURATION ---
GUILD_ID = 1377883327771574372  # Your Server ID
VERIFY_CHANNEL_ID = 1377883328526680065  # Verify Channel ID
LOG_CHANNEL_ID = 1377883329755611280  # Logs Channel ID 
GENERAL_CHANNEL_ID = 1377883329503821841  # General Channel ID 
MOD_ROLE_NAME = "Moderator"  # Mod role name
MEMBER_ROLE_NAME = "KuzzMember"  # Member role name
BAD_WORDS = ["Fuck", "Nigga"]  # Add more as needed
CAPTCHA_TIMEOUT = 60  # Seconds for CAPTCHA
COOLDOWN_SECONDS = 5  # Button cooldown
SERVICE_CHANNEL_ID = 1387386391800975390  # Service Channel ID

# --- KEEP ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "KuzzBot v5.2 is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix=["/", "wolf "], intents=intents)

# Store CAPTCHA and XP data
captcha_sessions = {}
button_cooldowns = {}
xp = {}

class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify Now", style=discord.ButtonStyle.green, custom_id="verify_kuzz_v5")
    async def verify_button(self, button, interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        current_time = discord.utils.utcnow().timestamp()
        if button_cooldowns.get(member.id, 0) + COOLDOWN_SECONDS > current_time:
            await interaction.followup.send("Please wait before trying again.", ephemeral=True)
            return
        button_cooldowns[member.id] = current_time

        captcha_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        captcha_sessions[member.id] = captcha_code
        embed = discord.Embed(title="🔒 CAPTCHA Verification", description=f"Enter code: **{captcha_code}** (within {CAPTCHA_TIMEOUT}s)", color=discord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)

        def check(msg):
            return msg.author.id == member.id and msg.channel == interaction.channel and msg.content == captcha_code

        try:
            msg = await bot.wait_for('message', check=check, timeout=CAPTCHA_TIMEOUT)
            await msg.delete()
            role = discord.utils.get(interaction.guild.roles, name=MEMBER_ROLE_NAME)
            if role and role not in member.roles:
                await member.add_roles(role)
                verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
                await verify_channel.set_permissions(member, view_channel=False)
                welcome_embed = discord.Embed(title="🎉 Welcome to KuzzMarket!", description=f"Congrats, {member.mention}! You are our **{len(interaction.guild.members)}th member**! Join #💬 | General.", color=discord.Color.blue())
                await interaction.followup.send(embed=welcome_embed, ephemeral=True)
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(title="Verification Log", color=discord.Color.purple())
                    log_embed.add_field(name="User", value=member.mention, inline=True)
                    log_embed.add_field(name="Role", value=role.name, inline=True)
                    log_embed.add_field(name="Time", value=discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
                    await log_channel.send(embed=log_embed)
            else:
                await interaction.followup.send("Already verified or role missing!", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("CAPTCHA timed out. Try again.", ephemeral=True)
        finally:
            captcha_sessions.pop(member.id, None)

class RoleSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Buyer", description="Access to buy services", custom_id="role_select_buyer"),
            discord.SelectOption(label="Seller", description="Sell your services", custom_id="role_select_seller")
        ]
        super().__init__(placeholder="Choose a role...", min_values=1, max_values=1, options=options, custom_id="role_select_kuzzmarket")

    async def callback(self, interaction):
        role_name = self.values[0]
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            role = await interaction.guild.create_role(name=role_name)
        if role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role_name} role!", ephemeral=True)
        else:
            await interaction.response.send_message(f"You already have {role_name}!", ephemeral=True)

class MarketplaceView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())

class ServiceView(View):
    def __init__(self, unique_suffix):
        super().__init__(timeout=None)
        self.add_item(Button(label="Facebook", emoji="🇫", custom_id=f"service_facebook_{unique_suffix}", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="Discord", emoji="🇩", custom_id=f"service_discord_{unique_suffix}", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="Instagram", emoji="🇮", custom_id=f"service_instagram_{unique_suffix}", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="Twitter", emoji="🇹", custom_id=f"service_twitter_{unique_suffix}", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="TikTok", emoji="⏰", custom_id=f"service_tiktok_{unique_suffix}", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="Twitch", emoji="🎮", custom_id=f"service_twitch_{unique_suffix}", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="Snapchat", emoji="👻", custom_id=f"service_snapchat_{unique_suffix}", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="YouTube", emoji="🎥", custom_id=f"service_youtube_{unique_suffix}", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="Spotify", emoji="🎵", custom_id=f"service_spotify_{unique_suffix}", style=discord.ButtonStyle.primary))

    async def interaction_check(self, interaction):
        return True

    @discord.ui.button(label="Facebook", emoji="🇫", custom_id="service_facebook_[unique]")
    async def facebook_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387742165681180754  # Facebook role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

    @discord.ui.button(label="Discord", emoji="🇩", custom_id="service_discord_[unique]")
    async def discord_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387742348175216720  # Discord role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

    @discord.ui.button(label="Instagram", emoji="🇮", custom_id="service_instagram_[unique]")
    async def instagram_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387735712874500096  # Instagram role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

    @discord.ui.button(label="Twitter", emoji="🇹", custom_id="service_twitter_[unique]")
    async def twitter_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387756089864486942  # Twitter role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

    @discord.ui.button(label="TikTok", emoji="⏰", custom_id="service_tiktok_[unique]")
    async def tiktok_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387756237566906488  # TikTok role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

    @discord.ui.button(label="Twitch", emoji="🎮", custom_id="service_twitch_[unique]")
    async def twitch_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387756062169366718  # Twitch role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

    @discord.ui.button(label="Snapchat", emoji="👻", custom_id="service_snapchat_[unique]")
    async def snapchat_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387755991243952229  # Snapchat role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

    @discord.ui.button(label="YouTube", emoji="🎥", custom_id="service_youtube_[unique]")
    async def youtube_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387742474533077084  # YouTube role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

    @discord.ui.button(label="Spotify", emoji="🎵", custom_id="service_spotify_[unique]")
    async def spotify_button(self, button, interaction):
        unique_suffix = interaction.custom_id.split('_')[-1]  # Extract suffix
        role_id = 1387756124165505065  # Spotify role ID
        role = interaction.guild.get_role(role_id)
        if role and role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
        else:
            await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    await bot.change_presence(activity=discord.Game(name="KuzzMarket | /help"))
    bot.add_view(VerifyView())
    bot.add_view(MarketplaceView())
    print(f"Bot ready - Service channel ID: {SERVICE_CHANNEL_ID}")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1387419489586380972)  # Use welcome channel ID
    if channel:
        welcome_message = f"🎉🌟 **Welcome to KuzzMarket, {member.mention}!** 🌟🎉\nGet started by verifying yourself here: <#1377883328526680065>! 🚀😊"
        await channel.send(welcome_message)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    # XP System
    user_id = message.author.id
    xp[user_id] = xp.get(user_id, 0) + 5
    if xp[user_id] >= 100:
        role = discord.utils.get(message.guild.roles, name="Active Member")
        if not role:
            role = await message.guild.create_role(name="Active Member", color=discord.Color.gold())
        if role and role not in message.author.roles:
            await message.author.add_roles(role)
            await message.channel.send(f"{message.author.mention} is now an Active Member!")
        xp[user_id] = 0

    # Auto-Moderation
    content = message.content.lower()
    if any(word in content for word in BAD_WORDS):
        await message.delete()
        await message.author.send("Avoid inappropriate language!")
        return

    await bot.process_commands(message)

# Prefix commands with "wolf"
@bot.command()
async def pingbot(ctx):
    await ctx.send("Bot is active! 🏓")

@bot.command()
@commands.has_role(MOD_ROLE_NAME)
async def createrole(ctx, name: str, color: str = "0x000000"):
    try:
        color_int = int(color, 16)
        role = await ctx.guild.create_role(name=name, color=discord.Color(color_int))
        await ctx.send(f"Created {role.name} with color {color}!")
    except ValueError:
        await ctx.send("Invalid hex color! Use 0xRRGGBB.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def sendverify(ctx):
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel:
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
        embed = discord.Embed(title="✅ Server Verification", description="Welcome! Click to verify and join KuzzMarket.", color=discord.Color.green())
        embed.set_footer(text="KuzzMarket - Powered by KuzzBot")
        await channel.send(embed=embed, view=VerifyView())
        await ctx.send("Verification message sent!")
    else:
        await ctx.send("Verify channel not found!")

@bot.command()
@commands.has_permissions(administrator=True)
async def clearverify(ctx):
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel:
        count = 0
        async for message in channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()
                count += 1
        await ctx.send(f"Cleared {count} messages!")
    else:
        await ctx.send("Verify channel not found!")

@bot.command()
@commands.has_permissions(administrator=True)
async def sendservices(ctx):
    channel = bot.get_channel(SERVICE_CHANNEL_ID)
    if channel:
        unique_suffix = str(random.randint(1000, 9999))  # Generate unique suffix
        embed = discord.Embed(title="🛒 Choose a Service", description="Click the button based on what service you want to buy:", color=discord.Color.gold())
        view = ServiceView(unique_suffix)
        await channel.send(embed=embed, view=view)
        await ctx.send("Service message sent to the service channel!")
    else:
        await ctx.send("Service channel not found or bot lacks permission!")

# Keep slash commands
@bot.slash_command(name="createrole", description="Create a custom role (Mods only)", guild_ids=[GUILD_ID])
@commands.has_role(MOD_ROLE_NAME)
async def createrole_slash(ctx, name: str, color: str = "0x000000"):
    try:
        color_int = int(color, 16)
        role = await ctx.guild.create_role(name=name, color=discord.Color(color_int))
        await ctx.respond(f"Created {role.name} with color {color}!", ephemeral=True)
    except ValueError:
        await ctx.respond("Invalid hex color! Use 0xRRGGBB.", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"Error: {e}", ephemeral=True)

@bot.slash_command(name="sendverify", description="Send verification message (Admins only)", guild_ids=[GUILD_ID])
@commands.has_permissions(administrator=True)
async def send_verify_message(ctx):
    await ctx.defer(ephemeral=True)
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel:
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
        embed = discord.Embed(title="✅ Server Verification", description="Welcome! Click to verify and join KuzzMarket.", color=discord.Color.green())
        embed.set_footer(text="KuzzMarket - Powered by KuzzBot")
        await channel.send(embed=embed, view=VerifyView())
        await ctx.followup.send("Verification message sent!", ephemeral=True)
    else:
        await ctx.followup.send("Verify channel not found!", ephemeral=True)

@bot.slash_command(name="clearverify", description="Clear old verify messages (Admins only)", guild_ids=[GUILD_ID])
@commands.has_permissions(administrator=True)
async def clear_verify_channel(ctx):
    await ctx.defer(ephemeral=True)
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel:
        count = 0
        async for message in channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()
                count += 1
        await ctx.followup.send(f"Cleared {count} messages!", ephemeral=True)
    else:
        await ctx.followup.send("Verify channel not found!", ephemeral=True)

@bot.slash_command(name="sendservices", description="Send service message (Admins only)", guild_ids=[GUILD_ID])
@commands.has_permissions(administrator=True)
async def send_services_message(ctx):
    await ctx.defer(ephemeral=True)
    channel = bot.get_channel(SERVICE_CHANNEL_ID)
    if channel:
        unique_suffix = str(random.randint(1000, 9999))  # Generate unique suffix
        embed = discord.Embed(title="🛒 Choose a Service", description="Click the button based on what service you want to buy:", color=discord.Color.gold())
        view = ServiceView(unique_suffix)
        await channel.send(embed=embed, view=view)
        await ctx.followup.send("Service message sent to the service channel!", ephemeral=True)
    else:
        await ctx.followup.send("Service channel not found or bot lacks permission!", ephemeral=True)

# Run bot
try:
    token = os.environ['DISCORD_TOKEN']
    keep_alive()
    bot.run(token)
except Exception as e:
    print(f"ERROR: {e}")
