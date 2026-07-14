import discord
from discord.ext import commands
import json
import os
from PIL import Image, ImageDraw, ImageFont
import aiohttp
from io import BytesIO


TOKEN = os.getenv("TOKEN")
PREFIX = ","

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# ==========================
# DATABASE
# ==========================

DATA_FILE = "levels.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, "r") as file:
        return json.load(file)


def save_data():
    with open(DATA_FILE, "w") as file:
        json.dump(
            data,
            file,
            indent=4
        )


data = load_data()


def get_user(guild_id, user_id):
    guild_id = str(guild_id)
    user_id = str(user_id)

    if guild_id not in data:
        data[guild_id] = {}

    if user_id not in data[guild_id]:
        data[guild_id][user_id] = {
            "level": 1,
            "xp": 0,
            "messages": 0,
            "prestige": 0,
            "badges": [],
            "status": ""
        }

    return data[guild_id][user_id]


# ==========================
# XP SYSTEM
# ==========================

def xp_needed_for_level(level):

    if level <= 0:
        return 0

    if level == 1:
        return 100

    if level == 100:
        return 10000

    if level <= 70:
        return int(
            100 + (0.495 * (level ** 2))
        )

    return int(
        100
        + (0.495 * (level ** 2))
        + (4.9 * ((level - 70) ** 1.8))
    )


def get_level_from_xp(xp):

    level = 1

    while level < 100:
        needed = xp_needed_for_level(level)

        if xp < needed:
            break

        xp -= needed
        level += 1

    return level


# ==========================
# LEVEL ROLES
# ==========================

LEVEL_ROLES_FILE = "level_roles.json"


def load_level_roles():

    if not os.path.exists(LEVEL_ROLES_FILE):
        return {}

    with open(LEVEL_ROLES_FILE, "r") as file:
        return json.load(file)


def save_level_roles():

    with open(LEVEL_ROLES_FILE, "w") as file:
        json.dump(
            level_roles,
            file,
            indent=4
        )


level_roles = load_level_roles()


async def give_level_role(member, old_level, new_level):

    guild_id = str(member.guild.id)

    if guild_id not in level_roles:
        return

    roles = level_roles[guild_id]

    old_role = None
    new_role = None

    for level, role_id in roles.items():

        if int(level) == old_level:
            old_role = member.guild.get_role(
                int(role_id)
            )

        if int(level) == new_level:
            new_role = member.guild.get_role(
                int(role_id)
            )

    if old_role:
        await member.remove_roles(old_role)

    if new_role:
        await member.add_roles(new_role)


# ==========================
# BADGES
# ==========================

def update_badges(user):

    messages = user["messages"]

    badges = user["badges"]

    if messages >= 1000 and "1K Messages" not in badges:
        badges.append("1K Messages")

    if messages >= 2000 and "2K Messages" not in badges:
        badges.append("2K Messages")

    if messages >= 5000 and "5K Messages" not in badges:
        badges.append("5K Messages")

    if messages >= 10000 and "10K Messages" not in badges:
        badges.append("10K Messages")


# ==========================
# BOT EVENTS
# ==========================

@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    print(
        "Leveling system online!"
    )


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        return

    user = get_user(
        message.guild.id,
        message.author.id
    )

    old_level = user["level"]

    user["xp"] += 1
    user["messages"] += 1

    update_badges(user)

    new_level = get_level_from_xp(
        user["xp"]
    )

    if new_level != old_level:

        user["level"] = new_level

        if new_level == 100:

            if user["prestige"] < 3:

                user["prestige"] += 1
                user["level"] = 1
                user["xp"] = 0

        await give_level_role(
            message.author,
            old_level,
            new_level
        )

        await message.channel.send(
            f"🎉 {message.author.mention} reached Level {new_level}!"
        )

    save_data()

    await bot.process_commands(message)
    # ==========================
# RANK CARD
# ==========================

RANK_COLOR = (238, 213, 240)


def get_user_rank(guild_id, user_id):

    guild_data = data.get(
        str(guild_id),
        {}
    )

    users = sorted(
        guild_data.items(),
        key=lambda x: x[1]["xp"],
        reverse=True
    )

    for index, (uid, info) in enumerate(users, start=1):

        if uid == str(user_id):
            return index

    return 0



async def create_rank_card(member, user):

    image = Image.new(
        "RGB",
        (700, 220),
        (25, 25, 25)
    )

    draw = ImageDraw.Draw(image)


    try:

        font_big = ImageFont.truetype(
            "arial.ttf",
            35
        )

        font = ImageFont.truetype(
            "arial.ttf",
            26
        )

        small_font = ImageFont.truetype(
            "arial.ttf",
            20
        )

    except:

        font_big = None
        font = None
        small_font = None



    async with aiohttp.ClientSession() as session:

        async with session.get(
            str(member.display_avatar.url)
        ) as response:

            avatar_bytes = await response.read()


    avatar = Image.open(
        BytesIO(avatar_bytes)
    ).convert(
        "RGBA"
    )


    avatar = avatar.resize(
        (110,110)
    )


    mask = Image.new(
        "L",
        (110,110),
        0
    )


    mask_draw = ImageDraw.Draw(mask)

    mask_draw.ellipse(
        (0,0,110,110),
        fill=255
    )


    image.paste(
        avatar,
        (35,80),
        mask
    )


    rank = get_user_rank(
        member.guild.id,
        member.id
    )


    draw.text(
        (35,25),
        f"#{rank}",
        fill="white",
        font=font
    )


    draw.text(
        (170,70),
        member.name,
        fill="white",
        font=font
    )


    level = user["level"]
    xp = user["xp"]


    needed = xp_needed_for_level(level)


    bar_x = 170
    bar_y = 115
    bar_width = 450
    bar_height = 25


    draw.rounded_rectangle(
        (
            bar_x,
            bar_y,
            bar_x + bar_width,
            bar_y + bar_height
        ),
        radius=12,
        fill=(70,70,70)
    )


    progress = 0

    if needed > 0:
        progress = xp / needed


    progress_width = int(
        bar_width * progress
    )


    draw.rounded_rectangle(
        (
            bar_x,
            bar_y,
            bar_x + progress_width,
            bar_y + bar_height
        ),
        radius=12,
        fill=RANK_COLOR
    )


    draw.text(
        (170,150),
        f"Level {level}",
        fill="white",
        font=small_font
    )


    draw.text(
        (450,150),
        f"{xp}/{needed} XP",
        fill="white",
        font=small_font
    )


    return image



# ==========================
# RANK COMMAND
# ==========================

@bot.command()
async def rank(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )


    card = await create_rank_card(
        ctx.author,
        user
    )


    card.save(
        "rank.png"
    )


    await ctx.send(
        file=discord.File(
            "rank.png"
        )
    )



# ==========================
# PROFILE CARD
# ==========================

async def create_profile_card(member, user):

    image = Image.new(
        "RGB",
        (900,900),
        (20,20,25)
    )


    draw = ImageDraw.Draw(image)


    try:

        title_font = ImageFont.truetype(
            "arial.ttf",
            45
        )

        font = ImageFont.truetype(
            "arial.ttf",
            30
        )

        small_font = ImageFont.truetype(
            "arial.ttf",
            24
        )

    except:

        title_font = None
        font = None
        small_font = None



    draw.text(
        (260,80),
        member.name,
        fill="white",
        font=title_font
    )


    status = user.get(
        "status",
        ""
    )


    if status:

        draw.text(
            (260,140),
            str(status),
            fill=(230,230,230),
            font=small_font
        )


    draw.text(
        (60,350),
        f"Level: {user['level']}",
        fill="white",
        font=font
    )


    draw.text(
        (60,420),
        f"XP: {user['xp']}",
        fill="white",
        font=font
    )


    draw.text(
        (60,490),
        f"Messages: {user['messages']}",
        fill="white",
        font=font
    )


    prestige = int(
        user.get(
            "prestige",
            0
        )
    )


    stars = "⭐" * prestige

    if not stars:
        stars = "None"


    draw.text(
        (60,560),
        f"Prestige: {stars}",
        fill="white",
        font=font
    )


    badges = user.get(
        "badges",
        []
    )


    badge_text = ", ".join(
        badges
    )


    if not badge_text:
        badge_text = "No badges"


    draw.text(
        (60,640),
        f"Badges: {badge_text}",
        fill="white",
        font=small_font
    )


    return image



# ==========================
# PROFILE COMMAND
# ==========================

@bot.command()
async def profile(ctx):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )


    card = await create_profile_card(
        ctx.author,
        user
    )


    card.save(
        "profile.png"
    )


    await ctx.send(
        file=discord.File(
            "profile.png"
        )
    )
    # ==========================
# LEADERBOARD
# ==========================

class LeaderboardButton(discord.ui.View):

    def __init__(self, guild_id):

        super().__init__(
            timeout=60
        )

        self.guild_id = guild_id
        self.top10 = False


    @discord.ui.button(
        label="Show Top 10",
        style=discord.ButtonStyle.blurple
    )
    async def leaderboard_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.top10 = not self.top10

        await interaction.response.edit_message(
            embed=create_leaderboard_embed(
                self.guild_id,
                self.top10
            ),
            view=self
        )



def create_leaderboard_embed(
    guild_id,
    top10=False
):

    guild_data = data.get(
        str(guild_id),
        {}
    )


    users = sorted(
        guild_data.items(),
        key=lambda x: x[1]["xp"],
        reverse=True
    )


    amount = 10 if top10 else 3


    embed = discord.Embed(
        title="🏆 Server Leaderboard",
        color=0xEED5F0
    )


    text = ""


    for index, (user_id, info) in enumerate(
        users[:amount],
        start=1
    ):

        text += (
            f"**#{index}** <@{user_id}>\n"
            f"Level {info['level']} • {info['xp']} XP\n\n"
        )


    if not text:

        text = "No users yet."


    embed.description = text


    return embed



@bot.command()
async def leaderboard(ctx):

    embed = create_leaderboard_embed(
        ctx.guild.id
    )


    view = LeaderboardButton(
        ctx.guild.id
    )


    await ctx.send(
        embed=embed,
        view=view
    )



# ==========================
# SERVER STATS
# ==========================

@bot.command()
async def serverstats(ctx):

    guild_data = data.get(
        str(ctx.guild.id),
        {}
    )


    total_messages = sum(
        user["messages"]
        for user in guild_data.values()
    )


    total_users = len(
        guild_data
    )


    embed = discord.Embed(
        title="📊 Server Level Stats",
        color=0xEED5F0
    )


    embed.add_field(
        name="Tracked Members",
        value=str(total_users)
    )


    embed.add_field(
        name="Total Messages",
        value=str(total_messages)
    )


    await ctx.send(
        embed=embed
    )



# ==========================
# ADMIN XP COMMANDS
# ==========================

def is_admin(ctx):

    return ctx.author.guild_permissions.administrator



@bot.command()
async def addxp(
    ctx,
    member: discord.Member,
    amount: int
):

    if not is_admin(ctx):
        return


    user = get_user(
        ctx.guild.id,
        member.id
    )


    user["xp"] += amount

    save_data()


    await ctx.send(
        f"✅ Added {amount} XP to {member.mention}"
    )



@bot.command()
async def removexp(
    ctx,
    member: discord.Member,
    amount: int
):

    if not is_admin(ctx):
        return


    user = get_user(
        ctx.guild.id,
        member.id
    )


    user["xp"] = max(
        0,
        user["xp"] - amount
    )


    save_data()


    await ctx.send(
        f"✅ Removed {amount} XP from {member.mention}"
    )



@bot.command()
async def setxp(
    ctx,
    member: discord.Member,
    amount: int
):

    if not is_admin(ctx):
        return


    user = get_user(
        ctx.guild.id,
        member.id
    )


    user["xp"] = amount

    save_data()


    await ctx.send(
        f"✅ Set {member.mention}'s XP to {amount}"
    )



# ==========================
# START BOT
# ==========================

print(
    "Starting bot..."
)

bot.run(TOKEN)
