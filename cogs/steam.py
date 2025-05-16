# cogs/steam.py

import discord
from discord.ext import commands
from discord.ui import Button, View

class SteamButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(
            label="🎮 Se connecter au serveur",
            url="https://pipoyd.github.io/bot-mille-voiles/steam_page.html"
        ))

class Steam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serveur")
    @commands.has_permissions(administrator=True)
    async def serveur(self, ctx):
        await ctx.message.delete()
        embed = discord.Embed(
            title="<:equipage:1358154724423106781> Ouverture du Serveur One Piece",
            description="Le serveur est **ouvert** !\nClique sur le bouton ci-dessous pour te connecter.",
            color=0xff0000
        )
        await ctx.send(content="@everyone", embed=embed, view=SteamButtonView())

async def setup(bot):
    await bot.add_cog(Steam(bot))
