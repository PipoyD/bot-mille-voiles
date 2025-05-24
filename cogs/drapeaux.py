import discord
from discord.ext import commands

class EmbedRelay(commands.Cog):
    # ID du canal source (départ) et du canal de destination (arrivée)
    SOURCE_CHANNEL_ID = 1375224459039998023
    TARGET_CHANNEL_ID = 1358162871585996822

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignorer les messages du bot lui-même et tous les canaux non sources
        if message.author.bot:
            return
        if message.channel.id != self.SOURCE_CHANNEL_ID:
            return

        # S’il y a au moins un embed, on le renvoie
        if message.embeds:
            target = self.bot.get_channel(self.TARGET_CHANNEL_ID)
            if target:
                for embed in message.embeds:
                    # Reconstruire proprement l’embed pour Discord.py
                    new_embed = discord.Embed.from_dict(embed.to_dict())
                    await target.send(embed=new_embed)
            else:
                # En cas de mauvais ID ou absence de permissions
                print(f"Impossible de trouver le canal cible {self.TARGET_CHANNEL_ID}")

def setup(bot: commands.Bot):
    bot.add_cog(EmbedRelay(bot))
