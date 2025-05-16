import discord
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        await ctx.message.delete()
        embed = discord.Embed(
            title="📖 Aide du Bot",
            description="Voici la liste des commandes disponibles :",
            color=0x3498db
        )
        embed.add_field("📋 !recrutement *(Admin)*", "Formulaire de recrutement.", inline=False)
        embed.add_field("⚓ !flottes *(Admin)*",   "Composition des flottes.", inline=False)
        embed.add_field("🎮 !serveur *(Admin)*",   "Annonce ouverture serveur.", inline=False)
        embed.add_field("📦 !coffre",              "Voir les emplacements de coffres.", inline=False)
        embed.add_field("❓ !help",                "Affiche ce message.", inline=False)
        embed.set_footer(text="Ce message disparaîtra automatiquement dans 5 minutes ⏳")
        await ctx.send(embed=embed, delete_after=300)

def setup(bot):
    bot.add_cog(Help(bot))
