# main.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    print("⚙️  Commandes disponibles :", ", ".join(sorted([c.name for c in bot.commands])))

# --- Chargement automatique des Cogs ---
cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
for filename in os.listdir(cogs_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        cog_name = filename[:-3]
        try:
            bot.load_extension(f"cogs.{cog_name}")
            print(f"✔️  Cog chargé : {cog_name}")
        except Exception as e:
            print(f"❌ Erreur chargement du cog {cog_name} : {e}")

if __name__ == "__main__":
    bot.run(TOKEN)
