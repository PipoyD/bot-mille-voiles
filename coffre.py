import discord
from discord.ext import commands

RECRUTEUR_ROLE_ID = 1317850709948891177

ILE_COFFRES = {
    "Logue Town": [
        {"desc": "Derrière Fushia News", "img": "https://i.imgur.com/BaLuctc.png"},
        {"desc": "Rue à droite en face de la Mairie", "img": "https://i.imgur.com/Ls3L6H2.png"},
        {"desc": "Batiment collé à gauche du QG Marine", "img": "https://i.imgur.com/UHVFxLY.png"},
        {"desc": "Derrière la Mairie", "img": "https://i.imgur.com/zMKd2ts.png"},
        {"desc": "Batiment à droite de la Banque entre la falaise", "img": "https://i.imgur.com/HMmEMpW.png"},
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

class CoffreNavigationView(discord.ui.View):
    def __init__(self, ile, index, interaction_user_id):
        super().__init__(timeout=600)
        self.ile = ile
        self.index = index
        self.interaction_user_id = interaction_user_id
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user.id != self.interaction_user_id:
            await interaction.response.send_message("🚫 Ce menu ne t'est pas destiné.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass

    @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(ILE_COFFRES[self.ile])
        await self.update_embed(interaction)

    @discord.ui.button(label="➡️ Suivant", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(ILE_COFFRES[self.ile])
        await self.update_embed(interaction)

    async def update_embed(self, interaction):
        emplacement = ILE_COFFRES[self.ile][self.index]
        embed = discord.Embed(
            title=f"📦 Emplacement du coffre ({self.ile})",
            description=emplacement["desc"],
            color=0xFFD700
        )
        embed.set_image(url=emplacement["img"])
        await interaction.response.edit_message(embed=embed, view=self)

class IleSelect(discord.ui.Select):
    def __init__(self, user_id):
        options = [discord.SelectOption(label=ile, description=f"Voir les coffres de {ile}") for ile in ILE_COFFRES]
        super().__init__(placeholder="Choisis une île", options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("🚫 Ce menu ne t'est pas destiné.", ephemeral=True)
            return

        ile = self.values[0]
        index = 0
        view = CoffreNavigationView(ile, index, interaction.user.id)
        emplacement = ILE_COFFRES[ile][index]
        embed = discord.Embed(
            title=f"📦 Emplacement du coffre ({ile})",
            description=emplacement["desc"],
            color=0xFFD700
        )
        embed.set_footer(text="⏳ Suppression dans 10 min")
        embed.set_image(url=emplacement["img"])
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = await interaction.original_response()

class IleSelectView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.add_item(IleSelect(user_id))

async def setup_coffres(bot):
    @bot.command()
    async def coffre(ctx):
        await ctx.message.delete()
        if not any(role.id == RECRUTEUR_ROLE_ID for role in ctx.author.roles):
            await ctx.send("🚫 Tu n'as pas accès à cette commande.", delete_after=10)
            return

        embed = discord.Embed(
            title="🌴 Choix de l'île",
            description="Sur quelle île veux-tu voir les emplacements de coffre ?",
            color=0x00bfff
        )
        embed.set_footer(text="⏳ Suppression automatique dans 10 min")
        await ctx.send(embed=embed, view=IleSelectView(ctx.author.id), delete_after=600)

