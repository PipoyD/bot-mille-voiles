import os
import discord
import json
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
recrutement_status = {"active": True}

VOTE_FILE = "votes.json"
RECRUTEUR_ROLE_ID = 1317850709948891177

# ---------------------- Votes persistants ----------------------
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

# ---------------------- Modal de formulaire ----------------------
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

        view = VoteView()
        await interaction.response.send_message("Merci pour ta candidature !", ephemeral=True)
        message = await interaction.channel.send(content=f"<@&{RECRUTEUR_ROLE_ID}>", embed=embed, view=view)
        view.message = message
        vote_data[str(message.id)] = {}
        save_votes()

# ---------------------- Vue de vote ----------------------
class VoteView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.message = None

    async def update_embed(self):
        votes = vote_data.get(str(self.message.id), {})
        pour = sum(1 for v in votes.values() if v == "pour")
        contre = sum(1 for v in votes.values() if v == "contre")

        color = 0x00ff00 if pour > contre else 0xff0000 if contre > pour else 0x2f3136
        embed = self.message.embeds[0]
        embed.color = color
        embed.set_footer(text=f"Votes : ✅ {pour} | ❌ {contre}")
        await self.message.edit(embed=embed, view=self)

    async def handle_vote(self, interaction, choix):
        if not any(role.id == RECRUTEUR_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("🚫 Seuls les recruteurs peuvent voter.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        msg_id = str(self.message.id)
        votes = vote_data.setdefault(msg_id, {})
        current_vote = votes.get(user_id)

        if current_vote == choix:
            del votes[user_id]
        else:
            votes[user_id] = choix

        save_votes()
        await self.update_embed()
        if not interaction.response.is_done():
            await interaction.response.defer()

    @discord.ui.button(label="✅ Pour", style=discord.ButtonStyle.success, custom_id="vote_pour")
    async def vote_pour(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, "pour")

    @discord.ui.button(label="❌ Contre", style=discord.ButtonStyle.danger, custom_id="vote_contre")
    async def vote_contre(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, "contre")

# ---------------------- Vue principale ----------------------
class RecrutementView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(FormulaireButton())
        self.add_item(AdminToggleButton())

class FormulaireButton(Button):
    def __init__(self):
        super().__init__(label="📋 Remplir le formulaire",
                         style=discord.ButtonStyle.primary,
                         custom_id="formulaire_button",
                         disabled=not recrutement_status["active"])

    async def callback(self, interaction: discord.Interaction):
        if not recrutement_status["active"]:
            await interaction.response.send_message("🚫 Le recrutement est fermé.", ephemeral=True)
            return
        await interaction.response.send_modal(RecrutementModal())

class AdminToggleButton(Button):
    def __init__(self):
        super().__init__(label="🛠️ Changer le statut",
                         style=discord.ButtonStyle.secondary,
                         custom_id="admin_toggle")

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

# ---------------------- Embed de recrutement ----------------------
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

# ---------------------- Commande !recrutement ----------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def recrutement(ctx):
    embed = build_recrutement_embed()
    view = RecrutementView()
    if recrutement_status["active"]:
        await ctx.send(content="@everyone", embed=embed, view=view)
    else:
        await ctx.send(embed=embed, view=view)

# ---------------------- Commande !flottes ----------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def flottes(ctx):
    guild = ctx.guild

    ROLES = {
        "CAPITAINE": 1317851007358734396,
        "VICE_CAPITAINE": 1358079100203569152,
        "COMMANDANT": 1358031308542181382,
        "VICE_COMMANDANT": 1358032259596288093,
        "LIEUTENANT": 1358030829225381908,
        "MEMBRE": 1317850709948891177,
        "ECARLATE": 1371942480316203018,
        "AZUR": 1371942559894736916,
    }

    def filter_by(grade_id, flotte_id=None):
        return [
            member.mention
            for member in guild.members
            if discord.utils.get(member.roles, id=grade_id) and
               (discord.utils.get(member.roles, id=flotte_id) if flotte_id else True)
        ]

    embed = discord.Embed(
        title="⚓ • Équipage : Les Mille Voiles • ⚓",
        description="**Effectif total :** {} membres".format(len([m for m in guild.members if not m.bot])),
        color=0x3498db
    )

    capitaine = filter_by(ROLES["CAPITAINE"])
    vice_capitaine = filter_by(ROLES["VICE_CAPITAINE"])
    embed.add_field(
        name="🧭 Capitainerie :",
        value=f"👑 **Capitaine :** {capitaine[0] if capitaine else 'N/A'}\n"
              f"🗡️ **Vice-Capitaine :** {vice_capitaine[0] if vice_capitaine else 'N/A'}",
        inline=False
    )

    embed.add_field(name="__**1ère Flotte : La Voile Écarlate**__", value="", inline=False)
    embed.add_field(name="🛡️ Commandant :", value="\n".join(filter_by(ROLES["COMMANDANT"], ROLES["ECARLATE"])) or "N/A", inline=False)
    embed.add_field(name="🗡️ Vice-Commandant :", value="\n".join(filter_by(ROLES["VICE_COMMANDANT"], ROLES["ECARLATE"])) or "N/A", inline=False)
    embed.add_field(name="🎖️ Lieutenants :", value="\n".join(filter_by(ROLES["LIEUTENANT"], ROLES["ECARLATE"])) or "N/A", inline=False)
    embed.add_field(name="👥 Membres :", value="\n".join(filter_by(ROLES["MEMBRE"], ROLES["ECARLATE"])) or "N/A", inline=False)

    embed.add_field(name="__**2ème Flotte : La Voile d'Azur**__", value="", inline=False)
    embed.add_field(name="🛡️ Commandant :", value="\n".join(filter_by(ROLES["COMMANDANT"], ROLES["AZUR"])) or "N/A", inline=False)
    embed.add_field(name="🗡️ Vice-Commandant :", value="\n".join(filter_by(ROLES["VICE_COMMANDANT"], ROLES["AZUR"])) or "N/A", inline=False)
    embed.add_field(name="🎖️ Lieutenants :", value="\n".join(filter_by(ROLES["LIEUTENANT"], ROLES["AZUR"])) or "N/A", inline=False)
    embed.add_field(name="👥 Membres :", value="\n".join(filter_by(ROLES["MEMBRE"], ROLES["AZUR"])) or "N/A", inline=False)

    all_lieutenants = set(filter_by(ROLES["LIEUTENANT"]))
    lieutenants_f1 = set(filter_by(ROLES["LIEUTENANT"], ROLES["ECARLATE"]))
    lieutenants_f2 = set(filter_by(ROLES["LIEUTENANT"], ROLES["AZUR"]))
    sans_flotte_lieutenants = list(all_lieutenants - lieutenants_f1 - lieutenants_f2)

    embed.add_field(
        name="🎖️ Lieutenants sans flotte :",
        value="\n".join(sans_flotte_lieutenants) or "Aucun",
        inline=False
    )

    all_membres = set(filter_by(ROLES["MEMBRE"]))
    membres_f1 = set(filter_by(ROLES["MEMBRE"], ROLES["ECARLATE"]))
    membres_f2 = set(filter_by(ROLES["MEMBRE"], ROLES["AZUR"]))
    sans_flotte_membres = list(all_membres - membres_f1 - membres_f2)

    embed.add_field(
        name="👥 Membres sans flotte :",
        value="\n".join(sans_flotte_membres) or "Aucun",
        inline=False
    )

    await ctx.send(embed=embed)

# ---------------------- Événement on_ready ----------------------
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    bot.add_view(RecrutementView())
    bot.add_view(VoteView())

# ---------------------- Lancement sécurisé ----------------------
token = os.getenv("TOKEN")
if not token:
    print("❌ Token manquant dans les variables d'environnement.")
else:
    bot.run(token)
