import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
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

# Store custom role button configurations
custom_roles = {}  # {message_id: {"title": str, "message": str, "channel_id": int, "buttons": {custom_id: role_id}}}

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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    await bot.change_presence(activity=discord.Game(name="KuzzMarket | /help"))
    bot.add_view(VerifyView())
    bot.add_view(MarketplaceView())
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="✅ Server Verification", description="Welcome! Click to verify and join KuzzMarket.", color=discord.Color.green())
        embed.set_footer(text="KuzzMarket - Powered by KuzzBot")
        await channel.send(embed=embed, view=VerifyView())

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

# Custom Role Button Command with Select Menu
class CustomRoleSelect(Select):
    def __init__(self, action):
        options = [discord.SelectOption(label=config["title"], value=str(msg_id), description=config["message"][:50]) for msg_id, config in custom_roles.items()]
        super().__init__(placeholder=f"Select a {action} role message...", min_values=1, max_values=1, options=options)
        self.action = action

    async def callback(self, interaction):
        msg_id = int(self.values[0])
        if self.action == "edit":
            await interaction.response.send_modal(CustomRoleModal("edit", msg_id))
        elif self.action == "remove":
            if msg_id in custom_roles:
                msg = await bot.get_channel(custom_roles[msg_id]["channel_id"]).fetch_message(msg_id)
                await msg.delete()
                del custom_roles[msg_id]
                await interaction.response.send_message("Role message removed!", ephemeral=True)

class CustomRoleModal(Modal, title="Custom Role Setup"):
    title_input = TextInput(label="Title", placeholder="Enter embed title", required=True)
    message_input = TextInput(label="Message", placeholder="Enter message content", required=True, style=discord.TextStyle.paragraph)
    channel_input = TextInput(label="Channel ID", placeholder="Enter channel ID", required=True)
    button_label = TextInput(label="Button Label", placeholder="Enter button label", required=True)
    role_id = TextInput(label="Role ID", placeholder="Enter role ID", required=True)

    def __init__(self, action, msg_id=None):
        super().__init__(title=f"Custom Role - {action}")
        self.action = action
        self.msg_id = msg_id
        if msg_id and msg_id in custom_roles:
            self.title_input.default = custom_roles[msg_id]["title"]
            self.message_input.default = custom_roles[msg_id]["message"]
            self.channel_input.default = str(custom_roles[msg_id]["channel_id"])

    async def on_submit(self, interaction):
        title = self.title_input.value
        message = self.message_input.value
        channel_id = int(self.channel_input.value)
        button_label = self.button_label.value
        role_id = int(self.role_id.value)

        channel = bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("Invalid channel ID!", ephemeral=True)
            return

        custom_id = f"custom_role_{random.randint(1000, 9999)}"
        if self.action == "add":
            view = discord.ui.View()
            button = discord.ui.Button(label=button_label, custom_id=custom_id, style=discord.ButtonStyle.primary)
            view.add_item(button)
            embed = discord.Embed(title=title, description=message, color=discord.Color.blue())
            msg = await channel.send(embed=embed, view=view)
            custom_roles[msg.id] = {"title": title, "message": message, "channel_id": channel_id, "buttons": {custom_id: role_id}}
            await interaction.response.send_message("Role button added!", ephemeral=True)
        elif self.action == "edit":
            if self.msg_id in custom_roles:
                custom_roles[self.msg_id]["title"] = title
                custom_roles[self.msg_id]["message"] = message
                msg = await bot.get_channel(custom_roles[self.msg_id]["channel_id"]).fetch_message(self.msg_id)
                await msg.edit(embed=discord.Embed(title=title, description=message, color=discord.Color.blue()))
                await interaction.response.send_message("Role button edited!", ephemeral=True)
            else:
                await interaction.response.send_message("Message not found!", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def customrole(ctx):
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Add", style=discord.ButtonStyle.green, custom_id="add_role"))
    view.add_item(discord.ui.Button(label="Edit", style=discord.ButtonStyle.blurple, custom_id="edit_role"))
    view.add_item(discord.ui.Button(label="Remove", style=discord.ButtonStyle.red, custom_id="remove_role"))
    await ctx.send("Select an action:", view=view)

    def check(interaction):
        return interaction.user == ctx.author and interaction.message.id == view.message.id

    try:
        interaction = await bot.wait_for("button_click", check=check, timeout=60)
        action = interaction.custom_id.split("_")[0]
        if action in ["edit", "remove"] and custom_roles:
            select = CustomRoleSelect(action)
            view = discord.ui.View()
            view.add_item(select)
            await interaction.response.send_message(f"Select a {action} role message:", view=view, ephemeral=True)
        else:
            await interaction.response.send_modal(CustomRoleModal(action))
    except asyncio.TimeoutError:
        await ctx.send("Timeout! Please try again.", delete_after=5)

@bot.event
async def on_button_click(interaction):
    custom_id = interaction.custom_id
    for msg_id, config in custom_roles.items():
        if custom_id in config["buttons"]:
            role = interaction.guild.get_role(config["buttons"][custom_id])
            if role and role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"Assigned {role.name} role!", ephemeral=True)
            else:
                await interaction.response.send_message("You already have this role or role not found!", ephemeral=True)
            break

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

@bot.slash_command(name="services", description="View marketplace services", guild_ids=[GUILD_ID])
async def services(ctx):
    embed = discord.Embed(title="🛒 KuzzMarket Services", description="Professional growth services!", color=discord.Color.gold())
    embed.add_field(name="Instagram Likes", value="500 Likes - $5", inline=True)
    embed.add_field(name="YouTube Subs", value="100 Subs - $10", inline=True)
    embed.add_field(name="Custom", value="Contact Sellers in #🛒 | Discord", inline=True)
    await ctx.respond(embed=embed, view=MarketplaceView())

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

# Run bot
try:
    token = os.environ['DISCORD_TOKEN']
    keep_alive()
    bot.run(token)
except Exception as e:
    print(f"ERROR: {e}")
