import discord
from discord.ext import commands
import json
import os
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


TOKEN = os.getenv("TOKEN")
PREFIX = ","


# ==========================
# INTENTS
# ==========================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.guilds = True


bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# ==========================
# FILES
# ==========================

DATA_FILE = "levels.json"


# ==========================
# DATABASE
# ==========================

def load_data():

    if not os.path.exists(DATA_FILE):

        return {}


    with open(DATA_FILE, "r") as file:

        return json.load(file)



data = load_data()



def save_data():

    with open(DATA_FILE, "w") as file:

        json.dump(
            data,
            file,
            indent=4
        )



# ==========================
# DEFAULT USER
# ==========================

def create_user():

    return {

        "level": 1,

        "xp": 0,

        "messages": 0,

        "prestige": 0,


        "badges": [],


        "title": "",


        "ring": "none",


        "theme": "default",


        "profile_background": "",


        "rank_background": "",


        "rank_end": "",


        "boosting": False,


        "staff": False

    }



# ==========================
# DEFAULT SERVER
# ==========================

def create_server():

    return {

        "users": {},


        "settings": {

    "level_message":
    "{user} reached level {level}",

    "level_title":
    "Level {level}",

    "xp_channels": [],

"level_channel": None,

"xp_category": None,


            "level_roles": {},


            "automod_roles": [],


            "ai_roles": []

        }

    }



# ==========================
# GET SERVER
# ==========================

def get_server(guild_id):

    guild_id = str(guild_id)


    if guild_id not in data:

        data[guild_id] = create_server()


    return data[guild_id]



# ==========================
# GET USER
# ==========================

def get_user(guild_id, user_id):

    server = get_server(guild_id)


    user_id = str(user_id)


    if user_id not in server["users"]:

        server["users"][user_id] = create_user()


    return server["users"][user_id]



# ==========================
# READY
# ==========================

@bot.event
async def on_ready():

    print(
        f"✅ Logged in as {bot.user}"
    )

    print(
        "✅ New leveling system online"
    )
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



# ==========================
# LEVEL CALCULATION
# ==========================


def check_level(user):

    level = user["level"]
    xp = user["xp"]


    leveled_up = False


    while level < 100:

        needed = xp_needed_for_level(level)


        if xp < needed:
            break


        xp -= needed
        level += 1

        leveled_up = True



    user["level"] = level
    user["xp"] = xp


    return leveled_up



# ==========================
# PRESTIGE SYSTEM
# ==========================


def prestige_check(user):

    if user["level"] >= 100:


        if user["prestige"] < 3:


            user["prestige"] += 1

            user["level"] = 1

            user["xp"] = 0


            return True


    return False



# ==========================
# BADGE SYSTEM
# ==========================


MESSAGE_BADGES = {

    1000:
    "1K Messages",

    5000:
    "5K Messages",

    20000:
    "20K Messages"

}



def add_badge(user, badge):

    if badge not in user["badges"]:

        user["badges"].append(badge)



def update_message_badges(user):

    messages = user["messages"]


    for amount, badge in MESSAGE_BADGES.items():

        if messages >= amount:

            add_badge(
                user,
                badge
            )



# ==========================
# STAFF / BOOSTER BADGES
# ==========================


def update_special_badges(user):


    if user.get("boosting"):

        add_badge(
            user,
            "Booster"
        )


    if user.get("staff"):

        add_badge(
            user,
            "Staff"
        )



# ==========================
# LEADERBOARD BADGES
# ==========================


def update_leaderboard_badges(guild_id):

    server = get_server(guild_id)


    users = sorted(

        server["users"].items(),

        key=lambda x:
        x[1]["xp"],

        reverse=True

    )


    for index, (user_id, user) in enumerate(users, start=1):


        # Remove old leaderboard badges

        user["badges"] = [

            badge for badge in user["badges"]

            if badge not in [

                "Top 10",
                "Top 3",
                "Top 1"

            ]

        ]


        if index == 1:

            add_badge(
                user,
                "Top 1"
            )


        elif index <= 3:

            add_badge(
                user,
                "Top 3"
            )


        elif index <= 10:

            add_badge(
                user,
                "Top 10"
            )



# ==========================
# EARLY USER BADGE
# ==========================


def give_early_user_badge(user_id):

    file = "early_users.json"


    if os.path.exists(file):

        with open(file, "r") as f:

            early_users = json.load(f)


    else:

        early_users = []



    if str(user_id) in early_users:

        return True



    if len(early_users) < 100:


        early_users.append(
            str(user_id)
        )


        with open(file, "w") as f:

            json.dump(
                early_users,
                f,
                indent=4
            )


        return True



    return False



# ==========================
# MESSAGE XP EVENT
# ==========================


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


    user["xp"] += 1

    user["messages"] += 1



    update_message_badges(user)

    update_special_badges(user)



    if give_early_user_badge(message.author.id):

        add_badge(
            user,
            "Early User"
        )



    leveled = check_level(user)


    if leveled:

    server = get_server(message.guild.id)

    roles = server["settings"]["level_roles"]

    current_level = str(user["level"])


    # Remove old level roles
    for level, role_id in roles.items():

        role = message.guild.get_role(role_id)

        if role and role in message.author.roles:

            await message.author.remove_roles(role)


    # Give new level role
    if current_level in roles:

        new_role = message.guild.get_role(
            roles[current_level]
        )

        if new_role:

            await message.author.add_roles(new_role)


    # Send level message
    channel_id = server["settings"]["level_channel"]

    if channel_id:

        channel = message.guild.get_channel(channel_id)

    else:

        channel = message.channel


    await channel.send(

        f"🎉 {message.author.mention} reached level {user['level']}!"

    )



    if prestige_check(user):


        await message.channel.send(

            f"⭐ {message.author.mention} reached Prestige {user['prestige']}!"

        )



    update_leaderboard_badges(

        message.guild.id

    )


    save_data()


    await bot.process_commands(message)

# ==========================
# PERMISSION CHECKS
# ==========================


def is_owner():

    async def predicate(ctx):

        return ctx.guild.owner_id == ctx.author.id

    return commands.check(predicate)



def is_admin():

    async def predicate(ctx):

        return ctx.author.guild_permissions.administrator

    return commands.check(predicate)



# ==========================
# LEVEL ROLES
# ==========================


@bot.command()
@is_owner()
async def setlevelrole(ctx, level: int, role: discord.Role):

    server = get_server(ctx.guild.id)


    server["settings"]["level_roles"][str(level)] = role.id


    save_data()


    await ctx.send(
        f"✅ Level {level} role set to {role.mention}"
    )



@bot.command()
@is_owner()
async def removelevelrole(ctx, level: int):

    server = get_server(ctx.guild.id)


    roles = server["settings"]["level_roles"]


    if str(level) in roles:

        del roles[str(level)]

        save_data()


        await ctx.send(
            f"✅ Removed level {level} role"
        )

    else:

        await ctx.send(
            "❌ No role found"
        )



@bot.command()
async def listlevelroles(ctx):

    server = get_server(ctx.guild.id)


    roles = server["settings"]["level_roles"]


    if not roles:

        return await ctx.send(
            "No level roles set."
        )


    text = ""


    for level, role in roles.items():

        text += f"Level {level}: <@&{role}>\n"


    await ctx.send(text)



# ==========================
# XP CHANNELS
# ==========================


@bot.command()
@is_owner()
async def setxpchannel(ctx, channel: discord.TextChannel):

    server = get_server(ctx.guild.id)


    server["settings"]["xp_channels"].append(
        channel.id
    )


    save_data()


    await ctx.send(
        f"✅ XP enabled in {channel.mention}"
    )



@bot.command()
async def listxpchannels(ctx):

    server = get_server(ctx.guild.id)


    channels = server["settings"]["xp_channels"]


    if not channels:

        return await ctx.send(
            "No XP channels set."
        )


    await ctx.send(

        "\n".join(
            f"<#{c}>"
            for c in channels
        )

    )



# ==========================
# XP CATEGORY
# ==========================


@bot.command()
@is_owner()
async def setxpcategory(ctx, category: discord.CategoryChannel):

    server = get_server(ctx.guild.id)


    server["settings"]["xp_category"] = category.id


    save_data()


    await ctx.send(
        f"✅ XP category set to {category.name}"
    )



@bot.command()
async def listxpcategories(ctx):

    server = get_server(ctx.guild.id)


    category = server["settings"]["xp_category"]


    if not category:

        return await ctx.send(
            "No XP category set."
        )


    await ctx.send(
        f"XP Category: <#{category}>"
    )



# ==========================
# AUTOMOD ROLES
# ==========================


@bot.command()
@is_admin()
async def setautomodrole(ctx, role: discord.Role):

    server = get_server(ctx.guild.id)


    if role.id not in server["settings"]["automod_roles"]:

        server["settings"]["automod_roles"].append(
            role.id
        )


    save_data()


    await ctx.send(
        f"✅ AutoMod role added {role.mention}"
    )



@bot.command()
@is_admin()
async def removeautomodrole(ctx, role: discord.Role):

    server = get_server(ctx.guild.id)


    if role.id in server["settings"]["automod_roles"]:

        server["settings"]["automod_roles"].remove(
            role.id
        )


    save_data()


    await ctx.send(
        "✅ AutoMod role removed"
    )



@bot.command()
async def listautomodroles(ctx):

    server = get_server(ctx.guild.id)


    roles = server["settings"]["automod_roles"]


    if not roles:

        return await ctx.send(
            "No AutoMod roles."
        )


    await ctx.send(

        "\n".join(
            f"<@&{r}>"
            for r in roles
        )

    )



# ==========================
# AI ROLES
# ==========================


@bot.command()
@is_owner()
async def setaitorole(ctx, role: discord.Role):

    server = get_server(ctx.guild.id)


    if role.id not in server["settings"]["ai_roles"]:

        server["settings"]["ai_roles"].append(
            role.id
        )


    save_data()


    await ctx.send(
        f"✅ AI role added {role.mention}"
    )



@bot.command()
@is_owner()
async def removeaitorole(ctx, role: discord.Role):

    server = get_server(ctx.guild.id)


    if role.id in server["settings"]["ai_roles"]:

        server["settings"]["ai_roles"].remove(
            role.id
        )


    save_data()


    await ctx.send(
        "✅ AI role removed"
    )



@bot.command()
async def listaitoroles(ctx):

    server = get_server(ctx.guild.id)


    roles = server["settings"]["ai_roles"]


    if not roles:

        return await ctx.send(
            "No AI roles."
        )


    await ctx.send(

        "\n".join(
            f"<@&{r}>"
            for r in roles
        )

    )



# ==========================
# LEVEL MESSAGE / TITLE
# ==========================


@bot.command()
async def setlevelmessage(ctx, *, message_text):

    server = get_server(ctx.guild.id)


    server["settings"]["level_message"] = message_text


    save_data()


    await ctx.send(
        "✅ Level message updated"
    )



@bot.command()
async def setleveltitle(ctx, *, title):

    server = get_server(ctx.guild.id)


    server["settings"]["level_title"] = title


    save_data()


    await ctx.send(
        "✅ Level title updated"
        )
# ==========================
# PROFILE CUSTOMIZATION
# ==========================


@bot.command()
async def setprofilebg(ctx, url: str):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    user["profile_background"] = url

    save_data()

    await ctx.send(
        "✅ Profile background updated!"
    )



@bot.command()
async def setrankbg(ctx, url: str):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    user["rank_background"] = url

    save_data()

    await ctx.send(
        "✅ Rank background updated!"
    )



@bot.command()
async def setrankend(ctx, url: str):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )

    user["rank_end"] = url

    save_data()

    await ctx.send(
        "✅ Rank progress ending image updated!"
    )



# ==========================
# PROFILE RINGS
# ==========================


VALID_RINGS = [

    "none",

    "pride",

    "lesbian",

    "trans"

]



@bot.command()
async def setring(ctx, ring: str):

    ring = ring.lower()


    if ring not in VALID_RINGS:

        return await ctx.send(
            "❌ Available rings: pride, lesbian, trans"
        )


    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )


    user["ring"] = ring


    save_data()


    await ctx.send(
        f"✅ Profile ring set to {ring}"
    )



# ==========================
# THEMES
# ==========================


VALID_THEMES = [

    "default",

    "arcane",

    "madeinabyss"

]



@bot.command()
async def settheme(ctx, theme: str):

    theme = theme.lower()


    if theme not in VALID_THEMES:

        return await ctx.send(
            "❌ Themes: default, arcane, madeinabyss"
        )


    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )


    user["theme"] = theme


    save_data()


    await ctx.send(
        f"✅ Theme changed to {theme}"
    )



# ==========================
# CUSTOM TITLE
# ==========================


@bot.command()
async def settitle(ctx, *, title):

    user = get_user(
        ctx.guild.id,
        ctx.author.id
    )


    user["title"] = title


    save_data()


    await ctx.send(
        "✅ Profile title changed!"
    )



# ==========================
# IMAGE DOWNLOADER
# ==========================


async def get_image(url):

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as response:

                if response.status != 200:
                    return None


                image_bytes = await response.read()


        return Image.open(
            BytesIO(image_bytes)
        ).convert(
            "RGBA"
        )


    except:

        return None



# ==========================
# CARD COLORS
# ==========================


ARCANE_PURPLE = (
    238,
    213,
    240
)


DARK_BACKGROUND = (
    20,
    20,
    25
        )

# ==========================
# CUSTOMIZE MENU
# ==========================


@bot.command()
async def customize(ctx):

    embed = discord.Embed(
        title="🎨 Profile Customization",
        description="Customize your profile and rank card!",
        color=0xEED5F0
    )


    embed.add_field(
        name="🖼️ Backgrounds",
        value=(
            "`,setprofilebg <url>`\n"
            "Change your profile background\n\n"
            "`,setrankbg <url>`\n"
            "Change your rank card background\n\n"
            "`,setrankend <url>`\n"
            "Change XP bar ending image"
        ),
        inline=False
    )


    embed.add_field(
        name="⭕ Profile Rings",
        value=(
            "`,setring pride`\n"
            "`,setring lesbian`\n"
            "`,setring trans`\n"
            "`,setring none`\n\n"
            "Add a ring around your profile picture"
        ),
        inline=False
    )


    embed.add_field(
        name="🌌 Themes",
        value=(
            "`,settheme arcane`\n"
            "`,settheme madeinabyss`\n"
            "`,settheme default`\n\n"
            "Change your profile style"
        ),
        inline=False
    )


    embed.add_field(
        name="🏷️ Titles",
        value=(
            "`,settitle <text>`\n\n"
            "Add a custom title under your username"
        ),
        inline=False
    )


    embed.add_field(
        name="📊 Preview Commands",
        value=(
            "`,rank`\n"
            "View your Arcane rank card\n\n"
            "`,profile`\n"
            "View your full profile card"
        ),
        inline=False
    )


    embed.set_footer(
        text="More cosmetics coming soon ✨"
    )


    await ctx.send(
        embed=embed
    )

# ==========================
# RANK SYSTEM
# ==========================


RANK_COLOR = (238, 213, 240)



def get_rank(guild_id, user_id):

    server = get_server(guild_id)


    users = sorted(
        server["users"].items(),
        key=lambda x: x[1]["xp"],
        reverse=True
    )


    for number, (uid, info) in enumerate(users, start=1):

        if uid == str(user_id):

            return number


    return 0



# ==========================
# FONT LOADER
# ==========================


def get_font(size):

    try:

        return ImageFont.truetype(
            "arial.ttf",
            size
        )

    except:

        return ImageFont.load_default()



# ==========================
# DRAW AVATAR
# ==========================


async def get_avatar(member):

    async with aiohttp.ClientSession() as session:

        async with session.get(
            str(member.display_avatar.url)
        ) as response:

            data = await response.read()


    return Image.open(
        BytesIO(data)
    ).convert(
        "RGBA"
    )



# ==========================
# RING LOADER
# ==========================


def get_ring_path(ring):

    paths = {

        "pride":
        "assets/rings/pride.png",


        "lesbian":
        "assets/rings/lesbian.png",


        "trans":
        "assets/rings/trans.png"

    }


    return paths.get(ring)



# ==========================
# CREATE RANK CARD
# ==========================


async def create_rank_card(member, user):


    # CARD SIZE
    image = Image.new(
        "RGBA",
        (700, 220),
        DARK_BACKGROUND
    )


    draw = ImageDraw.Draw(image)



    # Background

    if user["rank_background"]:


        background = await get_image(
            user["rank_background"]
        )


        if background:

            background = background.resize(
                (700,220)
            )


            image.paste(
                background
            )



    # Fonts

    big = get_font(32)

    normal = get_font(24)

    small = get_font(18)



    # Avatar

    avatar = await get_avatar(member)


    avatar = avatar.resize(
        (100,100)
    )


    mask = Image.new(
        "L",
        (100,100),
        0
    )


    ImageDraw.Draw(mask).ellipse(
        (0,0,100,100),
        fill=255
    )



    # Ring

    ring_path = get_ring_path(
        user["ring"]
    )


    if ring_path and os.path.exists(ring_path):


        ring = Image.open(
            ring_path
        ).convert(
            "RGBA"
        )


        ring = ring.resize(
            (120,120)
        )


        image.paste(
            ring,
            (25,70),
            ring
        )



    image.paste(
        avatar,
        (35,80),
        mask
    )



    # Rank

    rank = get_rank(
        member.guild.id,
        member.id
    )


    draw.text(

        (30,20),

        f"#{rank}",

        fill="white",

        font=big

    )



    # Username

    draw.text(

        (160,45),

        member.name,

        fill="white",

        font=normal

    )



    # Title

    if user["title"]:

        draw.text(

            (160,75),

            user["title"],

            fill=(220,220,220),

            font=small

        )



    # XP BAR

    level = user["level"]

    xp = user["xp"]


    needed = xp_needed_for_level(
        level
    )


    bar_x = 160

    bar_y = 120

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

        fill=(60,60,70)

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



    # Rank end image

    if user["rank_end"]:


        end_image = await get_image(
            user["rank_end"]
        )


        if end_image:


            end_image = end_image.resize(
                (35,35)
            )


            image.paste(

                end_image,

                (
                    bar_x + bar_width - 15,
                    bar_y - 5
                ),

                end_image

            )



    # Stats

    draw.text(

        (160,160),

        f"Level {level}",

        fill="white",

        font=small

    )


    draw.text(

        (300,160),

        f"{xp}/{needed} XP",

        fill="white",

        font=small

    )


    draw.text(

        (500,160),

        f"{user['messages']} msgs",

        fill="white",

        font=small

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
# BADGE IMAGE SYSTEM
# ==========================


def get_badge_path(badge):

    badges = {

        "Early User":
        "assets/badges/early_user.png",

        "Top 1":
        "assets/badges/top1.png",

        "Top 3":
        "assets/badges/top3.png",

        "Top 10":
        "assets/badges/top10.png",

        "1K Messages":
        "assets/badges/1k.png",

        "5K Messages":
        "assets/badges/5k.png",

        "20K Messages":
        "assets/badges/20k.png",

        "Booster":
        "assets/badges/booster.png",

        "Staff":
        "assets/badges/staff.png"

    }


    return badges.get(badge)



# ==========================
# PROFILE CARD
# ==========================


async def create_profile_card(member, user):


    image = Image.new(

        "RGBA",

        (900,900),

        (20,20,25)

    )


    # Background

    if user["profile_background"]:


        background = await get_image(

            user["profile_background"]

        )


        if background:

            background = background.resize(
                (900,900)
            )

            image.paste(
                background
            )



    draw = ImageDraw.Draw(image)


    title_font = get_font(45)

    font = get_font(28)

    small = get_font(22)



    # Avatar

    avatar = await get_avatar(member)


    avatar = avatar.resize(
        (180,180)
    )


    mask = Image.new(
        "L",
        (180,180),
        0
    )


    ImageDraw.Draw(mask).ellipse(

        (0,0,180,180),

        fill=255

    )


    image.paste(

        avatar,

        (70,80),

        mask

    )



    # Username

    draw.text(

        (300,100),

        member.name,

        fill="white",

        font=title_font

    )



    # Title

    if user["title"]:


        draw.text(

            (300,170),

            user["title"],

            fill=(230,230,230),

            font=small

        )



    # Stats


    draw.text(

        (80,330),

        f"Level: {user['level']}",

        fill="white",

        font=font

    )


    draw.text(

        (80,390),

        f"XP: {user['xp']}",

        fill="white",

        font=font

    )


    draw.text(

        (80,450),

        f"Messages: {user['messages']}",

        fill="white",

        font=font

    )



    # Prestige


    stars = "⭐" * user["prestige"]


    if not stars:

        stars = "None"



    draw.text(

        (80,510),

        f"Prestige: {stars}",

        fill="white",

        font=font

    )



    # Badges


    x = 80

    y = 620



    for badge in user["badges"]:


        path = get_badge_path(badge)


        if path and os.path.exists(path):


            icon = Image.open(
                path
            ).convert(
                "RGBA"
            )


            icon = icon.resize(
                (70,70)
            )


            image.paste(

                icon,

                (x,y),

                icon

            )


            x += 90



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


@bot.command(
    aliases=["ld"]
)
async def leaderboard(ctx):


    server = get_server(
        ctx.guild.id
    )


    users = sorted(

        server["users"].items(),

        key=lambda x:
        x[1]["xp"],

        reverse=True

    )


    embed = discord.Embed(

        title="🏆 Leaderboard",

        color=0xEED5F0

    )


    text = ""


    for i,(uid,user) in enumerate(users[:10],1):


        text += (

            f"#{i} <@{uid}> "

            f"Level {user['level']} "

            f"XP {user['xp']}\n"

        )



    if not text:

        text = "No users yet"



    embed.description = text


    await ctx.send(
        embed=embed
    )



# ==========================
# SERVER STATS
# ==========================


@bot.command()
async def serverstats(ctx):


    server = get_server(
        ctx.guild.id
    )


    total_messages = sum(

        u["messages"]

        for u in server["users"].values()

    )


    embed = discord.Embed(

        title="📊 Server Stats",

        color=0xEED5F0

    )


    embed.add_field(

        name="Members Tracked",

        value=len(server["users"])

    )


    embed.add_field(

        name="Messages",

        value=total_messages

    )


    await ctx.send(
        embed=embed
    )



# ==========================
# HELP COMMAND
# ==========================


@bot.command()
async def help(ctx):


    embed = discord.Embed(

        title="Leveling Bot Commands",

        color=0xEED5F0

    )


    embed.add_field(

        name="Profile",

        value=
        ",rank\n,profile\n,leaderboard"

    )


    embed.add_field(

        name="Customize",

        value=
        ",settitle\n,settheme\n,setring\n,setprofilebg"

    )


    embed.add_field(

        name="Stats",

        value=
        ",serverstats"

    )


    await ctx.send(
        embed=embed
    )



# ==========================
# ERROR HANDLER
# ==========================


@bot.event
async def on_command_error(ctx,error):


    if isinstance(
        error,
        commands.CommandNotFound
    ):

        return



    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "❌ Missing argument."
        )

        return



    print(error)



@bot.command()
@commands.has_permissions(administrator=True)
async def admin(ctx):
    embed = discord.Embed(
        title="🛡️ Admin Commands",
        description="Here are all administrator commands:",
        color=0xEED5F0
    )

    embed.add_field(
        name="⚙️ Level Management",
        value="""
`,setlevelrole` - Set a level reward role
`,editlevelrole` - Edit an existing level role
`,removelevelrole` - Remove a level role reward
`,listlevelroles` - View all level roles
        """,
        inline=False
    )

    embed.add_field(
        name="✨ XP Management",
        value="""
`,setxpchannel` - Set channels where XP works
`,removexpchannel` - Remove XP channel restrictions
`,listxpchannels` - View XP channels
`,addxp` - Add XP to a user
`,removexp` - Remove XP from a user
        """,
        inline=False
    )

    embed.add_field(
        name="🤖 Auto Moderation Roles",
        value="""
`,setautomodrole` - Set AutoMod role
`,removeautomodrole` - Remove AutoMod role
`,listautomodroles` - View AutoMod roles
        """,
        inline=False
    )

    embed.add_field(
        name="📢 Level Messages",
        value="""
`,setlevelmessage` - Set level-up message
`,resetlevelmessage` - Reset level-up message
        """,
        inline=False
    )

    embed.add_field(
        name="🔧 Server Management",
        value="""
`,purge` - Delete messages
`,lock` - Lock a channel
`,unlock` - Unlock a channel
        """,
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author}")

    await ctx.send(embed=embed)


@admin.error
async def admin_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need Administrator permission to use this command.")


@bot.command()
@is_owner()
async def setlevelchannel(ctx, channel: discord.TextChannel):

    server = get_server(ctx.guild.id)

    server["settings"]["level_channel"] = channel.id

    save_data()

    await ctx.send(
        f"✅ Level messages will now go to {channel.mention}"
    )


@bot.command()
@is_owner()
async def setlevelrole(ctx, level: int, role: discord.Role):

    server = get_server(ctx.guild.id)

    server["settings"]["level_roles"][str(level)] = role.id

    save_data()

    await ctx.send(
        f"✅ Successfully set **Level {level}** reward role to {role.mention}"
    )


@setlevelrole.error
async def setlevelrole_error(ctx, error):

    if isinstance(error, commands.MissingRequiredArgument):

        await ctx.send(
            "❌ Incorrect usage!\n"
            "Correct usage:\n"
            "`,setlevelrole <level> <role>`\n\n"
            "Example:\n"
            "`,setlevelrole 10 @Level10`"
        )

    elif isinstance(error, commands.BadArgument):

        await ctx.send(
            "❌ Invalid level or role!\n"
            "Make sure you enter a number and mention a real role.\n\n"
            "Example:\n"
            "`,setlevelrole 10 @Level10`"
        )

    elif isinstance(error, commands.CheckFailure):

        await ctx.send(
            "❌ You must be the server owner to use this command."
        )
# ==========================
# START BOT
# ==========================


print(
    "Starting bot..."
)


bot.run(TOKEN)
