# main.py
# One-file Discord bot with whitelist + moderation (Python / discord.py)

import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# ========= CONFIG =========
TOKEN = os.getenv("TOKEN")        # Put your bot token in environment or .env
GUILD_ID = int(os.getenv("GUILD_ID", "0"))  # Dev server ID for command sync (optional but recommended)

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

# ========= WHITELIST STORAGE =========
WHITELIST_FILE = "whitelist.json"

if not os.path.exists(WHITELIST_FILE):
    with open(WHITELIST_FILE, "w") as f:
        json.dump({"users": []}, f, indent=4)

with open(WHITELIST_FILE, "r") as f:
    whitelist_data = json.load(f)

def save_whitelist():
    with open(WHITELIST_FILE, "w") as f:
        json.dump(whitelist_data, f, indent=4)

def check_whitelist(user_id: int) -> bool:
    return str(user_id) in whitelist_data["users"]

def add_whitelist(user_id: int) -> bool:
    uid = str(user_id)
    if uid not in whitelist_data["users"]:
        whitelist_data["users"].append(uid)
        save_whitelist()
        return True
    return False

def remove_whitelist(user_id: int) -> bool:
    uid = str(user_id)
    if uid in whitelist_data["users"]:
        whitelist_data["users"].remove(uid)
        save_whitelist()
        return True
    return False

# ========= WHITELIST CHECK DECORATOR =========
def whitelisted_only():
    async def predicate(interaction: discord.Interaction):
        if not check_whitelist(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are not whitelisted to use this bot.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# ========= EVENTS =========
@bot.event
async def on_ready():
    print(f"{bot.user} is online.")

    # Sync commands to a specific guild (fast updates)
    if GUILD_ID != 0:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"Commands synced to guild {GUILD_ID}.")
    else:
        # Global sync (slower to update)
        await bot.tree.sync()
        print("Commands synced globally.")

# ========= SLASH COMMANDS =========

# /whitelist
@bot.tree.command(name="whitelist", description="Manage bot whitelist")
@app_commands.describe(
    action="add/remove/list",
    user="User to add/remove (not needed for list)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="add", value="add"),
    app_commands.Choice(name="remove", value="remove"),
    app_commands.Choice(name="list", value="list")
])
async def whitelist_cmd(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    user: discord.User | None = None
):
    # Only whitelisted users can manage whitelist
    if not check_whitelist(interaction.user.id):
        await interaction.response.send_message(
            "❌ You are not allowed to manage the whitelist.",
            ephemeral=True
        )
        return

    if action.value in ("add", "remove") and user is None:
        await interaction.response.send_message(
            "❌ You must specify a user for add/remove.",
            ephemeral=True
        )
        return

    if action.value == "add":
        added = add_whitelist(user.id)
        msg = (
            f"✅ **{user}** has been added to the whitelist."
            if added else
            f"⚠️ **{user}** is already whitelisted."
        )
        await interaction.response.send_message(msg)

    elif action.value == "remove":
        removed = remove_whitelist(user.id)
        msg = (
            f"🗑️ **{user}** has been removed from the whitelist."
            if removed else
            f"⚠️ **{user}** is not whitelisted."
        )
        await interaction.response.send_message(msg)

    elif action.value == "list":
        users = whitelist_data["users"]
        if not users:
            await interaction.response.send_message("📭 Whitelist is empty.")
            return
        mention_list = "\n".join(f"<@{uid}>" for uid in users)
        await interaction.response.send_message(f"📜 **Whitelisted Users:**\n{mention_list}")

# /ping
@bot.tree.command(name="ping", description="Check bot latency")
@whitelisted_only()
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms")

# /ban
@bot.tree.command(name="ban", description="Ban a member")
@whitelisted_only()
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(
    interaction: discord.Interaction,
    user: discord.User,
    reason: str | None = None
):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message(
            "❌ You lack **Ban Members** permission.",
            ephemeral=True
        )
        return

    member = interaction.guild.get_member(user.id)
    if member is None:
        await interaction.response.send_message("❌ Could not find that member.")
        return

    try:
        await member.ban(reason=reason or "No reason provided")
        await interaction.response.send_message(
            f"🔨 Banned **{user}** | Reason: {reason or 'No reason provided'}"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to ban: `{e}`", ephemeral=True)

# /kick
@bot.tree.command(name="kick", description="Kick a member")
@whitelisted_only()
@app_commands.describe(user="User to kick", reason="Reason for kick")
async def kick(
    interaction: discord.Interaction,
    user: discord.User,
    reason: str | None = None
):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message(
            "❌ You lack **Kick Members** permission.",
            ephemeral=True
        )
        return

    member = interaction.guild.get_member(user.id)
    if member is None:
        await interaction.response.send_message("❌ Could not find that member.")
        return

    try:
        await member.kick(reason=reason or "No reason provided")
        await interaction.response.send_message(
            f"👢 Kicked **{user}** | Reason: {reason or 'No reason provided'}"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to kick: `{e}`", ephemeral=True)

# /timeout
@bot.tree.command(name="timeout", description="Timeout a member (in minutes)")
@whitelisted_only()
@app_commands.describe(
    user="User to timeout",
    minutes="Duration in minutes",
    reason="Reason for timeout"
)
async def timeout(
    interaction: discord.Interaction,
    user: discord.User,
    minutes: int,
    reason: str | None = None
):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ You lack **Timeout Members** permission.",
            ephemeral=True
        )
        return

    member = interaction.guild.get_member(user.id)
    if member is None:
        await interaction.response.send_message("❌ Could not find that member.")
        return

    duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)

    try:
        await member.edit(timeout=duration, reason=reason or "No reason provided")
        await interaction.response.send_message(
            f"⏱️ Timed out **{user}** for **{minutes}** minutes | Reason: {reason or 'No reason provided'}"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to timeout: `{e}`", ephemeral=True)

# /purge
@bot.tree.command(name="purge", description="Delete a number of messages")
@whitelisted_only()
@app_commands.describe(amount="Number of messages to delete (1-100)")
async def purge(
    interaction: discord.Interaction,
    amount: int
):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You lack **Manage Messages** permission.",
            ephemeral=True
        )
        return

    if amount < 1 or amount > 100:
        await interaction.response.send_message(
            "❌ Amount must be between 1 and 100.",
            ephemeral=True
        )
        return

    channel = interaction.channel
    try:
        deleted = await channel.purge(limit=amount)
        await interaction.response.send_message(
            f"🧹 Deleted **{len(deleted)}** messages.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to delete messages: `{e}`", ephemeral=True)

# ========= RUN =========
if __name__ == "__main__":
    if not TOKEN:
        print("Set TOKEN (and optionally GUILD_ID) as environment variables.")
    else:
        bot.run(TOKEN)
