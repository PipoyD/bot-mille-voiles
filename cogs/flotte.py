import pytz
from datetime import datetime

import discord
from discord import Embed
from discord.ext import commands
from discord.ui import View, Button

ROLES = {
    "CAPITAINE":       1317851007358734396,
    "VICE_CAPITAINE":  1358079100203569152,
    "COMMANDANT":      1358031308542181382,
    "VICE_COMMANDANT": 1358032259596288093,
    "LIEUTENANT":      1358030829225381908,
    "MEMBRE":          1317850709948891177,
    "ECARLATE":        1371942480316203018,
    "AZUR":            1371942559894736916,
}

def build_flotte_embed(guild):
    # recopier ici intégralement ta fonction build_flotte_embed
    # … (inchangé) …
    embed = Embed(
        title="⚓ • Équipage : Les Mille Voiles • ⚓",
        description=f"**Effectif total :** {sum(1 for m in guild.members if not m.bot and any(r.id==ROLES['MEMBRE'] for r in m.roles))} membres",
        color=0xFFA500
    )
    # … champs, images & footer …
    return embed

class FlotteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @Button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_flotte")
    async def refresh(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("🚫 Réservé aux administrateurs.", ephemeral=True)
        await interaction.message.edit(embed=build_flotte_embed(interaction.guild), view=self)
        await interaction.response.send_message("✅ Liste actualisée.", ephemeral=True)

class Flotte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(FlotteView())

    @commands.command(name="flottes")
    @commands.has_permissions(administrator=True)
    async def flottes(self, ctx):
        await ctx.message.delete()
        await ctx.send(embed=build_flotte_embed(ctx.guild), view=FlotteView())

def setup(bot):
    bot.add_cog(Flotte(bot))
