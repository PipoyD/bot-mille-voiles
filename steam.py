from discord.ext import commands
from discord.ui import Button, View
import discord

def setup_steam_button(bot):
    class SteamButtonView(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(Button(label="🎮 Se connecter au serveur", url="https://pipoyd.github.io/bot-mille-voiles/steam_page.html"))

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def serveur(ctx):
        await ctx.message.delete()
        embed = discord.Embed(
            title="🌊 Ouverture du Serveur One Piece",
            description="Le serveur est **ouvert** ! Clique sur le bouton ci-dessous pour te connecter.",
            color=0xff0000
        )
        await ctx.send(content="@everyone", embed=embed, view=SteamButtonView())
