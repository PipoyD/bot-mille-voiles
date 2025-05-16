# main.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()  # lit TOKEN dans .env
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- Chargement automatique des Cogs ---
cogs_path = os.path.join(os.path.dirname(__file__), "cogs")
for filename in os.listdir(cogs_path):
    if filename.endswith(".py") and filename != "__init__.py":
        name = filename[:-3]
        try:
            bot.load_extension(f"cogs.{name}")
            print(f"✔️  Cog chargé : {name}")
        except Exception as e:
            print(f"❌ Erreur chargement Cog {name} :", e)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    cmds = sorted(c.name for c in bot.commands)
    print("⚙️  Commandes disponibles :", ", ".join(cmds) or "(aucune)")

if __name__ == "__main__":
    bot.run(TOKEN)
