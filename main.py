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

# Custom Role Button Command with Wizard Approach
class CustomRoleView(View):
    def __init__(self, ctx, step=1, data=None):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.step = step
        self.data = data or {}
        self.update_items()

    def update_items(self):
        self.clear_items()
        prompt = "Starting custom role setup. "
        if self.step == 1:
            prompt += "Enter title and click 'Next'."
            self.add_item(Button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_title"))
        elif self.step == 2:
            prompt += "Enter message and click 'Next'."
            self.add_item(Button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_message"))
        elif self.step == 3:
            prompt += "Enter channel ID and click 'Next'."
            self.add_item(Button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_channel"))
        elif self.step == 4:
            prompt += "Enter button label and click 'Next'."
            self.add_item(Button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_button_label"))
        elif self.step == 5:
            prompt += "Enter role ID and click 'Next'."
            self.add_item(Button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_role_id"))
        elif self.step == 6:
            prompt += "Click 'Confirm' to finish or 'Cancel' to abort."
            self.add_item(Button(label="Confirm", style=discord.ButtonStyle.green, custom_id="confirm"))
            self.add_item(Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel"))

    async def on_timeout(self):
        await self.ctx.send("Timeout! Please start again with `wolf customrole`.", delete_after=5)

    async def interaction_check(self, interaction):
        return interaction.user == self.ctx.author

    async def callback(self, interaction):
        await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_title")
    async def next_title(self, button, interaction):
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            self.data["title"] = msg.content
            await msg.delete()
            self.step = 2
            self.update_items()
            await interaction.message.edit(content=f"Step 2: Enter message and click 'Next'.", view=self)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timeout! Please start again.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_message")
    async def next_message(self, button, interaction):
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            self.data["message"] = msg.content
            await msg.delete()
            self.step = 3
            self.update_items()
            await interaction.message.edit(content=f"Step 3: Enter channel ID and click 'Next'.", view=self)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timeout! Please start again.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_channel")
    async def next_channel(self, button, interaction):
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            self.data["channel_id"] = int(msg.content)
            await msg.delete()
            self.step = 4
            self.update_items()
            await interaction.message.edit(content=f"Step 4: Enter button label and click 'Next'.", view=self)
        except (asyncio.TimeoutError, ValueError):
            await interaction.followup.send("Timeout or invalid input! Please start again.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_button_label")
    async def next_button_label(self, button, interaction):
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            self.data["button_label"] = msg.content
            await msg.delete()
            self.step = 5
            self.update_items()
            await interaction.message.edit(content=f"Step 5: Enter role ID and click 'Next'.", view=self)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timeout! Please start again.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_role_id")
    async def next_role_id(self, button, interaction):
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            self.data["role_id"] = int(msg.content)
            await msg.delete()
            self.step = 6
            self.update_items()
            await interaction.message.edit(content=f"Step 6: Click 'Confirm' to finish or 'Cancel' to abort.", view=self)
        except (asyncio.TimeoutError, ValueError):
            await interaction.followup.send("Timeout or invalid input! Please start again.", ephemeral=True)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="confirm")
    async def confirm(self, button, interaction):
        channel = bot.get_channel(self.data["channel_id"])
        if not channel:
            await interaction.response.send_message("Invalid channel ID!", ephemeral=True)
            return
        custom_id = f"custom_role_{random.randint(1000, 9999)}"
        view = discord.ui.View()
        button = discord.ui.Button(label=self.data["button_label"], custom_id=custom_id, style=discord.ButtonStyle.primary)
        view.add_item(button)
        embed = discord.Embed(title=self.data["title"], description=self.data["message"], color=discord.Color.blue())
        msg = await channel.send(embed=embed, view=view)
        custom_roles[msg.id] = {"title": self.data["title"], "message": self.data["message"], "channel_id": self.data["channel_id"], "buttons": {custom_id: self.data["role_id"]}}
        await interaction.response.send_message("Role button created!", ephemeral=True)
        await interaction.message.edit(content="Setup complete!", view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel")
    async def cancel(self, button, interaction):
        await interaction.response.send_message("Cancelled!", ephemeral=True)
        await interaction.message.edit(content="Setup cancelled!", view=None)
        self.stop()

class CustomRoleSelect(Select):
    def __init__(self, action):
        options = [discord.SelectOption(label=config["title"], value=str(msg_id), description=config["message"][:50]) for msg_id, config in custom_roles.items()]
        super().__init__(placeholder=f"Select a {action} role message...", min_values=1, max_values=1, options=options)
        self.action = action

    async def callback(self, interaction):
        msg_id = int(self.values[0])
        if self.action == "edit":
            await interaction.response.send_message("Edit not fully supported yet—use add to recreate.", ephemeral=True)
        elif self.action == "remove":
            if msg_id in custom_roles:
                msg = await bot.get_channel(custom_roles[msg_id]["channel_id"]).fetch_message(msg_id)
                await msg.delete()
                del custom_roles[msg_id]
                await interaction.response.send_message("Role message removed!", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def customrole(ctx):
    view = CustomRoleView(ctx)
    await ctx.send("Starting custom role setup. Enter title and click 'Next'.", view=view)

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
