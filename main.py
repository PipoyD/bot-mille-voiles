import os
import discord
from discord.ext import commands

from recrutement import setup_recrutement
from flotte import setup_flotte
from coffre import setup_coffres
from steam import setup_steam_button
from help import setup_help

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    await setup_recrutement()
    await setup_flotte()
    await setup_coffres()
    setup_steam_button()
    setup_help()

token = os.getenv("TOKEN")
if not token:
    print("❌ Token manquant dans les variables d'environnement.")
else:
    bot.run(token)
