import discord
from discord.ext import commands
import json
import os
import math
from PIL import Image, ImageDraw, ImageFont
import aiohttp
from io import BytesIO


# ==========================
# BOT SETTINGS
# ==========================

TOKEN = "YOUR_BOT_TOKEN"

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
# FILE DATABASE
# ==========================

DATA_FILE = "levels.json"


def load_data():

    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, "r") as file:
        return json.load(file)



def save_data(data):

    with open(DATA_FILE, "w") as file:
        json.dump(
            data,
            file,
            indent=4
        )


data = load_data()



# ==========================
# USER DATABASE
# ==========================

def get_user(data, guild_id, user_id):

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
            "status": "",

        }


    return data[guild_id][user_id]



# ==========================
# XP REQUIRED SYSTEM
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
            100 +
            (0.495 * (level ** 2))
        )


    return int(

        100
        +
        (0.495 * (level ** 2))
        +
        (4.9 * ((level - 70) ** 1.8))

    )



# ==========================
# LEVEL CALCULATION
# ==========================

def get_level_from_xp(xp):

    level = 1


    while level < 100:

        needed = xp_needed_for_level(level)


        if xp < needed:
            break


        xp -= needed

        level += 1


    return level



def get_xp_progress(xp, level):

    needed = xp_needed_for_level(level)


    return xp, needed



# ==========================
# START EVENT
# ==========================

@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    print(
        "Leveling system online!"
    )
# ==========================
# LEVEL ROLE SETTINGS
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



# ==========================
# LEVEL UP SETTINGS
# ==========================

LEVEL_CHANNEL_FILE = "level_channel.json"


def load_level_channel():

    if not os.path.exists(LEVEL_CHANNEL_FILE):
        return {}

    with open(LEVEL_CHANNEL_FILE, "r") as file:
        return json.load(file)



def save_level_channel():

    with open(LEVEL_CHANNEL_FILE, "w") as file:
        json.dump(
            level_channels,
            file,
            indent=4
        )


level_channels = load_level_channel()



level_messages_enabled = True



# ==========================
# BADGE SYSTEM
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
# MESSAGE XP SYSTEM
# ==========================

@bot.event
async def on_message(message):

    if message.author.bot:
        return


    if not message.guild:
        return



    user = get_user(
        data,
        message.guild.id,
        message.author.id
    )


    old_level = user["level"]


    # 1 XP per message
    user["xp"] += 1

    user["messages"] += 1



    update_badges(user)



    new_level = get_level_from_xp(
        user["xp"]
    )


    if new_level != old_level:

        user["level"] = new_level


        # Prestige system

        if new_level == 100:

            if user["prestige"] < 3:

                user["prestige"] += 1

                user["level"] = 1

                user["xp"] = 0



        # Level role system

        await give_level_role(
            message.author,
            old_level,
            new_level
        )



        if level_messages_enabled:


            channel = message.channel


            if str(message.guild.id) in level_channels:

                channel = bot.get_channel(
                    int(level_channels[str(message.guild.id)])
                )


            if user["prestige"] > 0 and new_level == 1:

                await channel.send(

                    f"⭐ Prestige Unlocked!\n"
                    f"{message.author.mention} reached "
                    f"Prestige {user['prestige']}!"

                )


            else:

                await channel.send(

                    f"🎉 Congratulations "
                    f"{message.author.mention}!\n"
                    f"You reached Level {new_level}!"

                )



    save_data(data)


    await bot.process_commands(message)



# ==========================
# GIVE LEVEL ROLE
# ==========================

async def give_level_role(member, old_level, new_level):


    guild_id = str(member.guild.id)


    if guild_id not in level_roles:
        return



    roles = level_roles[guild_id]



    old_role = None
    new_role = None



    for level, role_id in roles.items():

        if int(level) == new_level:

            new_role = member.guild.get_role(
                int(role_id)
            )


        if int(level) == old_level:

            old_role = member.guild.get_role(
                int(role_id)
            )



    if old_role:

        await member.remove_roles(
            old_role
        )



    if new_role:

        await member.add_roles(
            new_role
        )

        await member.send(

            f"🌸 Level reward unlocked!\n"
            f"You received {new_role.name}"

        )
# ==========================
# RANK CARD SETTINGS
# ==========================

RANK_COLOR = (238, 213, 240)



async def create_rank_card(member, user):

    width = 700
    height = 220


    image = Image.new(
        "RGB",
        (width, height),
        (25, 25, 25)
    )


    draw = ImageDraw.Draw(image)



    # Fonts

    try:

        font_big = ImageFont.truetype(
            "arial.ttf",
            35
        )

        font = ImageFont.truetype(
            "arial.ttf",
            26
        )

        font_small = ImageFont.truetype(
            "arial.ttf",
            20
        )

    except:

        font_big = None
        font = None
        font_small = None



    # Download avatar

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



    # Circle avatar mask

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



    # Rank

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



    # Username

    draw.text(

        (170,70),

        member.name,

        fill="white",

        font=font

    )



    level = user["level"]

    xp = user["xp"]


    current_xp = xp

    needed_xp = xp_needed_for_level(level)



    # Progress bar

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



    progress = current_xp / needed_xp

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



    # Level + XP text

    draw.text(

        (170,145),

        f"Lv {level}",

        fill="white",

        font=font_small

    )


    draw.text(

        (520,145),

        f"{current_xp}/{needed_xp} EXP",

        fill="white",

        font=font_small

    )



    # Messages left

    messages_left = max(
        needed_xp - current_xp,
        0
    )


    draw.text(

        (520,175),

        f"{messages_left} msgs left",

        fill="white",

        font=font_small

    )



    return image



# ==========================
# GET USER RANK
# ==========================

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



# ==========================
# RANK COMMAND
# ==========================

@bot.command()
async def rank(ctx):

    user = get_user(
        data,
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
# PROFILE SETTINGS
# ==========================

PROFILE_BACKGROUND = "https://cdn.discordapp.com/attachments/1506965953492291605/1526406076063289494/927de7134c3fe3859fe18946867366ec.jpg"



# ==========================
# DOWNLOAD IMAGE
# ==========================

async def download_image(url):

    async with aiohttp.ClientSession() as session:

        async with session.get(url) as response:

            image_bytes = await response.read()


    return Image.open(
        BytesIO(image_bytes)
    ).convert(
        "RGB"
    )



# ==========================
# PROFILE CARD
# ==========================

async def create_profile_card(member, user):


    width = 900
    height = 900


    image = await download_image(
        PROFILE_BACKGROUND
    )


    image = image.resize(
        (width,height)
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



    # Dark overlay

    overlay = Image.new(
        "RGBA",
        image.size,
        (0,0,0,130)
    )


    image = Image.alpha_composite(
        image.convert("RGBA"),
        overlay
    )



    draw = ImageDraw.Draw(image)



    # Avatar

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
        (170,170)
    )


    mask = Image.new(
        "L",
        (170,170),
        0
    )


    mask_draw = ImageDraw.Draw(mask)

    mask_draw.ellipse(
        (0,0,170,170),
        fill=255
    )


    image.paste(
        avatar,
        (60,60),
        mask
    )



    # Username

    draw.text(

        (260,80),

        member.name,

        fill="white",

        font=title_font

    )



    # Status

    status = user.get(
        "status",
        ""
    )


    if status:

        draw.text(

            (260,140),

            status,

            fill=(230,230,230),

            font=small_font

        )



    # Level

    draw.text(

        (60,300),

        f"Level {user['level']}",

        fill="white",

        font=font

    )



    # XP

    draw.text(

        (60,350),

        f"XP: {user['xp']}",

        fill="white",

        font=font

    )



    # Messages

    draw.text(

        (60,420),

        f"Messages: {user['messages']}",

        fill="white",

        font=font

    )



    # Rank

    rank = get_user_rank(

        member.guild.id,

        member.id

    )


    draw.text(

        (60,490),

        f"Server Rank: #{rank}",

        fill="white",

        font=font

    )



    # Prestige stars

    stars = "⭐" * user.get(
        "prestige",
        0
    )


    if stars == "":

        stars = "None"



    draw.text(

        (60,560),

        f"Prestige: {stars}",

        fill="white",

        font=font

    )



    # Badges

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

        data,

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
# REWARDS STORAGE
# ==========================

REWARDS_FILE = "rewards.json"


def load_rewards():

    if not os.path.exists(REWARDS_FILE):
        return {}

    with open(REWARDS_FILE, "r") as file:
        return json.load(file)



def save_rewards():

    with open(REWARDS_FILE, "w") as file:
        json.dump(
            rewards,
            file,
            indent=4
        )


rewards = load_rewards()



# ==========================
# LEADERBOARD VIEW
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



# ==========================
# LEADERBOARD EMBED
# ==========================

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

            f"**#{index}** "
            f"<@{user_id}>\n"
            f"Level {info['level']} • "
            f"{info['xp']} XP\n\n"

        )



    if not text:

        text = "No users yet."



    embed.description = text


    return embed



# ==========================
# LEADERBOARD COMMAND
# ==========================

@bot.command()
async def leaderboard(ctx):


    embed = create_leaderboard_embed(

        ctx.guild.id,

        False

    )


    view = LeaderboardButton(

        ctx.guild.id

    )


    await ctx.send(

        embed=embed,

        view=view

    )



# ==========================
# REWARDS COMMAND
# ==========================

@bot.command()
async def rewards(ctx):


    guild_rewards = rewards.get(

        str(ctx.guild.id),

        {}

    )


    embed = discord.Embed(

        title="🎁 Level Rewards",

        color=0xEED5F0

    )


    if not guild_rewards:

        embed.description = (

            "No rewards have been set."

        )

    else:


        text = ""


        for level, role in guild_rewards.items():

            text += (

                f"Level {level} "
                f"→ <@&{role}>\n"

            )


        embed.description = text



    await ctx.send(

        embed=embed

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


    highest = max(

        guild_data.values(),

        key=lambda x: x["level"],

        default=None

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


    if highest:

        embed.add_field(

            name="Highest Level",

            value=str(highest["level"])

        )


    await ctx.send(

        embed=embed

)
# ==========================
# ADMIN CHECK
# ==========================

def is_admin(ctx):

    return (
        ctx.author.guild_permissions.administrator
    )



# ==========================
# ADD XP
# ==========================

@bot.command()
async def addxp(ctx, member: discord.Member, amount: int):

    if not is_admin(ctx):
        return


    user = get_user(
        data,
        ctx.guild.id,
        member.id
    )


    user["xp"] += amount


    save_data(data)


    await ctx.send(

        f"✅ Added {amount} XP to {member.mention}"

    )



# ==========================
# REMOVE XP
# ==========================

@bot.command()
async def removexp(ctx, member: discord.Member, amount: int):

    if not is_admin(ctx):
        return


    user = get_user(
        data,
        ctx.guild.id,
        member.id
    )


    user["xp"] = max(

        0,

        user["xp"] - amount

    )


    save_data(data)


    await ctx.send(

        f"✅ Removed {amount} XP from {member.mention}"

    )



# ==========================
# SET XP
# ==========================

@bot.command()
async def setxp(ctx, member: discord.Member, amount: int):

    if not is_admin(ctx):
        return


    user = get_user(
        data,
        ctx.guild.id,
        member.id
    )


    user["xp"] = amount


    save_data(data)


    await ctx.send(

        f"✅ Set {member.mention}'s XP to {amount}"

    )



# ==========================
# SET LEVEL ROLE
# ==========================

@bot.command()
async def setlevelrole(ctx, level: int, role: discord.Role):

    if not is_admin(ctx):
        return


    guild_id = str(
        ctx.guild.id
    )


    if guild_id not in level_roles:

        level_roles[guild_id] = {}



    level_roles[guild_id][str(level)] = role.id


    save_level_roles()


    await ctx.send(

        f"✅ Level {level} reward set to {role.mention}"

    )



# ==========================
# EDIT LEVEL ROLE
# ==========================

@bot.command()
async def editlevelrole(ctx, level: int, role: discord.Role):

    if not is_admin(ctx):
        return


    guild_id = str(
        ctx.guild.id
    )


    if guild_id not in level_roles:

        level_roles[guild_id] = {}



    level_roles[guild_id][str(level)] = role.id


    save_level_roles()


    await ctx.send(

        f"✅ Level {level} role updated to {role.mention}"

    )



# ==========================
# REMOVE LEVEL ROLE
# ==========================

@bot.command()
async def removelevelrole(ctx, level: int):

    if not is_admin(ctx):
        return


    guild_id = str(
        ctx.guild.id
    )


    if guild_id in level_roles:

        if str(level) in level_roles[guild_id]:

            del level_roles[guild_id][str(level)]



    save_level_roles()


    await ctx.send(

        f"✅ Removed Level {level} reward"

    )



# ==========================
# LEVEL UP CHANNEL
# ==========================

@bot.command()
async def setlevelupchannel(ctx, channel: discord.TextChannel):

    if not is_admin(ctx):
        return


    level_channels[str(ctx.guild.id)] = channel.id


    save_level_channel()


    await ctx.send(

        f"✅ Level up messages will go to {channel.mention}"

    )



# ==========================
# TOGGLE LEVEL UP MESSAGES
# ==========================

@bot.command()
async def togglelevelup(ctx):

    global level_messages_enabled


    if not is_admin(ctx):
        return


    level_messages_enabled = not level_messages_enabled



    status = (

        "enabled"

        if level_messages_enabled

        else "disabled"

    )


    await ctx.send(

        f"✅ Level up messages {status}"

    )



# ==========================
# HELP COMMAND
# ==========================

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="🌸 Leveling Bot Commands",
        description="All available commands",
        color=0xEED5F0
    )


    embed.add_field(
        name="👤 Profile Commands",
        value=(
            "**,rank**\n"
            "view your level progress card\n\n"
            
            "**,profile**\n"
            "view your full profile card\n\n"

            "**,leaderboard**\n"
            "view the server XP leaderboard\n\n"

            "**,rewards**\n"
            "view level role rewards\n\n"

            "**,serverstats**\n"
            "view server leveling statistics"
        ),
        inline=False
    )


    embed.add_field(
        name="⚙️ Admin Commands",
        value=(
            "**,addxp @user amount**\n"
            "add XP to a user\n\n"

            "**,removexp @user amount**\n"
            "remove XP from a user\n\n"

            "**,setxp @user amount**\n"
            "set a user's XP\n\n"

            "**,setlevelrole level @role**\n"
            "create a level role reward\n\n"

            "**,editlevelrole level @role**\n"
            "change a level role reward\n\n"

            "**,removelevelrole level**\n"
            "remove a level role reward\n\n"

            "**,setlevelupchannel #channel**\n"
            "set where level up messages appear\n\n"

            "**,togglelevelup**\n"
            "enable or disable level up messages"
        ),
        inline=False
    )


    embed.set_footer(
        text="Leveling System"
    )


    await ctx.send(
        embed=embed
    )

print("Starting bot...")
bot.run(TOKEN)
        
