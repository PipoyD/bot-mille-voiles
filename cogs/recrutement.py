# cogs/recrutement.py

import os
import json
import pytz
from datetime import datetime

import discord
from discord import Embed
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

VOTE_FILE = "data/votes.json"
RECRUTEUR_ROLE_ID = 1317850709948891177
VOTE_CHANNEL_ID  = 1371557531373277376

def load_votes():
    try:
        with open(VOTE_FILE, "r") as f:
            return json.load(f) or {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_votes(data):
    with open(VOTE_FILE, "w") as f:
        json.dump(data, f, indent=2)

vote_data = load_votes()
recrutement_status = {"active": True}

def build_recrutement_embed() -> Embed:
    statut = "✅ ON" if recrutement_status["active"] else "❌ OFF"
    couleur = 0x00ff99 if recrutement_status["active"] else 0xff4444

    description = f"> - **Statut des recrutements :** {statut}"

    if recrutement_status["active"]:
        description += (
            "\n\n"
            "__Veuillez soumettre votre candidature en préparant les informations ci-dessous :__\n\n"
            "- **Nom RP :**\n"
            "- **Âge :**\n"
            "- **Fruit :**\n"
            "- **Niveau :**\n"
            "- **Aura :**"
        )

    return Embed(
        title="__𝙍𝙚𝙘𝙧𝙪𝙩𝙚𝙢𝙚𝙣𝙩__",
        description=description,
        color=couleur
    )
class RecrutementModal(Modal, title="Formulaire de Recrutement"):
    nom_rp = TextInput(label="Nom RP", placeholder="Ex: Akira le Flamme")
    age    = TextInput(label="Âge",    placeholder="Ex: 17 ans")
    fruit  = TextInput(label="Fruit",  placeholder="Ex: Hie Hie no Mi")
    niveau = TextInput(label="Niveau", placeholder="Ex: 150")
    aura   = TextInput(label="Aura",   placeholder="Ex: Fort / Moyen / Faible")

    async def on_submit(self, interaction: discord.Interaction):
        embed = Embed(
            title="📋 Nouvelle Candidature",
            description=f"👤 **Candidat :** {interaction.user.mention}",
            color=0x2f3136
        )
        for name, field in [
            ("Nom RP", self.nom_rp), ("Âge", self.age),
            ("Fruit", self.fruit), ("Niveau", self.niveau),
            ("Aura", self.aura)
        ]:
            embed.add_field(name=name, value=field.value, inline=False)
        embed.set_footer(text="Votes : ✅ 0 | ❌ 0")

        msg = await interaction.channel.send(
            content=f"<@&{RECRUTEUR_ROLE_ID}>",
            embed=embed
        )
        vote_data[str(msg.id)] = {}
        save_votes(vote_data)
        await msg.edit(view=VoteView())
        await interaction.response.send_message(
            "✅ Candidature envoyée !", ephemeral=True
        )

class VoteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Pour", style=discord.ButtonStyle.success, custom_id="vote_pour")
    async def pour(self, interaction: discord.Interaction, button: Button):
        await self._vote(interaction, "pour")

    @discord.ui.button(label="❌ Contre", style=discord.ButtonStyle.danger, custom_id="vote_contre")
    async def contre(self, interaction: discord.Interaction, button: Button):
        await self._vote(interaction, "contre")

    async def _vote(self, interaction: discord.Interaction, choix: str):
        if RECRUTEUR_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message(
                "🚫 Seuls les recruteurs peuvent voter.", ephemeral=True
            )

        mid = str(interaction.message.id)
        uid = str(interaction.user.id)
        votes = vote_data.setdefault(mid, {})

        if votes.get(uid) == choix:
            del votes[uid]
        else:
            votes[uid] = choix

        save_votes(vote_data)

        embed = interaction.message.embeds[0]
        p = sum(1 for v in votes.values() if v == "pour")
        c = sum(1 for v in votes.values() if v == "contre")
        embed.color = 0x00ff00 if p > c else 0xff0000 if c > p else 0x2f3136
        embed.set_footer(text=f"Votes : ✅ {p} | ❌ {c}")

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()

class FormulaireButton(Button):
    def __init__(self):
        super().__init__(
            label="📋 Remplir le formulaire",
            style=discord.ButtonStyle.primary,
            custom_id="formulaire_button"
        )

    async def callback(self, interaction: discord.Interaction):
        if not recrutement_status["active"]:
            return await interaction.response.send_message(
                "🚫 Le recrutement est fermé.", ephemeral=True
            )
        await interaction.response.send_modal(RecrutementModal())

class AdminToggleButton(Button):
    def __init__(self):
        super().__init__(
            label="🛠️ Changer le statut",
            style=discord.ButtonStyle.secondary,
            custom_id="admin_toggle"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "🚫 Administrateurs uniquement.", ephemeral=True
            )

        recrutement_status["active"] = not recrutement_status["active"]
        # On reconstruit l'embed complet
        embed = build_recrutement_embed()
        await interaction.message.edit(embed=embed, view=RecrutementView())
        await interaction.response.send_message(
            f"🔄 Recrutement {('ON' if recrutement_status['active'] else 'OFF')}",
            ephemeral=True
        )

class RecrutementView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FormulaireButton())
        self.add_item(AdminToggleButton())

class Recrutement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(RecrutementView())
        bot.add_view(VoteView())

    @commands.Cog.listener()
    async def on_ready(self):
        chan = await self.bot.fetch_channel(VOTE_CHANNEL_ID)
        async for msg in chan.history(limit=200):
            if msg.author.id == self.bot.user.id and msg.embeds:
                if msg.embeds[0].title == "📋 Nouvelle Candidature":
                    await msg.edit(view=VoteView())

    @commands.command(name="recrutement")
    @commands.has_permissions(administrator=True)
    async def recrutement(self, ctx: commands.Context):
        await ctx.message.delete()
        await ctx.send(embed=build_recrutement_embed(), view=RecrutementView())

async def setup(bot: commands.Bot):
    await bot.add_cog(Recrutement(bot))
