# cogs/prime.py

import os
import re
import unicodedata
import aiohttp
import asyncpg
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

# Préfixe fixe de l'URL GitBook
URL_PREFIX = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel/"

# Hiérarchie des rôles & icônes
ROLE_IDS = {
    "CAPITAINE":       1317851007358734396,
    "VICE_CAPITAINE":  1358079100203569152,
    "COMMANDANT":      1358031308542181382,
    "VICE_COMMANDANT": 1358032259596288093,
    "LIEUTENANT":      1358030829225381908,
    "MEMBRE":          1317850709948891177,
}
ROLE_ORDER = [
    (ROLE_IDS["CAPITAINE"],       "👑", "Capitaine"),
    (ROLE_IDS["VICE_CAPITAINE"],  "⚔️", "Vice-Capitaine"),
    (ROLE_IDS["COMMANDANT"],      "🛡️", "Commandant"),
    (ROLE_IDS["VICE_COMMANDANT"], "🗡️", "Vice-Commandant"),
    (ROLE_IDS["LIEUTENANT"],      "🎖️", "Lieutenant"),
    (ROLE_IDS["MEMBRE"],          "⚓", "Membre d’équipage"),
]

# Flotte → emoji
FLEET_EMOJIS = {
    1371942480316203018: "<:1reflotte:1372158546531324004>",  # Écarlate
    1371942559894736916: "<:2meflotte:1372158586951696455>",  # Azur
}

# Seuils de classification et emojis
QUOTAS = {
    "Très Dangereux": 1_150_000_000,
    "Dangereux":       300_000_000,
    "Très Puissant":   150_000_000,
    "Puissant":         30_000_000,
    "Fort":              5_000_000,
    "Faible":                   0,
}
EMOJI_FORCE = {
    "Très Dangereux": "🏹 Très Dangereux",
    "Dangereux":      "🏹 Dangereux",
    "Très Puissant":  "🔥 Très Puissant",
    "Puissant":       "🔥 Puissant",
    "Fort":           "⚔️ Fort",
    "Faible":         "💀 Faible",
}

def normalize(text: str) -> str:
    """
    Insensible aux accents et à la casse : NFD + casefold,
    ne garde que a-z, 0-9 et espace.
    """
    nfkd = unicodedata.normalize("NFD", text).casefold()
    stripped = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", "", stripped)

def name_matches(dname: str, entry: str) -> bool:
    """
    Chaque mot dans dname doit apparaître parmi les tokens normalisés d'entry.
    """
    dn = normalize(dname).split()
    en = normalize(entry).split()
    return all(tok in en for tok in dn)

def get_fleet_emoji(member: discord.Member) -> str:
    """Retourne l'emoji de flotte associé au membre, s’il existe."""
    for r in member.roles:
        if r.id in FLEET_EMOJIS:
            return FLEET_EMOJIS[r.id]
    return ""

class SlugModal(Modal):
    slug = TextInput(
        label="Identifiant de la page primes (slug)",
        placeholder="gvednstndtrsdd",
        style=discord.TextStyle.short,
        required=True,
    )

    def __init__(self, cog: "Prime", message: discord.Message):
        super().__init__(title="Actualiser les primes")
        self.cog = cog
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        slug = self.slug.value.strip()
        url  = URL_PREFIX + slug
        try:
            await self.cog.fetch_and_upsert(url)
            new_embed = await self.cog.build_embed(interaction.guild)
            await self.message.edit(embed=new_embed, view=self.cog.RefreshView(self.cog))
            await interaction.response.send_message("✅ Primes actualisées.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Échec mise à jour : {e}", ephemeral=True)

class Prime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot    = bot
        self.db_url = os.getenv("DATABASE_URL")
        self.pool   = None
        bot.add_view(self.RefreshView(self))

    async def cog_load(self):
        self.pool = await asyncpg.create_pool(self.db_url)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS primes (
                    name TEXT PRIMARY KEY,
                    bounty BIGINT
                )
            """)

    async def cog_unload(self):
        await self.pool.close()

    async def fetch_and_upsert(self, url: str):
        """
        Scrape la page GitBook à l'URL fournie et upserte les primes.
        """
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status} pour {url}")
                html = await resp.text()

        pattern = re.compile(r"([^\-<>\r\n]+?)\s*[–-]\s*([\d,]+)\s*B")
        rows = pattern.findall(html)
        if not rows:
            raise RuntimeError("Aucune prime trouvée dans le HTML")

        data = [(name.strip(), int(bounty.replace(",", ""))) for name, bounty in rows]
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO primes(name, bounty)
                VALUES($1, $2)
                ON CONFLICT(name) DO UPDATE
                  SET bounty = EXCLUDED.bounty
                """,
                data
            )

    async def get_all_primes(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT name, bounty FROM primes")

    async def find_prime_for(self, display_name: str):
        for record in await self.get_all_primes():
            if name_matches(display_name, record["name"]):
                return record["name"], record["bounty"]
        return None, None

    async def build_embed(self, guild: discord.Guild) -> discord.Embed:
        # Récupère toutes les primes
        rows       = await self.get_all_primes()
        primes_raw = {r["name"]: r["bounty"] for r in rows}
        entries    = list(primes_raw.keys())

        # Embed de base
        embed = discord.Embed(
            title=f"• Équipage : {guild.name} • ⚓",
            color=0x1abc9c
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Fonction utilitaire pour tronquer à 1024 chars
        def safe_value(text: str) -> str:
            return text if len(text) <= 1024 else text[:1020] + "…"

        # Effectif total
        membre_role = guild.get_role(ROLE_IDS["MEMBRE"])
        total = len(membre_role.members) if membre_role else 0
        embed.add_field(name="Effectif total", value=str(total), inline=False)

        displayed      = set()
        classification = {cat: set() for cat in QUOTAS.keys()}

        # Sections par rôle
        for role_id, emoji_role, label in ROLE_ORDER:
            role = guild.get_role(role_id)
            if not role:
                continue

            lines = []
            for m in role.members:
                if m.id in displayed:
                    continue
                for entry in entries:
                    if name_matches(m.display_name, entry):
                        val = primes_raw[entry]
                        # Catégorie
                        if val >= QUOTAS["Très Dangereux"]:
                            cat = "Très Dangereux"
                        elif val >= QUOTAS["Dangereux"]:
                            cat = "Dangereux"
                        elif val >= QUOTAS["Très Puissant"]:
                            cat = "Très Puissant"
                        elif val >= QUOTAS["Puissant"]:
                            cat = "Puissant"
                        elif val >= QUOTAS["Fort"]:
                            cat = "Fort"
                        else:
                            cat = "Faible"

                        fleet   = get_fleet_emoji(m)
                        mention = f"{fleet}{m.mention}"
                        lines.append(f"- {mention} – 💰 `{val:,} B` – *{EMOJI_FORCE[cat]}*")
                        classification[cat].add(mention)
                        displayed.add(m.id)
                        break

            group_text = "\n".join(lines) or "N/A"
            embed.add_field(
                name=f"{emoji_role} {label}",
                value=safe_value(group_text),
                inline=False
            )
            embed.add_field(name="\u200b", value="__________________", inline=False)

        # Classification globale complète
        categories = [
            "Très Dangereux",
            "Dangereux",
            "Très Puissant",
            "Puissant",
            "Fort",
            "Faible",
        ]
        global_lines = []
        for cat in categories:
            mentions = sorted(classification[cat])
            mention_str = " ".join(mentions) if mentions else "N/A"
            global_lines.append(f"{EMOJI_FORCE[cat]} **{cat}** ({len(mentions)}) : {mention_str}")

        embed.add_field(
            name="📊 Classification Globale",
            value=safe_value("\n".join(global_lines)),
            inline=False
        )

        return embed

    @commands.command(name="primes")
    @commands.has_permissions(administrator=True)
    async def primes(self, ctx: commands.Context):
        """
        !primes — Demande le slug, scrape et affiche l’embed avec bouton Actualiser.
        """
        await ctx.message.delete()
        await ctx.send(
            "Cliquez sur « 🔁 Actualiser » pour saisir l’identifiant de la page primes.",
            view=self.RefreshView(self)
        )

    @commands.command(name="prime")
    @commands.has_role(ROLE_IDS["MEMBRE"])
    async def prime_user(self, ctx: commands.Context):
        """!prime — Affiche votre prime et votre nom RP."""
        await ctx.message.delete()
        entry, bounty = await self.find_prime_for(ctx.author.display_name)
        if bounty is None:
            return await ctx.send("❌ Prime introuvable pour votre Nom RP.", ephemeral=True)
        await ctx.send(
            f"📜 **Nom RP :** {entry}\n"
            f"💰 **Prime :** {bounty:,} B",
            ephemeral=True
        )

    class RefreshView(View):
        def __init__(self, cog: "Prime"):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_primes")
        async def refresh(self, interaction: discord.Interaction, button: Button):
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(
                    "🚫 Réservé aux administrateurs.", ephemeral=True
                )
            await interaction.response.send_modal(SlugModal(self.cog, interaction.message))

    @commands.command(name="clearprimes")
    @commands.has_permissions(administrator=True)
    async def clear_primes(self, ctx: commands.Context):
        """Vide entièrement la table primes."""
        await ctx.message.delete()
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM primes")
        await ctx.send("✅ La table `primes` a été vidée.", delete_after=5)

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
