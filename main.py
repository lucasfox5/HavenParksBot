# main.py — Prefix command bot with whitelist + admin bypass + moderation + help

import discord
from discord.ext import commands
import json
import os

# ========= CONFIG =========
TOKEN = os.getenv("TOKEN")
PREFIX = "!"

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)

# REMOVE DEFAULT HELP (fixes help command crash)
bot.remove_command("help")

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

# ========= WHITELIST CHECK =========
async def whitelist_check(ctx):
    # Admins always allowed
    if ctx.author.guild_permissions.administrator:
        return True

    # Whitelisted users allowed
    if check_whitelist(ctx.author.id):
        return True

    # Everyone else blocked
    await ctx.reply("❌ You are not whitelisted to use this bot.")
    return False

# ========= EVENTS =========
@bot.event
async def on_ready():
    print(f"{bot.user} is online with prefix {PREFIX}")

# ========= HELP COMMAND =========
@bot.command()
async def help(ctx):
    if not await whitelist_check(ctx):
        return

    commands_list = """
📜 **Available Commands**

**Whitelist**
!whitelist add @user  
!whitelist remove @user  
!whitelist list  

**Moderation**
!ban @user [reason]  
!kick @user [reason]  
!timeout @user <minutes> [reason]  
!purge <amount>  

**Utility**
!ping  
!help  
"""

    await ctx.reply(commands_list)

# ========= WHITELIST COMMAND =========
@bot.command()
async def whitelist(ctx, action=None, user: discord.User=None):
    if not await whitelist_check(ctx):
        return

    if action == "add":
        if user is None:
            return await ctx.reply("❌ You must mention a user.")
        added = add_whitelist(user.id)
        msg = f"✅ {user} added to whitelist." if added else f"⚠️ {user} already whitelisted."
        return await ctx.reply(msg)

    elif action == "remove":
        if user is None:
            return await ctx.reply("❌ You must mention a user.")
        removed = remove_whitelist(user.id)
        msg = f"🗑️ {user} removed from whitelist." if removed else f"⚠️ {user} not in whitelist."
        return await ctx.reply(msg)

    elif action == "list":
        users = whitelist_data["users"]
        if not users:
            return await ctx.reply("📭 Whitelist is empty.")
        mentions = "\n".join(f"<@{uid}>" for uid in users)
        return await ctx.reply(f"📜 **Whitelisted Users:**\n{mentions}")

    else:
        await ctx.reply("Usage: !whitelist add/remove/list @user")

# ========= PING =========
@bot.command()
async def ping(ctx):
    if not await whitelist_check(ctx):
        return
    await ctx.reply(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# ========= BAN =========
@bot.command()
async def ban(ctx, user: discord.User=None, *, reason="No reason provided"):
    if not await whitelist_check(ctx):
        return
    if not ctx.author.guild_permissions.ban_members:
        return await ctx.reply("❌ You lack **Ban Members** permission.")

    if user is None:
        return await ctx.reply("❌ You must mention a user.")

    member = ctx.guild.get_member(user.id)
    if member is None:
        return await ctx.reply("❌ User not found.")

    await member.ban(reason=reason)
    await ctx.reply(f"🔨 Banned **{user}** | Reason: {reason}")

# ========= KICK =========
@bot.command()
async def kick(ctx, user: discord.User=None, *, reason="No reason provided"):
    if not await whitelist_check(ctx):
        return
    if not ctx.author.guild_permissions.kick_members:
        return await ctx.reply("❌ You lack **Kick Members** permission.")

    if user is None:
        return await ctx.reply("❌ You must mention a user.")

    member = ctx.guild.get_member(user.id)
    if member is None:
        return await ctx.reply("❌ User not found.")

    await member.kick(reason=reason)
    await ctx.reply(f"👢 Kicked **{user}** | Reason: {reason}")

# ========= TIMEOUT =========
@bot.command()
async def timeout(ctx, user: discord.User=None, minutes: int=None, *, reason="No reason provided"):
    if not await whitelist_check(ctx):
        return
    if not ctx.author.guild_permissions.moderate_members:
        return await ctx.reply("❌ You lack **Timeout Members** permission.")

    if user is None or minutes is None:
        return await ctx.reply("Usage: !timeout @user <minutes> [reason]")

    member = ctx.guild.get_member(user.id)
    if member is None:
        return await ctx.reply("❌ User not found.")

    duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
    await member.edit(timeout=duration, reason=reason)
    await ctx.reply(f"⏱️ Timed out **{user}** for **{minutes}** minutes | Reason: {reason}")

# ========= PURGE =========
@bot.command()
async def purge(ctx, amount: int=None):
    if not await whitelist_check(ctx):
        return
    if not ctx.author.guild_permissions.manage_messages:
        return await ctx.reply("❌ You lack **Manage Messages** permission.")

    if amount is None or amount < 1 or amount > 100:
        return await ctx.reply("❌ Amount must be between 1 and 100.")

    deleted = await ctx.channel.purge(limit=amount)
    await ctx.reply(f"🧹 Deleted **{len(deleted)}** messages.", delete_after=3)

# ========= RUN =========
if __name__ == "__main__":
    if not TOKEN:
        print("Missing TOKEN environment variable.")
    else:
        bot.run(TOKEN)
