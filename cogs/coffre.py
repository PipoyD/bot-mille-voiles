import discord
from discord.ext import commands
from discord.ui import View, Select, Button
from discord import Embed

RECRUTEUR_ROLE_ID = 1317850709948891177

ILE_COFFRES = {
    "Logue Town": [
        {"desc": "Derrière Fushia News", "img": "https://i.imgur.com/BaLuctc.png"},
        # … reste des emplacements …
    ],
    # … autres îles …
}

class CoffreNavigationView(View):
    def __init__(self, ile, index, user_id):
        super().__init__(timeout=600)
        self.ile = ile
        self.index = index
        self.user_id = user_id
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("🚫 Ce menu ne t'est pas destiné.", ephemeral=True)
            return False
        return True

    @Button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        self.index = (self.index - 1) % len(ILE_COFFRES[self.ile])
        await self._update(interaction)

    @Button(label="➡️ Suivant", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        self.index = (self.index + 1) % len(ILE_COFFRES[self.ile])
        await self._update(interaction)

    async def _update(self, interaction):
        em = ILE_COFFRES[self.ile][self.index]
        embed = Embed(title=f"📦 Coffre ({self.ile})", description=em["desc"], color=0xFFD700)
        embed.set_image(url=em["img"])
        await interaction.response.edit_message(embed=embed, view=self)

class IleSelect(Select):
    def __init__(self, user_id):
        options = [
            discord.SelectOption(label=ile, description=f"Voir coffres de {ile}")
            for ile in ILE_COFFRES.keys()
        ]
        super().__init__(placeholder="Choisis une île", options=options)
        self.user_id = user_id

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🚫 Ce menu ne t'est pas destiné.", ephemeral=True)
        ile = self.values[0]
        view = CoffreNavigationView(ile, 0, self.user_id)
        em = ILE_COFFRES[ile][0]
        embed = Embed(title=f"📦 Coffre ({ile})", description=em["desc"], color=0xFFD700)
        embed.set_footer(text="Suppression dans 10 min")
        embed.set_image(url=em["img"])
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = await interaction.original_response()

class Coffre(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="coffre")
    async def coffre(self, ctx):
        await ctx.message.delete()
        if not any(r.id == RECRUTEUR_ROLE_ID for r in ctx.author.roles):
            return await ctx.send("🚫 Pas accès", delete_after=10)
        embed = Embed(
            title="🌴 Choix de l'île",
            description="Sur quelle île veux-tu voir les coffres ?",
            color=0x00bfff
        )
        embed.set_footer(text="Suppression auto 10 min")
        await ctx.send(embed=embed, view=View().add_item(IleSelect(ctx.author.id)), delete_after=600)

def setup(bot):
    bot.add_cog(Coffre(bot))
