# cogs/coffre.py

import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Select
from discord import Embed

RECRUTEUR_ROLE_ID = 1317850709948891177

ILE_COFFRES = {
    "Logue Town": [
        {"desc": "Derrière Fushia News", "img": "https://i.imgur.com/BaLuctc.png"},
        {"desc": "Rue à droite en face de la Mairie", "img": "https://i.imgur.com/Ls3L6H2.png"},
        {"desc": "Bâtiment collé à gauche du QG Marine", "img": "https://i.imgur.com/UHVFxLY.png"},
        {"desc": "Derrière la Mairie", "img": "https://i.imgur.com/zMKd2ts.png"},
        {"desc": "Bâtiment à droite de la Banque entre la falaise", "img": "https://i.imgur.com/HMmEMpW.png"},
        {"desc": "Ruelle diagonale à droite du bar", "img": "https://i.imgur.com/WHcRTW2.png"},
        {"desc": "Maison du Phare", "img": "https://i.imgur.com/vvKqaX3.png"},
    ],
    "Arlong Park": [
        {"desc": "Sous le pont cassé", "img": "https://example.com/image1.jpg"},
        {"desc": "Derrière la statue de requin", "img": "https://example.com/image2.jpg"},
        {"desc": "Dans la cabane du chef", "img": "https://example.com/image3.jpg"},
    ],
    "Fushia": [
        {"desc": "Près du bar de Makino", "img": "https://example.com/image4.jpg"},
        {"desc": "Derrière le moulin", "img": "https://example.com/image5.jpg"},
        {"desc": "Sous le vieux chêne", "img": "https://example.com/image6.jpg"},
    ]
}

class CoffreNavigationView(View):
    def __init__(self, ile: str, index: int, user_id: int):
        super().__init__(timeout=None)
        self.ile = ile
        self.index = index
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("🚫 Ce menu ne t'est pas destiné.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(ILE_COFFRES[self.ile])
        await self._update(interaction)

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(ILE_COFFRES[self.ile])
        await self._update(interaction)

    async def _update(self, interaction: discord.Interaction):
        emplacement = ILE_COFFRES[self.ile][self.index]
        embed = Embed(
            title=f"📦 Emplacement du coffre ({self.ile})",
            description=emplacement["desc"],
            color=0xFFD700
        )
        embed.set_image(url=emplacement["img"])
        await interaction.response.edit_message(embed=embed, view=self)
        # Schedule deletion in 10 minutes
        asyncio.create_task(self._auto_delete(interaction.message))

    async def _auto_delete(self, message: discord.Message):
        await asyncio.sleep(600)
        try:
            await message.delete()
        except discord.NotFound:
            pass


class IleSelect(Select):
    def __init__(self, user_id: int):
        options = [
            discord.SelectOption(label=ile, description=f"Voir les coffres de {ile}")
            for ile in ILE_COFFRES.keys()
        ]
        super().__init__(placeholder="Choisis une île", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🚫 Ce menu ne t'est pas destiné.", ephemeral=True)

        ile = self.values[0]
        view = CoffreNavigationView(ile, 0, self.user_id)
        emplacement = ILE_COFFRES[ile][0]
        embed = Embed(
            title=f"📦 Emplacement du coffre ({ile})",
            description=emplacement["desc"],
            color=0xFFD700
        )
        embed.set_footer(text="⏳ Ce message sera supprimé dans 10 minutes")
        embed.set_image(url=emplacement["img"])
        await interaction.response.edit_message(embed=embed, view=view)
        # Schedule deletion in 10 minutes
        asyncio.create_task(view._auto_delete(interaction.message))


class IleSelectView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.add_item(IleSelect(user_id))


class Coffre(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="coffre")
    async def coffre(self, ctx: commands.Context):
        await ctx.message.delete()
        if not any(r.id == RECRUTEUR_ROLE_ID for r in ctx.author.roles):
            return await ctx.send("🚫 Pas accès à cette commande.", delete_after=10)

        embed = Embed(
            title="🌴 Choix de l'île",
            description="Sur quelle île veux-tu voir les emplacements de coffre ?",
            color=0x00BFFF
        )
        embed.set_footer(text="⏳ Ce message sera supprimé dans 10 minutes")

        view = IleSelectView(ctx.author.id)
        message = await ctx.send(embed=embed, view=view)
        # Schedule deletion of the initial embed in 10 minutes
        asyncio.create_task(self._auto_delete(message))

    async def _auto_delete(self, message: discord.Message):
        await asyncio.sleep(600)
        try:
            await message.delete()
        except discord.NotFound:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Coffre(bot))
