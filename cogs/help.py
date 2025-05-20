import discord
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        # on supprime la commande de l'utilisateur
        await ctx.message.delete()

        embed = discord.Embed(
            title="📖 Aide du Bot",
            description="Voici la liste des commandes disponibles :",
            color=0x3498db
        )
        # utilisation de name= et value= obligatoires
        embed.add_field(
            name="📋 !recrutement *(Admin)*",
            value="Formulaire de recrutement.",
            inline=False
        )
        embed.add_field(
            name="⚓ !flottes *(Admin)*",
            value="Composition des flottes.",
            inline=False
        )
        embed.add_field(
            name="🎮 !serveur *(Admin)*",
            value="Annonce ouverture serveur.",
            inline=False
        )
        embed.add_field(
            name="📦 !coffre",
            value="Voir les emplacements de coffres.",
            inline=False
        )
        embed.add_field(
            name="❓ !help",
            value="Affiche ce message.",
            inline=False
        )
        embed.set_footer(text="Ce message disparaîtra automatiquement dans 5 minutes ⏳")

        # envoi de l'embed avec suppression automatique
        await ctx.send(embed=embed, delete_after=300)

async def setup(bot):
    # si tu n'as pas déjà désactivé la commande help par défaut :
    # bot.help_command = None
    await bot.add_cog(Help(bot))
