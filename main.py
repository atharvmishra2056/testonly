import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, InputText
import os
from flask import Flask
from threading import Thread
import random
import string
import asyncio
import time

# --- CONFIGURATION ---
# It's good practice to keep all your IDs and names in one place.
GUILD_ID = 1377883327771574372          # Your Server ID
VERIFY_CHANNEL_ID = 1377883328526680065  # Verify Channel ID
LOG_CHANNEL_ID = 1377883329755611280    # Logs Channel ID
WELCOME_CHANNEL_ID = 1387419489586380972 # Welcome Channel ID
SERVICE_CHANNEL_ID = 1387386391800975390 # Service Channel ID
GENERAL_CHANNEL_ID = 1377883329503821841 # General Channel ID

MOD_ROLE_NAME = "Moderator"
MEMBER_ROLE_NAME = "KuzzMember"
ACTIVE_MEMBER_ROLE_NAME = "Active Member"

BAD_WORDS = ["fuck", "nigga"]  # Storing in lowercase for easier checking
CAPTCHA_TIMEOUT = 180  # Seconds for CAPTCHA
BUTTON_COOLDOWN = 5    # Seconds for button cooldown

# This dictionary makes the service roles much easier to manage.
# Format: "internal_name": ["Button Label", "Button Emoji", Role_ID]
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

# --- KEEP ALIVE (FOR HOSTING SERVICES LIKE RENDER) ---
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
bot = commands.Bot(command_prefix=["/", "wolf "], intents=intents)

# --- IN-MEMORY DATA STORAGE ---
# WARNING: This data will be lost on bot restart. For a production bot,
# consider using a database (like SQLite, PostgreSQL) for persistence.
captcha_sessions = {}
button_cooldowns = {}
xp_data = {}  # Stores {'user_id': {'xp': 10, 'last_message_time': ...}}

# Auto role feature flag
AUTO_ROLE_ENABLED = False

# --- MODALS & VERIFICATION FLOW VIEWS ---

class CaptchaModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="🔒 CAPTCHA Verification")
        self.user_id = user_id
        self.add_item(InputText(label="Enter the CAPTCHA Code", placeholder="Case-sensitive code...", style=discord.InputTextStyle.short, required=True))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user_input = self.children[0].value
        correct_code = captcha_sessions.get(self.user_id)
        
        # Cleanup session data regardless of outcome
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
            
            # Hide verify channel from the user
            verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
            if verify_channel:
                await verify_channel.set_permissions(member, view_channel=False)
            
            welcome_embed = discord.Embed(
                title="🎉 Welcome to KuzzMarket!",
                description=f"Congratulations, {member.mention}! You are verified. Head over to <#{GENERAL_CHANNEL_ID}>.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=welcome_embed, ephemeral=True)
            
            # Send log message
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
            print(f"Error during verification for {member.id}: {e}")

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

# --- BOT EVENTS ---

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    await bot.change_presence(activity=discord.Game(name="KuzzMarket | /help"))
    bot.add_view(VerifyView())
    bot.add_view(ServiceView())
    print("Persistent views registered.")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        welcome_message = f"🎉🌟 **Welcome to KuzzMarket, {member.mention}!** 🌟🎉\nGet started by verifying yourself here: <#{VERIFY_CHANNEL_ID}>! 🚀😊"
        await channel.send(welcome_message)

    if AUTO_ROLE_ENABLED:
        guild = bot.get_guild(GUILD_ID)
        role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
        if role and role not in member.roles:
            try:
                await member.add_roles(role)
                welcome_channel = bot.get_channel(GENERAL_CHANNEL_ID)
                if welcome_channel:
                    await welcome_channel.send(f"🎉 Welcome {member.mention} to KuzzMarket! You have been automatically assigned the {role.name} role!")
            except discord.Forbidden:
                print(f"Could not assign {MEMBER_ROLE_NAME} role to {member.name} due to permissions.")

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
        
    content = message.content.lower()
    if any(word in content for word in BAD_WORDS):
        try:
            await message.delete()
            await message.author.send(f"Your message in **{message.guild.name}** was deleted for using inappropriate language. Please adhere to the server rules.")
        except discord.Forbidden:
            print(f"Could not delete message or DM user {message.author.name} due to permissions.")
        except Exception as e:
            print(f"Error in auto-moderation: {e}")
        return

    user_id_str = str(message.author.id)
    current_time = time.time()
    
    if user_id_str not in xp_data:
        xp_data[user_id_str] = {'xp': 0, 'last_message_time': 0}
        
    if current_time - xp_data[user_id_str]['last_message_time'] > 60:
        xp_data[user_id_str]['xp'] += 5
        xp_data[user_id_str]['last_message_time'] = current_time
        
        if xp_data[user_id_str]['xp'] >= 100:
            role = discord.utils.get(message.guild.roles, name=ACTIVE_MEMBER_ROLE_NAME)
            if role and role not in message.author.roles:
                try:
                    await message.author.add_roles(role)
                    await message.channel.send(f"🎉 Congratulations {message.author.mention}, you've earned the **{ACTIVE_MEMBER_ROLE_NAME}** role for being active!")
                    xp_data[user_id_str]['xp'] = 0
                except discord.Forbidden:
                    print(f"Could not assign Active Member role to {message.author.name}")

    await bot.process_commands(message)

# --- CORE LOGIC FUNCTIONS ---

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

# --- COMMANDS (Slash and Prefix) ---

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

# New commands for auto role feature
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
