import os
import discord
from discord.ext import commands
import json

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=",", intents=intents)

DATA_FILE = "levels.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def xp_needed(level):
    return 100 + (-9.629 * level) + (9.629 * (level ** 2))

def get_user(data, guild_id, user_id):
    guild_id = str(guild_id)
    user_id = str(user_id)

    if guild_id not in data:
        data[guild_id] = {}

    if user_id not in data[guild_id]:
        data[guild_id][user_id] = {
            "level": 1,
            "xp": 0,
            "messages": 0
        }

    return data[guild_id][user_id]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    data = load_data()
    user = get_user(data, message.guild.id, message.author.id)

    user["messages"] += 1
    user["xp"] += 12.5

    while user["level"] < 100 and user["xp"] >= xp_needed(user["level"]):
        user["xp"] -= xp_needed(user["level"])
        user["level"] += 1

        await message.channel.send(
            f"🎉 {message.author.mention} leveled up to **Level {user['level']}**!"
        )

    save_data(data)

    await bot.process_commands(message)

def progress_bar(current, needed, length=20):
    percent = current / needed if needed > 0 else 0
    filled = int(length * percent)
    return "█" * filled + "░" * (length - filled)


@bot.command(name="level")
async def level(ctx, member: discord.Member = None):

    if member is None:
        member = ctx.author

    data = load_data()
    user = get_user(data, ctx.guild.id, member.id)

    level = user["level"]
    xp = user["xp"]
    messages = user["messages"]

    needed = xp_needed(level)
    remaining = max(0, needed - xp)

    bar = progress_bar(xp, needed)

    embed = discord.Embed(
        title=f"{member.display_name}'s Level",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name="⭐ Level",
        value=f"**{level}**",
        inline=True
    )

    embed.add_field(
        name="💬 Messages",
        value=f"**{messages:,}**",
        inline=True
    )

    embed.add_field(
        name="📈 XP",
        value=f"**{xp:.1f} / {needed:.1f} XP**",
        inline=False
    )

    embed.add_field(
        name="📊 Progress",
        value=f"`{bar}`\n{(xp/needed)*100:.1f}% Complete",
        inline=False
    )

    embed.add_field(
        name="⏳ XP Remaining",
        value=f"**{remaining:.1f} XP**",
        inline=False
    )

    embed.set_footer(
        text="Level System • Max Level 100"
    )

    await ctx.send(embed=embed)
    
@bot.command(name="rank")
async def rank(ctx):
    await level(ctx)

@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx):

    data = load_data()

    guild = data.get(str(ctx.guild.id), {})

    leaderboard = []

    for user_id, stats in guild.items():
        member = ctx.guild.get_member(int(user_id))

        if member is not None:
            leaderboard.append(
                (
                    member.display_name,
                    stats["level"],
                    stats["messages"]
                )
            )

    leaderboard.sort(
        key=lambda x: (x[1], x[2]),
        reverse=True
    )

    embed = discord.Embed(
        title="🏆 Server Leaderboard",
        color=discord.Color.gold()
    )

    if len(leaderboard) == 0:
        embed.description = "No users have earned XP yet."

    else:
        text = ""

        for i, (name, level, messages) in enumerate(leaderboard[:10], start=1):
            text += f"**{i}.** {name}\n⭐ Level **{level}** • 💬 {messages:,} messages\n\n"

        embed.description = text

    await ctx.send(embed=embed)


print("Starting bot...")
bot.run(TOKEN)
