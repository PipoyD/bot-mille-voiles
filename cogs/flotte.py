# cogs/flotte.py

import pytz
from datetime import datetime

import discord
from discord import Embed
from discord.ext import commands
from discord.ui import View, Button

# Identifiants des rôles
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

def build_flotte_embed(guild: discord.Guild) -> Embed:
    """Construit et retourne l'Embed de la composition des flottes."""
    membres_equipage = [
        m for m in guild.members
        if any(r.id == ROLES["MEMBRE"] for r in m.roles) and not m.bot
    ]

    embed = Embed(
        title="⚓ • Équipage : Les Mille Voiles • ⚓",
        description=f"**Effectif total :** {len(membres_equipage)} membres",
        color=0xFFA500
    )

    déjà_affichés = set()

    def filter_unique(role_id, flotte_id=None):
        return [
            m for m in guild.members
            if any(r.id == role_id for r in m.roles)
            and (not flotte_id or any(r.id == flotte_id for r in m.roles))
        ]

    def filtrer(role_id, flotte_id=None):
        result = []
        for m in filter_unique(role_id, flotte_id):
            if m.id not in déjà_affichés:
                déjà_affichés.add(m.id)
                result.append(m.mention)
        return result or ["N/A"]

    # Capitainerie
    embed.add_field(
        name="<:equipage:1358154724423106781> __** Capitainerie :**__",
        value=(
            f"👑 **Capitaine :** {filtrer(ROLES['CAPITAINE'])[0]}\n"
            f"🗡️ **Vice-Capitaine :** {filtrer(ROLES['VICE_CAPITAINE'])[0]}"
        ),
        inline=False
    )

    # 1ère Flotte – Écarlate
    embed.add_field(
        name="<:2meflotte:1372158586951696455> __**1ère Flotte : La Voile Écarlate**__",
        value="",
        inline=False
    )
    embed.add_field(
        name="🛡️ Commandant :",
        value="\n".join(filtrer(ROLES["COMMANDANT"], ROLES["ECARLATE"])),
        inline=False
    )
    embed.add_field(
        name="🗡️ Vice-Commandant :",
        value="\n".join(filtrer(ROLES["VICE_COMMANDANT"], ROLES["ECARLATE"])),
        inline=False
    )
    embed.add_field(
        name="🎖️ Lieutenants :",
        value="\n".join(filtrer(ROLES["LIEUTENANT"], ROLES["ECARLATE"])),
        inline=False
    )
    embed.add_field(
        name="👥 Membres :",
        value="\n".join(filtrer(ROLES["MEMBRE"], ROLES["ECARLATE"])),
        inline=False
    )

    # 2ème Flotte – Azur
    embed.add_field(
        name="<:1reflotte:1372158546531324004> __**2ème Flotte : La Voile d'Azur**__",
        value="",
        inline=False
    )
    embed.add_field(
        name="🛡️ Commandant :",
        value="\n".join(filtrer(ROLES["COMMANDANT"], ROLES["AZUR"])),
        inline=False
    )
    embed.add_field(
        name="🗡️ Vice-Commandant :",
        value="\n".join(filtrer(ROLES["VICE_COMMANDANT"], ROLES["AZUR"])),
        inline=False
    )
    embed.add_field(
        name="🎖️ Lieutenants :",
        value="\n".join(filtrer(ROLES["LIEUTENANT"], ROLES["AZUR"])),
        inline=False
    )
    embed.add_field(
        name="👥 Membres :",
        value="\n".join(filtrer(ROLES["MEMBRE"], ROLES["AZUR"])),
        inline=False
    )

    # Sans flotte
    embed.add_field(name="__**Sans Flotte**__", value="", inline=False)
    embed.add_field(
        name="🎖️ Lieutenants :",
        value="\n".join(filtrer(ROLES["LIEUTENANT"])),
        inline=False
    )

    def membres_sans_flotte():
        rest = []
        for m in guild.members:
            if m.id in déjà_affichés:
                continue
            ids = [r.id for r in m.roles]
            if ROLES["MEMBRE"] in ids and all(r not in ROLES.values() or r == ROLES["MEMBRE"] for r in ids):
                rest.append(m.mention)
        return rest or ["N/A"]

    embed.add_field(
        name="👥 Membres :",
        value="\n".join(membres_sans_flotte()),
        inline=False
    )

    embed.set_thumbnail(url="https://i.imgur.com/w0G8DCx.png")
    embed.set_image(url="https://i.imgur.com/tqrOqYS.jpeg")
    paris = pytz.timezone("Europe/Paris")
    now = datetime.now(paris).strftime("Dernière mise à jour : %d/%m/%Y à %H:%M")
    embed.set_footer(text=now)

    return embed


class FlotteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_flotte")
    async def refresh(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("🚫 Réservé aux administrateurs.", ephemeral=True)

        new_embed = build_flotte_embed(interaction.guild)
        await interaction.message.edit(embed=new_embed, view=self)
        await interaction.response.send_message("✅ Liste actualisée.", ephemeral=True)


class Flotte(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(FlotteView())

    @commands.command(name="flottes")
    @commands.has_permissions(administrator=True)
    async def flottes(self, ctx: commands.Context):
        await ctx.message.delete()
        embed = build_flotte_embed(ctx.guild)
        await ctx.send(embed=embed, view=FlotteView())


def setup(bot: commands.Bot):
    bot.add_cog(Flotte(bot))
