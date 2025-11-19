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
DISBOARD_ID = 302050872383242240

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler_started = False
last_bump_time = None

# =======================
# READY
# =======================
@bot.event
async def on_ready():
    global scheduler_started
    print(f"Connecté en tant que {bot.user}")

    if not scheduler_started:
        print("Lancement du scheduler bump...")
        scheduler_started = True
        bot.loop.create_task(bump_scheduler())
    else:
        print("Scheduler déjà actif, ignoré.")

# =======================
# SCHEDULER
# =======================
async def bump_scheduler():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        print("Erreur channel invalide.")
        return

    global last_bump_time

    while True:
        if last_bump_time is None:
            await asyncio.sleep(5)
            continue

        next_run = last_bump_time + timedelta(minutes=2)
        now = datetime.now()
        wait_seconds = (next_run - now).total_seconds()

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        # Envoi du rappel
        await channel.send(f"⏰ N’oubliez pas de faire **/bump** <@&{OWNER_ROLE_ID}> !")

        # Reset après envoi
        last_bump_time = None
        await asyncio.sleep(5)

# =======================
# MESSAGE / BUMP
# =======================
@bot.event
async def on_message(message):
    global last_bump_time

    # Ignorer les messages du bot lui-même
    if message.author.id == bot.user.id:
        await bot.process_commands(message)
        return

    # CAS : DISBOARD ENVOIE UN MESSAGE DANS LE SALON
    if message.author.id == DISBOARD_ID and message.channel.id == CHANNEL_ID:
        last_bump_time = datetime.now()
        print("✔ Disboard a bump, timer démarré !")

        # Supprimer d'éventuels anciens rappels
        if isinstance(message.channel, discord.TextChannel):
            async for msg in message.channel.history(limit=50):
                if msg.author == bot.user and "n’oubliez pas de faire" in msg.content.lower():
                    try:
                        await msg.delete()
                    except:
                        pass
                    break

    await bot.process_commands(message)

# =======================
# STATUS COMMAND
# =======================
@bot.command()
async def status(ctx):
    global last_bump_time

    if last_bump_time is None:
        embed = discord.Embed(
            title="📊 Statut du Bot",
            description="Aucun bump n'a encore été détecté.",
            color=0xED4245
        )
        embed.add_field(name="État", value="🔴 Inactif")
        await ctx.send(embed=embed)
        return

    now = datetime.now()
    elapsed = now - last_bump_time
    seconds = int(elapsed.total_seconds())
    remaining = max(0, 120 - seconds)

    embed = discord.Embed(
        title="📊 Statut du Bot",
        color=0x57F287
    )
    embed.add_field(name="Dernier bump détecté il y a :", value=f"{seconds} secondes", inline=False)
    embed.add_field(name="Temps avant le prochain rappel :", value=f"{remaining} secondes", inline=False)
    embed.add_field(name="État :", value="🟢 Prêt pour le prochain rappel")

    embed.set_footer(text="Le timer se déclenche automatiquement à l'envoi de Disboard")
    await ctx.send(embed=embed)

# =======================
# Lancement
# =======================
bot.run(TOKEN)
