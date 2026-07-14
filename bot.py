import os
import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont

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


def xp_needed_for_level(level):
    if level <= 0:
        return 0

    if level == 1:
        return 100

    if level == 100:
        return 10000

    if level <= 70:
        return int(100 + (0.495 * (level ** 2)))

    return int(
        100
        + (0.495 * (level ** 2))
        + (4.9 * ((level - 70) ** 1.8))
    )


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

    if message.guild is None:
        return

    data = load_data()

    user = get_user(
        data,
        message.guild.id,
        message.author.id
    )

    user["messages"] += 1
    user["xp"] += 1

    while user["xp"] >= xp_needed_for_level(user["level"]):
        user["xp"] -= xp_needed_for_level(user["level"])
        user["level"] += 1

        await message.channel.send(
            f"🎉 {message.author.mention} leveled up to **Level {user['level']}**!"
        )

    save_data(data)

    await bot.process_commands(message)


def progress_bar(current, needed, length=28):
    percent = current / needed if needed > 0 else 0
    filled = int(length * percent)

    return "▰" * filled + "▱" * (length - filled)
    
@bot.command(name="level")
async def level(ctx, member: discord.Member = None):

    if member is None:
        member = ctx.author

    data = load_data()
    user = get_user(data, ctx.guild.id, member.id)

    current_level = user["level"]
    xp = user["xp"]
    messages = user["messages"]

    needed = xp_needed_for_level(current_level)

    percent = min(xp / needed, 1)

    # Download avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(str(member.display_avatar.url)) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((180, 180))


    # Card
    img = Image.new(
        "RGBA",
        (900, 350),
        (20, 20, 25, 255)
    )

    draw = ImageDraw.Draw(img)


    # Avatar
    img.paste(
        avatar,
        (50, 80),
        avatar
    )


    # Fonts
    try:
        title_font = ImageFont.truetype(
            "arial.ttf",
            45
        )

        font = ImageFont.truetype(
            "arial.ttf",
            30
        )

    except:
        title_font = None
        font = None


    # Username
    draw.text(
        (270, 55),
        member.name,
        font=title_font,
        fill="white"
    )


    # Underline
    draw.line(
        (270, 115, 800, 115),
        fill="white",
        width=3
    )


    # Stats
    draw.text(
        (270, 140),
        f"⭐ Level {current_level}",
        font=font,
        fill="white"
    )

    draw.text(
        (270, 180),
        f"💬 {messages:,} Messages",
        font=font,
        fill="white"
    )


    draw.text(
        (270, 220),
        f"✨ {xp:,.0f} / {needed:,.0f} XP",
        font=font,
        fill="white"
    )


    # Progress bar
    bar_x = 270
    bar_y = 290
    bar_width = 520
    bar_height = 25


    # Background
    draw.rounded_rectangle(
        (
            bar_x,
            bar_y,
            bar_x + bar_width,
            bar_y + bar_height
        ),
        radius=15,
        fill=(50,50,60)
    )


    # Filled part #eed5f0
    filled = int(bar_width * percent)

    draw.rounded_rectangle(
        (
            bar_x,
            bar_y,
            bar_x + filled,
            bar_y + bar_height
        ),
        radius=15,
        fill="#eed5f0"
    )


    # Send image
    file = discord.File(
        io.BytesIO(
            save_image(img)
        ),
        filename="level.png"
    )

    await ctx.send(file=file)



def save_image(img):
    buffer = io.BytesIO()
    img.save(
        buffer,
        format="PNG"
    )
    buffer.seek(0)
    return buffer
async def level(ctx, member: discord.Member = None):

    if member is None:
        member = ctx.author

    data = load_data()

    user = get_user(
        data,
        ctx.guild.id,
        member.id
    )

    current_level = user["level"]
    xp = user["xp"]
    messages = user["messages"]

    needed = xp_needed_for_level(current_level)

    remaining_xp = max(0, needed - xp)

    messages_left = max(
        0,
        int((remaining_xp / 20) + 0.99)
    )

    # leaderboard position
    guild_data = data.get(str(ctx.guild.id), {})

    ranking = []

    for uid, stats in guild_data.items():
        ranking.append(
            (
                uid,
                stats["level"],
                stats["messages"]
            )
        )

    ranking.sort(
        key=lambda x: (x[1], x[2]),
        reverse=True
    )

    position = 1

    for index, item in enumerate(ranking, start=1):
        if item[0] == str(member.id):
            position = index
            break


    bar = progress_bar(xp, needed)

    percent = int((xp / needed) * 100)


    embed = discord.Embed(
        color=discord.Color.blurple()
    )


    embed.set_thumbnail(
        url=member.display_avatar.url
    )


    embed.description = (
        f"**{member.name}**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🏆 Server Rank: **#{position}**\n\n"
        f"`{bar}`\n"
        f"**{xp:,.0f} / {needed:,.0f} XP**  •  **{percent}%**\n\n"
        f"⭐ Level **{current_level}**\n"
        f"💬 Messages **{messages:,}**\n"
        f"📨 Messages until next level: **{messages_left:,}**"
    )


    embed.set_footer(
        text="Level System"
    )


    await ctx.send(embed=embed)



@bot.command(name="rank")
async def rank(ctx):
    await level(ctx)
    import discord
from discord.ui import View, Button


class LeaderboardView(View):
    def __init__(self, top10):
        super().__init__(timeout=60)
        self.top10 = top10


    @discord.ui.button(
        label="Show Top 10",
        style=discord.ButtonStyle.blurple
    )
    async def show_top10(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        text = ""

        for i, user in enumerate(
            self.top10[:10],
            start=1
        ):
            member, level, messages, xp = user

            text += (
                f"**{i}.** {member.mention}\n"
                f"⭐ Level **{level}** • "
                f"💬 {messages:,} messages • "
                f"✨ {xp:,.0f} XP\n\n"
            )


        embed = discord.Embed(
            title="🏆 Server Leaderboard - Top 10",
            description=text,
            color=discord.Color.gold()
        )


        await interaction.response.edit_message(
            embed=embed,
            view=None
        )



@bot.command(name="leaderboard", aliases=["ld"])
async def leaderboard(ctx):

    data = load_data()

    guild = data.get(
        str(ctx.guild.id),
        {}
    )


    leaderboard = []


    for user_id, stats in guild.items():

        member = ctx.guild.get_member(
            int(user_id)
        )

        if member:

            leaderboard.append(
                (
                    member,
                    stats["level"],
                    stats["messages"],
                    stats["xp"]
                )
            )


    leaderboard.sort(
        key=lambda x: (
            x[1],
            x[2],
            x[3]
        ),
        reverse=True
    )


    if len(leaderboard) == 0:

        await ctx.send(
            "No users have earned XP yet."
        )
        return


    text = ""


    for i, user in enumerate(
        leaderboard[:3],
        start=1
    ):

        member, level, messages, xp = user

        text += (
            f"**{i}.** {member.mention}\n"
            f"⭐ Level **{level}** • "
            f"💬 {messages:,} messages • "
            f"✨ {xp:,.0f} XP\n\n"
        )


    embed = discord.Embed(
        title="🏆 Server Leaderboard",
        description=text,
        color=discord.Color.gold()
    )


    await ctx.send(
        embed=embed,
        view=LeaderboardView(leaderboard)
            )

print("Starting bot...")
bot.run(TOKEN)
