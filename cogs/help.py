import discord
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Désactive la commande help par défaut
        bot.help_command = None

    @commands.command(name="help")
    async def help_command(self, ctx):
        # Supprime la commande de l'utilisateur pour garder le chat propre
        await ctx.message.delete()

        embed = discord.Embed(
            title="📖 Aide du Bot",
            description="Voici la liste des commandes disponibles :",
            color=0x3498db
        )

        # ⬇️ Commandes administrateur ⬇️
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
            name="📜 !primes *(Admin)*",
            value="Scrape les primes depuis GitBook et affiche l’embed avec bouton Actualiser.",
            inline=False
        )
        embed.add_field(
            name="🧹 !clearprimes *(Admin)*",
            value="Vide entièrement la table des primes en base.",
            inline=False
        )

        # ⬇️ Commandes tout public ⬇️
        embed.add_field(
            name="📦 !coffre",
            value="Voir les emplacements de coffres.",
            inline=False
        )
        embed.add_field(
            name="💰 !prime",
            value="Affiche votre prime RP.",
            inline=False
        )
        embed.add_field(
            name="❓ !help",
            value="Affiche ce message d’aide.",
            inline=False
        )

        embed.set_footer(text="Ce message disparaîtra automatiquement dans 5 minutes ⏳")

        # Envoi de l'embed avec suppression auto après 5 minutes
        await ctx.send(embed=embed, delete_after=300)

async def setup(bot):
    await bot.add_cog(Help(bot))
