# cogs/prime.py

import os
import re
import unicodedata
import aiohttp
import asyncpg
import discord
from discord.ext import commands
from discord.ui import View, Button

# URL de base GitBook et suffixe pour la version statique
PRIME_URL = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel/gvednstndtrsdd"
PRINT_SUFFIX = "/print.html"

def _print_url(url: str) -> str:
    """Retourne l’URL pointant vers la version statique /print.html."""
    return url.rstrip("/") + PRINT_SUFFIX

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

# Association rôle de flotte → emoji
FLEET_EMOJIS = {
    1371942480316203018: "<:1reflotte:1372158546531324004>",  # Écarlate
    1371942559894736916: "<:2meflotte:1372158586951696455>",  # Azur
}

# Seuils de classification et emojis correspondants
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
    """Retire accents et caractères non alphanumériques pour comparaison."""
    txt = unicodedata.normalize("NFD", text).lower()
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", "", txt)

def name_matches(dname: str, entry: str) -> bool:
    """Vérifie que chaque mot du display_name est dans le entry scrappé."""
    dn = normalize(dname).split()
    en = normalize(entry).split()
    return all(tok in en for tok in dn)

def get_fleet_emoji(member: discord.Member) -> str:
    """Retourne l'emoji de flotte si le membre a l'un des rôles de flotte."""
    for r in member.roles:
        if r.id in FLEET_EMOJIS:
            return FLEET_EMOJIS[r.id]
    return ""

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

    async def fetch_and_upsert(self):
        """Scrape la page GitBook, extrait les primes, et upserte en base."""
        url = _print_url(PRIME_URL)
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status} en GET {url}")
                html = await resp.text()

        # Extraction de la <ul> sous "Liste des Primes"
        m = re.search(r"Liste des Primes.*?<ul>(.*?)</ul>", html, flags=re.DOTALL)
        if not m:
            raise RuntimeError("Impossible de trouver la liste des primes dans le HTML")
        block = m.group(1)

        # Récupère chaque <li>…</li>
        items = re.findall(r"<li>(.*?)</li>", block, flags=re.DOTALL)
        data = []
        for item in items:
            text = re.sub(r"<.*?>", "", item).strip()
            if "–" in text:
                name_part, bounty_part = map(str.strip, text.split("–", 1))
            else:
                name_part, bounty_part = map(str.strip, text.split("-", 1))
            bounty = int(re.sub(r"[^\d]", "", bounty_part))
            data.append((name_part, bounty))

        # Upsert en base sans suppression préalable
        async with self.pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO primes(name, bounty)
                VALUES($1, $2)
                ON CONFLICT (name) DO UPDATE
                  SET bounty = EXCLUDED.bounty
            """, data)

    async def get_all_primes(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT name, bounty FROM primes")

    async def find_prime_for(self, display_name: str):
        for r in await self.get_all_primes():
            if name_matches(display_name, r["name"]):
                return r["name"], r["bounty"]
        return None, None

    async def build_embed(self, guild: discord.Guild) -> discord.Embed:
        rows       = await self.get_all_primes()
        primes_raw = {r["name"]: r["bounty"] for r in rows}
        entries    = list(primes_raw.keys())

        embed = discord.Embed(
            title=f"• Équipage : {guild.name} • ⚓",
            color=0x1abc9c
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Effectif total
        membre_role = guild.get_role(ROLE_IDS["MEMBRE"])
        total = len(membre_role.members) if membre_role else 0
        embed.add_field(name="Effectif total", value=f"{total} membres", inline=False)

        displayed      = set()
        classification = {cat: [] for cat in EMOJI_FORCE}

        # Parcours des rôles dans l'ordre défini
        for role_id, emoji_role, label in ROLE_ORDER:
            role = guild.get_role(role_id)
            if not role:
                continue

            grp = []
            for m in role.members:
                if m.id in displayed:
                    continue
                for e in entries:
                    if name_matches(m.display_name, e):
                        val = primes_raw[e]
                        # Détermination de la catégorie
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

                        fleet = get_fleet_emoji(m)
                        grp.append((fleet, m, val, EMOJI_FORCE[cat]))
                        classification[cat].append(f"{fleet}{m.mention}")
                        displayed.add(m.id)
                        break

            grp.sort(key=lambda x: x[2], reverse=True)
            value = "\n".join(
                f"- {fleet}{member.mention} – 💰 `{val:,} B` – *{force}*"
                for fleet, member, val, force in grp
            ) or "N/A"
            embed.add_field(name=f"{emoji_role} {label}", value=value, inline=False)
            embed.add_field(name="\u200b", value="__________________", inline=False)

        # Classification globale synthétisée
        lines = []
        for cat in ("Puissant", "Fort", "Faible"):
            em       = EMOJI_FORCE[cat]
            mentions = " ".join(classification[cat]) or "N/A"
            lines.append(f"{em} **{cat}** ({len(classification[cat])}) : {mentions}")
        embed.add_field(name="📊 Classification Globale", value="\n".join(lines), inline=False)

        return embed

    @commands.command(name="primes")
    @commands.has_permissions(administrator=True)
    async def primes(self, ctx: commands.Context):
        """!primes — met à jour la DB puis affiche l’embed avec bouton Actualiser."""
        await ctx.message.delete()
        loading = await ctx.send("⏳ Mise à jour des primes…")
        try:
            await self.fetch_and_upsert()
            embed = await self.build_embed(ctx.guild)
            await loading.delete()
            await ctx.send(embed=embed, view=self.RefreshView(self))
        except Exception as e:
            await loading.edit(content=f"❌ Échec mise à jour : {e}")

    @commands.command(name="prime")
    @commands.has_role(ROLE_IDS["MEMBRE"])
    async def prime_user(self, ctx: commands.Context):
        """!prime — affiche votre prime + votre Nom RP."""
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

        @discord.ui.button(
            label="🔁 Actualiser",
            style=discord.ButtonStyle.secondary,
            custom_id="refresh_primes"
        )
        async def refresh(self, interaction: discord.Interaction, button: Button):
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(
                    "🚫 Réservé aux administrateurs.", ephemeral=True
                )

            # Message éphémère de chargement
            loading = await interaction.response.send_message("⏳ Actualisation…", ephemeral=True)
            try:
                await self.cog.fetch_and_upsert()
                new_embed = await self.cog.build_embed(interaction.guild)
                await interaction.message.edit(embed=new_embed, view=self)
                await interaction.followup.edit_message(loading.id, content="✅ Primes actualisées.")
            except Exception as e:
                await interaction.followup.edit_message(loading.id, content=f"❌ Erreur : {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
