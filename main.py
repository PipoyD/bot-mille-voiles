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
VOTE_CHANNEL_ID = 1371557531373277376

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

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    bot.add_view(RecrutementView())
    bot.add_view(FlotteView())

    try:
        channel = await bot.fetch_channel(VOTE_CHANNEL_ID)
        async for message in channel.history(limit=200):
            if message.author.id != bot.user.id or not message.embeds:
                continue
            embed = message.embeds[0]
            if embed.title != "📋 Nouvelle Candidature":
                continue
            await message.edit(view=VoteView())
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

class FlotteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_flotte")
    async def refresh(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Réservé aux administrateurs.", ephemeral=True)
            return

        embed = build_flotte_embed(interaction.guild)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Liste actualisée.", ephemeral=True)

def build_flotte_embed(guild):
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

    def filter_unique(grade_id, flotte_id=None):
        return [
            member for member in guild.members
            if discord.utils.get(member.roles, id=grade_id)
            and (discord.utils.get(member.roles, id=flotte_id) if flotte_id else True)
        ]

    membres_equipage = [
        m for m in guild.members if discord.utils.get(m.roles, id=ROLES["MEMBRE"]) and not m.bot
    ]

    embed = discord.Embed(
        title="⚓ • Équipage : Les Mille Voiles • ⚓",
        description=f"**Effectif total :** {len(membres_equipage)} membres",
        color=0xFFA500
    )

    déjà_affichés = set()

    def filtrer(role_id, flotte_id=None):
        result = []
        for m in filter_unique(role_id, flotte_id):
            if m.id not in déjà_affichés:
                déjà_affichés.add(m.id)
                result.append(m.mention)
        return result or ["N/A"]

    embed.add_field(
        name="🧭 Capitainerie :",
        value=f"👑 **Capitaine :** {filtrer(ROLES['CAPITAINE'])[0]}\n"
              f"🗡️ **Vice-Capitaine :** {filtrer(ROLES['VICE_CAPITAINE'])[0]}",
        inline=False
    )

    embed.add_field(name="__**1ère Flotte : La Voile Écarlate**__", value="", inline=False)
    embed.add_field(name="🛡️ Commandant :", value="\n".join(filtrer(ROLES["COMMANDANT"], ROLES["ECARLATE"])), inline=False)
    embed.add_field(name="🗡️ Vice-Commandant :", value="\n".join(filtrer(ROLES["VICE_COMMANDANT"], ROLES["ECARLATE"])), inline=False)
    embed.add_field(name="🎖️ Lieutenants :", value="\n".join(filtrer(ROLES["LIEUTENANT"], ROLES["ECARLATE"])), inline=False)
    embed.add_field(name="👥 Membres :", value="\n".join(filtrer(ROLES["MEMBRE"], ROLES["ECARLATE"])), inline=False)

    embed.add_field(name="__**2ème Flotte : La Voile d'Azur**__", value="", inline=False)
    embed.add_field(name="🛡️ Commandant :", value="\n".join(filtrer(ROLES["COMMANDANT"], ROLES["AZUR"])), inline=False)
    embed.add_field(name="🗡️ Vice-Commandant :", value="\n".join(filtrer(ROLES["VICE_COMMANDANT"], ROLES["AZUR"])), inline=False)
    embed.add_field(name="🎖️ Lieutenants :", value="\n".join(filtrer(ROLES["LIEUTENANT"], ROLES["AZUR"])), inline=False)
    embed.add_field(name="👥 Membres :", value="\n".join(filtrer(ROLES["MEMBRE"], ROLES["AZUR"])), inline=False)

    embed.add_field(name="__**Sans Flotte**__", value="", inline=False)
    lieutenants_sans = filtrer(ROLES["LIEUTENANT"])
    embed.add_field(name="🎖️ Lieutenants :", value="\n".join(lieutenants_sans), inline=False)

    def membres_sans_flotte():
        result = []
        for m in guild.members:
            if m.id in déjà_affichés:
                continue
            roles_ids = [r.id for r in m.roles]
            if ROLES["MEMBRE"] in roles_ids and all(r not in ROLES.values() or r == ROLES["MEMBRE"] for r in roles_ids):
                déjà_affichés.add(m.id)
                result.append(m.mention)
        return result or ["N/A"]

    embed.add_field(name="👥 Membres :", value="\n".join(membres_sans_flotte()), inline=False)

    embed.set_thumbnail(url="https://i.imgur.com/w0G8DCx.png")
    embed.set_image(url="https://i.imgur.com/tqrOqYS.jpeg")

    paris = pytz.timezone("Europe/Paris")
    now = datetime.now(paris).strftime("Dernière mise à jour : %d/%m/%Y à %H:%M")
    embed.set_footer(text=now)

    return embed

@bot.command()
@commands.has_permissions(administrator=True)
async def flottes(ctx):
    embed = build_flotte_embed(ctx.guild)
    await ctx.send(embed=embed, view=FlotteView())

# ---------- PRIMES AUTOMATIQUES ----------

PRIME_FILE = "primes.json"
RANKS = [
    (3_200_000_000, "Empereur Pirate", "👑"),
    (1_150_000_000, "SuperNova", "🚀"),
    (300_000_000, "Rang Z", "💎"),
    (200_000_000, "Rang S+", "🔥"),
    (150_000_000, "Rang S", "🔴"),
    (60_000_000, "Rang A+", "🟠"),
    (30_000_000, "Rang A", "🟡"),
    (15_000_000, "Rang B", "🟢"),
    (5_000_000, "Rang C", "🔵"),
    (1_000_000, "Rang D", "🟣"),
    (500_000, "Rang E", "⚪"),
    (0, "Rookie", "💤")
]
FLOTTE_EMOJIS = {
    "ECARLATE": "🔴",
    "AZUR": "🔵"
}

def load_primes():
    try:
        with open(PRIME_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_primes(data):
    with open(PRIME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def format_prime(prime):
    return f"{prime:,}".replace(",", " ") + " Berrys"

def get_rank(prime):
    for value, label, emoji in RANKS:
        if prime >= value:
            return label, emoji
    return "Inconnu", "❓"

class PrimeView(View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild

    @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_prime")
    async def refresh(self, interaction: discord.Interaction, button: Button):
        embed = build_prime_embed(self.guild)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Primes actualisées.", ephemeral=True)

    @discord.ui.button(label="📝 Mettre à jour les primes", style=discord.ButtonStyle.primary, custom_id="edit_primes")
    async def edit(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Réservé aux administrateurs.", ephemeral=True)
            return
        await interaction.response.send_modal(UpdatePrimesModal(self.guild))

class UpdatePrimesModal(Modal, title="Mise à jour des Primes"):
    input = TextInput(label="Copiez-collez ici les nouvelles primes", style=discord.TextStyle.paragraph, placeholder="Ex: Mounir San: 45,357,752", required=True)

    def __init__(self, guild):
        super().__init__()
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        new_data = self.input.value
        prime_data = load_primes()
        lignes = new_data.split("\n")
        for ligne in lignes:
            if ":" in ligne:
                nom, valeur = ligne.split(":", 1)
                nom = nom.strip()
                valeur = int(valeur.replace(",", "").replace(" ", ""))
                prime_data[nom] = valeur
        save_primes(prime_data)
        embed = build_prime_embed(self.guild)
        await interaction.message.edit(embed=embed, view=PrimeView(self.guild))
        await interaction.response.send_message("✅ Primes mises à jour avec succès !", ephemeral=True)

def build_prime_embed(guild):
    prime_data = load_primes()
    roles_by_category = {
        "🧭 Capitainerie": ["CAPITAINE", "VICE_CAPITAINE"],
        "🛡️ Commandants": ["COMMANDANT"],
        "🗡️ Vice-Commandants": ["VICE_COMMANDANT"],
        "🎖️ Lieutenants": ["LIEUTENANT"],
        "👥 Membres": ["MEMBRE"]
    }
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

    def flotte_emoji(member):
        for key, role_id in ROLES.items():
            if key in FLOTTE_EMOJIS and discord.utils.get(member.roles, id=role_id):
                return FLOTTE_EMOJIS[key]
        return ""

    embed = discord.Embed(title="📜 Primes & Rangs", color=0x00ffcc)
    déjà_affichés = set()

    for titre, types in roles_by_category.items():
        group = []
        for role in types:
            members = [m for m in guild.members if discord.utils.get(m.roles, id=ROLES[role]) and not m.bot]
            for m in members:
                if m.id not in déjà_affichés:
                    name = m.display_name
                    prime = prime_data.get(name, 0)
                    rank, emoji = get_rank(prime)
                    group.append((prime, f"{flotte_emoji(m)} {m.mention} — 💰 {format_prime(prime)} — {emoji} {rank}"))
                    déjà_affichés.add(m.id)
        if group:
            sorted_group = sorted(group, key=lambda x: x[0], reverse=True)
            embed.add_field(name=titre, value="\n".join([x[1] for x in sorted_group]), inline=False)

    embed.set_footer(text=datetime.now(pytz.timezone("Europe/Paris")).strftime("Mis à jour le %d/%m/%Y à %H:%M"))
    return embed

@bot.command()
@commands.has_permissions(administrator=True)
async def prime(ctx):
    embed = build_prime_embed(ctx.guild)
    view = PrimeView(ctx.guild)
    await ctx.send(embed=embed, view=view)


# ---------------------- Lancement sécurisé ----------------------
token = os.getenv("TOKEN")
if not token:
    print("❌ Token manquant dans les variables d'environnement.")
else:
    bot.run(token)
