from discord.ext import commands
import discord

def setup_help_command(bot):
    @bot.command(name="help")
    async def help_command(ctx):
        await ctx.message.delete()
        embed = discord.Embed(
            title="📖 Aide du Bot",
            description="Voici la liste des commandes disponibles :",
            color=0x3498db
        )
        embed.add_field(name="📋 !recrutement *(Admin)*", value="Afficher le formulaire", inline=False)
        embed.add_field(name="⚓ !flottes *(Admin)*", value="Afficher la composition des flottes", inline=False)
        embed.add_field(name="📦 !coffre", value="Voir les emplacements de coffres", inline=False)
        embed.add_field(name="🎮 !serveur *(Admin)*", value="Annoncer l'ouverture du serveur", inline=False)
        embed.add_field(name="❓ !help", value="Afficher ce message", inline=False)
        embed.set_footer(text="Disparaît dans 5 min ⏳")
        await ctx.send(embed=embed, delete_after=300)
