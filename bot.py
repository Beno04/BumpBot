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
PROBOT_ID = 282859044593598464

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler_started = False
last_bump_time = None
top_pending = False  # Pour savoir si on attend ProBot

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

    global last_bump_time, top_pending

    while True:
        if last_bump_time is None:
            await asyncio.sleep(5)
            continue

        next_run = last_bump_time + timedelta(minutes=2)
        now = datetime.now()
        wait_seconds = (next_run - now).total_seconds()

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        # Envoi du rappel uniquement si le /top a été confirmé ou en attente
        await channel.send(f"⏰ N’oubliez pas de faire **/bump** <@&{OWNER_ROLE_ID}> !")

        # On reset pour ne pas spam
        last_bump_time = None
        top_pending = False
        await asyncio.sleep(5)

# =======================
# MESSAGE / BUMP
# =======================
@bot.event
async def on_message(message):
    global last_bump_time, top_pending

    # On ignore les messages du bot lui-même
    if message.author.id == bot.user.id:
        await bot.process_commands(message)
        return

    # ========== CAS 1 : UN OWNER ENVOIE LA COMMANDE /top ==========
    if message.content.startswith("/top"):
        channel = bot.get_channel(CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title="⏳ Timer lancé",
                description="Le bot attend la réponse de **ProBot**...\n"
                            "Le rappel sera envoyé **2 minutes après** la confirmation.",
                color=0x5865F2
            )
            embed.set_footer(text="En attente du résultat du /top")
            await channel.send(embed=embed)

            # On met le timer en attente
            last_bump_time = datetime.now()
            top_pending = True

    # ========== CAS 2 : PROBOT ENVOIE SON RÉSULTAT ==========
    if message.author.id == PROBOT_ID:
        if message.embeds:
            embed = message.embeds[0]
            title = (embed.title or "").lower()
            description = (embed.description or "").lower()
            if any(keyword in title for keyword in ["top", "rank", "invite"]) or \
               any(keyword in description for keyword in ["top", "rank", "invite"]):
                print("✔ ProBot a confirmé le /top, timer mis à jour.")
                last_bump_time = datetime.now()
                top_pending = False

                # Supprime l'ancien rappel
                channel = message.channel
                if isinstance(channel, discord.TextChannel):
                    async for msg in channel.history(limit=50):
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
    global last_bump_time, top_pending

    if last_bump_time is None:
        embed = discord.Embed(
            title="📊 Statut du Bot",
            description="Aucun `/top` n'a encore été détecté.",
            color=0xED4245
        )
        embed.add_field(name="État", value="🔴 Inactif")
        await ctx.send(embed=embed)
        return

    now = datetime.now()
    elapsed = now - last_bump_time
    seconds = int(elapsed.total_seconds())
    remaining = max(0, 120 - seconds)  # 2 min = 120 sec

    embed = discord.Embed(
        title="📊 Statut du Bot",
        color=0xFEE75C if top_pending else 0x57F287
    )
    embed.add_field(name="Dernier /top détecté il y a :", value=f"{seconds} secondes", inline=False)
    embed.add_field(name="Temps avant le prochain rappel :", value=f"{remaining} secondes", inline=False)
    embed.add_field(name="État :", value="🟡 En attente de confirmation ProBot" if top_pending else "🟢 Prêt pour le prochain /top")

    embed.set_footer(text="Utilisez /top avec ProBot pour relancer le timer")
    await ctx.send(embed=embed)

# =======================
# Lancement
# =======================
bot.run(TOKEN)
