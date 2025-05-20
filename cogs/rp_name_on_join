# cogs/rp_name_on_join.py

import discord
from discord import Embed
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

WELCOME_CHANNEL_ID = 1317911633778970666

# IDs des rôles à attribuer après définition du Nom RP
RP_ROLES = [
    1371944910264991859,
    1372207508462108753
]

class RpNameModal(Modal, title="Définissez votre Nom RP"):
    rp_name = TextInput(
        label="Votre Nom RP",
        placeholder="Ex : Akira le Flamme",
        max_length=32
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = guild.get_member(interaction.user.id) or interaction.user

        # 1️⃣ On change le pseudo
        try:
            await member.edit(nick=self.rp_name.value)
        except discord.Forbidden:
            return await interaction.response.send_message(
                "🚫 Je n'ai pas la permission de changer votre pseudo.",
                ephemeral=True
            )

        # 2️⃣ On attribue les rôles RP
        roles_to_add = []
        for rid in RP_ROLES:
            role = guild.get_role(rid)
            if role:
                roles_to_add.append(role)
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Nom RP défini")
            except discord.Forbidden:
                # On ignore si pas la permission, mais on continue
                pass

        # 3️⃣ Confirmation à l'utilisateur
        await interaction.response.send_message(
            f"✅ Votre Nom RP a bien été mis à **{self.rp_name.value}** "
            f"et vos rôles ont été attribués !",
            ephemeral=True
        )

class RpNameOnJoin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Enregistre une vue globale pour que le bouton reste fonctionnel
        bot.add_view(self._build_join_view(0))

    def _build_join_view(self, target_id: int) -> View:
        view = View(timeout=None)
        button = Button(
            label="🖋️ Définir mon Nom RP",
            style=discord.ButtonStyle.primary,
            custom_id=f"set_rp_name_button:{target_id}"
        )
        async def on_click(interaction: discord.Interaction):
            # Sécurité : seul le destinataire peut cliquer
            if interaction.user.id != target_id:
                return await interaction.response.send_message(
                    "❌ Ce bouton n'est pas pour vous.", ephemeral=True
                )
            await interaction.response.send_modal(RpNameModal())
        button.callback = on_click
        view.add_item(button)
        return view

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return

        view = self._build_join_view(member.id)
        try:
            await channel.send(
                f"🎉 Bienvenue {member.mention} !\n"
                "Clique sur le bouton ci-dessous pour choisir ton **Nom RP**.",
                view=view
            )
        except discord.Forbidden:
            # Pas la permission d'envoyer dans ce canal
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(RpNameOnJoin(bot))
