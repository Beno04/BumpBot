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
CHANNEL_ID = 1430468986558091277
ADMIN_ROLE_ID = 1430468984343363739
DISBOARD_ID = 302050872383242240

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler_started = False
last_bump_time = None

# =======================
# Formatage du temps
# =======================
def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# =======================
# Barre de progression
# =======================
def progress_bar(current, total, size=20):
    ratio = current / total
    filled = int(ratio * size)
    empty = size - filled
    percent = int(ratio * 100)
    return f"[{'█'*filled}{'░'*empty}] {percent}%"

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
# SCHEDULER (2h) + restriction 00h–08h
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

        next_run = last_bump_time + timedelta(hours=2)
        now = datetime.now()
        wait_seconds = (next_run - now).total_seconds()

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        # 🔒 Restriction : pas de messages entre 00h00 et 08h00
        now = datetime.now()
        if 11 <= now.hour < 13 :
            print("⏸ Rappel retardé (entre 00h et 08h). Envoi à 08h00.")
            next_morning = now.replace(hour=13, minute=0, second=0, microsecond=0)
            wait_more = (next_morning - now).total_seconds()
            if wait_more > 0:
                await asyncio.sleep(wait_more)

        # Envoi du rappel
        await channel.send(f"⏰ N’oubliez pas de faire **/bump** <@&{ADMIN_ROLE_ID}> !")

        # Reset
        last_bump_time = None
        await asyncio.sleep(5)

# =======================
# MESSAGE / BUMP
# =======================
@bot.event
async def on_message(message):
    global last_bump_time

    # Ignorer le bot
    if message.author.id == bot.user.id:
        await bot.process_commands(message)
        return

    # Détection du bump Disboard
    if message.author.id == DISBOARD_ID and message.channel.id == CHANNEL_ID:
        last_bump_time = datetime.now()
        print("✔ Disboard a bump, timer démarré !")

        # Supprimer anciens rappels
        async for msg in message.channel.history(limit=50):
            if msg.author == bot.user and "bump" in msg.content.lower():
                try:
                    await msg.delete()
                except:
                    pass
                break

    await bot.process_commands(message)

# =======================
# Commande STATUS
# =======================
@bot.command()
async def status(ctx):
    global last_bump_time

    now = datetime.now()

    # AUCUN BUMP ENREGISTRÉ
    if last_bump_time is None:
        embed = discord.Embed(
            title="📊 Statut du Bot",
            description="Aucun bump n'a encore été détecté.",
            color=0xED4245
        )
        embed.add_field(name="État", value="🔴 Inactif")
        await ctx.send(embed=embed)
        return

    elapsed = int((now - last_bump_time).total_seconds())
    TOTAL = 7200  # 2h
    remaining = max(0, TOTAL - elapsed)

    embed = discord.Embed(
        title="📊 Statut du Bot",
        color=0x57F287
    )

    embed.add_field(
        name="⏱ Dernier bump :",
        value=f"Il y a **{format_time(elapsed)}**",
        inline=False
    )

    embed.add_field(
        name="⌛ Temps restant :",
        value=f"**{format_time(remaining)}**",
        inline=False
    )

    embed.add_field(
        name="📉 Progression :",
        value=progress_bar(elapsed, TOTAL),
        inline=False
    )

    # ==========================
    # 🟡 CAS SPÉCIAL : INTERRUPTION
    # ==========================
    if remaining <= 0 and (0 <= now.hour < 8):
        state_text = "🟡 Interruption de service (00h–08h)"
        note_text = "Le rappel sera automatiquement envoyé à **08h00**."
    else:
        state_text = "🟢 Timer en cours" if remaining > 0 else "🟢 Prêt pour un nouveau bump"
        note_text = "Le timer se déclenche automatiquement quand Disboard confirme /bump"

    embed.add_field(name="État :", value=state_text)
    embed.set_footer(text=note_text)

    await ctx.send(embed=embed)

# =======================
# Lancement
# =======================
bot.run(TOKEN)


