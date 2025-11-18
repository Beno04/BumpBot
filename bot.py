import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread

# =======================
# Flask pour 24/7 uptime
# =======================
app = Flask('')

@app.route('/')
def home():
    return "Bot actif !"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# =======================
# Bot Discord
# =======================
TOKEN = os.environ["TOKEN"]
CHANNEL_ID = 1430468986558091277
OWNER_ROLE_ID = 1438117792539873370
ADMIN_ROLE_ID = 1430468984343363739
MODO_ROLE_ID = 1430468984343363738
BOT_ROLE_ID = 1430468984272191572

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =======================
# Gestion du bump dynamique
# =======================
last_bump_time = None  # Heure du dernier bump

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    bot.loop.create_task(bump_scheduler())

async def bump_scheduler():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        print(f"CHANNEL_ID {CHANNEL_ID} n'est pas un TextChannel !")
        return

    global last_bump_time
    while True:
        if last_bump_time is None:
            # Si aucun bump n'a encore eu lieu, on attend 5 min
            await asyncio.sleep(300)
            continue

        next_run = last_bump_time + timedelta(hours=2)
        now = datetime.now()

        # Si on est entre minuit et 08:00, attendre 08:00
        if next_run.hour >= 24:
            tomorrow = now + timedelta(days=1)
            next_run = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
        if next_run.hour < 8:
            next_run = next_run.replace(hour=8, minute=0, second=0, microsecond=0)

        wait_seconds = (next_run - now).total_seconds()
        if wait_seconds > 0:
            print(f"Prochain rappel à {next_run}")
            await asyncio.sleep(wait_seconds)

        current_hour = datetime.now().hour
        if 8 <= current_hour < 24:
            owner_mention = f"<@&{OWNER_ROLE_ID}>"
            admin_mention = f"<@&{ADMIN_ROLE_ID}>"
            await channel.send(f"⏰ N’oubliez pas de faire **/bump** {owner_mention} {admin_mention} !")

# =====================================
# Commande test pour envoyer le rappel
# =====================================
@bot.command()
async def bumpnow(ctx):
    if isinstance(ctx.channel, discord.TextChannel):
        owner_mention = f"<@&{OWNER_ROLE_ID}>"
        admin_mention = f"<@&{ADMIN_ROLE_ID}>"
        await ctx.send(f"⏰ Test : n’oubliez pas de faire **/bump** {owner_mention} {admin_mention} !")

# =====================================
# Détecter le bump d’un Admin ou Owner
# =====================================
@bot.event
async def on_message(message):
    global last_bump_time

    if message.author != bot.user and any(role.id in [OWNER_ROLE_ID, ADMIN_ROLE_ID, MODO_ROLE_ID, BOT_ROLE_ID] for role in message.author.roles):
        # Vérifier si le message contient /bump
        if "/bump" in message.content.lower():
            print(f"{message.author} a fait /bump, mise à jour du timer")
            last_bump_time = datetime.now()

            # Supprimer le dernier message du bot contenant le rappel
            channel = message.channel
            if isinstance(channel, discord.TextChannel):
                async for msg in channel.history(limit=50):
                    if msg.author == bot.user and "n’oubliez pas de faire /bump" in msg.content:
                        await msg.delete()
                        print("Message du bot supprimé après bump")
                        break

    await bot.process_commands(message)

# =======================
# Lancer le bot
# =======================
bot.run(TOKEN)


