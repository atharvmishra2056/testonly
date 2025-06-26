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

MOD_ROLE_NAME = "Moderator"
MEMBER_ROLE_NAME = "KuzzMember"
ACTIVE_MEMBER_ROLE_NAME = "Active Member"

BAD_WORDS = ["fuck", "nigga"]  # Storing in lowercase for easier checking
CAPTCHA_TIMEOUT = 180  # Seconds for CAPTCHA Modal
BUTTON_COOLDOWN = 5    # Seconds for button cooldown

# This dictionary makes the service roles much easier to manage.
# Format: "internal_name": ["Button Label", "Button Emoji", Role_ID]
SERVICE_ROLES = {
    "facebook":  ["Facebook",  ":Facebook:", 1387742165681180754],
    "discord":   ["Discord",   "🇩", 1387742348175216720],
    "instagram": ["Instagram", "🇮", 1387735712874500096],
    "twitter":   ["Twitter",   "🇹", 1387756089864486942],
    "tiktok":    ["TikTok",    "⏰", 1387756237566906488],
    "twitch":    ["Twitch",    "🎮", 1387756062169366718],
    "snapchat":  ["Snapchat",  "👻", 1387755991243952229],
    "youtube":   ["YouTube",   "🎥", 1387742474533077084],
    "spotify":   ["Spotify",   "🎵", 1387756124165505065],
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
xp_data = {} # Stores {'user_id': {'xp': 10, 'last_message_time': ...}}


# --- MODALS (Modern way to get user text input) ---

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
            await interaction.followup.send("❌ Incorrect CAPTCHA. Please click the verify button and try again.", ephemeral=True)
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


# --- VIEWS (For Buttons and Select Menus) ---

class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify Now", style=discord.ButtonStyle.green, custom_id="verify_kuzz_v5")
    async def verify_button(self, button: Button, interaction: discord.Interaction):
        member = interaction.user
        
        # Cooldown check
        last_click = button_cooldowns.get(member.id, 0)
        if time.time() < last_click + BUTTON_COOLDOWN:
            await interaction.response.send_message("Please wait a few seconds before trying again.", ephemeral=True, delete_after=5)
            return
        button_cooldowns[member.id] = time.time()

        # Generate and store CAPTCHA
        captcha_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        captcha_sessions[member.id] = captcha_code
        
        # Send the modal to the user
        modal = CaptchaModal(user_id=member.id)
        await interaction.response.send_modal(modal)
        
        # Send the captcha image in a followup ephemeral message
        # NOTE: Using a simple embed here. For an image, you would use a library like Pillow.
        embed = discord.Embed(
            title="Your CAPTCHA Code Is:",
            description=f"**{captcha_code}**",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Enter this code in the pop-up modal.")
        await interaction.followup.send(embed=embed, ephemeral=True)


class ServiceView(View):
    def __init__(self):
        super().__init__(timeout=None)
        # FIX: Loop through the SERVICE_ROLES dictionary to create buttons dynamically.
        # This prevents duplicate buttons and makes the code much cleaner (DRY principle).
        for service_name, details in SERVICE_ROLES.items():
            label, emoji, role_id = details
            button = Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"service_role_{service_name}" # Unique ID for each button
            )
            # Assign the generic callback to each button
            button.callback = self.service_button_callback
            self.add_item(button)

    async def service_button_callback(self, interaction: discord.Interaction):
        """A single callback to handle all service role buttons."""
        await interaction.response.defer(ephemeral=True)
        
        # Extract the service name from the custom_id (e.g., 'facebook')
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

        # Toggle role
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
    # Register persistent views on startup
    bot.add_view(VerifyView())
    bot.add_view(ServiceView())
    print("Persistent views registered.")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        welcome_message = f"🎉🌟 **Welcome to KuzzMarket, {member.mention}!** 🌟🎉\nGet started by verifying yourself here: <#{VERIFY_CHANNEL_ID}>! 🚀😊"
        await channel.send(welcome_message)

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
        
    # --- Auto-Moderation ---
    content = message.content.lower()
    if any(word in content for word in BAD_WORDS):
        try:
            await message.delete()
            await message.author.send(f"Your message in **{message.guild.name}** was deleted for using inappropriate language. Please adhere to the server rules.")
        except discord.Forbidden:
            print(f"Could not delete message or DM user {message.author.name} due to permissions.")
        except Exception as e:
            print(f"Error in auto-moderation: {e}")
        return # Stop processing the message further

    # --- XP System (with cooldown) ---
    user_id_str = str(message.author.id)
    current_time = time.time()
    
    # Initialize user if not present
    if user_id_str not in xp_data:
        xp_data[user_id_str] = {'xp': 0, 'last_message_time': 0}
        
    # Add XP only if cooldown has passed (e.g., 60 seconds)
    if current_time - xp_data[user_id_str]['last_message_time'] > 60:
        xp_data[user_id_str]['xp'] += 5
        xp_data[user_id_str]['last_message_time'] = current_time
        
        # Check for level up
        if xp_data[user_id_str]['xp'] >= 100:
            role = discord.utils.get(message.guild.roles, name=ACTIVE_MEMBER_ROLE_NAME)
            if role and role not in message.author.roles:
                try:
                    await message.author.add_roles(role)
                    await message.channel.send(f"🎉 Congratulations {message.author.mention}, you've earned the **{ACTIVE_MEMBER_ROLE_NAME}** role for being active!")
                    xp_data[user_id_str]['xp'] = 0 # Reset XP
                except discord.Forbidden:
                    print(f"Could not assign Active Member role to {message.author.name}")

    # Process prefix commands
    await bot.process_commands(message)


# --- CORE LOGIC FUNCTIONS (to avoid repeating code) ---

async def send_verify_logic(ctx_or_interaction):
    """Core logic for sending the verification message."""
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if not channel:
        response_message = "❌ Verify channel not found!"
        if isinstance(ctx_or_interaction, discord.ApplicationContext):
            await ctx_or_interaction.followup.send(response_message, ephemeral=True)
        else:
            await ctx_or_interaction.send(response_message)
        return

    # Clean up old bot messages
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
    """Core logic for sending the services message."""
    channel = bot.get_channel(SERVICE_CHANNEL_ID)
    if not channel:
        response_message = "❌ Service channel not found or bot lacks permissions!"
        if isinstance(ctx_or_interaction, discord.ApplicationContext):
            await ctx_or_interaction.followup.send(response_message, ephemeral=True)
        else:
            await ctx_or_interaction.send(response_message)
        return

    # Clean up old bot messages
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

# Keeping one prefix command as an example
@bot.command(name="ping")
async def ping(ctx):
    """Checks the bot's latency."""
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.slash_command(name="ping", description="Checks the bot's latency.", guild_ids=[GUILD_ID])
async def ping_slash(ctx: discord.ApplicationContext):
    await ctx.respond(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms", ephemeral=True)

# --- Admin Commands ---
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
