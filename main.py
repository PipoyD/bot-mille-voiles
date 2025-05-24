# main.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
from aiohttp import web

# Charger les variables d'environnement depuis .env
load_dotenv()
TOKEN = os.getenv("TOKEN")
# ID du canal où republier les embeds reçus via webhook
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

# Intents Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot Discord
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Chargement automatique des cogs
async def load_all_cogs():
    cogs_path = os.path.join(os.path.dirname(__file__), "cogs")
    for filename in os.listdir(cogs_path):
        if filename.endswith(".py") and filename != "__init__.py":
            name = filename[:-3]
            try:
                await bot.load_extension(f"cogs.{name}")
                print(f"✔️  Cog chargé : {name}")
            except Exception as e:
                print(f"❌ Erreur chargement Cog {name} :", e)

# Handler HTTP pour recevoir les POST du webhook Discord source
async def handle_webhook(request):
    data = await request.json()
    embeds = data.get("embeds", [])
    if embeds:
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        if channel:
            for e in embeds:
                # Reposter chaque embed dans le canal cible
                await channel.send(embed=discord.Embed.from_dict(e))
    return web.Response(status=204)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    # Affichage des commandes disponibles
    cmds = sorted(c.name for c in bot.commands)
    print("⚙️  Commandes disponibles :", ", ".join(cmds) if cmds else "(aucune)")

    # Démarrage du serveur HTTP intégré pour /webhook-source
    app = web.Application()
    app.router.add_post("/webhook-source", handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ HTTP server listening on 0.0.0.0:{port}")

# Point d'entrée principal
async def main():
    await load_all_cogs()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
