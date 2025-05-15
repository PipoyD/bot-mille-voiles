import os
import discord
import json
import pytz
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
recrutement_status = {"active": True}

VOTE_FILE = "votes.json"
RECRUTEUR_ROLE_ID = 1317850709948891177
VOTE_CHANNEL_ID = 1358037356749394111

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
        display_name = interaction.user.display_name
        embed = discord.Embed(title="📋 Nouvelle Candidature",
                              description=f"👤 **Candidat :** {display_name}",
                              color=0x2f3136)
        embed.add_field(name="Nom RP", value=self.nom_rp.value, inline=False)
        embed.add_field(name="Âge", value=self.age.value, inline=False)
        embed.add_field(name="Fruit", value=self.fruit.value, inline=False)
        embed.add_field(name="Niveau", value=self.niveau.value, inline=False)
        embed.add_field(name="Aura", value=self.aura.value, inline=False)
        embed.set_footer(text="Votes : ✅ 0 | ❌ 0")

        message = await interaction.channel.send(content=f"<@&{RECRUTEUR_ROLE_ID}>", embed=embed)
        view = VoteView(message.id)
        await message.edit(view=view)
        vote_data[str(message.id)] = {}
        save_votes()
        await interaction.response.send_message("✅ Candidature envoyée avec succès !", ephemeral=True)
class VoteView(View):
    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = message_id
        self.add_item(Button(label="✅ Pour", style=discord.ButtonStyle.success, custom_id=f"vote_pour_{message_id}"))
        self.add_item(Button(label="❌ Contre", style=discord.ButtonStyle.danger, custom_id=f"vote_contre_{message_id}"))

    async def handle_vote(self, interaction: discord.Interaction, choix: str):
        if not any(role.id == RECRUTEUR_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("🚫 Seuls les recruteurs peuvent voter.", ephemeral=True)
            return

        msg_id = str(self.message_id)
        user_id = str(interaction.user.id)
        votes = vote_data.setdefault(msg_id, {})
        current_vote = votes.get(user_id)

        if current_vote == choix:
            del votes[user_id]
        else:
            votes[user_id] = choix

        save_votes()

        channel = interaction.channel
        try:
            message = await channel.fetch_message(self.message_id)
            embed = message.embeds[0]
            pour = sum(1 for v in votes.values() if v == "pour")
            contre = sum(1 for v in votes.values() if v == "contre")
            color = 0x00ff00 if pour > contre else 0xff0000 if contre > pour else 0x2f3136
            embed.color = color
            embed.set_footer(text=f"Votes : ✅ {pour} | ❌ {contre}")
            await message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du message : {e}")

        await interaction.response.defer()
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    custom_id = interaction.data["custom_id"]
    if custom_id.startswith("vote_pour_") or custom_id.startswith("vote_contre_"):
        try:
            action, msg_id_str = custom_id.split("_")[1], custom_id.split("_")[2]
            msg_id = int(msg_id_str)
            view = VoteView(msg_id)
            await view.handle_vote(interaction, "pour" if "pour" in custom_id else "contre")
        except Exception as e:
            print(f"❌ Erreur interaction vote : {e}")
            await interaction.response.send_message("❌ Une erreur est survenue.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    bot.add_view(RecrutementView())

    # Restaurer les boutons pour les candidatures existantes
    try:
        channel = await bot.fetch_channel(VOTE_CHANNEL_ID)
        async for message in channel.history(limit=200):
            if message.author.id != bot.user.id or not message.embeds:
                continue
            embed = message.embeds[0]
            if embed.title != "📋 Nouvelle Candidature":
                continue
            view = VoteView(message.id)
            await message.edit(view=view)
            print(f"🔁 Boutons restaurés pour : {message.id}")
    except Exception as e:
        print(f"❌ Erreur restauration boutons : {e}")
class RecrutementView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FormulaireButton())
        self.add_item(AdminToggleButton())

class FormulaireButton(Button):
    def __init__(self):
        super().__init__(
            label="📋 Remplir le formulaire",
            style=discord.ButtonStyle.primary,
            custom_id="formulaire_button",
            disabled=not recrutement_status["active"]
        )

    async def callback(self, interaction: discord.Interaction):
        if not recrutement_status["active"]:
            await interaction.response.send_message("🚫 Le recrutement est fermé.", ephemeral=True)
            return
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
            await interaction.response.send_message("🚫 Seuls les administrateurs peuvent changer le statut.", ephemeral=True)
            return

        recrutement_status["active"] = not recrutement_status["active"]
        embed = build_recrutement_embed()
        view = RecrutementView()
        await interaction.message.edit(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ Statut mis à jour : {'ON' if recrutement_status['active'] else 'OFF'}",
            ephemeral=True
        )

def build_recrutement_embed():
    statut = "✅ ON" if recrutement_status["active"] else "❌ OFF"
    couleur = 0x00ff99 if recrutement_status["active"] else 0xff4444
    embed = discord.Embed(
        title="__𝙍𝙚𝙘𝙧𝙪𝙩𝙚𝙢𝙚𝙣𝙩__",
        description=(
            f"> - **Statut des recrutements :** {statut}\n\n"
            "__Veuillez soumettre votre candidature en préparant les informations ci-dessous :__\n\n"
            "- **Nom RP :**\n"
            "- **Âge :**\n"
            "- **Fruit :**\n"
            "- **Niveau :**\n"
            "- **Aura :**"
        ),
        color=couleur
    )
    return embed
@bot.command()
@commands.has_permissions(administrator=True)
async def recrutement(ctx):
    embed = build_recrutement_embed()
    view = RecrutementView()
    await ctx.send(embed=embed, view=view)

# ---------------------- Commande de test (optionnelle) ----------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def resetvotes(ctx):
    vote_data.clear()
    save_votes()
    await ctx.send("🔄 Tous les votes ont été réinitialisés.")

# ---------------------- Lancement sécurisé ----------------------
token = os.getenv("TOKEN")
if not token:
    print("❌ Token manquant dans les variables d'environnement.")
else:
    bot.run(token)
