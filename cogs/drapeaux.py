import discord
from discord.ext import commands
from aiohttp import web
import asyncio

# === CONFIGURATION ===
SOURCE_CHANNEL_ID = 1375224459039998023  # ID d'un canal Discord à écouter (si bot dans les 2 serveurs)
TARGET_CHANNEL_ID = 1358162871585996822  # ID du canal cible de ton serveur
WEBHOOK_PORT = 8080  # Port d'écoute HTTP pour les requêtes entrantes externes

class RelayFilter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # --- Serveur Web aiohttp ---
        self.app = web.Application()
        self.app.router.add_post("/relay", self.handle_webhook_post)
        self.runner = web.AppRunner(self.app)
        self.bot.loop.create_task(self.start_webserver())

    async def start_webserver(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', WEBHOOK_PORT)
        await site.start()
        print(f"[RelayFilter] Webhook actif sur le port {WEBHOOK_PORT}")

    async def handle_webhook_post(self, request):
        try:
            data = await request.json()
            content = data.get("content")

            # --- Filtrage custom ---
            if not content or "banni" in content.lower():
                return web.Response(status=400, text="Message refusé (vide ou interdit)")

            target = self.bot.get_channel(TARGET_CHANNEL_ID)
            if target:
                await target.send(f"🌐 Webhook : {content}")
                return web.Response(status=200, text="Message relayé")
            else:
                return web.Response(status=404, text="Canal introuvable")

        except Exception as e:
            return web.Response(status=500, text=f"Erreur serveur : {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.channel.id == SOURCE_CHANNEL_ID:
            if "interdit" in message.content.lower():
                return  # filtre simple par mot clé

            target = self.bot.get_channel(TARGET_CHANNEL_ID)
            if target:
                await target.send(f"📨 {message.author.display_name} : {message.content}")

async def setup(bot):
    await bot.add_cog(RelayFilter(bot))
