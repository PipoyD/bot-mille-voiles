import discord
import json
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

VOTE_FILE = "votes.json"
RECRUTEUR_ROLE_ID = 1317850709948891177
VOTE_CHANNEL_ID = 1371557531373277376
recrutement_status = {"active": True}

def load_votes():
    try:
        with open(VOTE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_votes():
    with open(VOTE_FILE, "w") as f:
        json.dump(vote_data, f)

vote_data = load_votes()

class RecrutementModal(Modal, title="Formulaire de Recrutement"):
    nom_rp = TextInput(label="Nom RP", placeholder="Ex: Akira le Flamme", required=True)
    age = TextInput(label="Âge", placeholder="Ex: 17 ans", required=True)
    fruit = TextInput(label="Fruit", placeholder="Ex: Hie Hie no Mi", required=True)
    niveau = TextInput(label="Niveau", placeholder="Ex: 150", required=True)
    aura = TextInput(label="Aura", placeholder="Ex: Fort / Moyen / Faible", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📋 Nouvelle Candidature", description=f"👤 **Candidat :** {interaction.user.mention}", color=0x2f3136)
        embed.add_field(name="Nom RP", value=self.nom_rp.value, inline=False)
        embed.add_field(name="Âge", value=self.age.value, inline=False)
        embed.add_field(name="Fruit", value=self.fruit.value, inline=False)
        embed.add_field(name="Niveau", value=self.niveau.value, inline=False)
        embed.add_field(name="Aura", value=self.aura.value, inline=False)
        embed.set_footer(text="Votes : ✅ 0 | ❌ 0")
        message = await interaction.channel.send(content=f"<@&{RECRUTEUR_ROLE_ID}>", embed=embed)
        vote_data[str(message.id)] = {}
        save_votes()
        await message.edit(view=VoteView())
        await interaction.response.send_message("✅ Candidature envoyée avec succès !", ephemeral=True)

class VoteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Pour", style=discord.ButtonStyle.success, custom_id="vote_pour")
    async def vote_pour(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, "pour")

    @discord.ui.button(label="❌ Contre", style=discord.ButtonStyle.danger, custom_id="vote_contre")
    async def vote_contre(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, "contre")

    async def handle_vote(self, interaction: discord.Interaction, choix: str):
        if not any(role.id == RECRUTEUR_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("🚫 Seuls les recruteurs peuvent voter.", ephemeral=True)
            return

        msg_id = str(interaction.message.id)
        user_id = str(interaction.user.id)
        votes = vote_data.setdefault(msg_id, {})
        current_vote = votes.get(user_id)

        if current_vote == choix:
            del votes[user_id]
        else:
            votes[user_id] = choix

        save_votes()

        try:
            embed = interaction.message.embeds[0]
            pour = sum(1 for v in votes.values() if v == "pour")
            contre = sum(1 for v in votes.values() if v == "contre")
            embed.color = 0x00ff00 if pour > contre else 0xff0000 if contre > pour else 0x2f3136
            embed.set_footer(text=f"Votes : ✅ {pour} | ❌ {contre}")
            await interaction.message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du message : {e}")
            await interaction.response.send_message("❌ Une erreur est survenue lors de la mise à jour.", ephemeral=True)
            return

        await interaction.response.defer()

class RecrutementView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FormulaireButton())
        self.add_item(AdminToggleButton())

class FormulaireButton(Button):
    def __init__(self):
        super().__init__(label="📋 Remplir le formulaire", style=discord.ButtonStyle.primary, custom_id="formulaire_button", disabled=not recrutement_status["active"])

    async def callback(self, interaction: discord.Interaction):
        if not recrutement_status["active"]:
            await interaction.response.send_message("🚫 Le recrutement est fermé.", ephemeral=True)
        else:
            await interaction.response.send_modal(RecrutementModal())

class AdminToggleButton(Button):
    def __init__(self):
        super().__init__(label="🛠️ Changer le statut", style=discord.ButtonStyle.secondary, custom_id="admin_toggle")

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Seuls les administrateurs peuvent changer le statut.", ephemeral=True)
            return

        recrutement_status["active"] = not recrutement_status["active"]
        await interaction.message.edit(embed=build_recrutement_embed(), view=RecrutementView())
        await interaction.response.send_message(f"✅ Statut mis à jour : {'ON' if recrutement_status['active'] else 'OFF'}", ephemeral=True)

def build_recrutement_embed():
    statut = "✅ ON" if recrutement_status["active"] else "❌ OFF"
    couleur = 0x00ff99 if recrutement_status["active"] else 0xff4444
    description = f"""> - **Statut des recrutements :** {statut}

__Veuillez soumettre votre candidature en préparant les informations ci-dessous :__

- **Nom RP :**
- **Âge :**
- **Fruit :**
- **Niveau :**
- **Aura :**"""
    return discord.Embed(title="__𝙍𝙚𝙘𝙧𝙪𝙩𝙚𝙢𝙚𝙣𝙩__", description=description, color=couleur)

async def setup_recrutement(bot):
    bot.add_view(RecrutementView())
    bot.add_view(VoteView())

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def recrutement(ctx):
        await ctx.message.delete()
        embed = build_recrutement_embed()
        view = RecrutementView()
        await ctx.send(embed=embed, view=view)

    try:
        channel = await bot.fetch_channel(VOTE_CHANNEL_ID)
        async for message in channel.history(limit=200):
            if message.author.id == bot.user.id and message.embeds and message.embeds[0].title == "📋 Nouvelle Candidature":
                await message.edit(view=VoteView())
    except Exception as e:
        print(f"❌ Erreur restauration boutons : {e}")
