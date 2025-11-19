import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread

# =======================
# Flask (keepalive)
# =======================
app = Flask('')

@app.route('/')
def home():
    return "Bot actif !"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# =======================
# Bot
# =======================
TOKEN = os.environ["TOKEN"]
CHANNEL_ID = 1431277019668156486
OWNER_ROLE_ID = 1411777383996063834
BOT_ROLE_ID = 1431274301209837691

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Empêche le scheduler d'être lancé en double
scheduler_started = False

# Dernier bump
last_bump_time = None


# =======================
# READY
# =======================
@bot.event
async def on_ready():
    global scheduler_started

    print(f"Connecté en tant que {bot.user}")

    # N’EXÉCUTE LE SCHEDULER QU’UNE SEULE FOIS
    if not scheduler_started:
        print("Lancement du scheduler bump...")
        scheduler_started = True
        bot.loop.create_task(bump_scheduler())
    else:
        print("Scheduler déjà actif, ignoré.")


# =======================
# SCHEDULER CORRIGÉ
# =======================
async def bump_scheduler():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        print("Erreur channel invalide.")
        return

    global last_bump_time

    while True:

        # Si aucun bump n'a été fait, on attend
        if last_bump_time is None:
            await asyncio.sleep(30)
            continue

        next_run = last_bump_time + timedelta(minute=2)
        now = datetime.now()

        # Plage horaire (pas avant 8h)
        if next_run.hour < 8:
            next_run = next_run.replace(hour=8, minute=0, second=0)

        wait_seconds = (next_run - now).total_seconds()
        if wait_seconds > 0:
            print(f"Rappel prévu pour {next_run}")
            await asyncio.sleep(wait_seconds)

        # On renvoie UNE SEULE fois
        current_hour = datetime.now().hour
        if 8 <= current_hour < 24:
            owner = f"<@&{OWNER_ROLE_ID}>"
            admin = f"<@&{ADMIN_ROLE_ID}>"
            await channel.send(f"⏰ N’oubliez pas de faire **/bump** {owner} {admin} !")

        # Empêche l'envoi multiple
        last_bump_time = None
        await asyncio.sleep(5)


# =======================
# MESSAGE / BUMP
# =======================
@bot.event
async def on_message(message):
    global last_bump_time

    if not message.author.bot and hasattr(message.author, "roles"):
        if any(role.id in [OWNER_ROLE_ID] for role in message.author.roles):
            if "/bump" in message.content.lower():
                last_bump_time = datetime.now()
                print("Bump détecté, timer relancé.")

    await bot.process_commands(message)


# =======================
# Lancement
# =======================
bot.run(TOKEN)

