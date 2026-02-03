# main.py — Prefix command bot with embeds + whitelist + admin bypass + moderation

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
bot.remove_command("help")  # Remove default help

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

# ========= WHITELIST CHECK =========
async def whitelist_check(ctx):
    # Admins always allowed
    if ctx.author.guild_permissions.administrator:
        return True

    # Whitelisted users allowed
    if check_whitelist(ctx.author.id):
        return True

    # Block everyone else
    embed = discord.Embed(
        title="Access Denied",
        description="❌ You are **not whitelisted** to use this bot.",
        color=discord.Color.red()
    )
    await ctx.reply(embed=embed)
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

    embed = discord.Embed(
        title="📜 Command List",
        description="Here are all available commands:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Whitelist",
        value="`!whitelist add @user`\n`!whitelist remove @user`\n`!whitelist list`",
        inline=False
    )

    embed.add_field(
        name="Moderation",
        value="`!ban @user [reason]`\n`!kick @user [reason]`\n`!timeout @user <minutes> [reason]`\n`!purge <amount>`",
        inline=False
    )

    embed.add_field(
        name="Utility",
        value="`!ping`\n`!help`",
        inline=False
    )

    await ctx.reply(embed=embed)

# ========= WHITELIST COMMAND =========
@bot.command()
async def whitelist(ctx, action=None, user: discord.User=None):
    if not await whitelist_check(ctx):
        return

    if action == "add":
        if user is None:
            return await ctx.reply(embed=discord.Embed(
                title="Error",
                description="❌ You must mention a user.",
                color=discord.Color.red()
            ))

        added = add_whitelist(user.id)
        msg = f"✅ {user.mention} added to whitelist." if added else f"⚠️ {user.mention} is already whitelisted."

        embed = discord.Embed(title="Whitelist Update", description=msg, color=discord.Color.green())
        return await ctx.reply(embed=embed)

    elif action == "remove":
        if user is None:
            return await ctx.reply(embed=discord.Embed(
                title="Error",
                description="❌ You must mention a user.",
                color=discord.Color.red()
            ))

        removed = remove_whitelist(user.id)
        msg = f"🗑️ {user.mention} removed from whitelist." if removed else f"⚠️ {user.mention} is not in whitelist."

        embed = discord.Embed(title="Whitelist Update", description=msg, color=discord.Color.orange())
        return await ctx.reply(embed=embed)

    elif action == "list":
        users = whitelist_data["users"]
        if not users:
            embed = discord.Embed(
                title="Whitelist",
                description="📭 Whitelist is empty.",
                color=discord.Color.blue()
            )
            return await ctx.reply(embed=embed)

        mentions = "\n".join(f"<@{uid}>" for uid in users)
        embed = discord.Embed(
            title="Whitelisted Users",
            description=mentions,
            color=discord.Color.blue()
        )
        return await ctx.reply(embed=embed)

    else:
        embed = discord.Embed(
            title="Whitelist Command Usage",
            description="`!whitelist add/remove/list @user`",
            color=discord.Color.yellow()
        )
        await ctx.reply(embed=embed)

# ========= PING =========
@bot.command()
async def ping(ctx):
    if not await whitelist_check(ctx):
        return

    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: **{round(bot.latency * 1000)}ms**",
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed)

# ========= BAN =========
@bot.command()
async def ban(ctx, user: discord.User=None, *, reason="No reason provided"):
    if not await whitelist_check(ctx):
        return

    if not ctx.author.guild_permissions.ban_members:
        return await ctx.reply(embed=discord.Embed(
            title="Permission Denied",
            description="❌ You lack **Ban Members** permission.",
            color=discord.Color.red()
        ))

    if user is None:
        return await ctx.reply(embed=discord.Embed(
            title="Error",
            description="❌ You must mention a user.",
            color=discord.Color.red()
        ))

    member = ctx.guild.get_member(user.id)
    if member is None:
        return await ctx.reply(embed=discord.Embed(
            title="Error",
            description="❌ User not found.",
            color=discord.Color.red()
        ))

    await member.ban(reason=reason)

    embed = discord.Embed(
        title="User Banned",
        description=f"🔨 **{user}** has been banned.\n**Reason:** {reason}",
        color=discord.Color.red()
    )
    await ctx.reply(embed=embed)

# ========= KICK =========
@bot.command()
async def kick(ctx, user: discord.User=None, *, reason="No reason provided"):
    if not await whitelist_check(ctx):
        return

    if not ctx.author.guild_permissions.kick_members:
        return await ctx.reply(embed=discord.Embed(
            title="Permission Denied",
            description="❌ You lack **Kick Members** permission.",
            color=discord.Color.red()
        ))

    if user is None:
        return await ctx.reply(embed=discord.Embed(
            title="Error",
            description="❌ You must mention a user.",
            color=discord.Color.red()
        ))

    member = ctx.guild.get_member(user.id)
    if member is None:
        return await ctx.reply(embed=discord.Embed(
            title="Error",
            description="❌ User not found.",
            color=discord.Color.red()
        ))

    await member.kick(reason=reason)

    embed = discord.Embed(
        title="User Kicked",
        description=f"👢 **{user}** has been kicked.\n**Reason:** {reason}",
        color=discord.Color.orange()
    )
    await ctx.reply(embed=embed)

# ========= TIMEOUT =========
@bot.command()
async def timeout(ctx, user: discord.User=None, minutes: int=None, *, reason="No reason provided"):
    if not await whitelist_check(ctx):
        return

    if not ctx.author.guild_permissions.moderate_members:
        return await ctx.reply(embed=discord.Embed(
            title="Permission Denied",
            description="❌ You lack **Timeout Members** permission.",
            color=discord.Color.red()
        ))

    if user is None or minutes is None:
        return await ctx.reply(embed=discord.Embed(
            title="Usage Error",
            description="Usage: `!timeout @user <minutes> [reason]`",
            color=discord.Color.yellow()
        ))

    member = ctx.guild.get_member(user.id)
    if member is None:
        return await ctx.reply(embed=discord.Embed(
            title="Error",
            description="❌ User not found.",
            color=discord.Color.red()
        ))

    duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
    await member.edit(timeout=duration, reason=reason)

    embed = discord.Embed(
        title="User Timed Out",
        description=f"⏱️ **{user}** timed out for **{minutes} minutes**.\n**Reason:** {reason}",
        color=discord.Color.orange()
    )
    await ctx.reply(embed=embed)

# ========= PURGE =========
@bot.command()
async def purge(ctx, amount: int=None):
    if not await whitelist_check(ctx):
        return

    if not ctx.author.guild_permissions.manage_messages:
        return await ctx.reply(embed=discord.Embed(
            title="Permission Denied",
            description="❌ You lack **Manage Messages** permission.",
            color=discord.Color.red()
        ))

    if amount is None or amount < 1 or amount > 100:
        return await ctx.reply(embed=discord.Embed(
            title="Error",
            description="❌ Amount must be between **1 and 100**.",
            color=discord.Color.red()
        ))

    deleted = await ctx.channel.purge(limit=amount)

    embed = discord.Embed(
        title="Messages Purged",
        description=f"🧹 Deleted **{len(deleted)}** messages.",
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed, delete_after=3)

# ========= RUN =========
if __name__ == "__main__":
    if not TOKEN:
        print("Missing TOKEN environment variable.")
    else:
        bot.run(TOKEN)
